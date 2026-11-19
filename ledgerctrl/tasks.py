"""Scheduled tasks for ledgerctrl delivery/fleet operations."""
import frappe
from frappe.utils import nowdate, add_days, now_datetime, getdate


def all():
    """Runs on every scheduler tick."""
    update_overdue_delivery_status()


def hourly():
    """Hourly checks: SLA breach flags, batch status refresh."""
    flag_sla_breaches()
    refresh_active_batches()


def daily():
    """Daily summaries and alerts."""
    check_missing_clock_ins()
    check_vehicle_maintenance_due()
    check_document_expiries()
    check_overdue_deliveries()
    generate_daily_summaries()


def weekly():
    pass


def monthly():
    pass


def update_overdue_delivery_status():
    """Mark deliveries past their scheduled end as delayed (SLA flag only)."""
    frappe.db.sql(
        """
        UPDATE `tabDelivery Job`
        SET sla_status = 'Breached'
        WHERE status IN ('Dispatched','Accepted','En Route','Arrived','In Progress')
          AND delivery_sla IS NOT NULL AND delivery_sla != ''
          AND scheduled_delivery_end IS NOT NULL
          AND scheduled_delivery_end < %s
          AND (sla_status IS NULL OR sla_status != 'Breached')
        """,
        (now_datetime(),),
    )
    frappe.db.commit()


def flag_sla_breaches():
    update_overdue_delivery_status()


def refresh_active_batches():
    batches = frappe.get_all(
        "Delivery Batch",
        filters={"batch_status": ["in", ["Dispatched", "In Progress"]]},
        pluck="name",
        limit_page_length=200,
    )
    from ledgerctrl.ledgerctrl.doctype.delivery_batch.delivery_batch import DeliveryBatch

    for b in batches:
        try:
            DeliveryBatch.refresh_batch_stats(b)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Batch refresh failed: {0}".format(b))


def check_missing_clock_ins():
    """Alert when a scheduled shift's start time has passed without clock-in."""
    today = nowdate()
    now_time = now_datetime().time()
    shifts = frappe.get_all(
        "Rider Shift",
        filters={
            "shift_date": today,
            "shift_status": "Scheduled",
            "shift_start": ["<", str(now_time)],
        },
        fields=["name", "rider", "shift_start"],
        limit_page_length=200,
    )
    for s in shifts:
        frappe.publish_realtime(
            "ledgerctrl:shift_no_clockin",
            {"shift": s.name, "rider": s.rider},
            user=frappe.session.user,
        )
        frappe.get_doc(
            {
                "doctype": "ToDo",
                "allocated_to": "Delivery Manager",
                "description": "Rider shift {0} started at {1} but rider has not clocked in.".format(
                    s.name, s.shift_start
                ),
                "status": "Open",
                "priority": "Medium",
                "date": today,
            }
        ).insert(ignore_permissions=True)


def check_vehicle_maintenance_due():
    settings = frappe.get_single("Delivery Settings")
    days = getattr(settings, "maintenance_reminder_days", 7) or 7
    due = frappe.db.sql(
        """
        SELECT name, vehicle, next_service_date
        FROM `tabVehicle Maintenance Record`
        WHERE status != 'Cancelled'
          AND next_service_date IS NOT NULL
          AND next_service_date <= %s
        """,
        (add_days(nowdate(), days),),
        as_dict=True,
    )
    for r in due:
        frappe.get_doc(
            {
                "doctype": "ToDo",
                "allocated_to": "Fleet Manager",
                "description": "Vehicle {0} maintenance {1} is due on {2}.".format(
                    r.vehicle, r.name, r.next_service_date
                ),
                "status": "Open",
                "priority": "High",
                "date": nowdate(),
            }
        ).insert(ignore_permissions=True)


def check_document_expiries():
    settings = frappe.get_single("Delivery Settings")
    days = getattr(settings, "document_expiry_alert_days", 30) or 30
    expiring = frappe.db.sql(
        """
        SELECT name, rider, document_type, expiry_date
        FROM `tabRider Document`
        WHERE expiry_date IS NOT NULL
          AND expiry_date <= %s
          AND verification_status != 'Expired'
        """,
        (add_days(nowdate(), days),),
        as_dict=True,
    )
    for r in expiring:
        frappe.db.set_value(
            "Rider Document", r.name, "verification_status", "Expired",
            update_modified=False,
        ) if r.expiry_date < nowdate() else None
        frappe.get_doc(
            {
                "doctype": "ToDo",
                "allocated_to": "Delivery Supervisor",
                "description": "Rider document {0} ({1}) for {2} expires on {3}.".format(
                    r.document_type, r.name, r.rider, r.expiry_date
                ),
                "status": "Open",
                "priority": "Medium",
                "date": nowdate(),
            }
        ).insert(ignore_permissions=True)


def check_overdue_deliveries():
    overdue = frappe.db.sql(
        """
        SELECT name, rider_profile, scheduled_delivery_end
        FROM `tabDelivery Job`
        WHERE status IN ('Dispatched','Accepted','En Route','Arrived','In Progress')
          AND scheduled_delivery_end IS NOT NULL
          AND scheduled_delivery_end < %s
        """,
        (now_datetime(),),
        as_dict=True,
    )
    for j in overdue:
        frappe.get_doc(
            {
                "doctype": "ToDo",
                "allocated_to": "Delivery Dispatcher",
                "description": "Delivery {0} is overdue (scheduled end {1}).".format(
                    j.name, j.scheduled_delivery_end
                ),
                "status": "Open",
                "priority": "High",
                "date": nowdate(),
            }
        ).insert(ignore_permissions=True)


def generate_daily_summaries():
    """Refresh shift stats and batch stats for yesterday."""
    yesterday = add_days(nowdate(), -1)
    shifts = frappe.get_all(
        "Rider Shift",
        filters={"shift_date": yesterday},
        pluck="name",
        limit_page_length=500,
    )
    from ledgerctrl.ledgerctrl.doctype.rider_shift.rider_shift import RiderShift

    for s in shifts:
        try:
            RiderShift.refresh_delivery_stats(s)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Shift stats failed: {0}".format(s))
    frappe.db.commit()
