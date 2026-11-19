import frappe
from frappe import _
from frappe.utils import now_datetime, nowdate, get_datetime
from ledgerctrl.ledgerctrl.api.decorators import jwt_required

ACTIVE_STATUSES = ["Pending", "Dispatched", "Accepted", "En Route", "Arrived", "In Progress"]


def _get_rider():
    from ledgerctrl.ledgerctrl.doctype.rider_profile.rider_profile import RiderProfile

    return RiderProfile.get_rider_for_user()


def _check_job_access(job_name, rider=None):
    job = frappe.db.get_value(
        "Delivery Job",
        job_name,
        ["status", "rider_profile", "driver", "vehicle", "customer", "delivery_batch"],
        as_dict=True,
    )
    if not job:
        frappe.throw(_("Delivery Job not found"), frappe.DoesNotExistError)
    if rider:
        employee = frappe.db.get_value("Rider Profile", rider, "employee")
        if job.rider_profile != rider and job.driver != employee:
            frappe.throw(_("Not authorized for this delivery"), frappe.PermissionError)
    return job


@frappe.whitelist()
@jwt_required
def create_delivery_attempt(delivery_job, attempt_status, failure_reason=None,
                            lat=None, lng=None, notes=None, attachment=None,
                            arrival_time=None, completion_time=None,
                            idempotency_key=None):
    """Record a delivery attempt. Idempotent via idempotency_key."""
    if idempotency_key:
        existing = frappe.db.get_value(
            "Delivery Attempt",
            {"delivery_job": delivery_job, "notes": ["like", f"%{idempotency_key}%"]},
            "name",
        )
        if existing:
            return {"success_key": 1, "attempt": existing, "duplicate": True}

    rider = _get_rider()
    job = _check_job_access(delivery_job, rider=rider)

    vehicle = job.vehicle
    if not vehicle and rider:
        vehicle = frappe.db.get_value("Rider Profile", rider, "default_vehicle")

    attempt = frappe.get_doc(
        {
            "doctype": "Delivery Attempt",
            "delivery_job": delivery_job,
            "attempt_status": attempt_status,
            "failure_reason": failure_reason,
            "gps_latitude": lat,
            "gps_longitude": lng,
            "notes": (notes or "") + (f" [idem:{idempotency_key}]" if idempotency_key else ""),
            "attachment": attachment,
            "arrival_time": get_datetime(arrival_time) if arrival_time else now_datetime(),
            "completion_time": get_datetime(completion_time) if completion_time else now_datetime(),
            "rider": rider,
            "vehicle": vehicle,
        }
    )
    attempt.insert(ignore_permissions=True)
    return {"success_key": 1, "attempt": attempt.name}


@frappe.whitelist()
@jwt_required
def submit_proof_of_delivery(delivery_job, delivery_attempt=None,
                             recipient_name=None, recipient_phone=None,
                             received_by=None, lat=None, lng=None,
                             customer_signature=None, delivery_photograph=None,
                             otp=None, notes=None, idempotency_key=None):
    """Submit digital proof of delivery."""
    if idempotency_key:
        existing = frappe.db.get_value(
            "Proof of Delivery", {"idempotency_key": idempotency_key}, "name"
        )
        if existing:
            return {"success_key": 1, "pod": existing, "duplicate": True}

    rider = _get_rider()
    job = _check_job_access(delivery_job, rider=rider)

    # If the job's Delivery Note has an OTP and one was supplied, verify it
    otp_status = "Not Required"
    otp_verified_at = None
    if otp:
        dn = job.get("delivery_note") if hasattr(job, "get") else frappe.db.get_value(
            "Delivery Job", delivery_job, "delivery_note"
        )
        expected = frappe.db.get_value("Delivery Note", dn, "custom_otp_code") if dn else None
        if expected:
            if str(otp) == str(expected):
                otp_status = "Verified"
                otp_verified_at = now_datetime()
            else:
                otp_status = "Failed"
                frappe.throw(_("Invalid OTP"), frappe.ValidationError)

    pod = frappe.get_doc(
        {
            "doctype": "Proof of Delivery",
            "delivery_job": delivery_job,
            "delivery_attempt": delivery_attempt,
            "recipient_name": recipient_name,
            "recipient_phone": recipient_phone or frappe.db.get_value(
                "Delivery Job", delivery_job, "customer_contact"
            ),
            "received_by": received_by or recipient_name,
            "delivery_timestamp": now_datetime(),
            "gps_latitude": lat,
            "gps_longitude": lng,
            "customer_signature": customer_signature,
            "delivery_photograph": delivery_photograph,
            "otp_verification_status": otp_status,
            "otp_verified_at": otp_verified_at,
            "idempotency_key": idempotency_key,
            "notes": notes,
        }
    )
    pod.insert(ignore_permissions=True)
    return {"success_key": 1, "pod": pod.name}


