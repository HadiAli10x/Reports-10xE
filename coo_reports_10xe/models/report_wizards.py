from collections import defaultdict
from datetime import timedelta

from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError


class CooReportBaseMixin(models.AbstractModel):
    _name = "coo.report.base.mixin"
    _description = "COO Report Common Helpers"
    _inherit = "coo.report.xlsx.mixin"

    def _active_employee_domain(self):
        domain = [("active", "=", True)]
        Employee = self.env["hr.employee"]
        if "x_active_inactive" in Employee._fields:
            domain.append(("x_active_inactive", "=", "active"))
        return domain

    def _is_active_employee(self, employee):
        if not employee or not employee.active:
            return False
        return (
            "x_active_inactive" not in employee._fields
            or employee.x_active_inactive == "active"
        )

    def _require_active_employee(self, employee):
        if not self._is_active_employee(employee):
            raise ValidationError(_("Only active employees can be included in this report."))

    def _employee_code(self, employee):
        return employee.x_code if "x_code" in employee._fields else ""

    def _employee_designation(self, employee):
        for field_name in ("x_designation", "job_title"):
            if field_name in employee._fields and employee[field_name]:
                value = employee[field_name]
                return value.display_name if hasattr(value, "display_name") else value
        return ""

    def _employee_department(self, employee):
        if employee.department_id:
            return employee.department_id.display_name
        for field_name in ("x_department_name", "x_depratment", "x_department"):
            if field_name in employee._fields and employee[field_name]:
                value = employee[field_name]
                return value.display_name if hasattr(value, "display_name") else value
        return ""

    def _employee_business_line(self, employee):
        for field_name in ("x_group", "x_business_line", "x_studio_business_line"):
            if field_name in employee._fields and employee[field_name]:
                value = employee[field_name]
                return value.display_name if hasattr(value, "display_name") else value
        return ""

    def _selection_label(self, record, field_name):
        value = record[field_name]
        if not value:
            return ""
        field = record._fields[field_name]
        selection = field.selection or []
        if isinstance(selection, str):
            selection = getattr(record, selection)()
        elif callable(selection):
            selection = selection(record)
        return dict(selection or []).get(value, value)

    def _date_text(self, value):
        return fields.Date.to_string(value) if value else ""


class CooOrgChartReportWizard(models.TransientModel):
    _name = "coo.org.chart.report.wizard"
    _description = "COO Organization Chart Report"
    _inherit = "coo.report.base.mixin"

    root_employee_id = fields.Many2one(
        "hr.employee",
        string="Start From",
        domain="[('active', '=', True), ('x_active_inactive', '=', 'active')]",
        help="Leave empty to export the complete active organization.",
    )
    department_id = fields.Many2one("hr.department", string="Department")

    def action_export_xlsx(self):
        self.ensure_one()
        self._check_coo_report_access()
        if self.root_employee_id:
            self._require_active_employee(self.root_employee_id)

        employees = self.env["hr.employee"].sudo().search(
            self._active_employee_domain(), order="name"
        )
        if self.root_employee_id:
            root = self.root_employee_id
            employees = employees.filtered(
                lambda employee: employee == root or self._is_descendant_of(employee, root)
            )
        if self.department_id:
            employees = employees.filtered(
                lambda employee: employee.department_id == self.department_id
            )

        employee_ids = set(employees.ids)
        ordered = sorted(employees, key=lambda employee: self._hierarchy_path(employee, employee_ids))
        rows = []
        for employee in ordered:
            level = self._hierarchy_level(employee, employee_ids)
            rows.append([
                level,
                f"{'    ' * level}{employee.name or ''}",
                self._employee_code(employee),
                self._employee_designation(employee),
                self._employee_department(employee),
                employee.parent_id.name or "",
                employee.work_email or employee.user_id.email or "",
                len(employee.child_ids.filtered(self._is_active_employee)),
            ])

        title = "Active Organization Chart"
        if self.root_employee_id:
            title += f" - {self.root_employee_id.name}"
        if self.department_id:
            title += f" - {self.department_id.display_name}"
        return self._download_xlsx("active_organization_chart.xlsx", [{
            "name": "Organization Chart",
            "title": title,
            "note": "Hierarchy is based on the employee Manager field. Only active employees are included.",
            "headers": [
                "Level", "Employee", "Employee Code", "Designation", "Department",
                "Reports To", "Work Email", "Active Direct Reports",
            ],
            "rows": rows,
            "widths": [10, 38, 16, 28, 24, 30, 34, 20],
        }])

    def _is_descendant_of(self, employee, root):
        seen = set()
        current = employee.parent_id
        while current and current.id not in seen:
            if current == root:
                return True
            seen.add(current.id)
            current = current.parent_id
        return False

    def _hierarchy_level(self, employee, employee_ids):
        level = 0
        seen = set()
        current = employee.parent_id
        while current and current.id in employee_ids and current.id not in seen:
            seen.add(current.id)
            level += 1
            current = current.parent_id
        return level

    def _hierarchy_path(self, employee, employee_ids):
        path = []
        seen = set()
        current = employee
        while current and current.id in employee_ids and current.id not in seen:
            seen.add(current.id)
            path.append((current.name or "").casefold())
            current = current.parent_id
        return tuple(reversed(path))


