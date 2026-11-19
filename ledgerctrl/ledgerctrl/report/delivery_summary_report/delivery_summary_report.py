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

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    # Inject non-date filters as literal values (Link/Select validated server-side)
    sql = """SELECT dj.name, dj.customer, dj.status, dj.scheduled_date, dj.completed_at,
       dj.actual_duration, dj.customer_delivery_charge, dj.actual_delivery_cost,
       dj.delivery_revenue, dj.sla_status
FROM `tabDelivery Job` dj
{where}
ORDER BY dj.scheduled_date DESC""".format(where=where)
    data = frappe.db.sql(sql, values, as_dict=True)
    return [
    {"label": "Delivery Job", "fieldname": "name", "fieldtype": "Link", "options": "Delivery Job", "width": 140},
    {"label": "Customer", "fieldname": "customer", "fieldtype": "Data", "width": 140},
    {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 100},
    {"label": "Scheduled", "fieldname": "scheduled_date", "fieldtype": "Date", "width": 100},
    {"label": "Completed At", "fieldname": "completed_at", "fieldtype": "Datetime", "width": 140},
    {"label": "Actual Duration (min)", "fieldname": "actual_duration", "fieldtype": "Int", "width": 120},
    {"label": "Delivery Charge", "fieldname": "customer_delivery_charge", "fieldtype": "Currency", "width": 120},
    {"label": "Delivery Cost", "fieldname": "actual_delivery_cost", "fieldtype": "Currency", "width": 120},
    {"label": "Revenue", "fieldname": "delivery_revenue", "fieldtype": "Currency", "width": 110},
    {"label": "SLA Status", "fieldname": "sla_status", "fieldtype": "Data", "width": 100},
], [tuple(d.values()) for d in data]
