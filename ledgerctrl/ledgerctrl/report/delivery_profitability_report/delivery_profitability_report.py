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
    sql = """SELECT dj.name, dj.customer, dj.rider_profile,
       COALESCE(dj.customer_delivery_charge, dj.grand_total, 0) charge,
       COALESCE(dj.actual_delivery_cost,0) actual_delivery_cost,
       (SELECT COALESCE(SUM(amount),0) FROM `tabDelivery Expense` e WHERE e.delivery_job=dj.name AND e.expense_status!='Cancelled') expenses,
       COALESCE(dj.delivery_revenue, COALESCE(dj.customer_delivery_charge, dj.grand_total,0) - COALESCE(dj.actual_delivery_cost,0)) revenue,
       COALESCE(dj.delivery_revenue, COALESCE(dj.customer_delivery_charge, dj.grand_total,0) - COALESCE(dj.actual_delivery_cost,0))
         - (SELECT COALESCE(SUM(amount),0) FROM `tabDelivery Expense` e WHERE e.delivery_job=dj.name AND e.expense_status!='Cancelled') contribution
FROM `tabDelivery Job` dj
{where}
ORDER BY dj.scheduled_date DESC""".format(where=where)
    data = frappe.db.sql(sql, values, as_dict=True)
    return [
    {"label": "Job", "fieldname": "name", "fieldtype": "Link", "options": "Delivery Job", "width": 130},
    {"label": "Customer", "fieldname": "customer", "fieldtype": "Data", "width": 130},
    {"label": "Rider", "fieldname": "rider_profile", "fieldtype": "Link", "options": "Rider Profile", "width": 120},
    {"label": "Charge", "fieldname": "charge", "fieldtype": "Currency", "width": 100},
    {"label": "Delivery Cost", "fieldname": "actual_delivery_cost", "fieldtype": "Currency", "width": 110},
    {"label": "Expenses", "fieldname": "expenses", "fieldtype": "Currency", "width": 100},
    {"label": "Revenue", "fieldname": "revenue", "fieldtype": "Currency", "width": 100},
    {"label": "Contribution", "fieldname": "contribution", "fieldtype": "Currency", "width": 110},
], [tuple(d.values()) for d in data]
