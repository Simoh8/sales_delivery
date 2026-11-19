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
    sql = """SELECT dj.rider_profile rider,
       COUNT(*) assigned,
       SUM(dj.status='Completed') completed,
       SUM(dj.status='Failed') failed,
       ROUND(SUM(dj.status='Completed')/NULLIF(COUNT(*)-SUM(dj.status='Cancelled'),0)*100,2) success_rate,
       ROUND(AVG(CASE WHEN dj.status='Completed' THEN dj.actual_duration END),1) avg_duration,
       ROUND(SUM(COALESCE(dj.actual_distance, dj.estimated_distance,0)),2) distance,
       SUM(dj.number_of_attempts>1) multi_attempt
FROM `tabDelivery Job` dj
{where}
GROUP BY dj.rider_profile""".format(where=where)
    data = frappe.db.sql(sql, values, as_dict=True)
    return [
    {"label": "Rider", "fieldname": "rider", "fieldtype": "Link", "options": "Rider Profile", "width": 140},
    {"label": "Assigned", "fieldname": "assigned", "fieldtype": "Int", "width": 90},
    {"label": "Completed", "fieldname": "completed", "fieldtype": "Int", "width": 90},
    {"label": "Failed", "fieldname": "failed", "fieldtype": "Int", "width": 80},
    {"label": "Success Rate %", "fieldname": "success_rate", "fieldtype": "Float", "width": 110},
    {"label": "Avg Duration (min)", "fieldname": "avg_duration", "fieldtype": "Float", "width": 120},
    {"label": "Total Distance (km)", "fieldname": "distance", "fieldtype": "Float", "width": 120},
    {"label": "Multi-attempt Jobs", "fieldname": "multi_attempt", "fieldtype": "Int", "width": 130},
], [tuple(d.values()) for d in data]
