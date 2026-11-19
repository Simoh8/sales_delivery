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

    if "fuel_date" != "None":
        if filters.get("date_from"):
            conditions.append("fuel_date >= %(date_from)s")
            values["date_from"] = filters["date_from"]
        if filters.get("date_to"):
            conditions.append("fuel_date <= %(date_to)s")
            values["date_to"] = filters["date_to"]

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    # Inject non-date filters as literal values (Link/Select validated server-side)
    sql = """SELECT name, vehicle, fuel_date, fuel_type, quantity, unit_price, total_cost,
       odometer_reading, consumption_kmpl, flag_reason
FROM `tabFuel Log`
{where}
ORDER BY fuel_date DESC""".format(where=where)
    data = frappe.db.sql(sql, values, as_dict=True)
    return [
    {"label": "Log", "fieldname": "name", "fieldtype": "Link", "options": "Fuel Log", "width": 110},
    {"label": "Vehicle", "fieldname": "vehicle", "fieldtype": "Link", "options": "Vehicle", "width": 120},
    {"label": "Date", "fieldname": "fuel_date", "fieldtype": "Date", "width": 100},
    {"label": "Type", "fieldname": "fuel_type", "fieldtype": "Data", "width": 80},
    {"label": "Qty", "fieldname": "quantity", "fieldtype": "Float", "width": 70},
    {"label": "Unit Price", "fieldname": "unit_price", "fieldtype": "Currency", "width": 100},
    {"label": "Total Cost", "fieldname": "total_cost", "fieldtype": "Currency", "width": 100},
    {"label": "Odometer", "fieldname": "odometer_reading", "fieldtype": "Float", "width": 100},
    {"label": "km/L", "fieldname": "consumption_kmpl", "fieldtype": "Float", "width": 70},
    {"label": "Flag", "fieldname": "flag_reason", "fieldtype": "Data", "width": 160},
], [tuple(d.values()) for d in data]
