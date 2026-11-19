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

    if "scheduled_date" != "None":
        if filters.get("date_from"):
            conditions.append("scheduled_date >= %(date_from)s")
            values["date_from"] = filters["date_from"]
        if filters.get("date_to"):
            conditions.append("scheduled_date <= %(date_to)s")
            values["date_to"] = filters["date_to"]

    where = ("AND " + " AND ".join(conditions)) if conditions else ""
    # Inject non-date filters as literal values (Link/Select validated server-side)
    sql = """SELECT name, customer, delivery_sla, status, sla_status,
       scheduled_delivery_end, completed_at, delay_minutes
FROM `tabDelivery Job`
WHERE delivery_sla IS NOT NULL AND delivery_sla != ''
{where}
ORDER BY scheduled_date DESC""".format(where=where)
    data = frappe.db.sql(sql, values, as_dict=True)
    return [
    {"label": "Job", "fieldname": "name", "fieldtype": "Link", "options": "Delivery Job", "width": 130},
    {"label": "Customer", "fieldname": "customer", "fieldtype": "Data", "width": 130},
    {"label": "SLA", "fieldname": "delivery_sla", "fieldtype": "Link", "options": "Delivery SLA", "width": 110},
    {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 100},
    {"label": "SLA Status", "fieldname": "sla_status", "fieldtype": "Data", "width": 100},
    {"label": "Scheduled End", "fieldname": "scheduled_delivery_end", "fieldtype": "Datetime", "width": 150},
    {"label": "Completed At", "fieldname": "completed_at", "fieldtype": "Datetime", "width": 150},
    {"label": "Delay (min)", "fieldname": "delay_minutes", "fieldtype": "Int", "width": 100},
], [tuple(d.values()) for d in data]
