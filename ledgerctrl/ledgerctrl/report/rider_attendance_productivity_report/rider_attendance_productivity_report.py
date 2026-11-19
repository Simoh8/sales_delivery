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

    if "shift_date" != "None":
        if filters.get("date_from"):
            conditions.append("shift_date >= %(date_from)s")
            values["date_from"] = filters["date_from"]
        if filters.get("date_to"):
            conditions.append("shift_date <= %(date_to)s")
            values["date_to"] = filters["date_to"]

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    # Inject non-date filters as literal values (Link/Select validated server-side)
    sql = """SELECT rider,
       COUNT(*) shifts,
       ROUND(SUM(total_working_hours),2) total_hours,
       SUM(total_deliveries) deliveries,
       SUM(completed_deliveries) completed,
       ROUND(SUM(completed_deliveries)/NULLIF(SUM(total_working_hours),0),2) per_hour,
       ROUND(SUM(total_distance_travelled),2) distance
FROM `tabRider Shift`
{where}
GROUP BY rider""".format(where=where)
    data = frappe.db.sql(sql, values, as_dict=True)
    return [
    {"label": "Rider", "fieldname": "rider", "fieldtype": "Link", "options": "Rider Profile", "width": 140},
    {"label": "Shifts", "fieldname": "shifts", "fieldtype": "Int", "width": 80},
    {"label": "Total Hours", "fieldname": "total_hours", "fieldtype": "Float", "width": 100},
    {"label": "Deliveries", "fieldname": "deliveries", "fieldtype": "Int", "width": 90},
    {"label": "Completed", "fieldname": "completed", "fieldtype": "Int", "width": 90},
    {"label": "Deliveries/Hour", "fieldname": "per_hour", "fieldtype": "Float", "width": 120},
    {"label": "Distance (km)", "fieldname": "distance", "fieldtype": "Float", "width": 100},
], [tuple(d.values()) for d in data]
