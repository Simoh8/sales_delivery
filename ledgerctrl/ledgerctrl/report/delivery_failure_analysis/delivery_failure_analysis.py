# Copyright (c) 2026, ledgerctrl
# License: MIT

import frappe


def execute(filters=None):
    filters = filters or {}
    conditions = []
    values = {}
    # defaults so %(date_from)s / %(date_to)s always resolve
    from frappe.utils import add_days, nowdate
    values.setdefault("date_from", filters.get("date_from") or add_days(nowdate(), -365))
    values.setdefault("date_to", filters.get("date_to") or nowdate())

    if "a.attempt_date" != "None":
        if filters.get("date_from"):
            conditions.append("a.attempt_date >= %(date_from)s")
            values["date_from"] = filters["date_from"]
        if filters.get("date_to"):
            conditions.append("a.attempt_date <= %(date_to)s")
            values["date_to"] = filters["date_to"]

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    # Inject non-date filters as literal values (Link/Select validated server-side)
    sql = """SELECT a.name, a.delivery_job, a.rider, a.attempt_status, a.failure_reason, a.attempt_date
FROM `tabDelivery Attempt` a
{where}
ORDER BY a.attempt_date DESC""".format(where=where)
    data = frappe.db.sql(sql, values, as_dict=True)
    return [
    {"label": "Attempt", "fieldname": "name", "fieldtype": "Link", "options": "Delivery Attempt", "width": 130},
    {"label": "Job", "fieldname": "delivery_job", "fieldtype": "Link", "options": "Delivery Job", "width": 130},
    {"label": "Rider", "fieldname": "rider", "fieldtype": "Link", "options": "Rider Profile", "width": 120},
    {"label": "Status", "fieldname": "attempt_status", "fieldtype": "Data", "width": 120},
    {"label": "Failure Reason", "fieldname": "failure_reason", "fieldtype": "Data", "width": 200},
    {"label": "Date", "fieldname": "attempt_date", "fieldtype": "Date", "width": 100},
], [tuple(d.values()) for d in data]
