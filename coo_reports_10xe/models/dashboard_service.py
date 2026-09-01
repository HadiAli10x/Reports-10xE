from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


class CooReportDashboardService(models.TransientModel):
    _name = "coo.report.dashboard.service"
    _description = "COO Report Dashboard Service"

    def _check_access(self):
        if not (
            self.env.su
            or self.env.user.has_group("coo_reports_10xe.group_coo_reports_ayesha")
        ):
            raise AccessError(_("You are not allowed to access the COO reporting hub."))

    def _helper(self):
        return self.env["coo.org.chart.report.wizard"].new({})

    def _active_employees(self):
        helper = self._helper()
        return self.env["hr.employee"].sudo().search(
            helper._active_employee_domain(), order="name"
        )

    def _options(self, employees):
        return [{"id": employee.id, "name": employee.name or ""} for employee in employees]

    @api.model
    def get_employee_report(self, report_key, selected_id=False):
        self._check_access()
        handlers = {
            "organization": self._organization_report,
            "experience": self._experience_report,
            "direct_reports": self._direct_reports_report,
        }
        if report_key not in handlers:
            raise ValidationError(_("Unknown employee report."))
        return handlers[report_key](selected_id)

    @api.model
    def export_employee_report(self, report_key, selected_id=False):
        self._check_access()
        if report_key == "organization":
            wizard = self.env["coo.org.chart.report.wizard"].create({})
        elif report_key == "experience":
            if not selected_id:
                raise ValidationError(_("Select an active employee first."))
            wizard = self.env["coo.employee.experience.report.wizard"].create({
                "employee_id": selected_id,
            })
        elif report_key == "direct_reports":
            wizard = self.env["coo.manager.direct.reports.wizard"].create({
                "manager_id": selected_id or False,
            })
        else:
            raise ValidationError(_("Unknown employee report."))
        return wizard.action_export_xlsx()

    @api.model
    def export_utilization(self):
        self._check_access()
        wizard = self.env["coo.utilization.report.wizard"].create({})
        return wizard.action_export_xlsx()

    def _organization_report(self, selected_id=False):
        helper = self._helper()
        employees = self._active_employees()
        employee_ids = set(employees.ids)
        ordered = sorted(
            employees,
            key=lambda employee: helper._hierarchy_path(employee, employee_ids),
        )
        rows = []
        for employee in ordered:
            level = helper._hierarchy_level(employee, employee_ids)
            rows.append({
                "employee": f"{'  ' * level}{employee.name or ''}",
                "code": helper._employee_code(employee),
                "designation": helper._employee_designation(employee),
                "department": helper._employee_department(employee),
                "manager": employee.parent_id.name or "",
                "email": employee.work_email or employee.user_id.email or "",
                "direct_reports": len(employee.child_ids.filtered(helper._is_active_employee)),
            })
        return {
            "title": "Organization Chart",
            "description": "All active employees and their reporting lines.",
            "selector": False,
            "selected_id": False,
            "options": [],
            "sections": [{
                "title": "Active organization",
                "columns": [
                    {"key": "employee", "label": "Employee"},
                    {"key": "code", "label": "Code"},
                    {"key": "designation", "label": "Designation"},
                    {"key": "department", "label": "Department"},
                    {"key": "manager", "label": "Reports To"},
                    {"key": "email", "label": "Work Email"},
                    {"key": "direct_reports", "label": "Direct Reports"},
                ],
                "rows": rows,
            }],
        }

    def _experience_report(self, selected_id=False):
        helper = self.env["coo.employee.experience.report.wizard"].new({})
        employees = self._active_employees()
        result = {
            "title": "Single Employee Experience",
            "description": "Current employee details and appraisal history.",
            "selector": "employee",
            "selected_id": selected_id or False,
            "options": self._options(employees),
            "sections": [],
        }
        if not selected_id:
            return result

        employee = employees.filtered(lambda record: record.id == int(selected_id))[:1]
        if not employee:
            raise ValidationError(_("Select a valid active employee."))
        helper._require_active_employee(employee)

        today = fields.Date.context_today(self)
        joining_date = employee.x_joining_date if "x_joining_date" in employee._fields else False
        computed_service = (
            round(max((today - joining_date).days, 0) / 365.25, 2)
            if joining_date else 0.0
        )
        recorded_service = (
            employee.x_years_of_service
            if "x_years_of_service" in employee._fields else 0.0
        ) or 0.0
        prior_experience = (
            employee.x_prior_work_experience
            if "x_prior_work_experience" in employee._fields else 0.0
        ) or 0.0
        service = computed_service if joining_date else recorded_service

        summary_rows = [
            {"field": "Employee", "value": employee.name or ""},
            {"field": "Employee Code", "value": helper._employee_code(employee)},
            {"field": "Work Email", "value": employee.work_email or employee.user_id.email or ""},
            {"field": "Designation", "value": helper._employee_designation(employee)},
            {"field": "Department", "value": helper._employee_department(employee)},
            {"field": "Manager", "value": employee.parent_id.name or ""},
            {"field": "Joining Date", "value": helper._date_text(joining_date)},
            {"field": "Prior Work Experience (years)", "value": round(prior_experience, 2)},
            {"field": "Service at 10xE (years)", "value": round(service, 2)},
            {"field": "Total Experience (years)", "value": round(prior_experience + service, 2)},
        ]
        history_rows = []
        for history in helper._employee_history(employee):
            history_rows.append({
                "period": history.review_period or "",
                "date": helper._date_text(history.review_cycle),
                "designation": history.designation or "",
                "experience": history.experience or "",
                "manager": history.manager_id.name or "",
                "new_manager": history.final_manager_id.name or "",
                "department": history.department_id.display_name or "",
                "score": history.score or 0.0,
                "time_in_title": history.time_in_title or "",
                "time_in_management": history.time_in_management or "",
                "promoted": helper._selection_label(history, "is_promoted"),
            })
        result["sections"] = [
            {
                "title": "Current details",
                "columns": [
                    {"key": "field", "label": "Field"},
                    {"key": "value", "label": "Value"},
                ],
                "rows": summary_rows,
            },
            {
                "title": "Appraisal history",
                "columns": [
                    {"key": "period", "label": "Review Period"},
                    {"key": "date", "label": "Review Date"},
                    {"key": "designation", "label": "Designation"},
                    {"key": "experience", "label": "Experience"},
                    {"key": "manager", "label": "Manager"},
                    {"key": "new_manager", "label": "Manager After Review"},
                    {"key": "department", "label": "Department"},
                    {"key": "score", "label": "Score"},
                    {"key": "time_in_title", "label": "Time in Title"},
                    {"key": "time_in_management", "label": "Time in Management"},
                    {"key": "promoted", "label": "Promoted"},
                ],
                "rows": history_rows,
            },
        ]
        return result

    def _direct_reports_report(self, selected_id=False):
        helper = self.env["coo.manager.direct.reports.wizard"].new({})
        employees = self._active_employees()
        active_ids = set(employees.ids)
        managers = employees.filtered(
            lambda employee: any(child.id in active_ids for child in employee.child_ids)
        ).sorted(key=lambda employee: (employee.name or "").casefold())

        if selected_id:
            manager = managers.filtered(lambda record: record.id == int(selected_id))[:1]
            if not manager:
                raise ValidationError(_("Select a valid active manager."))
            reports = employees.filtered(lambda employee: employee.parent_id == manager)
        else:
            reports = employees.filtered(
                lambda employee: employee.parent_id and employee.parent_id.id in active_ids
            )
        reports = reports.sorted(
            key=lambda employee: (
                (employee.parent_id.name or "").casefold(),
                (employee.name or "").casefold(),
            )
        )

        detail_rows = [{
            "manager": report.parent_id.name or "",
            "manager_email": report.parent_id.work_email or report.parent_id.user_id.email or "",
            "manager_designation": helper._employee_designation(report.parent_id),
            "employee": report.name or "",
            "code": helper._employee_code(report),
            "email": report.work_email or report.user_id.email or "",
            "designation": helper._employee_designation(report),
            "department": helper._employee_department(report),
            "joining_date": helper._date_text(
                report.x_joining_date if "x_joining_date" in report._fields else False
            ),
        } for report in reports]

        grouped = defaultdict(list)
        for report in reports:
            grouped[report.parent_id].append(report)
        summary_rows = [{
            "manager": manager.name or "",
            "designation": helper._employee_designation(manager),
            "department": helper._employee_department(manager),
            "count": len(direct_reports),
        } for manager, direct_reports in sorted(
            grouped.items(), key=lambda item: (item[0].name or "").casefold()
        )]

        return {
            "title": "Managers' Direct Reports",
            "description": "Active managers and their active direct reports.",
            "selector": "manager",
            "selected_id": selected_id or False,
            "options": self._options(managers),
            "sections": [
                {
                    "title": "Direct reports",
                    "columns": [
                        {"key": "manager", "label": "Manager"},
                        {"key": "manager_email", "label": "Manager Email"},
                        {"key": "manager_designation", "label": "Manager Designation"},
                        {"key": "employee", "label": "Direct Report"},
                        {"key": "code", "label": "Code"},
                        {"key": "email", "label": "Work Email"},
                        {"key": "designation", "label": "Designation"},
                        {"key": "department", "label": "Department"},
                        {"key": "joining_date", "label": "Joining Date"},
                    ],
                    "rows": detail_rows,
                },
                {
                    "title": "Manager summary",
                    "columns": [
                        {"key": "manager", "label": "Manager"},
                        {"key": "designation", "label": "Designation"},
                        {"key": "department", "label": "Department"},
                        {"key": "count", "label": "Active Direct Reports"},
                    ],
                    "rows": summary_rows,
                },
            ],
        }
