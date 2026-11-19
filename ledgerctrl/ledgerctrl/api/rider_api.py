import frappe
from frappe import _
from frappe.utils import now_datetime, nowdate, get_datetime
from ledgerctrl.ledgerctrl.api.decorators import jwt_required

ACTIVE_JOB_STATUSES = ["Pending", "Dispatched", "Accepted", "En Route", "Arrived", "In Progress"]


def _get_rider_profile():
    """Resolve the Rider Profile for the current session user."""
    from ledgerctrl.ledgerctrl.doctype.rider_profile.rider_profile import RiderProfile

    return RiderProfile.get_rider_for_user()


def _require_rider():
    rider = _get_rider_profile()
    if not rider:
        frappe.local.response.http_status_code = 403
        frappe.throw(_("No active Rider Profile found for this user"), frappe.PermissionError)
    return rider


@frappe.whitelist()
@jwt_required
def get_my_profile():
    rider = _require_rider()
    profile = frappe.get_doc("Rider Profile", rider)
    return {
        "success_key": 1,
        "data": {
            "name": profile.name,
            "rider_name": profile.rider_name,
            "employee": profile.employee,
            "mobile_number": profile.mobile_number,
            "employment_status": profile.employment_status,
            "verification_status": profile.verification_status,
            "default_vehicle": profile.default_vehicle,
            "operating_zones": [r.zone for r in profile.operating_zones],
        },
    }


@frappe.whitelist()
@jwt_required
def get_availability():
    rider = _require_rider()
    from ledgerctrl.ledgerctrl.doctype.rider_availability.rider_availability import (
        RiderAvailability,
    )

    status = RiderAvailability.get_current_status(rider)
    return {"success_key": 1, "data": status}


@frappe.whitelist()
@jwt_required
def set_availability(status, lat=None, lng=None, notes=None):
    rider = _require_rider()
    valid = ["Available", "Busy", "On Break", "Offline", "Unavailable"]
    if status not in valid:
        frappe.throw(_("Invalid availability status"))

    from ledgerctrl.ledgerctrl.doctype.rider_availability.rider_availability import (
        RiderAvailability,
    )

    # Riders cannot mark themselves Available while they have active jobs
    if status == "Available":
        active = frappe.db.count(
            "Delivery Job",
            {"rider_profile": rider, "status": ["in", ACTIVE_JOB_STATUSES]},
        )
        if active:
            frappe.throw(
                _("Cannot go Available while {0} active deliveries exist").format(active)
            )

    avail_id = RiderAvailability.set_status(
        rider, status, lat=lat, lng=lng, notes=notes
    )
    return {"success_key": 1, "availability_id": avail_id, "status": status}


@frappe.whitelist()
@jwt_required
def update_location(lat, lng, accuracy=None, speed=None, delivery_job=None):
    """Update rider's last known location and optionally log GPS."""
    rider = _require_rider()
    from ledgerctrl.ledgerctrl.doctype.rider_availability.rider_availability import (
        RiderAvailability,
    )

    status = RiderAvailability.get_current_status(rider)
    if status["availability_id"]:
        frappe.db.set_value(
            "Rider Availability",
            status["availability_id"],
            {
                "last_location_latitude": lat,
                "last_location_longitude": lng,
                "last_updated": now_datetime(),
            },
            update_modified=False,
        )

    # If a delivery job is active, also write a GPS Log
    job = delivery_job or status["current_delivery_job"]
    if job:
        try:
            frappe.get_doc(
                {
                    "doctype": "GPS Log",
                    "delivery_job": job,
                    "latitude": lat,
                    "longitude": lng,
                    "accuracy": accuracy,
                    "speed": speed,
                    "timestamp": now_datetime(),
                    "created_via": "Mobile App",
                }
            ).insert(ignore_permissions=True)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "GPS log insert failed")

    return {"success_key": 1}


