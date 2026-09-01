/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";


const REPORT_MODULES = [
    {
        key: "employees",
        name: "Employees",
        eyebrow: "Workforce structure",
        description: "Reporting lines, employee experience, and manager team structures.",
        icon: "fa-users",
        color: "violet",
        reports: [
            {
                name: "Organization Chart",
                description: "Export the active employee hierarchy for the company, a department, or one reporting branch.",
                format: "XLSX",
                action: "coo_reports_10xe.action_coo_org_chart_report",
            },
            {
                name: "Single Employee Experience",
                description: "Current experience summary and appraisal history for one active employee.",
                format: "XLSX",
                action: "coo_reports_10xe.action_coo_employee_experience_report",
            },
            {
                name: "Managers' Direct Reports",
                description: "Active manager-to-direct-report relationships with a manager summary sheet.",
                format: "XLSX",
                action: "coo_reports_10xe.action_coo_manager_direct_reports",
            },
        ],
    },
    {
        key: "assignments",
        name: "Daily Assignment Tracker",
        eyebrow: "Capacity and delivery",
        description: "Allocation, activity, completeness, classification, and utilization reporting.",
        icon: "fa-tasks",
        color: "blue",
        reports: [
            {
                name: "Assignments Report",
                description: "Assignment allocations overlapping a selected reporting period, with summary totals.",
                format: "XLSX",
                action: "coo_reports_10xe.action_coo_assignments_report",
            },
            {
                name: "Utilization",
                description: "Client, internal, recorded, and unreported weekday capacity by employee and department.",
                format: "XLSX",
                action: "coo_reports_10xe.action_coo_utilization_report",
            },
            {
                name: "Assignment Completeness",
                description: "Daily submission completeness for active employees across a selected date range.",
                format: "XLSX",
                action: "daily_assignment_tracker.action_daily_assignment_completeness_report",
            },
            {
                name: "Engineering Assignment Activity",
                description: "Engineering assignment activity, allocation detail, and submission status.",
                format: "XLSX",
                action: "daily_assignment_tracker.action_daily_assignment_engineering_report",
            },
            {
                name: "Engineering Billing Classification",
                description: "Billed, not billable, ready, and not-ready engineering classification.",
                format: "XLSX",
                action: "daily_assignment_tracker.action_daily_assignment_engineering_classification_report",
            },
            {
                name: "Engineering Weekly Area",
                description: "Weekly engineering classification and business-line area trends over a month range.",
                format: "XLSX",
                action: "daily_assignment_tracker.action_daily_assignment_engineering_weekly_area_report",
            },
        ],
    },
    {
        key: "appraisal",
        name: "Performance Appraisal",
        eyebrow: "Performance and rewards",
        description: "Review outcomes, calibration, compensation, promotions, and competency reports.",
        icon: "fa-line-chart",
        color: "amber",
        reports: [
            {
                name: "Peer Nominations",
                description: "Peer nomination selections and reviewer assignments for the selected cycle.",
                format: "CSV",
                action: "employee_appraisal.action_peer_nomination_report_wizard",
            },
            {
                name: "Goals and Reflection",
                description: "Submitted professional goals and employee reflections from self appraisals.",
                format: "XLSX",
                action: "employee_appraisal.action_self_appraisal_goals_reflection_wizard",
            },
            {
                name: "Salary Report",
                description: "Compensation outcomes and salary changes for an appraisal review cycle.",
                format: "XLSX",
                sensitive: true,
                action: "employee_appraisal.action_rp_salary_wizard",
            },
            {
                name: "Updated Managers",
                description: "Employees whose reporting manager changed in the selected review cycle.",
                format: "XLSX",
                action: "employee_appraisal.action_rp_updated_managers_wizard",
            },
            {
                name: "Promotions",
                description: "Employees whose designation changed during the selected review cycle.",
                format: "XLSX",
                action: "employee_appraisal.action_rp_promotions_wizard",
            },
            {
                name: "Review Results",
                description: "Consolidated appraisal outcomes, scores, and finalized review results.",
                format: "XLSX",
                action: "employee_appraisal.action_rp_review_results_wizard",
            },
            {
                name: "Director Calibration",
                description: "Director-level calibration detail across employee and manager review data.",
                format: "XLSX",
                action: "employee_appraisal.action_director_calibration_report_wizard",
            },
            {
                name: "Needs Improvement CC",
                description: "Core competency assessments marked as Needs Improvement.",
                format: "XLSX",
                action: "employee_appraisal.action_director_needs_improvement_cc_report_wizard",
            },
            {
                name: "CC Assessment Summary",
                description: "Core competency assessment coverage, changes, and category-level totals.",
                format: "XLSX",
                action: "employee_appraisal.action_director_cc_assessment_summary_report_wizard",
            },
            {
                name: "Manager-wise CC Misalignment",
                description: "Self-versus-manager core competency rating differences grouped by manager.",
                format: "XLSX",
                action: "employee_appraisal.action_manager_cc_misalignment_report_wizard",
            },
        ],
    },
    {
        key: "recruitment",
        name: "Recruitment",
        eyebrow: "Hiring pipeline",
        description: "Requisition health, hiring activity, and applicant movement through stages.",
        icon: "fa-user-plus",
        color: "green",
        reports: [
            {
                name: "Recruitment Dashboard",
                description: "Requisitions, interviews, hires, opportunistic pipeline, and detailed XLSX export.",
                format: "Dashboard + XLSX",
                action: "recruitment_10xE.action_recruitment_dashboard",
            },
            {
                name: "Applicant Stage Report",
                description: "Applicant stage snapshot for a date range and optional job position.",
                format: "Pivot / Export",
                action: "recruitment_10xE.action_applicant_stage_report_wizard",
            },
        ],
    },
    {
        key: "time_off",
        name: "Time Off",
        eyebrow: "Availability and leave",
        description: "Employee leave balances, current leave status, and range checks.",
        icon: "fa-calendar-check-o",
        color: "coral",
        reports: [
            {
                name: "Leave Balances",
                description: "Allocated, taken, pending, remaining, and expiring balances for active employees.",
                format: "List / Export",
                action: "time_off_balances.action_time_off_balance_wizard_server",
            },
        ],
    },
];


