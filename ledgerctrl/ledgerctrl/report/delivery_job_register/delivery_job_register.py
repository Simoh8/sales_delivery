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

    if "dj.scheduled_date" != "None":
        if filters.get("date_from"):
            conditions.append("dj.scheduled_date >= %(date_from)s")
            values["date_from"] = filters["date_from"]
        if filters.get("date_to"):
            conditions.append("dj.scheduled_date <= %(date_to)s")
            values["date_to"] = filters["date_to"]

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    # Inject non-date filters as literal values (Link/Select validated server-side)
    sql = """SELECT dj.name, dj.customer, COALESCE(rp.rider_name, dj.driver_name) rider_name,
       dj.vehicle, dj.status, dj.priority, dj.number_of_attempts,
       dj.scheduled_date, dj.completed_at
FROM `tabDelivery Job` dj
LEFT JOIN `tabRider Profile` rp ON rp.name = dj.rider_profile
{where}
ORDER BY dj.scheduled_date DESC""".format(where=where)
    data = frappe.db.sql(sql, values, as_dict=True)
    return [
    {"label": "Job", "fieldname": "name", "fieldtype": "Link", "options": "Delivery Job", "width": 130},
    {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 130},
    {"label": "Rider", "fieldname": "rider_name", "fieldtype": "Data", "width": 120},
    {"label": "Vehicle", "fieldname": "vehicle", "fieldtype": "Link", "options": "Vehicle", "width": 110},
    {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 100},
    {"label": "Priority", "fieldname": "priority", "fieldtype": "Data", "width": 80},
    {"label": "Attempts", "fieldname": "number_of_attempts", "fieldtype": "Int", "width": 80},
    {"label": "Scheduled", "fieldname": "scheduled_date", "fieldtype": "Date", "width": 100},
    {"label": "Completed", "fieldname": "completed_at", "fieldtype": "Datetime", "width": 140},
], [tuple(d.values()) for d in data]
