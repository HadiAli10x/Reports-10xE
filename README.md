# 10xE COO Reports

`coo_reports_10xe` is an Odoo 19 application that gives the COO one restricted reporting hub instead of requiring access to several operational applications.

## Included reports

| Menu section | Report | Source data | Export |
|---|---|---|---|
| Employees | Organization Chart | Employees / manager hierarchy | XLSX |
| Employees | Single Employee Experience | Employee master data + appraisal history | XLSX (summary and history sheets) |
| Employees | Managers' Direct Reports | Employees / manager hierarchy | XLSX (detail and summary sheets) |
| Daily Assignment Tracker | Assignments Report | Assignment allocations | XLSX (detail and summary sheets) |
| Daily Assignment Tracker | Utilization | Submitted daily assignment entries | XLSX (employee, department, and methodology sheets) |

The same app also exposes the existing export workflows from its installed source modules under their module names:

- Daily Assignment Tracker: Assignment Completeness, Engineering Assignment Activity, Engineering Billing Classification, and Engineering Weekly Area.
- Performance Appraisal: Peer Nominations, Goals and Reflection, Salary, Updated Managers, Promotions, Review Results, Director Calibration, Needs Improvement CC, CC Assessment Summary, and Manager-wise CC Misalignment.

The hub grants only the wizard-level access needed to run these exports and performs the same report logic from the source modules. It does not imply the Assignment Owner, HR Officer, or Appraisal Director roles, so those source applications do not become broadly visible to the COO account.

The single-employee experience selector and the managers/direct-reports report are restricted to employees whose standard Odoo `active` flag is true and whose 10xE status is `Active`. The same rule is checked in Python when exporting, so it cannot be bypassed by changing the browser request.

## Access

Every menu, action, and wizard ACL is restricted to the **Ayesha - COO Reports** group. That group also grants spreadsheet export permission.

At installation, the post-install hook assigns the group automatically only when it can identify exactly one user with:

- the exact name, login, email, or email local part `Ayesha`; or
- a unique name beginning with `Ayesha`.

If there is no unique match, access remains unassigned and the server log explains why. An administrator must then assign **COO Reports / Ayesha - COO Reports** to the correct account in Settings. Do not assign this group to anyone else.

## Installation

Place this repository on the Odoo addons path alongside these existing 10xE modules:

- `employee_10xE`
- `employee_appraisal`
- `daily_assignment_tracker`

Update the Apps list, install **10xE COO Reports**, then sign in as Ayesha. A new **COO Reports** application appears in the app switcher.

## Utilization definition

Utilization uses submitted Daily Assignment Tracker entries over Monday-Friday days in the selected range:

- Client utilization = percentage-weighted client-assignment weekdays / expected weekdays.
- Internal percentage = percentage-weighted internal-assignment weekdays / expected weekdays.
- Recorded percentage = client + internal recorded capacity, capped at 100%.
- Unreported percentage = 100% - recorded percentage.

Approved leave and public holidays are intentionally not subtracted because the current assignment module does not own a common capacity calendar. The exported workbook includes this methodology so figures cannot be mistaken for leave-adjusted utilization.

## Technical notes

- Built for Odoo 19 (`res.groups.privilege`, `<list>`-era APIs, and environment-style post-init hook).
- XLSX output is generated with Python's standard library; no third-party Excel package is required.
- Source operational records are read with `sudo()` only after the restricted wizard group and server-side access check have succeeded. The hub does not grant Ayesha edit access to the underlying modules.
