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
    sql = """SELECT name, rider, shift_date, actual_clock_in, actual_clock_out,
       total_working_hours, total_deliveries, completed_deliveries,
       total_distance_travelled, shift_status
FROM `tabRider Shift`
{where}
ORDER BY shift_date DESC""".format(where=where)
    data = frappe.db.sql(sql, values, as_dict=True)
    return [
    {"label": "Shift", "fieldname": "name", "fieldtype": "Link", "options": "Rider Shift", "width": 120},
    {"label": "Rider", "fieldname": "rider", "fieldtype": "Link", "options": "Rider Profile", "width": 130},
    {"label": "Date", "fieldname": "shift_date", "fieldtype": "Date", "width": 100},
    {"label": "Clock In", "fieldname": "actual_clock_in", "fieldtype": "Datetime", "width": 140},
    {"label": "Clock Out", "fieldname": "actual_clock_out", "fieldtype": "Datetime", "width": 140},
    {"label": "Working Hours", "fieldname": "total_working_hours", "fieldtype": "Float", "width": 110},
    {"label": "Deliveries", "fieldname": "total_deliveries", "fieldtype": "Int", "width": 90},
    {"label": "Completed", "fieldname": "completed_deliveries", "fieldtype": "Int", "width": 90},
    {"label": "Distance (km)", "fieldname": "total_distance_travelled", "fieldtype": "Float", "width": 110},
    {"label": "Status", "fieldname": "shift_status", "fieldtype": "Data", "width": 90},
], [tuple(d.values()) for d in data]
