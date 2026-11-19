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

    if "maintenance_date" != "None":
        if filters.get("date_from"):
            conditions.append("maintenance_date >= %(date_from)s")
            values["date_from"] = filters["date_from"]
        if filters.get("date_to"):
            conditions.append("maintenance_date <= %(date_to)s")
            values["date_to"] = filters["date_to"]

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    # Inject non-date filters as literal values (Link/Select validated server-side)
    sql = """SELECT name, vehicle, maintenance_type, maintenance_date, odometer_reading,
       service_provider, total_cost, next_service_date, status
FROM `tabVehicle Maintenance Record`
{where}
ORDER BY maintenance_date DESC""".format(where=where)
    data = frappe.db.sql(sql, values, as_dict=True)
    return [
    {"label": "Record", "fieldname": "name", "fieldtype": "Link", "options": "Vehicle Maintenance Record", "width": 140},
    {"label": "Vehicle", "fieldname": "vehicle", "fieldtype": "Link", "options": "Vehicle", "width": 120},
    {"label": "Type", "fieldname": "maintenance_type", "fieldtype": "Data", "width": 100},
    {"label": "Date", "fieldname": "maintenance_date", "fieldtype": "Date", "width": 100},
    {"label": "Odometer", "fieldname": "odometer_reading", "fieldtype": "Float", "width": 100},
    {"label": "Provider", "fieldname": "service_provider", "fieldtype": "Data", "width": 130},
    {"label": "Cost", "fieldname": "total_cost", "fieldtype": "Currency", "width": 100},
    {"label": "Next Service", "fieldname": "next_service_date", "fieldtype": "Date", "width": 110},
    {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 90},
], [tuple(d.values()) for d in data]
