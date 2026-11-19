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
    sql = """SELECT dj.vehicle,
       v.vehicle_type,
       COUNT(*) jobs,
       SUM(dj.status='Completed') completed,
       ROUND(SUM(COALESCE(dj.actual_distance,0)),2) distance,
       (SELECT ROUND(SUM(total_cost),2) FROM `tabFuel Log` f WHERE f.vehicle=dj.vehicle AND f.fuel_date BETWEEN %(date_from)s AND %(date_to)s) fuel_cost,
       (SELECT ROUND(SUM(total_cost),2) FROM `tabVehicle Maintenance Record` m WHERE m.vehicle=dj.vehicle AND m.maintenance_date BETWEEN %(date_from)s AND %(date_to)s AND m.status!='Cancelled') maint_cost
FROM `tabDelivery Job` dj
LEFT JOIN `tabVehicle` v ON v.name = dj.vehicle
{where}
GROUP BY dj.vehicle""".format(where=where)
    data = frappe.db.sql(sql, values, as_dict=True)
    return [
    {"label": "Vehicle", "fieldname": "vehicle", "fieldtype": "Link", "options": "Vehicle", "width": 130},
    {"label": "Type", "fieldname": "vehicle_type", "fieldtype": "Data", "width": 90},
    {"label": "Jobs", "fieldname": "jobs", "fieldtype": "Int", "width": 70},
    {"label": "Completed", "fieldname": "completed", "fieldtype": "Int", "width": 90},
    {"label": "Distance (km)", "fieldname": "distance", "fieldtype": "Float", "width": 110},
    {"label": "Fuel Cost", "fieldname": "fuel_cost", "fieldtype": "Currency", "width": 110},
    {"label": "Maint. Cost", "fieldname": "maint_cost", "fieldtype": "Currency", "width": 110},
], [tuple(d.values()) for d in data]