class CooEmployeeExperienceReportWizard(models.TransientModel):
    _name = "coo.employee.experience.report.wizard"
    _description = "COO Single Employee Experience Report"
    _inherit = "coo.report.base.mixin"

    employee_id = fields.Many2one(
        "hr.employee",
        string="Active Employee",
        required=True,
        domain="[('active', '=', True), ('x_active_inactive', '=', 'active')]",
    )

    def action_export_xlsx(self):
        self.ensure_one()
        self._check_coo_report_access()
        employee = self.employee_id.sudo()
        self._require_active_employee(employee)

        today = fields.Date.context_today(self)
        joining_date = employee.x_joining_date if "x_joining_date" in employee._fields else False
        computed_service = (
            round(max((today - joining_date).days, 0) / 365.25, 2)
            if joining_date
            else 0.0
        )
        recorded_service = (
            employee.x_years_of_service
            if "x_years_of_service" in employee._fields
            else 0.0
        ) or 0.0
        prior_experience = (
            employee.x_prior_work_experience
            if "x_prior_work_experience" in employee._fields
            else 0.0
        ) or 0.0
        service = computed_service if joining_date else recorded_service

        summary_rows = [
            ["Employee", employee.name or ""],
            ["Employee Code", self._employee_code(employee)],
            ["Work Email", employee.work_email or employee.user_id.email or ""],
            ["Designation", self._employee_designation(employee)],
            ["Department", self._employee_department(employee)],
            ["Manager", employee.parent_id.name or ""],
            ["Joining Date", self._date_text(joining_date)],
            ["Prior Work Experience (years)", round(prior_experience, 2)],
            ["Service at 10xE (years)", round(service, 2)],
            ["Total Experience (years)", round(prior_experience + service, 2)],
        ]

        history_rows = []
        for history in self._employee_history(employee):
            history_rows.append([
                history.review_period or "",
                self._date_text(history.review_cycle),
                history.designation or "",
                history.experience or "",
                history.manager_id.name or "",
                history.final_manager_id.name or "",
                history.department_id.display_name or "",
                history.score or 0.0,
                history.time_in_title or "",
                history.time_in_management or "",
                self._selection_label(history, "is_promoted"),
            ])

        filename = f"employee_experience_{self._safe_filename(employee.name)}.xlsx"
        return self._download_xlsx(filename, [
            {
                "name": "Experience Summary",
                "title": f"Employee Experience - {employee.name}",
                "note": "This report can only be generated for an active employee.",
                "headers": ["Field", "Value"],
                "rows": summary_rows,
                "widths": [34, 48],
            },
            {
                "name": "Appraisal History",
                "title": f"Experience and Role History - {employee.name}",
                "note": "Historical snapshots come from the Employee Appraisal module.",
                "headers": [
                    "Review Period", "Review Date", "Designation", "Experience",
                    "Manager", "Manager After Review", "Department", "Score",
                    "Time in Title", "Time in Management", "Promoted",
                ],
                "rows": history_rows,
                "widths": [20, 14, 28, 16, 28, 28, 24, 12, 18, 20, 14],
            },
        ])

    def _employee_history(self, employee):
        History = self.env["employee.historical.data"].sudo()
        records = History.search([("employee_id", "=", employee.id)], order="review_cycle desc, id desc")
        if records:
            return records
        fallback = []
        if self._employee_code(employee):
            fallback.append(("employee_code", "=ilike", self._employee_code(employee)))
        email = employee.work_email or employee.user_id.email
        if email:
            fallback.append(("email", "=ilike", email))
        if employee.name:
            fallback.append(("employee_name", "=ilike", employee.name))
        records = History
        for condition in fallback:
            records |= History.search([condition])
        return records.sorted(key=lambda row: (row.review_cycle or fields.Date.from_string("1900-01-01"), row.id), reverse=True)

    def _safe_filename(self, value):
        return "_".join((value or "employee").lower().split())


