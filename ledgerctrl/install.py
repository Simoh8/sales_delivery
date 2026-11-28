import frappe


def after_install():
    """Create custom fields and roles required by ledgerctrl."""
    create_vehicle_type_field()
    create_delivery_note_otp_fields()
    create_roles()


def create_delivery_note_otp_fields():
    """OTP fields on Delivery Note used by the delivery confirmation flow."""
    fields = [
        ("custom_otp_code", "OTP Code", "Data", "transporter", 0),
        ("custom_user_otp", "Customer OTP", "Data", "custom_otp_code", 0),
        ("custom_otp_verified", "OTP Verified", "Check", "custom_user_otp", 0),
    ]
    for fieldname, label, fieldtype, insert_after, hidden in fields:
        if frappe.db.exists("Custom Field", {"dt": "Delivery Note", "fieldname": fieldname}):
            continue
        frappe.get_doc(
            {
                "doctype": "Custom Field",
                "dt": "Delivery Note",
                "fieldname": fieldname,
                "label": label,
                "fieldtype": fieldtype,
                "insert_after": insert_after,
                "hidden": hidden,
            }
        ).insert(ignore_permissions=True)


def create_vehicle_type_field():
    """Add a vehicle_type select to ERPNext Vehicle (v15 lacks it)."""
    if frappe.db.exists("Custom Field", {"dt": "Vehicle", "fieldname": "vehicle_type"}):
        return
    frappe.get_doc(
        {
            "doctype": "Custom Field",
            "dt": "Vehicle",
            "fieldname": "vehicle_type",
            "label": "Vehicle Type",
            "fieldtype": "Select",
            "options": "Motorcycle\nPickup\nVan\nTruck\nOther",
            "insert_after": "model",
        }
    ).insert(ignore_permissions=True)


def create_roles():
    roles = [
        "Delivery Manager",
        "Delivery Dispatcher",
        "Delivery Supervisor",
        "Delivery Rider",
        "Fleet Manager",
        "Fleet Supervisor",
        "Delivery Analyst",
    ]
    for role in roles:
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(
                ignore_permissions=True
            )
