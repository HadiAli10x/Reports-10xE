{
    "name": "10xE COO Reports",
    "version": "19.0.1.0.0",
    "summary": "A single, restricted reporting hub for the COO",
    "category": "Human Resources",
    "author": "10xEngineers",
    "license": "LGPL-3",
    "depends": [
        "hr",
        "employee_10xE",
        "employee_appraisal",
        "daily_assignment_tracker",
    ],
    "data": [
        "security/coo_reports_security.xml",
        "security/ir.model.access.csv",
        "views/coo_report_views.xml",
    ],
    "application": True,
    "installable": True,
    "post_init_hook": "post_init_assign_ayesha",
}
