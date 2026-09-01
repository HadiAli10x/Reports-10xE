/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";


const REPORT_MODULES = [
    {
        key: "employees",
        name: "Employees",
        description: "Active employees, reporting lines, and experience.",
        reports: [
            { name: "Organization Chart", employeeKey: "organization", format: "XLSX" },
            { name: "Single Employee Experience", employeeKey: "experience", format: "XLSX" },
            { name: "Managers' Direct Reports", employeeKey: "direct_reports", format: "XLSX" },
        ],
    },
    {
        key: "assignments",
        name: "Daily Assignment Tracker",
        description: "Assignments, completion, classification, and utilization.",
        reports: [
            { name: "Assignments Report", format: "XLSX", action: "coo_reports_10xe.action_coo_assignments_report" },
            { name: "Utilization", format: "All active employees / XLSX", quickExport: true },
            { name: "Assignment Completeness", format: "XLSX", action: "daily_assignment_tracker.action_daily_assignment_completeness_report" },
            { name: "Engineering Assignment Activity", format: "XLSX", action: "daily_assignment_tracker.action_daily_assignment_engineering_report" },
            { name: "Engineering Billing Classification", format: "XLSX", action: "daily_assignment_tracker.action_daily_assignment_engineering_classification_report" },
            { name: "Engineering Weekly Area", format: "XLSX", action: "daily_assignment_tracker.action_daily_assignment_engineering_weekly_area_report" },
        ],
    },
    {
        key: "appraisal",
        name: "Performance Appraisal",
        description: "The same appraisal reports and filters used in the appraisal module.",
        reports: [
            { name: "Peer Nominations", format: "CSV", action: "employee_appraisal.action_peer_nomination_report_wizard" },
            { name: "Goals and Reflection", format: "XLSX", action: "employee_appraisal.action_self_appraisal_goals_reflection_wizard" },
            { name: "Salary Report", format: "XLSX", sensitive: true, action: "employee_appraisal.action_rp_salary_wizard" },
            { name: "Updated Managers", format: "XLSX", action: "employee_appraisal.action_rp_updated_managers_wizard" },
            { name: "Promotions", format: "XLSX", action: "employee_appraisal.action_rp_promotions_wizard" },
            { name: "Review Results", format: "XLSX", action: "employee_appraisal.action_rp_review_results_wizard" },
            { name: "Director Calibration", format: "XLSX", action: "employee_appraisal.action_director_calibration_report_wizard" },
            { name: "Needs Improvement CC", format: "XLSX", action: "employee_appraisal.action_director_needs_improvement_cc_report_wizard" },
            { name: "CC Assessment Summary", format: "XLSX", action: "employee_appraisal.action_director_cc_assessment_summary_report_wizard" },
            { name: "Manager-wise CC Misalignment", format: "XLSX", action: "employee_appraisal.action_manager_cc_misalignment_report_wizard" },
        ],
    },
    {
        key: "recruitment",
        name: "Recruitment",
        description: "Recruitment dashboard and applicant-stage reporting.",
        reports: [
            { name: "Recruitment Dashboard", format: "Dashboard / XLSX", action: "recruitment_10xE.action_recruitment_dashboard" },
            { name: "Applicant Stage Report", format: "Pivot / Export", action: "recruitment_10xE.action_applicant_stage_report_wizard" },
        ],
    },
    {
        key: "time_off",
        name: "Time Off",
        description: "Employee leave balances and availability.",
        reports: [
            { name: "Leave Balances", format: "List / Export", action: "time_off_balances.action_time_off_balance_wizard_server" },
        ],
    },
];


class CooReportsDashboard extends Component {
    static template = "coo_reports_10xe.CooReportsDashboard";
    static props = ["*"];

    setup() {
        this.action = useService("action");
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.modules = REPORT_MODULES;
        this.state = useState({
            query: "",
            view: "index",
            busyKey: null,
            employeeReportKey: null,
            selectedId: false,
            reportData: null,
        });
    }

    get visibleModules() {
        const query = this.state.query.trim().toLocaleLowerCase();
        if (!query) {
            return this.modules;
        }
        return this.modules.map((module) => {
            const moduleMatches = `${module.name} ${module.description}`.toLocaleLowerCase().includes(query);
            const reports = moduleMatches
                ? module.reports
                : module.reports.filter((report) =>
                    `${report.name} ${report.format}`.toLocaleLowerCase().includes(query)
                );
            return { ...module, reports };
        }).filter((module) => module.reports.length);
    }

    onSearch(event) {
        this.state.query = event.target.value;
    }

    reportButtonText(report) {
        if (report.employeeKey) {
            return "View report";
        }
        if (report.quickExport) {
            return "Export XLSX";
        }
        return "Open";
    }

    async openReport(report) {
        if (this.state.busyKey) {
            return;
        }
        if (report.employeeKey) {
            await this.loadEmployeeReport(report.employeeKey, false);
            return;
        }
        if (report.quickExport) {
            await this.exportUtilization();
            return;
        }
        this.state.busyKey = report.action;
        try {
            await this.action.doAction(report.action);
        } catch (error) {
            this.showError(`Could not open ${report.name}.`, error);
        } finally {
            this.state.busyKey = null;
        }
    }

    async loadEmployeeReport(reportKey, selectedId = false) {
        this.state.view = "report";
        this.state.employeeReportKey = reportKey;
        this.state.selectedId = selectedId;
        this.state.reportData = null;
        this.state.busyKey = `employee:${reportKey}`;
        try {
            const data = await this.orm.call(
                "coo.report.dashboard.service",
                "get_employee_report",
                [],
                { report_key: reportKey, selected_id: selectedId }
            );
            this.state.reportData = data;
            this.state.selectedId = data.selected_id || false;
        } catch (error) {
            this.state.view = "index";
            this.showError("Could not load the employee report.", error);
        } finally {
            this.state.busyKey = null;
        }
    }

    async onSelectorChange(event) {
        const selectedId = Number(event.target.value) || false;
        await this.loadEmployeeReport(this.state.employeeReportKey, selectedId);
    }

    backToReports() {
        this.state.view = "index";
        this.state.employeeReportKey = null;
        this.state.selectedId = false;
        this.state.reportData = null;
    }

    async exportEmployeeReport() {
        if (this.state.busyKey) {
            return;
        }
        if (this.state.employeeReportKey === "experience" && !this.state.selectedId) {
            this.notification.add("Select an active employee first.", { type: "warning" });
            return;
        }
        this.state.busyKey = "employee-export";
        try {
            const downloadAction = await this.orm.call(
                "coo.report.dashboard.service",
                "export_employee_report",
                [],
                {
                    report_key: this.state.employeeReportKey,
                    selected_id: this.state.selectedId,
                }
            );
            await this.action.doAction(downloadAction);
        } catch (error) {
            this.showError("Could not export the employee report.", error);
        } finally {
            this.state.busyKey = null;
        }
    }

    async exportUtilization() {
        this.state.busyKey = "utilization";
        try {
            const downloadAction = await this.orm.call(
                "coo.report.dashboard.service",
                "export_utilization"
            );
            await this.action.doAction(downloadAction);
        } catch (error) {
            this.showError("Could not export utilization.", error);
        } finally {
            this.state.busyKey = null;
        }
    }

    showError(message, error) {
        console.error(message, error);
        this.notification.add(message, { type: "danger" });
    }
}


registry.category("actions").add("coo_reports_10xe.dashboard", CooReportsDashboard);