@frappe.whitelist()
@jwt_required
def update_delivery_stop(stop, stop_status, actual_arrival=None,
                         departure_time=None, lat=None, lng=None, notes=None):
    stop_doc = frappe.get_doc("Delivery Stop", stop)
    # Authorization: rider must own the related job/batch
    rider = _get_rider()
    if rider and stop_doc.delivery_job:
        _check_job_access(stop_doc.delivery_job, rider=rider)
    if stop_status:
        stop_doc.stop_status = stop_status
        if stop_status == "Arrived" and not stop_doc.actual_arrival:
            stop_doc.actual_arrival = get_datetime(actual_arrival) if actual_arrival else now_datetime()
        if stop_status in ("Completed", "Failed", "Skipped"):
            stop_doc.departure_time = (
                get_datetime(departure_time) if departure_time else now_datetime()
            )
    if lat is not None:
        stop_doc.latitude = lat
    if lng is not None:
        stop_doc.longitude = lng
    if notes:
        stop_doc.notes = (stop_doc.notes or "") + "\n" + notes
    stop_doc.save(ignore_permissions=True)
    return {"success_key": 1, "stop": stop_doc.name, "status": stop_doc.stop_status}


@frappe.whitelist()
@jwt_required
def submit_vehicle_inspection(vehicle, inspection_type, odometer_reading=None,
                              fuel_level=None, tyre_condition=None, brakes_condition=None,
                              lights_condition=None, engine_condition=None,
                              general_condition=None, defects_identified=None,
                              attachments=None, lat=None, lng=None):
    rider = _get_rider()
    doc = frappe.get_doc(
        {
            "doctype": "Vehicle Inspection",
            "vehicle": vehicle,
            "rider": rider,
            "inspection_date": now_datetime(),
            "inspection_type": inspection_type,
            "odometer_reading": odometer_reading,
            "fuel_level": fuel_level,
            "tyre_condition": tyre_condition,
            "brakes_condition": brakes_condition,
            "lights_condition": lights_condition,
            "engine_condition": engine_condition,
            "general_condition": general_condition,
            "defects_identified": defects_identified,
            "attachments": attachments,
        }
    )
    doc.insert(ignore_permissions=True)
    return {
        "success_key": 1,
        "inspection": doc.name,
        "result": doc.inspection_result,
    }


