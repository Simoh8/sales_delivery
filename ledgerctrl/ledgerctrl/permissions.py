import frappe

RIDER_ROLE = "Delivery Rider"
MANAGER_ROLES = {
    "System Manager",
    "Delivery Manager",
    "Delivery Dispatcher",
    "Delivery Supervisor",
    "Fleet Manager",
    "Fleet Supervisor",
    "Delivery Analyst",
}


def _roles(user):
    return set(frappe.get_roles(user))


def _is_manager(user):
    return bool(_roles(user) & MANAGER_ROLES)


def _is_rider(user):
    return RIDER_ROLE in _roles(user)


def _rider_profile_for_user(user):
    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if not employee:
        return None
    return frappe.db.get_value("Rider Profile", {"employee": employee}, "name")


def _jobs_for_rider(user):
    rider = _rider_profile_for_user(user)
    if not rider:
        return []
    employee = frappe.db.get_value("Rider Profile", rider, "employee")
    jobs = set(
        frappe.get_all("Delivery Job", filters={"rider_profile": rider}, pluck="name")
    )
    if employee:
        jobs.update(
            frappe.get_all("Delivery Job", filters={"driver": employee}, pluck="name")
        )
    return list(jobs)


def _in_condition(doctype, field, values):
    if not values:
        return "1=0"
    escaped = ",".join(frappe.db.escape(v) for v in values)
    return "`tab{0}`.{1} IN ({2})".format(doctype, field, escaped)


def _rider_or_manager(user):
    """Return rider name if user is a non-manager rider, else None."""
    if _is_manager(user):
        return None
    if not _is_rider(user):
        return None
    return _rider_profile_for_user(user)


def delivery_job_query_conditions(user):
    if _is_manager(user):
        return ""
    if not _is_rider(user):
        return ""
    rider = _rider_profile_for_user(user)
    if not rider:
        return "1=0"
    employee = frappe.db.get_value("Rider Profile", rider, "employee")
    return (
        "(`tabDelivery Job`.rider_profile = {0} OR `tabDelivery Job`.driver = {1})".format(
            frappe.db.escape(rider), frappe.db.escape(employee or "")
        )
    )


def _job_children_condition(user, doctype, field):
    if _is_manager(user):
        return ""
    if not _is_rider(user):
        return ""
    jobs = _jobs_for_rider(user)
    cond = _in_condition(doctype, field, jobs)
    return cond


def delivery_attempt_query_conditions(user):
    return _job_children_condition(user, "Delivery Attempt", "delivery_job")


def proof_of_delivery_query_conditions(user):
    return _job_children_condition(user, "Proof of Delivery", "delivery_job")


def delivery_stop_query_conditions(user):
    if _is_manager(user):
        return ""
    if not _is_rider(user):
        return ""
    rider = _rider_profile_for_user(user)
    jobs = _jobs_for_rider(user)
    batches = (
        frappe.get_all(
            "Delivery Batch",
            filters={"assigned_rider": rider},
            pluck="name",
        )
        if rider
        else []
    )
    conds = [
        _in_condition("Delivery Stop", "delivery_job", jobs),
        _in_condition("Delivery Stop", "delivery_batch", batches),
    ]
    conds = [c for c in conds if c != "1=0"]
    return " OR ".join(conds) if conds else "1=0"


def delivery_expense_query_conditions(user):
    if _is_manager(user):
        return ""
    if not _is_rider(user):
        return ""
    rider = _rider_profile_for_user(user)
    jobs = _jobs_for_rider(user)
    conds = [_in_condition("Delivery Expense", "delivery_job", jobs)]
    if rider:
        conds.append("`tabDelivery Expense`.rider = {0}".format(frappe.db.escape(rider)))
    conds = [c for c in conds if c != "1=0"]
    return " OR ".join(conds) if conds else "1=0"


def _rider_record_condition(user, table):
    if _is_manager(user):
        return ""
    if not _is_rider(user):
        return ""
    rider = _rider_profile_for_user(user)
    if not rider:
        return "1=0"
    return "`tab{0}`.rider = {1}".format(table, frappe.db.escape(rider))


def rider_shift_query_conditions(user):
    return _rider_record_condition(user, "Rider Shift")


def rider_availability_query_conditions(user):
    return _rider_record_condition(user, "Rider Availability")


def rider_document_query_conditions(user):
    return _rider_record_condition(user, "Rider Document")


def fuel_log_query_conditions(user):
    if _is_manager(user):
        return ""
    roles = _roles(user)
    if roles & {"Fleet Manager", "Fleet Supervisor"}:
        return ""
    if not _is_rider(user):
        return ""
    rider = _rider_profile_for_user(user)
    if not rider:
        return "1=0"
    return "`tabFuel Log`.rider = {0}".format(frappe.db.escape(rider))


def vehicle_inspection_query_conditions(user):
    return _rider_record_condition(user, "Vehicle Inspection")
