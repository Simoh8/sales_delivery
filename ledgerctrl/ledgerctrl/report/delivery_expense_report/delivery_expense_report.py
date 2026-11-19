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

    if "expense_date" != "None":
        if filters.get("date_from"):
            conditions.append("expense_date >= %(date_from)s")
            values["date_from"] = filters["date_from"]
        if filters.get("date_to"):
            conditions.append("expense_date <= %(date_to)s")
            values["date_to"] = filters["date_to"]

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    # Inject non-date filters as literal values (Link/Select validated server-side)
    sql = """SELECT name, delivery_job, delivery_batch, vehicle, rider, expense_date,
       expense_type, amount, expense_status
FROM `tabDelivery Expense`
{where}
ORDER BY expense_date DESC""".format(where=where)
    data = frappe.db.sql(sql, values, as_dict=True)
    return [
    {"label": "Expense", "fieldname": "name", "fieldtype": "Link", "options": "Delivery Expense", "width": 130},
    {"label": "Job", "fieldname": "delivery_job", "fieldtype": "Link", "options": "Delivery Job", "width": 130},
    {"label": "Batch", "fieldname": "delivery_batch", "fieldtype": "Link", "options": "Delivery Batch", "width": 120},
    {"label": "Vehicle", "fieldname": "vehicle", "fieldtype": "Link", "options": "Vehicle", "width": 110},
    {"label": "Rider", "fieldname": "rider", "fieldtype": "Link", "options": "Rider Profile", "width": 120},
    {"label": "Date", "fieldname": "expense_date", "fieldtype": "Date", "width": 100},
    {"label": "Type", "fieldname": "expense_type", "fieldtype": "Data", "width": 90},
    {"label": "Amount", "fieldname": "amount", "fieldtype": "Currency", "width": 100},
    {"label": "Status", "fieldname": "expense_status", "fieldtype": "Data", "width": 90},
], [tuple(d.values()) for d in data]
