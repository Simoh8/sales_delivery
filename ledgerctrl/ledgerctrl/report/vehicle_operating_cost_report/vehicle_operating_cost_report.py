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

    if "None" != "None":
        if filters.get("date_from"):
            conditions.append("None >= %(date_from)s")
            values["date_from"] = filters["date_from"]
        if filters.get("date_to"):
            conditions.append("None <= %(date_to)s")
            values["date_to"] = filters["date_to"]

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    # Inject non-date filters as literal values (Link/Select validated server-side)
    sql = """SELECT v.name vehicle,
       (SELECT ROUND(SUM(total_cost),2) FROM `tabFuel Log` f WHERE f.vehicle=v.name AND f.fuel_date BETWEEN %(date_from)s AND %(date_to)s) fuel_cost,
       (SELECT ROUND(SUM(total_cost),2) FROM `tabVehicle Maintenance Record` m WHERE m.vehicle=v.name AND m.maintenance_date BETWEEN %(date_from)s AND %(date_to)s AND m.status!='Cancelled') maint_cost,
       (SELECT ROUND(SUM(total_cost),2) FROM `tabFuel Log` f WHERE f.vehicle=v.name AND f.fuel_date BETWEEN %(date_from)s AND %(date_to)s) +
       (SELECT ROUND(SUM(total_cost),2) FROM `tabVehicle Maintenance Record` m WHERE m.vehicle=v.name AND m.maintenance_date BETWEEN %(date_from)s AND %(date_to)s AND m.status!='Cancelled') total_cost,
       (SELECT COUNT(*) FROM `tabDelivery Job` d WHERE d.vehicle=v.name AND d.status='Completed' AND d.scheduled_date BETWEEN %(date_from)s AND %(date_to)s) deliveries
FROM `tabVehicle` v
ORDER BY total_cost DESC""".format(where=where)
    data = frappe.db.sql(sql, values, as_dict=True)
    return [
    {"label": "Vehicle", "fieldname": "vehicle", "fieldtype": "Link", "options": "Vehicle", "width": 130},
    {"label": "Fuel Cost", "fieldname": "fuel_cost", "fieldtype": "Currency", "width": 110},
    {"label": "Maint. Cost", "fieldname": "maint_cost", "fieldtype": "Currency", "width": 110},
    {"label": "Total Cost", "fieldname": "total_cost", "fieldtype": "Currency", "width": 110},
    {"label": "Deliveries", "fieldname": "deliveries", "fieldtype": "Int", "width": 90},
    {"label": "Cost/Delivery", "fieldname": "cost_per_delivery", "fieldtype": "Currency", "width": 120},
], [tuple(d.values()) for d in data]