class CooManagerDirectReportsWizard(models.TransientModel):
    _name = "coo.manager.direct.reports.wizard"
    _description = "COO Managers and Direct Reports Report"
    _inherit = "coo.report.base.mixin"

    manager_id = fields.Many2one(
        "hr.employee",
        string="Manager",
        domain="[('active', '=', True), ('x_active_inactive', '=', 'active')]",
        help="Leave empty to export every active manager and their active direct reports.",
    )

    def action_export_xlsx(self):
        self.ensure_one()
        self._check_coo_report_access()
        if self.manager_id:
            self._require_active_employee(self.manager_id)

        employee_domain = self._active_employee_domain()
        if self.manager_id:
            employee_domain.append(("parent_id", "=", self.manager_id.id))
        else:
            employee_domain.append(("parent_id", "!=", False))
        reports = self.env["hr.employee"].sudo().search(employee_domain, order="parent_id, name")
        reports = reports.filtered(lambda employee: self._is_active_employee(employee.parent_id))

        rows = [[
            report.parent_id.name or "",
            report.parent_id.work_email or report.parent_id.user_id.email or "",
            self._employee_designation(report.parent_id),
            report.name or "",
            self._employee_code(report),
            report.work_email or report.user_id.email or "",
            self._employee_designation(report),
            self._employee_department(report),
            self._date_text(report.x_joining_date if "x_joining_date" in report._fields else False),
        ] for report in reports]

        grouped = defaultdict(list)
        for report in reports:
            grouped[report.parent_id].append(report)
        summary_rows = [[
            manager.name or "",
            manager.work_email or manager.user_id.email or "",
            self._employee_designation(manager),
            self._employee_department(manager),
            len(direct_reports),
        ] for manager, direct_reports in sorted(grouped.items(), key=lambda item: (item[0].name or "").casefold())]

        suffix = f"_{self._safe_filename(self.manager_id.name)}" if self.manager_id else ""
        return self._download_xlsx(f"active_manager_direct_reports{suffix}.xlsx", [
            {
                "name": "Direct Reports",
                "title": "Active Managers and Active Direct Reports",
                "note": "Both the manager and direct report must be active. Indirect reports are not included.",
                "headers": [
                    "Manager", "Manager Email", "Manager Designation", "Direct Report",
                    "Employee Code", "Employee Email", "Employee Designation", "Department", "Joining Date",
                ],
                "rows": rows,
                "widths": [30, 34, 28, 30, 16, 34, 28, 24, 14],
            },
            {
                "name": "Manager Summary",
                "title": "Active Direct Report Counts by Manager",
                "headers": ["Manager", "Email", "Designation", "Department", "Active Direct Reports"],
                "rows": summary_rows,
                "widths": [30, 34, 28, 24, 22],
            },
        ])

    def _safe_filename(self, value):
        return "_".join((value or "manager").lower().split())