@frappe.whitelist()
@jwt_required
def clock_in(opening_odometer=None, shift_start=None, shift_end=None):
    rider = _require_rider()
    today = nowdate()

    existing = frappe.db.get_value(
        "Rider Shift",
        {"rider": rider, "shift_date": today, "shift_status": ["in", ["Scheduled", "Active"]]},
        "name",
    )
    if existing:
        frappe.db.set_value(
            "Rider Shift", existing, "shift_status", "Active", update_modified=False
        )
        frappe.db.set_value(
            "Rider Shift",
            existing,
            "actual_clock_in",
            frappe.db.get_value("Rider Shift", existing, "actual_clock_in") or now_datetime(),
            update_modified=False,
        )
        return {"success_key": 1, "shift": existing, "already_exists": True}

    doc = frappe.get_doc(
        {
            "doctype": "Rider Shift",
            "rider": rider,
            "shift_date": today,
            "shift_start": shift_start,
            "shift_end": shift_end,
            "opening_odometer": opening_odometer,
            "actual_clock_in": now_datetime(),
            "shift_status": "Active",
        }
    )
    doc.insert(ignore_permissions=True)
    from ledgerctrl.ledgerctrl.doctype.rider_availability.rider_availability import (
        RiderAvailability,
    )

    RiderAvailability.set_status(rider, "Available", notes="Clocked in")
    return {"success_key": 1, "shift": doc.name}


@frappe.whitelist()
@jwt_required
def clock_out(closing_odometer=None):
    rider = _require_rider()
    shift_name = frappe.db.get_value(
        "Rider Shift",
        {"rider": rider, "shift_status": "Active"},
        "name",
        order_by="creation desc",
    )
    if not shift_name:
        frappe.throw(_("No active shift found"))
    updates = {
        "actual_clock_out": now_datetime(),
        "shift_status": "Completed",
    }
    if closing_odometer is not None:
        updates["closing_odometer"] = closing_odometer
    frappe.db.set_value("Rider Shift", shift_name, updates)
    from ledgerctrl.ledgerctrl.doctype.rider_shift.rider_shift import RiderShift

    RiderShift.refresh_delivery_stats(shift_name)
    return {"success_key": 1, "shift": shift_name}


@frappe.whitelist()
@jwt_required
def get_my_shifts(limit=20):
    rider = _require_rider()
    shifts = frappe.get_all(
        "Rider Shift",
        filters={"rider": rider},
        fields=[
            "name", "shift_date", "shift_start", "shift_end",
            "actual_clock_in", "actual_clock_out", "shift_status",
            "total_working_hours", "total_deliveries", "completed_deliveries",
            "failed_deliveries", "total_distance_travelled",
        ],
        order_by="shift_date desc",
        limit_page_length=min(int(limit), 100),
    )
    return {"success_key": 1, "data": shifts}


@frappe.whitelist()
@jwt_required
def get_my_deliveries(status=None, limit=50, start=0):
    """Assigned delivery jobs for the logged-in rider (paginated)."""
    rider = _require_rider()
    filters = {"rider_profile": rider}
    if status:
        filters["status"] = status
    jobs = frappe.get_all(
        "Delivery Job",
        filters=filters,
        fields=[
            "name", "customer", "customer_name", "customer_address",
            "status", "priority", "scheduled_date", "scheduled_time",
            "latitude", "longitude", "delivery_batch", "delivery_zone",
            "number_of_attempts", "grand_total", "payment_status",
            "completed_at", "creation",
        ],
        order_by="scheduled_date asc, creation desc",
        limit_start=int(start),
        limit_page_length=min(int(limit), 100),
    )
    return {"success_key": 1, "data": jobs}


@frappe.whitelist()
@jwt_required
def get_my_batches():
    rider = _require_rider()
    batches = frappe.get_all(
        "Delivery Batch",
        filters={"assigned_rider": rider},
        fields=[
            "name", "batch_id", "batch_date", "batch_status",
            "total_jobs", "completed_jobs", "pending_jobs", "failed_jobs",
            "dispatch_time", "completion_time",
        ],
        order_by="batch_date desc",
        limit_page_length=50,
    )
    return {"success_key": 1, "data": batches}


@frappe.whitelist()
@jwt_required
def get_batch_detail(batch):
    rider = _require_rider()
    batch_doc = frappe.get_doc("Delivery Batch", batch)
    if batch_doc.assigned_rider != rider:
        frappe.throw(_("Not authorized for this batch"), frappe.PermissionError)
    jobs = [
        {
            "delivery_job": r.delivery_job,
            "stop_sequence": r.stop_sequence,
            "status": frappe.db.get_value("Delivery Job", r.delivery_job, "status"),
            "customer": frappe.db.get_value("Delivery Job", r.delivery_job, "customer"),
        }
        for r in batch_doc.jobs
    ]
    return {"success_key": 1, "data": {"batch": batch_doc.as_dict(), "jobs": jobs}}


@frappe.whitelist()
@jwt_required
def get_my_performance():
    rider = _require_rider()
    from ledgerctrl.ledgerctrl.api.analytics_api import rider_performance

    return rider_performance(rider_name=rider)
