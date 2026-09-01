import logging


_logger = logging.getLogger(__name__)


def _identity_parts(user):
    values = {
        (user.name or "").strip().casefold(),
        (user.login or "").strip().casefold(),
        (user.email or "").strip().casefold(),
    }
    values.update(value.split("@", 1)[0] for value in tuple(values) if "@" in value)
    return values


def post_init_assign_ayesha(env):
    """Assign the restricted group when exactly one Ayesha account is found.

    An ambiguous match is intentionally left untouched: silently granting COO data
    access to the wrong account would be worse than requiring an administrator to
    assign the group once from Settings.
    """
    group = env.ref("coo_reports_10xe.group_coo_reports_ayesha")
    users = env["res.users"].sudo().search([("active", "=", True)])
    exact = users.filtered(lambda user: "ayesha" in _identity_parts(user))
    candidates = exact or users.filtered(
        lambda user: (user.name or "").strip().casefold().split(" ", 1)[0] == "ayesha"
    )

    if len(candidates) == 1:
        candidates.sudo().write({"group_ids": [(4, group.id)]})
        _logger.info("Assigned 10xE COO Reports access to user %s", candidates.display_name)
    elif not candidates:
        _logger.warning(
            "No unique Ayesha account was found. The 10xE COO Reports group remains unassigned."
        )
    else:
        _logger.warning(
            "Multiple Ayesha accounts were found. The 10xE COO Reports group remains unassigned."
        )