class CooReportsDashboard extends Component {
    static template = "coo_reports_10xe.CooReportsDashboard";
    static props = ["*"];

    setup() {
        this.action = useService("action");
        this.notification = useService("notification");
        this.state = useState({ query: "", openingAction: null });
        this.modules = REPORT_MODULES;
    }

    get totalReportCount() {
        return this.modules.reduce((total, module) => total + module.reports.length, 0);
    }

    get visibleModules() {
        const query = this.state.query.trim().toLocaleLowerCase();
        if (!query) {
            return this.modules;
        }
        return this.modules.map((module) => {
            const moduleMatches = `${module.name} ${module.eyebrow} ${module.description}`
                .toLocaleLowerCase()
                .includes(query);
            const reports = moduleMatches
                ? module.reports
                : module.reports.filter((report) =>
                    `${report.name} ${report.description} ${report.format}`
                        .toLocaleLowerCase()
                        .includes(query)
                );
            return { ...module, reports };
        }).filter((module) => module.reports.length);
    }

    get visibleReportCount() {
        return this.visibleModules.reduce(
            (total, module) => total + module.reports.length,
            0
        );
    }

    onSearch(event) {
        this.state.query = event.target.value;
    }

    clearSearch() {
        this.state.query = "";
    }

    scrollToModule(moduleKey) {
        this.state.query = "";
        requestAnimationFrame(() => {
            document.getElementById(`crd-module-${moduleKey}`)?.scrollIntoView({
                behavior: "smooth",
                block: "start",
            });
        });
    }

    async openReport(report) {
        if (this.state.openingAction) {
            return;
        }
        this.state.openingAction = report.action;
        try {
            await this.action.doAction(report.action);
        } catch (error) {
            console.error("Unable to open COO report", report.action, error);
            this.notification.add(
                `Could not open ${report.name}. Please refresh the app and try again.`,
                { type: "danger" }
            );
        } finally {
            this.state.openingAction = null;
        }
    }
}


registry.category("actions").add("coo_reports_10xe.dashboard", CooReportsDashboard);
