import frappe


def execute():
    """Create the Delivery Note OTP custom fields for sites that installed
    ledgerctrl before they were added to after_install."""
    from ledgerctrl.install import create_delivery_note_otp_fields

    create_delivery_note_otp_fields()
