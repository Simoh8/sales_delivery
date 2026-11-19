import frappe


def on_job_update(doc, method):
    """Doc-event hook: keep batch stats and rider availability in sync."""
    # Batch stat refresh is already handled inside DeliveryJob.on_update.
    # Here we additionally refresh Rider Shift stats for the rider's active shift.
    try:
        if doc.rider_profile:
            shift = frappe.db.get_value(
                "Rider Shift",
                {"rider": doc.rider_profile, "shift_status": "Active"},
                "name",
            )
            if shift:
                from ledgerctrl.ledgerctrl.doctype.rider_shift.rider_shift import RiderShift

                RiderShift.refresh_delivery_stats(shift)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Shift stats refresh failed")
