import base64
import io

from odoo import api, models
from odoo.exceptions import UserError


def _is_coo_report_user(record):
    return record.env.su or record.env.user.has_group(
        "coo_reports_10xe.group_coo_reports_ayesha"
    )


class DailyAssignmentEngineeringReportWizard(models.TransientModel):
    _inherit = "daily.assignment.engineering.report.wizard"

    def _check_report_access(self):
        if _is_coo_report_user(self):
            return None
        return super()._check_report_access()


class DailyAssignmentEngineeringClassificationWizard(models.TransientModel):
    _inherit = "daily.assignment.engineering.classification.wizard"

    def _check_report_access(self):
        if _is_coo_report_user(self):
            return None
        return super()._check_report_access()


class DailyAssignmentEngineeringWeeklyAreaWizard(models.TransientModel):
    _inherit = "daily.assignment.engineering.weekly.area.wizard"

    def _check_report_access(self):
        if _is_coo_report_user(self):
            return None
        return super()._check_report_access()


class DailyAssignmentCompletenessWizard(models.TransientModel):
    _inherit = "daily.assignment.completeness.wizard"

    def action_generate_report(self):
        if not _is_coo_report_user(self):
            return super().action_generate_report()

        self.ensure_one()
        if self.end_date < self.start_date:
            raise UserError("End Date cannot be before Start Date.")
        report_dates = self._date_range(self.start_date, self.end_date)
        if not report_dates:
            raise UserError("No dates found for the selected range.")
        employees = self._get_active_employees()
        sheet_statuses = self._fetch_sheet_statuses(report_dates)
        assignment_dates = self._get_assignment_dates(
            employees, self.start_date, self.end_date
        )
        content = self._build_xlsx_report(
            employees, report_dates, assignment_dates, sheet_statuses
        )
        filename = f"assignment_completeness_{self.start_date}_{self.end_date}.xlsx"
        attachment = self.env["ir.attachment"].sudo().create({
            "name": filename,
            "type": "binary",
            "datas": base64.b64encode(content),
            "res_model": self._name,
            "res_id": self.id,
            "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        })
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
        }


class DirectorNeedsImprovementCCReportWizard(models.TransientModel):
    _inherit = "director.needs.improvement.cc.report.wizard"

    def _check_director_access(self):
        if _is_coo_report_user(self):
            return None
        return super()._check_director_access()


class DirectorCCAssessmentSummaryReportWizard(models.TransientModel):
    _inherit = "director.cc.assessment.summary.report.wizard"

    def _check_director_access(self):
        if _is_coo_report_user(self):
            return None
        return super()._check_director_access()


class ManagerCCMisalignmentReportWizard(models.TransientModel):
    _inherit = "manager.cc.misalignment.report.wizard"

    def _check_director_access(self):
        if _is_coo_report_user(self):
            return None
        return super()._check_director_access()


class DirectorCalibrationReportWizard(models.TransientModel):
    _inherit = "director.calibration.report.wizard"

    def action_download_excel(self):
        if not _is_coo_report_user(self):
            return super().action_download_excel()

        self.ensure_one()
        try:
            import openpyxl
        except ImportError as exc:
            raise UserError("openpyxl is required. Please install it.") from exc

        workbook = openpyxl.Workbook()
        worksheet = workbook.active
        count = self._build_sheet(worksheet)
        if count == 0:
            raise UserError("No appraisal or calibration records found for this cycle.")

        output = io.BytesIO()
        workbook.save(output)
        filename = f"Director_Calibration_Report_{self.cycle_id.name}.xlsx"
        attachment = self.env["ir.attachment"].sudo().create({
            "name": filename,
            "type": "binary",
            "datas": base64.b64encode(output.getvalue()),
            "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "res_model": self._name,
            "res_id": self.id,
        })
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "new",
        }


class TimeOffBalanceWizard(models.TransientModel):
    _inherit = "time.off.balance.wizard"

    @api.model
    def _check_group_access(self):
        if _is_coo_report_user(self):
            return None
        return super()._check_group_access()

    @api.model
    def _allowed_employee_domain(self):
        if not _is_coo_report_user(self):
            return super()._allowed_employee_domain()
        company_ids = self.env.companies.ids or [self.env.company.id]
        return [
            ("active", "=", True),
            ("x_active_inactive", "!=", "inactive"),
            ("company_id", "in", company_ids),
        ]

    @api.depends_context("uid")
    def _compute_scope(self):
        if not _is_coo_report_user(self):
            return super()._compute_scope()
        for wizard in self:
            wizard.scope = "officer"