@frappe.whitelist()
@jwt_required
def submit_fuel_log(vehicle, fuel_date, quantity, unit_price, fuel_type=None,
                    odometer_reading=None, fuel_station=None, payment_method=None,
                    receipt_attachment=None, notes=None, idempotency_key=None):
    """Submit a fuel log. Requires Fleet Manager/Supervisor or Delivery Manager role,
    or the rider assigned to the vehicle."""
    if idempotency_key:
        existing = frappe.db.get_value("Fuel Log", {"idempotency_key": idempotency_key}, "name")
        if existing:
            return {"success_key": 1, "fuel_log": existing, "duplicate": True}

    rider = _get_rider()
    user_roles = frappe.get_roles()
    allowed_roles = {"Fleet Manager", "Fleet Supervisor", "Delivery Manager", "System Manager"}
    if not allowed_roles.intersection(user_roles):
        # Riders may only log fuel for their assigned/default vehicle
        assigned = frappe.db.get_value(
            "Fleet Assignment",
            {"vehicle": vehicle, "assignment_status": "Active"},
            "rider",
        )
        default_vehicle = (
            frappe.db.get_value("Rider Profile", rider, "default_vehicle") if rider else None
        )
        if not rider or (assigned != rider and default_vehicle != vehicle):
            frappe.throw(_("Not authorized to log fuel for this vehicle"), frappe.PermissionError)

    doc = frappe.get_doc(
        {
            "doctype": "Fuel Log",
            "vehicle": vehicle,
            "rider": rider,
            "fuel_date": get_datetime(fuel_date).date() if fuel_date else nowdate(),
            "fuel_type": fuel_type,
            "quantity": quantity,
            "unit_price": unit_price,
            "odometer_reading": odometer_reading,
            "fuel_station": fuel_station,
            "payment_method": payment_method,
            "receipt_attachment": receipt_attachment,
            "idempotency_key": idempotency_key,
            "notes": notes,
        }
    )
    doc.insert(ignore_permissions=True)
    return {
        "success_key": 1,
        "fuel_log": doc.name,
        "total_cost": doc.total_cost,
        "flag_reason": doc.flag_reason,
    }


@frappe.whitelist()
@jwt_required
def submit_delivery_expense(delivery_job=None, delivery_batch=None, vehicle=None,
                            expense_date=None, expense_type=None, amount=None,
                            description=None, receipt_attachment=None,
                            idempotency_key=None):
    if idempotency_key:
        existing = frappe.db.get_value(
            "Delivery Expense", {"idempotency_key": idempotency_key}, "name"
        )
        if existing:
            return {"success_key": 1, "expense": existing, "duplicate": True}

    rider = _get_rider()
    doc = frappe.get_doc(
        {
            "doctype": "Delivery Expense",
            "delivery_job": delivery_job,
            "delivery_batch": delivery_batch,
            "vehicle": vehicle,
            "rider": rider,
            "expense_date": get_datetime(expense_date).date() if expense_date else nowdate(),
            "expense_type": expense_type,
            "amount": amount,
            "description": description,
            "receipt_attachment": receipt_attachment,
            "idempotency_key": idempotency_key,
        }
    )
    doc.insert(ignore_permissions=True)
    return {"success_key": 1, "expense": doc.name}


@frappe.whitelist()
@jwt_required
def sync_offline(payloads):
    """Batch offline-sync endpoint. `payloads` is a list of dicts:
    {"type": "attempt"|"pod"|"fuel_log"|"expense"|"gps", ...fields}
    Each item may carry idempotency_key for deduplication.
    """
    import json

    if isinstance(payloads, str):
        payloads = json.loads(payloads)
    results = []
    for item in payloads or []:
        item_type = item.pop("type", None)
        try:
            if item_type == "attempt":
                res = create_delivery_attempt(**item)
            elif item_type == "pod":
                res = submit_proof_of_delivery(**item)
            elif item_type == "fuel_log":
                res = submit_fuel_log(**item)
            elif item_type == "expense":
                res = submit_delivery_expense(**item)
            elif item_type == "gps":
                res = update_location(**item)
            else:
                res = {"success_key": 0, "error": "unknown type"}
            results.append({"type": item_type, "result": res})
        except Exception as e:
            frappe.db.rollback()
            results.append({"type": item_type, "success_key": 0, "error": str(e)})
    frappe.db.commit()
    return {"success_key": 1, "results": results}


@frappe.whitelist()
@jwt_required
def update_job_status(delivery_job, new_status, notes=None, lat=None, lng=None):
    """Driver-facing status transition with server-side validation."""
    rider = _get_rider()
    job_doc = frappe.get_doc("Delivery Job", delivery_job)
    _check_job_access(delivery_job, rider=rider)
    if job_doc.status in ("Completed", "Cancelled"):
        frappe.throw(_("Cannot modify a {0} delivery").format(job_doc.status))
    job_doc.update_status(new_status, notes=notes)
    if lat is not None and lng is not None:
        job_doc.add_gps_log(lat, lng)
    return {"success_key": 1, "status": job_doc.status}