class CooAssignmentsReportWizard(models.TransientModel):
    _name = "coo.assignments.report.wizard"
    _description = "COO Assignments Report"
    _inherit = "coo.report.base.mixin"

    start_date = fields.Date(
        string="From",
        required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1),
    )
    end_date = fields.Date(string="To", required=True, default=fields.Date.context_today)
    include_drafts = fields.Boolean(string="Include Draft Allocations", default=False)
    active_employees_only = fields.Boolean(
        string="Active Employees Only",
        default=False,
        help="Leave disabled to preserve historical assignments for former employees.",
    )

    def action_export_xlsx(self):
        self.ensure_one()
        self._check_coo_report_access()
        self._validate_date_range()
        domain = [
            ("assignment_start_date", "<=", self.end_date),
            "|", ("assignment_offboard_date", "=", False),
            ("assignment_offboard_date", ">=", self.start_date),
        ]
        if not self.include_drafts:
            domain.append(("state", "=", "allocated"))
        if self.active_employees_only:
            domain.extend([
                ("employee_id.active", "=", True),
                ("employee_id.x_active_inactive", "=", "active"),
            ])
        allocations = self.env["daily.assignment.allocation"].sudo().with_context(active_test=False).search(
            domain, order="assignment_type_id, employee_id, assignment_start_date"
        )
        rows = []
        counts = defaultdict(lambda: {"employees": set(), "allocations": 0})
        for allocation in allocations:
            assignment = allocation.assignment_type_id
            employee = allocation.employee_id
            scope = self._selection_label(assignment, "assignment_scope")
            rows.append([
                assignment.name or "",
                assignment.code or "",
                scope,
                assignment.business_line or "",
                employee.name or "",
                self._employee_code(employee),
                self._employee_designation(employee),
                self._employee_department(employee),
                employee.parent_id.name or "",
                self._date_text(allocation.assignment_start_date),
                self._date_text(allocation.assignment_offboard_date),
                self._selection_label(allocation, "state"),
                "Yes" if allocation._is_current_on(fields.Date.context_today(self)) else "No",
                "Active" if self._is_active_employee(employee) else "Inactive",
            ])
            key = assignment.name or "Unspecified"
            counts[key]["employees"].add(employee.id)
            counts[key]["allocations"] += 1

        summary_rows = [[name, values["allocations"], len(values["employees"])] for name, values in sorted(counts.items())]
        return self._download_xlsx(
            f"assignments_{self.start_date}_{self.end_date}.xlsx",
            [
                {
                    "name": "Assignments",
                    "title": f"Assignment Allocations - {self.start_date} to {self.end_date}",
                    "note": "The report includes allocations that overlap the selected period.",
                    "headers": [
                        "Assignment", "Code", "Scope", "Business Line", "Employee", "Employee Code",
                        "Designation", "Department", "Manager", "Start Date", "End Date", "State",
                        "Current Today", "Employee Status",
                    ],
                    "rows": rows,
                    "widths": [34, 12, 16, 22, 30, 16, 28, 24, 30, 14, 14, 14, 16, 18],
                },
                {
                    "name": "Assignment Summary",
                    "title": "Assignment Summary",
                    "headers": ["Assignment", "Allocations", "Unique Employees"],
                    "rows": summary_rows,
                    "widths": [36, 16, 20],
                },
            ],
        )

    def _validate_date_range(self):
        if self.end_date < self.start_date:
            raise ValidationError(_("To date cannot be before From date."))


