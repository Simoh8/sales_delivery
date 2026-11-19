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

    if "attempt_date" != "None":
        if filters.get("date_from"):
            conditions.append("attempt_date >= %(date_from)s")
            values["date_from"] = filters["date_from"]
        if filters.get("date_to"):
            conditions.append("attempt_date <= %(date_to)s")
            values["date_to"] = filters["date_to"]

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    # Inject non-date filters as literal values (Link/Select validated server-side)
    sql = """SELECT name, delivery_job, attempt_number, rider, vehicle, attempt_status,
       arrival_time, completion_time,
       CONCAT(gps_latitude, ',', gps_longitude) gps
FROM `tabDelivery Attempt`
{where}
ORDER BY attempt_date DESC, attempt_number""".format(where=where)
    data = frappe.db.sql(sql, values, as_dict=True)
    return [
    {"label": "Attempt", "fieldname": "name", "fieldtype": "Link", "options": "Delivery Attempt", "width": 120},
    {"label": "Job", "fieldname": "delivery_job", "fieldtype": "Link", "options": "Delivery Job", "width": 130},
    {"label": "Attempt #", "fieldname": "attempt_number", "fieldtype": "Int", "width": 90},
    {"label": "Rider", "fieldname": "rider", "fieldtype": "Link", "options": "Rider Profile", "width": 120},
    {"label": "Vehicle", "fieldname": "vehicle", "fieldtype": "Link", "options": "Vehicle", "width": 110},
    {"label": "Status", "fieldname": "attempt_status", "fieldtype": "Data", "width": 110},
    {"label": "Arrival", "fieldname": "arrival_time", "fieldtype": "Datetime", "width": 140},
    {"label": "Completion", "fieldname": "completion_time", "fieldtype": "Datetime", "width": 140},
    {"label": "GPS", "fieldname": "gps", "fieldtype": "Data", "width": 150},
], [tuple(d.values()) for d in data]