class CooUtilizationReportWizard(models.TransientModel):
    _name = "coo.utilization.report.wizard"
    _description = "COO Employee Utilization Report"
    _inherit = "coo.report.base.mixin"

    start_date = fields.Date(
        string="From",
        required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1),
    )
    end_date = fields.Date(string="To", required=True, default=fields.Date.context_today)
    department_id = fields.Many2one("hr.department", string="Department")

    def action_export_xlsx(self):
        self.ensure_one()
        self._check_coo_report_access()
        if self.end_date < self.start_date:
            raise ValidationError(_("To date cannot be before From date."))
        workdays = self._workdays(self.start_date, self.end_date)
        if not workdays:
            raise UserError(_("The selected period has no weekdays."))

        domain = self._active_employee_domain()
        if self.department_id:
            domain.append(("department_id", "=", self.department_id.id))
        employees = self.env["hr.employee"].sudo().search(domain, order="department_id, name")
        entries = self.env["daily.assignment.entry"].sudo().search([
            ("employee_id", "in", employees.ids),
            ("state", "=", "submitted"),
            ("start_date", "<=", self.end_date),
            ("end_date", ">=", self.start_date),
        ], order="employee_id, start_date")
        entries_by_employee = defaultdict(list)
        for entry in entries:
            entries_by_employee[entry.employee_id.id].append(entry)

        report_rows = []
        department_totals = defaultdict(lambda: {"count": 0, "client": 0.0, "recorded": 0.0})
        for employee in employees:
            metrics = self._utilization_metrics(entries_by_employee[employee.id], workdays)
            department = self._employee_department(employee) or "No Department"
            report_rows.append([
                employee.name or "",
                self._employee_code(employee),
                self._employee_designation(employee),
                department,
                self._employee_business_line(employee),
                employee.parent_id.name or "",
                len(workdays),
                metrics["reported_days"],
                round(metrics["recorded_percent"], 2),
                round(metrics["client_percent"], 2),
                round(metrics["internal_percent"], 2),
                round(metrics["unreported_percent"], 2),
                ", ".join(sorted(metrics["assignments"], key=str.casefold)),
            ])
            department_totals[department]["count"] += 1
            department_totals[department]["client"] += metrics["client_percent"]
            department_totals[department]["recorded"] += metrics["recorded_percent"]

        summary_rows = []
        for department, values in sorted(department_totals.items()):
            count = values["count"]
            summary_rows.append([
                department,
                count,
                round(values["client"] / count, 2) if count else 0.0,
                round(values["recorded"] / count, 2) if count else 0.0,
            ])

        filename = f"utilization_{self.start_date}_{self.end_date}.xlsx"
        return self._download_xlsx(filename, [
            {
                "name": "Employee Utilization",
                "title": f"Employee Utilization - {self.start_date} to {self.end_date}",
                "note": "Active employees only. Percentages use weekdays and submitted Daily Assignment entries; approved leave and public holidays are not subtracted.",
                "headers": [
                    "Employee", "Employee Code", "Designation", "Department", "Business Line", "Manager",
                    "Expected Weekdays", "Reported Weekdays", "Recorded %", "Client Utilization %",
                    "Internal %", "Unreported %", "Assignments",
                ],
                "rows": report_rows,
                "widths": [30, 16, 28, 24, 22, 30, 18, 18, 15, 20, 14, 16, 46],
            },
            {
                "name": "Department Summary",
                "title": "Average Utilization by Department",
                "headers": ["Department", "Active Employees", "Average Client Utilization %", "Average Recorded %"],
                "rows": summary_rows,
                "widths": [28, 18, 30, 22],
            },
            {
                "name": "Methodology",
                "title": "Utilization Methodology",
                "headers": ["Metric", "Definition"],
                "rows": [
                    ["Expected Weekdays", "Monday through Friday in the selected period."],
                    ["Recorded %", "Submitted assignment-entry weekday coverage divided by expected weekdays."],
                    ["Client Utilization %", "Client assignment percentage-weighted weekdays divided by expected weekdays."],
                    ["Internal %", "Internal assignment percentage-weighted weekdays divided by expected weekdays."],
                    ["Unreported %", "100% minus recorded assignment capacity, never below zero."],
                ],
                "widths": [30, 86],
            },
        ])

    def _workdays(self, start_date, end_date):
        days = []
        current = start_date
        while current <= end_date:
            if current.weekday() < 5:
                days.append(current)
            current += timedelta(days=1)
        return days

    def _utilization_metrics(self, entries, workdays):
        expected = len(workdays)
        workday_set = set(workdays)
        covered_days = set()
        client_fte_days = 0.0
        internal_fte_days = 0.0
        assignments = set()
        for entry in entries:
            overlap = {
                day for day in workday_set
                if entry.start_date <= day <= entry.end_date
            }
            if not overlap:
                continue
            covered_days.update(overlap)
            for assignment_field, percentage_field in (
                ("assignment_type_id", "assignment_1_percentage"),
                ("assignment_type_2_id", "assignment_2_percentage"),
                ("assignment_type_3_id", "assignment_3_percentage"),
            ):
                assignment = entry[assignment_field]
                if not assignment:
                    continue
                assignments.add(assignment.name or "Unspecified")
                fte_days = len(overlap) * max(entry[percentage_field] or 0.0, 0.0) / 100.0
                if assignment.assignment_scope == "client":
                    client_fte_days += fte_days
                else:
                    internal_fte_days += fte_days
        recorded_percent = min((client_fte_days + internal_fte_days) / expected * 100.0, 100.0)
        return {
            "reported_days": len(covered_days),
            "recorded_percent": recorded_percent,
            "client_percent": min(client_fte_days / expected * 100.0, 100.0),
            "internal_percent": min(internal_fte_days / expected * 100.0, 100.0),
            "unreported_percent": max(100.0 - recorded_percent, 0.0),
            "assignments": assignments,
        }
