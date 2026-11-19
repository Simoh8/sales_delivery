"""Fleet Command Center APIs.

Read/aggregation endpoints powering the React Fleet Command Center, plus
dispatch actions (assign / unassign delivery). All endpoints require JWT
authentication and enforce delivery/fleet manager roles where appropriate.
"""

import json
import math

import frappe
from frappe import _
from frappe.utils import nowdate, getdate, add_days, now_datetime, get_datetime

from ledgerctrl.ledgerctrl.api.decorators import jwt_required, role_required
from ledgerctrl.ledgerctrl.api import analytics_api

MANAGER_ROLES = (
    "System Manager",
    "Delivery Manager",
    "Delivery Dispatcher",
    "Delivery Supervisor",
    "Delivery Analyst",
    "Fleet Manager",
    "Fleet Supervisor",
    "Sales Manager",
)

ACTIVE_JOB_STATUSES = [
    "Pending", "Dispatched", "Accepted", "En Route", "Arrived", "In Progress",
]
TERMINAL_JOB_STATUSES = ["Completed", "Failed", "Cancelled"]

STALE_MINUTES = 10

# Doctypes exposed through the generic list endpoint.
LISTABLE_DOCTYPES = {
    "Delivery Job",
    "Delivery Batch",
    "Delivery Batch Item",
    "Delivery Attempt",
    "Delivery Event",
    "Delivery Stop",
    "Proof of Delivery",
    "Assignment History",
    "Delivery Expense",
    "Rider Profile",
    "Rider Shift",
    "Rider Availability",
    "Rider Zone",
    "Rider Document",
    "Fleet Assignment",
    "Vehicle Inspection",
    "Fuel Log",
    "Delivery Zone",
    "Delivery SLA",
    "Delivery Settings",
    "Vehicle",
    "Vehicle Maintenance Record",
    "Delivery Trip",
    "Company",
}


def _manager_guard():
    roles = set(frappe.get_roles())
    if "System Manager" in roles:
        return
    if not roles.intersection(MANAGER_ROLES):
        frappe.local.response.http_status_code = 403
        frappe.throw(
            _("Insufficient permissions. Delivery/Fleet manager role required."),
            frappe.PermissionError,
        )


def _date_range(frm=None, to=None, default_days=30):
    frm = getdate(frm) if frm else getdate(add_days(nowdate(), -default_days))
    to = getdate(to) if to else getdate(nowdate())
    if frm > to:
        frm, to = to, frm
    return frm, to


def _haversine_km(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return None
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(2 * r * math.asin(math.sqrt(a)), 2)


def _latest_per_group(doctype, group_field, extra_fields=None):
    """Return {group_value: row dict} for the latest record per group."""
    fields = ["name", group_field] + (extra_fields or [])
    # doctype is only ever called with internal constants
    rows = frappe.db.sql(
        f"""
        SELECT {", ".join("`" + f + "`" for f in fields)}
        FROM `tab{doctype}` t
        JOIN (
            SELECT `{group_field}` g, MAX(name) mx
            FROM `tab{doctype}`
            GROUP BY `{group_field}`
        ) x ON x.g = t.`{group_field}` AND x.mx = t.name
        """,
        as_dict=True,
    )
    return {r[group_field]: r for r in rows}


def _latest_availability():
    return _latest_per_group(
        "Rider Availability",
        "rider",
        [
            "availability_status", "effective_from", "effective_until",
            "current_delivery_job", "last_location_latitude",
            "last_location_longitude", "last_updated", "notes",
        ],
    )


def _latest_gps_for_riders():
    """Latest GPS Log per employee (joined through Rider Profile)."""
    rows = frappe.db.sql(
        """
        SELECT g.driver, g.latitude, g.longitude, g.speed, g.location_accuracy,
               g.timestamp, g.delivery_job, g.vehicle
        FROM `tabGPS Log` g
        JOIN (
            SELECT driver, MAX(name) mx FROM `tabGPS Log`
            WHERE driver IS NOT NULL GROUP BY driver
        ) x ON x.driver = g.driver AND x.mx = g.name
        """,
        as_dict=True,
    )
    return {r.driver: r for r in rows}


def _rider_live_status(avail, gps, now=None):
    """Derive display status for a rider marker."""
    now = now or now_datetime()
    status = (avail or {}).get("availability_status") or "Offline"
    last_updated = (avail or {}).get("last_updated")
    stale = True
    if last_updated:
        try:
            stale = (now - get_datetime(last_updated)).total_seconds() > STALE_MINUTES * 60
        except Exception:
            stale = True
    if gps and gps.get("timestamp"):
        try:
            if (now - get_datetime(gps["timestamp"])).total_seconds() <= STALE_MINUTES * 60:
                stale = False
        except Exception:
            pass
    if status == "Available" and not stale:
        display = "Available"
    elif status == "On Break":
        display = "On Break"
    elif status in ("Busy", "Unavailable"):
        display = "Busy" if status == "Busy" else "Offline"
    else:
        display = "Offline"
    if stale and display not in ("Offline",):
        display = "Stale"
    return display, stale


def _job_counts_by_status(filters=None):
    rows = frappe.get_all(
        "Delivery Job",
        filters=filters or {},
        fields=["status"],
    )
    counts = {}
    for r in rows:
        counts[r.status] = counts.get(r.status, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# Command center summary
# ---------------------------------------------------------------------------

@frappe.whitelist()
@jwt_required
@role_required(*MANAGER_ROLES)
def get_command_center_summary(frm=None, to=None, company=None, branch=None):
    """Operational KPI strip for the Command Center."""
    _manager_guard()
    frm, to = _date_range(frm, to, default_days=1)

    riders = frappe.get_all(
        "Rider Profile",
        filters={"employment_status": "Active"},
        fields=["name", "rider_name", "employee", "default_vehicle", "company"],
    )
    if company:
        riders = [r for r in riders if not r.company or r.company == company]

    avail_map = _latest_availability()
    avail_counts = {"Available": 0, "Busy": 0, "On Break": 0, "Offline": 0, "Unavailable": 0}
    riders_with_location = 0
    for r in riders:
        a = avail_map.get(r.name)
        st = (a or {}).get("availability_status") or "Offline"
        key = st if st in avail_counts else "Offline"
        avail_counts[key] += 1
        if a and a.get("last_location_latitude") is not None:
            riders_with_location += 1

    job_filters = {"scheduled_date": ["between", [frm, to]]}
    if company:
        job_filters["company"] = company
    if branch:
        job_filters["branch"] = branch
    status_counts = _job_counts_by_status(job_filters)

    active_jobs = sum(status_counts.get(s, 0) for s in ACTIVE_JOB_STATUSES)
    completed = status_counts.get("Completed", 0)
    failed = status_counts.get("Failed", 0)
    delayed = frappe.db.count(
        "Delivery Job",
        dict(job_filters, **{
            "status": ["in", ACTIVE_JOB_STATUSES + ["Completed"]],
            "sla_status": "Breached",
        }),
    ) + frappe.db.count(
        "Delivery Job",
        dict(job_filters, **{
            "status": ["in", ACTIVE_JOB_STATUSES],
            "delay_minutes": [">", 0],
        }),
    )

    vehicles = frappe.get_all("Vehicle", fields=["name", "vehicle_type", "license_plate"])
    in_maintenance = frappe.db.count(
        "Vehicle Maintenance Record",
        {"status": ["in", ["Open", "In Progress"]]},
    )
    active_vehicle_names = set(
        frappe.get_all(
            "Delivery Job",
            filters={"status": ["in", ACTIVE_JOB_STATUSES], "vehicle": ["is", "set"]},
            pluck="vehicle",
        )
    )
    active_assignments = set(
        frappe.get_all(
            "Fleet Assignment",
            filters={"assignment_status": "Active"},
            pluck="vehicle",
        )
    )
    vehicles_active = len(
        {v.name for v in vehicles} & (active_vehicle_names | active_assignments)
    )

    # Previous period comparison (same length, immediately before)
    days = (to - frm).days + 1
    p_to = add_days(frm, -1)
    p_from = add_days(p_to, -(days - 1))
    p_filters = {"scheduled_date": ["between", [p_from, p_to]]}
    if company:
        p_filters["company"] = company
    if branch:
        p_filters["branch"] = branch
    p_counts = _job_counts_by_status(p_filters)
    p_active = sum(p_counts.get(s, 0) for s in ACTIVE_JOB_STATUSES)
    p_completed = p_counts.get("Completed", 0)
    p_failed = p_counts.get("Failed", 0)

    def delta(cur, prev):
        if prev in (None, 0):
            return None if cur in (None, 0) else 100.0
        return round((cur - prev) / prev * 100, 1)

    return {
        "success_key": 1,
        "generated_at": str(now_datetime()),
        "period": {"from": str(frm), "to": str(to)},
        "kpis": {
            "total_riders": len(riders),
            "available_riders": avail_counts["Available"],
            "busy_riders": avail_counts["Busy"] + avail_counts["Unavailable"],
            "offline_riders": avail_counts["Offline"] + avail_counts["On Break"],
            "active_deliveries": active_jobs,
            "completed_deliveries": completed,
            "delayed_deliveries": delayed,
            "failed_deliveries": failed,
            "active_vehicles": vehicles_active,
            "vehicles_under_maintenance": in_maintenance,
            "riders_with_location": riders_with_location,
        },
        "previous": {
            "active_deliveries": p_active,
            "completed_deliveries": p_completed,
            "failed_deliveries": p_failed,
        },
        "deltas": {
            "active_deliveries": delta(active_jobs, p_active),
            "completed_deliveries": delta(completed, p_completed),
            "failed_deliveries": delta(failed, p_failed),
        },
    }


# ---------------------------------------------------------------------------
# Live map data
# ---------------------------------------------------------------------------

@frappe.whitelist()
@jwt_required
@role_required(*MANAGER_ROLES)
def get_live_rider_locations():
    """All active riders with latest known position + operational status."""
    _manager_guard()
    riders = frappe.get_all(
        "Rider Profile",
        filters={"employment_status": "Active"},
        fields=["name", "rider_name", "employee", "default_vehicle", "company", "mobile_number"],
    )
    avail_map = _latest_availability()
    gps_by_employee = _latest_gps_for_riders()
    emp_to_rider = {r.employee: r.name for r in riders if r.employee}

    # Active jobs per rider (for status + current delivery)
    active_jobs = frappe.get_all(
        "Delivery Job",
        filters={"status": ["in", ACTIVE_JOB_STATUSES]},
        fields=["name", "rider_profile", "driver", "vehicle", "status",
                "delivery_batch", "sla_status", "delay_minutes", "priority",
                "customer_name", "latitude", "longitude"],
    )
    job_by_rider = {}
    for j in active_jobs:
        key = j.rider_profile or emp_to_rider.get(j.driver)
        if key and key not in job_by_rider:
            job_by_rider[key] = j

    vehicles = {
        v.name: v for v in frappe.get_all(
            "Vehicle", fields=["name", "license_plate", "vehicle_type"]
        )
    }

    out = []
    for r in riders:
        a = avail_map.get(r.name) or {}
        gps = gps_by_employee.get(r.employee) or {}
        job = job_by_rider.get(r.name)

        lat = gps.get("latitude") if gps.get("latitude") is not None else a.get("last_location_latitude")
        lng = gps.get("longitude") if gps.get("longitude") is not None else a.get("last_location_longitude")
        ts = gps.get("timestamp") or a.get("last_updated")

        display_status, stale = _rider_live_status(a, gps)
        if job and job.status in ("En Route", "Arrived", "In Progress"):
            display_status = "Delayed" if (job.delay_minutes or 0) > 0 or job.sla_status == "Breached" else "On Delivery"
        elif job:
            display_status = "Busy"

        vehicle_name = (job.vehicle if job else None) or r.default_vehicle
        veh = vehicles.get(vehicle_name) or {}

        out.append({
            "rider": r.name,
            "rider_name": r.rider_name,
            "employee": r.employee,
            "mobile_number": r.mobile_number,
            "availability_status": a.get("availability_status") or "Offline",
            "status": display_status,
            "stale": stale,
            "latitude": lat,
            "longitude": lng,
            "last_updated": str(ts) if ts else None,
            "speed": gps.get("speed"),
            "accuracy": gps.get("location_accuracy"),
            "current_job": job.name if job else None,
            "current_job_status": job.status if job else None,
            "delivery_batch": job.delivery_batch if job else None,
            "vehicle": vehicle_name,
            "vehicle_type": veh.get("vehicle_type"),
            "license_plate": veh.get("license_plate"),
        })

    # Vehicle markers: latest GPS per vehicle + current assignment
    veh_gps = frappe.db.sql(
        """
        SELECT g.vehicle, g.latitude, g.longitude, g.speed, g.timestamp, g.delivery_job
        FROM `tabGPS Log` g
        JOIN (
            SELECT vehicle v, MAX(name) mx FROM `tabGPS Log`
            WHERE vehicle IS NOT NULL GROUP BY vehicle
        ) x ON x.v = g.vehicle AND x.mx = g.name
        """,
        as_dict=True,
    )
    veh_assign = {
        a.vehicle: a
        for a in frappe.get_all(
            "Fleet Assignment",
            filters={"assignment_status": "Active"},
            fields=["vehicle", "rider", "employee"],
        )
    }
    rider_by_emp = {r.employee: r for r in riders if r.employee}
    vehicles_out = []
    for g in veh_gps:
        v = vehicles.get(g.vehicle)
        if not v:
            continue
        a = veh_assign.get(g.vehicle)
        rider = None
        if a:
            if a.rider:
                rider = next((r for r in riders if r.name == a.rider), None)
            elif a.employee:
                rider = rider_by_emp.get(a.employee)
        vehicles_out.append({
            "vehicle": g.vehicle,
            "license_plate": v.license_plate,
            "vehicle_type": v.vehicle_type,
            "rider": rider.name if rider else None,
            "rider_name": rider.rider_name if rider else None,
            "latitude": g.latitude,
            "longitude": g.longitude,
            "speed": g.speed,
            "last_updated": str(g.timestamp) if g.timestamp else None,
            "delivery_job": g.delivery_job,
        })

    return {"success_key": 1, "generated_at": str(now_datetime()),
            "riders": out, "vehicles": vehicles_out}


@frappe.whitelist()
@jwt_required
@role_required(*MANAGER_ROLES)
def get_active_delivery_locations():
    """Active delivery jobs with destination coords + stop sequence."""
    _manager_guard()
    jobs = frappe.get_all(
        "Delivery Job",
        filters={
            "status": ["in", ACTIVE_JOB_STATUSES],
            "latitude": ["is", "set"],
            "longitude": ["is", "set"],
        },
        fields=[
            "name", "customer", "customer_name", "status", "priority",
            "latitude", "longitude", "scheduled_date", "scheduled_time",
            "scheduled_delivery_end", "rider_profile", "driver", "vehicle",
            "delivery_batch", "delivery_zone", "sla_status", "delay_minutes",
            "number_of_attempts", "estimated_distance", "grand_total",
            "dispatched_at", "accepted_at", "en_route_at", "arrived_at",
        ],
        order_by="scheduled_date asc, creation asc",
        limit_page_length=1000,
    )

    job_names = [j.name for j in jobs]
    stops = []
    if job_names:
        stops = frappe.get_all(
            "Delivery Stop",
            filters={"delivery_job": ["in", job_names]},
            fields=["name", "delivery_job", "stop_sequence", "stop_type",
                    "stop_status", "latitude", "longitude", "customer",
                    "expected_arrival", "actual_arrival"],
            order_by="stop_sequence asc",
        )
    stops_by_job = {}
    for s in stops:
        stops_by_job.setdefault(s.delivery_job, []).append(s)

    rider_names = {
        r.name: r.rider_name
        for r in frappe.get_all(
            "Rider Profile", filters={"name": ["in", [j.rider_profile for j in jobs if j.rider_profile]]},
            fields=["name", "rider_name"],
        )
    } if any(j.rider_profile for j in jobs) else {}

    result = []
    for j in jobs:
        result.append({
            "name": j.name,
            "customer": j.customer,
            "customer_name": j.customer_name,
            "status": j.status,
            "priority": j.priority,
            "latitude": j.latitude,
            "longitude": j.longitude,
            "scheduled_date": str(j.scheduled_date) if j.scheduled_date else None,
            "scheduled_time": str(j.scheduled_time) if j.scheduled_time else None,
            "scheduled_delivery_end": str(j.scheduled_delivery_end) if j.scheduled_delivery_end else None,
            "rider": j.rider_profile,
            "rider_name": rider_names.get(j.rider_profile),
            "driver": j.driver,
            "vehicle": j.vehicle,
            "delivery_batch": j.delivery_batch,
            "delivery_zone": j.delivery_zone,
            "sla_status": j.sla_status,
            "delay_minutes": j.delay_minutes,
            "number_of_attempts": j.number_of_attempts,
            "estimated_distance": j.estimated_distance,
            "grand_total": j.grand_total,
            "dispatched_at": str(j.dispatched_at) if j.dispatched_at else None,
            "accepted_at": str(j.accepted_at) if j.accepted_at else None,
            "en_route_at": str(j.en_route_at) if j.en_route_at else None,
            "arrived_at": str(j.arrived_at) if j.arrived_at else None,
            "stops": [
                {
                    "name": s.name, "stop_sequence": s.stop_sequence,
                    "stop_type": s.stop_type, "stop_status": s.stop_status,
                    "latitude": s.latitude, "longitude": s.longitude,
                    "customer": s.customer,
                    "expected_arrival": str(s.expected_arrival) if s.expected_arrival else None,
                    "actual_arrival": str(s.actual_arrival) if s.actual_arrival else None,
                }
                for s in stops_by_job.get(j.name, [])
            ],
        })
    return {"success_key": 1, "deliveries": result}


# ---------------------------------------------------------------------------
# Dispatch board
# ---------------------------------------------------------------------------

@frappe.whitelist()
@jwt_required
@role_required(*MANAGER_ROLES)
def get_available_riders():
    """Riders eligible for assignment right now."""
    _manager_guard()
    riders = frappe.get_all(
        "Rider Profile",
        filters={"employment_status": "Active"},
        fields=["name", "rider_name", "employee", "default_vehicle", "company"],
    )
    avail_map = _latest_availability()
    active_jobs = frappe.get_all(
        "Delivery Job",
        filters={"status": ["in", ACTIVE_JOB_STATUSES]},
        fields=["name", "rider_profile", "driver"],
    )
    emp_to_rider = {r.employee: r.name for r in riders if r.employee}
    jobs_by_rider = {}
    for j in active_jobs:
        key = j.rider_profile or emp_to_rider.get(j.driver)
        if key:
            jobs_by_rider.setdefault(key, []).append(j.name)

    vehicles = {
        v.name: v for v in frappe.get_all(
            "Vehicle", fields=["name", "license_plate", "vehicle_type"]
        )
    }
    active_assign = {
        a.rider: a.vehicle
        for a in frappe.get_all(
            "Fleet Assignment",
            filters={"assignment_status": "Active"},
            fields=["rider", "vehicle"],
        )
    }

    out = []
    for r in riders:
        a = avail_map.get(r.name) or {}
        st = a.get("availability_status") or "Offline"
        vehicle = active_assign.get(r.name) or r.default_vehicle
        veh = vehicles.get(vehicle) or {}
        jobs = jobs_by_rider.get(r.name, [])
        eligible = st in ("Available", "Busy") and st != "Unavailable"
        if st == "Available" and jobs:
            eligible = False
        out.append({
            "rider": r.name,
            "rider_name": r.rider_name,
            "employee": r.employee,
            "availability_status": st,
            "eligible": eligible and not jobs,
            "has_active_jobs": bool(jobs),
            "active_job_count": len(jobs),
            "active_jobs": jobs[:5],
            "vehicle": vehicle,
            "vehicle_type": veh.get("vehicle_type"),
            "license_plate": veh.get("license_plate"),
            "latitude": a.get("last_location_latitude"),
            "longitude": a.get("last_location_longitude"),
            "last_updated": str(a.get("last_updated")) if a.get("last_updated") else None,
        })
    return {"success_key": 1, "riders": out}


@frappe.whitelist()
@jwt_required
@role_required(*MANAGER_ROLES)
def get_dispatch_board_data():
    """Unassigned jobs + available riders for the dispatch workspace."""
    _manager_guard()
    unassigned = frappe.get_all(
        "Delivery Job",
        filters={
            "status": ["in", ["Pending", "Dispatched"]],
            "rider_profile": ["is", "not set"],
            "driver": ["is", "not set"],
        },
        fields=[
            "name", "customer", "customer_name", "status", "priority",
            "latitude", "longitude", "scheduled_date", "scheduled_time",
            "scheduled_delivery_end", "delivery_batch", "delivery_zone",
            "estimated_distance", "grand_total", "company", "branch",
            "number_of_attempts", "delivery_type",
        ],
        order_by="priority desc, scheduled_date asc, creation asc",
        limit_page_length=500,
    )
    riders = get_available_riders()["riders"]

    # distance from each rider's last location to each job (client can recompute)
    for j in unassigned:
        j["scheduled_date"] = str(j.scheduled_date) if j.scheduled_date else None
        j["scheduled_time"] = str(j.scheduled_time) if j.scheduled_time else None
        j["scheduled_delivery_end"] = str(j.scheduled_delivery_end) if j.scheduled_delivery_end else None

    return {
        "success_key": 1,
        "unassigned_jobs": unassigned,
        "riders": riders,
        "generated_at": str(now_datetime()),
    }


# ---------------------------------------------------------------------------
# Rider snapshot
# ---------------------------------------------------------------------------

@frappe.whitelist()
@jwt_required
@role_required(*MANAGER_ROLES)
def get_rider_snapshot(rider):
    """Rich operational profile for a single rider."""
    _manager_guard()
    if not frappe.db.exists("Rider Profile", rider):
        frappe.throw(_("Rider Profile not found"), frappe.DoesNotExistError)

    profile = frappe.db.get_value(
        "Rider Profile", rider,
        ["name", "rider_name", "employee", "user", "company", "mobile_number",
         "email", "identification_number", "default_vehicle", "joining_date",
         "employment_status", "verification_status"],
        as_dict=True,
    )
    employee_name = frappe.db.get_value("Employee", profile.employee, "employee_name") if profile.employee else None

    avail_map = _latest_availability()
    avail = avail_map.get(rider) or {}
    gps_by_employee = _latest_gps_for_riders()
    gps = gps_by_employee.get(profile.employee) or {}

    lat = gps.get("latitude") if gps.get("latitude") is not None else avail.get("last_location_latitude")
    lng = gps.get("longitude") if gps.get("longitude") is not None else avail.get("last_location_longitude")
    ts = gps.get("timestamp") or avail.get("last_updated")
    display_status, stale = _rider_live_status(avail, gps)

    # Active jobs
    jobs = frappe.get_all(
        "Delivery Job",
        filters={"rider_profile": rider, "status": ["in", ACTIVE_JOB_STATUSES]},
        fields=["name", "customer", "customer_name", "status", "priority",
                "scheduled_date", "delivery_batch", "delivery_zone", "vehicle",
                "latitude", "longitude", "number_of_attempts", "sla_status",
                "delay_minutes", "grand_total", "dispatched_at", "accepted_at"],
        order_by="scheduled_date asc",
    )
    current_job = jobs[0] if jobs else None
    if current_job and current_job.status in ("En Route", "Arrived", "In Progress"):
        display_status = "Delayed" if (current_job.delay_minutes or 0) > 0 or current_job.sla_status == "Breached" else "On Delivery"
    elif current_job:
        display_status = "Busy"

    # Today's shift
    shift = frappe.db.get_value(
        "Rider Shift",
        {"rider": rider, "shift_date": nowdate()},
        ["name", "shift_start", "shift_end", "actual_clock_in", "actual_clock_out",
         "shift_status", "total_working_hours", "total_deliveries",
         "completed_deliveries", "failed_deliveries", "total_distance_travelled",
         "opening_odometer", "closing_odometer"],
        as_dict=True,
    )

    # Vehicle: active fleet assignment else default
    assignment = frappe.db.get_value(
        "Fleet Assignment",
        {"rider": rider, "assignment_status": "Active"},
        ["name", "vehicle", "assignment_start", "opening_odometer"],
        as_dict=True, order_by="assignment_start desc",
    )
    vehicle_name = (assignment.vehicle if assignment else None) or profile.default_vehicle
    vehicle = None
    if vehicle_name:
        vehicle = frappe.db.get_value(
            "Vehicle", vehicle_name,
            ["name", "license_plate", "vehicle_type", "make", "model",
             "last_odometer", "fuel_type", "location", "employee"],
            as_dict=True,
        )
        if vehicle:
            vehicle["vehicle_type"] = frappe.db.get_value(
                "Vehicle", vehicle_name, "vehicle_type"
            ) or vehicle.get("vehicle_type")

    # Today's delivery stats
    today = nowdate()
    today_jobs = frappe.get_all(
        "Delivery Job",
        filters={"rider_profile": rider, "scheduled_date": today},
        fields=["name", "status"],
    )
    today_stats = {
        "total": len(today_jobs),
        "completed": sum(1 for j in today_jobs if j.status == "Completed"),
        "failed": sum(1 for j in today_jobs if j.status == "Failed"),
        "pending": sum(1 for j in today_jobs if j.status in ACTIVE_JOB_STATUSES),
    }

    for j in jobs:
        for k in ("scheduled_date", "dispatched_at", "accepted_at"):
            if j.get(k):
                j[k] = str(j[k])

    return {
        "success_key": 1,
        "rider": {
            "name": profile.name,
            "rider_name": profile.rider_name or employee_name,
            "employee": profile.employee,
            "employee_name": employee_name,
            "user": profile.user,
            "company": profile.company,
            "mobile_number": profile.mobile_number,
            "email": profile.email,
            "identification_number": profile.identification_number,
            "default_vehicle": profile.default_vehicle,
            "joining_date": str(profile.joining_date) if profile.joining_date else None,
            "employment_status": profile.employment_status,
            "verification_status": profile.verification_status,
        },
        "live": {
            "status": display_status,
            "availability_status": avail.get("availability_status") or "Offline",
            "stale": stale,
            "latitude": lat,
            "longitude": lng,
            "last_updated": str(ts) if ts else None,
            "speed": gps.get("speed"),
            "accuracy": gps.get("location_accuracy"),
            "battery_level": None,
        },
        "current_job": current_job,
        "active_jobs": jobs,
        "shift": {k: (str(v) if hasattr(v, "isoformat") else v) for k, v in (shift or {}).items()},
        "vehicle": vehicle,
        "fleet_assignment": {k: (str(v) if hasattr(v, "isoformat") else v) for k, v in (assignment or {}).items()},
        "today": today_stats,
    }


@frappe.whitelist()
@jwt_required
@role_required(*MANAGER_ROLES)
def get_rider_performance(rider, frm=None, to=None):
    _manager_guard()
    frm, to = _date_range(frm, to)
    result = analytics_api.rider_performance(frm=frm, to=to, rider_name=rider)
    result["period"] = {"from": str(frm), "to": str(to)}
    return result


@frappe.whitelist()
@jwt_required
@role_required(*MANAGER_ROLES)
def get_rider_earnings(rider, frm=None, to=None):
    """Earnings snapshot. There is no commission engine; we report actual
    recorded amounts: delivery charges on completed jobs and Delivery
    Expense records. `paid` is only populated when an Expense Claim link
    exists on the expense."""
    _manager_guard()
    frm, to = _date_range(frm, to)

    jobs = frappe.get_all(
        "Delivery Job",
        filters={"rider_profile": rider, "scheduled_date": ["between", [frm, to]]},
        fields=["name", "status", "customer_delivery_charge", "delivery_revenue",
                "actual_delivery_cost", "grand_total"],
    )
    completed = [j for j in jobs if j.status == "Completed"]
    delivery_charges = sum(float(j.customer_delivery_charge or 0) for j in completed)
    delivery_revenue = sum(
        float(j.delivery_revenue)
        if j.delivery_revenue is not None
        else float(j.customer_delivery_charge or j.grand_total or 0)
        - float(j.actual_delivery_cost or 0)
        for j in completed
    )

    expenses = frappe.get_all(
        "Delivery Expense",
        filters={"rider": rider, "expense_date": ["between", [frm, to]]},
        fields=["name", "expense_type", "amount", "expense_status",
                "expense_claim", "delivery_job", "expense_date"],
    )
    by_type = {}
    by_status = {}
    total_expenses = 0.0
    reimbursed = 0.0
    for e in expenses:
        amt = float(e.amount or 0)
        total_expenses += amt
        by_type[e.expense_type or "Other"] = by_type.get(e.expense_type or "Other", 0) + amt
        by_status[e.expense_status or "Draft"] = by_status.get(e.expense_status or "Draft", 0) + amt
        if e.expense_status in ("Reimbursed",) or e.expense_claim:
            reimbursed += amt

    return {
        "success_key": 1,
        "period": {"from": str(frm), "to": str(to)},
        "rider": rider,
        "summary": {
            "deliveries_completed": len(completed),
            "total_delivery_charges": round(delivery_charges, 2),
            "total_delivery_revenue": round(delivery_revenue, 2),
            "total_expenses": round(total_expenses, 2),
            "expenses_reimbursed": round(reimbursed, 2),
            "net_calculated": round(delivery_revenue - total_expenses, 2),
        },
        "expenses_by_type": [{"type": k, "amount": round(v, 2)} for k, v in by_type.items()],
        "expenses_by_status": [{"status": k, "amount": round(v, 2)} for k, v in by_status.items()],
        "note": _("Amounts are calculated from Delivery Job charges and Delivery Expense records. Commission rules and payroll payments are managed outside this module."),
    }


@frappe.whitelist()
@jwt_required
@role_required(*MANAGER_ROLES)
def get_rider_delivery_history(rider, start=0, limit=50, status=None):
    _manager_guard()
    filters = {"rider_profile": rider}
    if status:
        filters["status"] = status
    jobs = frappe.get_all(
        "Delivery Job",
        filters=filters,
        fields=["name", "customer", "customer_name", "customer_address",
                "status", "priority", "scheduled_date", "scheduled_time",
                "dispatched_at", "accepted_at", "arrived_at",
                "started_delivery_at", "completed_at", "actual_delivery_time",
                "delivery_batch", "delivery_zone", "vehicle", "latitude",
                "longitude", "number_of_attempts", "actual_distance",
                "actual_duration", "delay_minutes", "grand_total",
                "payment_status", "delivery_notes", "special_instructions",
                "sla_status", "creation"],
        order_by="scheduled_date desc, creation desc",
        limit_start=int(start),
        limit_page_length=min(int(limit), 100),
    )
    for j in jobs:
        for k in ("scheduled_date", "scheduled_time", "dispatched_at", "accepted_at",
                  "arrived_at", "started_delivery_at", "completed_at",
                  "actual_delivery_time", "creation"):
            if j.get(k):
                j[k] = str(j[k])
    total = frappe.db.count("Delivery Job", filters)
    return {"success_key": 1, "data": jobs, "total": total}


@frappe.whitelist()
@jwt_required
@role_required(*MANAGER_ROLES)
def get_rider_activity_timeline(rider, limit=100):
    """Merged timeline: delivery events, assignments, shift clock events."""
    _manager_guard()
    jobs = frappe.get_all(
        "Delivery Job",
        filters={"rider_profile": rider},
        pluck="name",
        order_by="creation desc",
        limit_page_length=300,
    )
    employee = frappe.db.get_value("Rider Profile", rider, "employee")

    events = []
    if jobs:
        for e in frappe.get_all(
            "Delivery Event",
            filters={"delivery_job": ["in", jobs]},
            fields=["name", "delivery_job", "event_type", "timestamp",
                    "old_status", "new_status", "notes", "reason",
                    "created_via", "latitude", "longitude"],
            order_by="timestamp desc",
            limit_page_length=int(limit),
        ):
            events.append({
                "type": "delivery_event",
                "at": str(e.timestamp),
                "title": e.event_type,
                "delivery_job": e.delivery_job,
                "detail": e.new_status or e.notes or e.reason,
                "sub": f"{e.old_status or ''} → {e.new_status or ''}".strip(" →"),
            })
        for a in frappe.get_all(
            "Assignment History",
            filters={"delivery_job": ["in", jobs]},
            fields=["name", "delivery_job", "assignment_status", "assigned_at",
                    "accepted_at", "rejected_at", "unassigned_at", "assigned_via",
                    "vehicle", "notes", "reason_for_change"],
            order_by="assigned_at desc",
            limit_page_length=int(limit),
        ):
            events.append({
                "type": "assignment",
                "at": str(a.assigned_at),
                "title": f"Assignment {a.assignment_status or ''}".strip(),
                "delivery_job": a.delivery_job,
                "detail": a.reason_for_change or a.notes,
                "sub": a.assigned_via,
            })

    if employee:
        for a in frappe.get_all(
            "Assignment History",
            filters={"driver": employee},
            fields=["name", "delivery_job", "assignment_status", "assigned_at",
                    "accepted_at", "rejected_at", "unassigned_at", "assigned_via",
                    "vehicle", "notes", "reason_for_change"],
            order_by="assigned_at desc",
            limit_page_length=50,
        ):
            events.append({
                "type": "assignment",
                "at": str(a.assigned_at),
                "title": f"Assignment {a.assignment_status or ''}".strip(),
                "delivery_job": a.delivery_job,
                "detail": a.reason_for_change or a.notes,
                "sub": a.assigned_via,
            })

    for s in frappe.get_all(
        "Rider Shift",
        filters={"rider": rider},
        fields=["name", "shift_date", "shift_status", "actual_clock_in",
                "actual_clock_out", "total_working_hours", "total_deliveries",
                "completed_deliveries", "failed_deliveries"],
        order_by="shift_date desc",
        limit_page_length=30,
    ):
        if s.actual_clock_in:
            events.append({
                "type": "shift", "at": str(s.actual_clock_in),
                "title": "Clocked in", "delivery_job": None,
                "detail": f"Shift {s.name} · {s.shift_date}", "sub": s.shift_status,
            })
        if s.actual_clock_out:
            events.append({
                "type": "shift", "at": str(s.actual_clock_out),
                "title": "Clocked out", "delivery_job": None,
                "detail": f"Shift {s.name} · {s.shift_date}",
                "sub": f"{s.total_working_hours or 0}h · {s.completed_deliveries or 0} completed",
            })

    events.sort(key=lambda e: e["at"] or "", reverse=True)
    return {"success_key": 1, "timeline": events[: int(limit)]}


# ---------------------------------------------------------------------------
# Vehicle snapshot
# ---------------------------------------------------------------------------

@frappe.whitelist()
@jwt_required
@role_required(*MANAGER_ROLES)
def get_vehicle_snapshot(vehicle):
    _manager_guard()
    if not frappe.db.exists("Vehicle", vehicle):
        frappe.throw(_("Vehicle not found"), frappe.DoesNotExistError)

    veh = frappe.db.get_value(
        "Vehicle", vehicle,
        ["name", "license_plate", "vehicle_type", "make", "model", "fuel_type",
         "last_odometer", "location", "employee", "acquisition_date",
         "vehicle_value", "chassis_no"],
        as_dict=True,
    )

    assignment = frappe.db.get_value(
        "Fleet Assignment",
        {"vehicle": vehicle, "assignment_status": "Active"},
        ["name", "rider", "employee", "assignment_start", "opening_odometer"],
        as_dict=True, order_by="assignment_start desc",
    )
    rider_name = None
    if assignment and assignment.rider:
        rider_name = frappe.db.get_value("Rider Profile", assignment.rider, "rider_name")
    elif assignment and assignment.employee:
        rider_name = frappe.db.get_value("Employee", assignment.employee, "employee_name")

    active_job = frappe.db.get_value(
        "Delivery Job",
        {"vehicle": vehicle, "status": ["in", ACTIVE_JOB_STATUSES]},
        ["name", "customer_name", "status", "rider_profile"],
        as_dict=True, order_by="creation desc",
    )

    # Latest GPS for vehicle
    gps = frappe.db.get_value(
        "GPS Log",
        {"vehicle": vehicle},
        ["latitude", "longitude", "speed", "timestamp", "delivery_job"],
        as_dict=True, order_by="timestamp desc",
    )

    latest_inspection = frappe.db.get_value(
        "Vehicle Inspection",
        {"vehicle": vehicle},
        ["name", "inspection_date", "inspection_type", "inspection_result",
         "odometer_reading", "defects_identified"],
        as_dict=True, order_by="inspection_date desc",
    )

    next_service = frappe.db.get_value(
        "Vehicle Maintenance Record",
        {"vehicle": vehicle, "next_service_date": ["is", "set"]},
        ["next_service_date", "next_service_odometer"],
        as_dict=True, order_by="next_service_date asc",
    )

    # Stats (last 30 days)
    frm, to = _date_range(None, None, 30)
    fuel = frappe.db.sql(
        """SELECT COALESCE(SUM(quantity),0) qty, COALESCE(SUM(total_cost),0) cost,
                  COALESCE(SUM(consumption_kmpl),0) kmpl
           FROM `tabFuel Log` WHERE vehicle=%s AND fuel_date BETWEEN %s AND %s""",
        (vehicle, frm, to), as_dict=True,
    )[0]
    maint_cost = frappe.db.sql(
        """SELECT COALESCE(SUM(total_cost),0) cost, COUNT(*) n
           FROM `tabVehicle Maintenance Record`
           WHERE vehicle=%s AND maintenance_date BETWEEN %s AND %s AND status != 'Cancelled'""",
        (vehicle, frm, to), as_dict=True,
    )[0]
    deliveries = frappe.db.count(
        "Delivery Job",
        {"vehicle": vehicle, "status": "Completed",
         "scheduled_date": ["between", [frm, to]]},
    )
    distance = frappe.db.sql(
        """SELECT COALESCE(SUM(actual_distance),0) d FROM `tabDelivery Job`
           WHERE vehicle=%s AND scheduled_date BETWEEN %s AND %s""",
        (vehicle, frm, to),
    )[0][0]

    def _s(v):
        return str(v) if v and hasattr(v, "isoformat") else v

    return {
        "success_key": 1,
        "vehicle": {k: _s(v) for k, v in (veh or {}).items()},
        "assignment": {k: _s(v) for k, v in (assignment or {}).items()} or None,
        "assigned_rider_name": rider_name,
        "active_job": {k: _s(v) for k, v in (active_job or {}).items()} or None,
        "last_location": {
            "latitude": gps.latitude if gps else None,
            "longitude": gps.longitude if gps else None,
            "speed": gps.speed if gps else None,
            "timestamp": str(gps.timestamp) if gps and gps.timestamp else None,
        } if gps else None,
        "latest_inspection": {k: _s(v) for k, v in (latest_inspection or {}).items()} or None,
        "next_service": {k: _s(v) for k, v in (next_service or {}).items()} or None,
        "stats_30d": {
            "fuel_quantity": float(fuel.qty or 0),
            "fuel_cost": float(fuel.cost or 0),
            "fuel_efficiency_kmpl": round(float(fuel.kmpl or 0), 2),
            "maintenance_cost": float(maint_cost.cost or 0),
            "maintenance_count": maint_cost.n,
            "completed_deliveries": deliveries,
            "distance_km": round(float(distance or 0), 2),
            "period": {"from": str(frm), "to": str(to)},
        },
    }


@frappe.whitelist()
@jwt_required
@role_required(*MANAGER_ROLES)
def get_vehicle_performance(vehicle, frm=None, to=None):
    _manager_guard()
    frm, to = _date_range(frm, to)
    result = analytics_api.fleet_performance(frm=frm, to=to, vehicle=vehicle)
    by_vehicle = [v for v in result.get("by_vehicle", []) if v["vehicle"] == vehicle]
    return {
        "success_key": 1,
        "vehicle": by_vehicle[0] if by_vehicle else None,
        "fleet": result.get("fleet", {}),
        "period": {"from": str(frm), "to": str(to)},
    }


# ---------------------------------------------------------------------------
# Delivery snapshot + route
# ---------------------------------------------------------------------------

@frappe.whitelist()
@jwt_required
@role_required(*MANAGER_ROLES)
def get_delivery_snapshot(delivery_job):
    _manager_guard()
    job = frappe.db.get_value(
        "Delivery Job", delivery_job,
        ["name", "customer", "customer_name", "customer_address", "customer_contact",
         "delivery_note", "delivery_trip", "driver", "driver_name", "rider_profile",
         "assigned_employee", "vehicle", "scheduled_date", "scheduled_time",
         "scheduled_delivery_start", "scheduled_delivery_end", "delivery_type",
         "delivery_batch", "delivery_zone", "delivery_sla", "branch", "company",
         "status", "priority", "estimated_distance", "estimated_duration",
         "latitude", "longitude", "location_accuracy", "dispatched_at",
         "accepted_at", "en_route_at", "arrived_at", "started_delivery_at",
         "completed_at", "cancelled_at", "actual_distance", "actual_duration",
         "delay_minutes", "actual_pickup_time", "actual_delivery_time",
         "first_attempt_date", "number_of_attempts", "customer_delivery_charge",
         "actual_delivery_cost", "delivery_revenue", "cod_expected", "cod_collected",
         "sla_status", "proof_of_delivery", "grand_total", "payment_status",
         "delivery_notes", "special_instructions", "created_via", "creation",
         "modified"],
        as_dict=True,
    )
    if not job:
        frappe.throw(_("Delivery Job not found"), frappe.DoesNotExistError)

    rider_name = frappe.db.get_value("Rider Profile", job.rider_profile, "rider_name") if job.rider_profile else None
    vehicle_plate = frappe.db.get_value("Vehicle", job.vehicle, "license_plate") if job.vehicle else None
    zone_name = frappe.db.get_value("Delivery Zone", job.delivery_zone, "zone_name") if job.delivery_zone else None

    items = frappe.get_all(
        "Delivery Job Item",
        filters={"parent": delivery_job},
        fields=["item_code", "item_name", "qty", "uom", "rate", "amount"],
    )
    attempts = frappe.get_all(
        "Delivery Attempt",
        filters={"delivery_job": delivery_job},
        fields=["name", "attempt_number", "attempt_status", "failure_reason",
                "attempt_date", "arrival_time", "completion_time", "rider",
                "vehicle", "gps_latitude", "gps_longitude", "notes", "attachment"],
        order_by="attempt_number asc",
    )
    pods = frappe.get_all(
        "Proof of Delivery",
        filters={"delivery_job": delivery_job},
        fields=["name", "recipient_name", "recipient_phone", "received_by",
                "delivery_timestamp", "gps_latitude", "gps_longitude",
                "customer_signature", "delivery_photograph",
                "otp_verification_status", "otp_verified_at", "notes"],
        order_by="delivery_timestamp desc",
    )
    events = frappe.get_all(
        "Delivery Event",
        filters={"delivery_job": delivery_job},
        fields=["name", "event_type", "timestamp", "old_status", "new_status",
                "notes", "reason", "created_via", "latitude", "longitude"],
        order_by="timestamp asc",
    )
    stops = frappe.get_all(
        "Delivery Stop",
        filters={"delivery_job": delivery_job},
        fields=["name", "stop_sequence", "stop_type", "stop_status", "customer",
                "latitude", "longitude", "expected_arrival", "actual_arrival",
                "departure_time", "waiting_duration", "notes"],
        order_by="stop_sequence asc",
    )
    expenses = frappe.get_all(
        "Delivery Expense",
        filters={"delivery_job": delivery_job},
        fields=["name", "expense_type", "amount", "expense_status",
                "expense_date", "description"],
    )

    def _s(doc):
        return {k: (str(v) if v and hasattr(v, "isoformat") else v)
                for k, v in doc.items()} if doc else None

    return {
        "success_key": 1,
        "job": _s(job),
        "rider_name": rider_name,
        "vehicle_plate": vehicle_plate,
        "zone_name": zone_name,
        "items": items,
        "attempts": [_s(a) for a in attempts],
        "proofs_of_delivery": [_s(p) for p in pods],
        "events": [_s(e) for e in events],
        "stops": [_s(s) for s in stops],
        "expenses": [_s(e) for e in expenses],
    }


@frappe.whitelist()
@jwt_required
@role_required(*MANAGER_ROLES)
def get_delivery_route(delivery_job, limit=500):
    """GPS trail for a delivery job + rider's current position."""
    _manager_guard()
    points = frappe.get_all(
        "GPS Log",
        filters={"delivery_job": delivery_job},
        fields=["latitude", "longitude", "speed", "location_accuracy", "timestamp",
                "heading", "address"],
        order_by="timestamp asc",
        limit_page_length=min(int(limit), 2000),
    )
    job = frappe.db.get_value(
        "Delivery Job", delivery_job,
        ["name", "status", "rider_profile", "driver", "latitude", "longitude",
         "vehicle"],
        as_dict=True,
    )
    rider_pos = None
    if job and job.status in ACTIVE_JOB_STATUSES:
        avail = _latest_availability()
        a = avail.get(job.rider_profile) or {}
        if a.get("last_location_latitude") is not None:
            rider_pos = {
                "latitude": a.last_location_latitude,
                "longitude": a.last_location_longitude,
                "last_updated": str(a.last_updated),
            }
    for p in points:
        p["timestamp"] = str(p.timestamp)
    return {
        "success_key": 1,
        "delivery_job": delivery_job,
        "job": {k: (str(v) if v and hasattr(v, "isoformat") else v)
                for k, v in (job or {}).items()},
        "points": points,
        "rider_position": rider_pos,
    }


# ---------------------------------------------------------------------------
# Dispatch actions
# ---------------------------------------------------------------------------

def _validate_assignment(delivery_job, rider, vehicle=None):
    """Server-side validation before assigning a delivery to a rider."""
    job = frappe.db.get_value(
        "Delivery Job", delivery_job,
        ["name", "status", "rider_profile", "driver", "vehicle",
         "delivery_batch", "company", "branch"],
        as_dict=True,
    )
    if not job:
        frappe.throw(_("Delivery Job not found"), frappe.DoesNotExistError)
    if job.status in TERMINAL_JOB_STATUSES:
        frappe.throw(_("Cannot assign a {0} delivery").format(job.status))
    if job.rider_profile or job.driver:
        frappe.throw(_("Delivery is already assigned"))

    rp = frappe.db.get_value(
        "Rider Profile", rider,
        ["name", "rider_name", "employment_status", "employee",
         "default_vehicle", "company"],
        as_dict=True,
    )
    if not rp:
        frappe.throw(_("Rider Profile not found"), frappe.DoesNotExistError)
    if rp.employment_status != "Active":
        frappe.throw(_("Rider is not active"))

    avail = (_latest_availability().get(rider) or {}).get("availability_status")
    if avail in ("Offline", "Unavailable", "On Break"):
        frappe.throw(_("Rider availability is {0}").format(avail or "unknown"))

    active_jobs = frappe.db.count(
        "Delivery Job",
        {"rider_profile": rider, "status": ["in", ACTIVE_JOB_STATUSES]},
    )
    allow_multiple = frappe.db.get_single_value(
        "Delivery Settings", "allow_multiple_active_deliveries"
    )
    if active_jobs and not allow_multiple:
        frappe.throw(
            _("Rider already has {0} active deliveries").format(active_jobs)
        )

    vehicle = vehicle or rp.default_vehicle
    if vehicle:
        assignment = frappe.db.get_value(
            "Fleet Assignment",
            {"vehicle": vehicle, "assignment_status": "Active"},
            "rider",
        )
        if assignment and assignment != rider:
            frappe.throw(_("Vehicle is currently assigned to another rider"))
        inspections = frappe.get_all(
            "Vehicle Inspection",
            filters={"vehicle": vehicle},
            fields=["inspection_result", "inspection_date"],
            order_by="inspection_date desc",
            limit_page_length=1,
        )
        if inspections and inspections[0].inspection_result == "Failed":
            frappe.throw(_("Vehicle failed its latest inspection"))
    return job, rp, vehicle


@frappe.whitelist()
@jwt_required
@role_required(*MANAGER_ROLES)
def assign_delivery(delivery_job, rider, vehicle=None):
    """Assign a delivery job to a rider (validated server-side)."""
    _manager_guard()
    job, rp, vehicle = _validate_assignment(delivery_job, rider, vehicle)

    updates = {
        "rider_profile": rider,
        "driver": rp.employee,
        "assigned_employee": rp.employee,
    }
    if vehicle:
        updates["vehicle"] = vehicle
    if job.status == "Pending":
        updates["status"] = "Dispatched"
        updates["dispatched_at"] = now_datetime()

    frappe.db.set_value("Delivery Job", delivery_job, updates)

    # Assignment History
    ah = frappe.get_doc(
        {
            "doctype": "Assignment History",
            "delivery_job": delivery_job,
            "driver": rp.employee,
            "driver_name": rp.rider_name,
            "vehicle": vehicle,
            "assigned_by": frappe.session.user,
            "assigned_at": now_datetime(),
            "assigned_via": "Manual",
            "assignment_status": "Assigned",
        }
    )
    ah.insert(ignore_permissions=True)

    frappe.get_doc(
        {
            "doctype": "Delivery Event",
            "delivery_job": delivery_job,
            "event_type": "Assignment",
            "timestamp": now_datetime(),
            "new_status": updates.get("status"),
            "notes": f"Assigned to {rider} by {frappe.session.user}",
            "created_via": "Manual",
        }
    ).insert(ignore_permissions=True)

    frappe.db.commit()
    return {"success_key": 1, "delivery_job": delivery_job, "rider": rider,
            "vehicle": vehicle, "status": updates.get("status", job.status)}


@frappe.whitelist()
@jwt_required
@role_required(*MANAGER_ROLES)
def unassign_delivery(delivery_job, reason=None):
    _manager_guard()
    job = frappe.db.get_value(
        "Delivery Job", delivery_job,
        ["name", "status", "rider_profile", "driver"],
        as_dict=True,
    )
    if not job:
        frappe.throw(_("Delivery Job not found"), frappe.DoesNotExistError)
    if job.status in TERMINAL_JOB_STATUSES:
        frappe.throw(_("Cannot unassign a {0} delivery").format(job.status))

    frappe.db.set_value(
        "Delivery Job", delivery_job,
        {"rider_profile": None, "driver": None, "assigned_employee": None,
         "vehicle": None, "status": "Pending"},
    )
    # Mark latest open assignment history as unassigned
    latest = frappe.db.get_value(
        "Assignment History",
        {"delivery_job": delivery_job, "assignment_status": ["in", ["Assigned", "Accepted"]]},
        "name", order_by="assigned_at desc",
    )
    if latest:
        frappe.db.set_value(
            "Assignment History", latest,
            {"assignment_status": "Unassigned", "unassigned_at": now_datetime(),
             "reason_for_change": reason or "Unassigned by dispatcher"},
        )
    frappe.get_doc(
        {
            "doctype": "Delivery Event",
            "delivery_job": delivery_job,
            "event_type": "Reassignment",
            "timestamp": now_datetime(),
            "old_status": job.status,
            "new_status": "Pending",
            "reason": reason or "Unassigned",
            "notes": f"Unassigned by {frappe.session.user}",
            "created_via": "Manual",
        }
    ).insert(ignore_permissions=True)
    frappe.db.commit()
    return {"success_key": 1, "delivery_job": delivery_job}


# ---------------------------------------------------------------------------
# Analytics wrappers (delegate to analytics_api for consistent calculations)
# ---------------------------------------------------------------------------

@frappe.whitelist()
@jwt_required
@role_required(*MANAGER_ROLES)
def get_delivery_analytics(frm=None, to=None, **filters):
    _manager_guard()
    frm, to = _date_range(frm, to, 30)
    kpis = analytics_api.executive_kpis(frm=frm, to=to, **filters)
    trends = analytics_api.delivery_trends(frm=frm, to=to, group_by="day", **filters)
    status = analytics_api.status_distribution(frm=frm, to=to, **filters)
    sla = analytics_api.sla_compliance(frm=frm, to=to, **filters)
    eff = analytics_api.operational_efficiency(frm=frm, to=to, **filters)
    return {
        "success_key": 1,
        "period": {"from": str(frm), "to": str(to)},
        "kpis": kpis.get("kpis", {}),
        "formulas": kpis.get("formulas", {}),
        "trends": trends.get("data", []),
        "status_distribution": status.get("data", []),
        "sla_compliance": sla.get("data", []),
        "efficiency": eff.get("efficiency", {}),
    }


@frappe.whitelist()
@jwt_required
@role_required(*MANAGER_ROLES)
def get_rider_analytics(frm=None, to=None, **filters):
    _manager_guard()
    frm, to = _date_range(frm, to, 30)
    return analytics_api.rider_performance(frm=frm, to=to, **filters)


@frappe.whitelist()
@jwt_required
@role_required(*MANAGER_ROLES)
def get_fleet_analytics(frm=None, to=None, **filters):
    _manager_guard()
    frm, to = _date_range(frm, to, 30)
    fleet = analytics_api.fleet_performance(frm=frm, to=to, **filters)
    fuel = analytics_api.fuel_trends(frm=frm, to=to, **filters)
    fleet["fuel_trends"] = fuel.get("data", [])
    fleet["period"] = {"from": str(frm), "to": str(to)}
    return fleet


@frappe.whitelist()
@jwt_required
@role_required(*MANAGER_ROLES)
def get_geographic_analytics(frm=None, to=None, **filters):
    _manager_guard()
    frm, to = _date_range(frm, to, 30)
    geo = analytics_api.geographic_analytics(frm=frm, to=to, **filters)
    geo["period"] = {"from": str(frm), "to": str(to)}
    return geo


# ---------------------------------------------------------------------------
# Generic list + meta endpoints for module pages
# ---------------------------------------------------------------------------

def _sanitize_filters(raw):
    """Validate a JSON filter dict against DocType meta fields."""
    if not raw:
        return {}
    if isinstance(raw, str):
        raw = json.loads(raw)
    return raw or {}


@frappe.whitelist()
@jwt_required
@role_required(*MANAGER_ROLES)
def get_doctype_fields(doctype):
    """Return field metadata for allowlisted doctypes (for dynamic tables)."""
    _manager_guard()
    if doctype not in LISTABLE_DOCTYPES:
        frappe.throw(_("Doctype not allowed"), frappe.PermissionError)
    meta = frappe.get_meta(doctype)
    fields = []
    for f in meta.fields:
        if f.fieldtype in ("Section Break", "Column Break", "Tab Break", "HTML", "Button"):
            continue
        if f.fieldtype == "Table":
            continue
        fields.append({
            "fieldname": f.fieldname,
            "label": f.label or f.fieldname,
            "fieldtype": f.fieldtype,
            "options": f.options,
        })
    return {"success_key": 1, "doctype": doctype, "fields": fields}


@frappe.whitelist()
@jwt_required
@role_required(*MANAGER_ROLES)
def list_doctype(doctype, filters=None, fields=None, or_filters=None,
                 order_by=None, limit_start=0, limit_page_length=50):
    """Generic paginated list for allowlisted DocTypes.

    `filters` is a JSON object: {field: value} or {field: [op, value]}.
    `fields` is a comma-separated list (validated against meta).
    """
    _manager_guard()
    if doctype not in LISTABLE_DOCTYPES:
        frappe.throw(_("Doctype not allowed"), frappe.PermissionError)

    meta = frappe.get_meta(doctype)
    valid = {f.fieldname for f in meta.fields} | {"name", "creation", "modified"}

    def clean_field_list(fl):
        if not fl:
            return None
        names = [x.strip() for x in fl.split(",") if x.strip()]
        bad = [x for x in names if x not in valid]
        if bad:
            frappe.throw(_("Invalid fields: {0}").format(", ".join(bad)))
        return names

    field_list = clean_field_list(fields) or [
        "name", "creation", "modified"
    ]

    f = _sanitize_filters(filters)
    clean_filters = {}
    for k, v in f.items():
        if k not in valid:
            frappe.throw(_("Invalid filter field: {0}").format(k))
        clean_filters[k] = v

    orf = None
    if or_filters:
        try:
            orf = json.loads(or_filters) if isinstance(or_filters, str) else or_filters
        except Exception:
            orf = None
        if isinstance(orf, dict):
            orf = [
                [k] + (v if isinstance(v, list) else [v])
                for k, v in orf.items() if k in valid
            ] or None

    if meta.issingle:
        doc = frappe.get_doc(doctype)
        data = doc.as_dict()
        keep = set(field_list) | {"name", "creation", "modified"}
        row = {k: v for k, v in data.items() if k in keep}
        for k, v in list(row.items()):
            if v is not None and hasattr(v, "isoformat"):
                row[k] = str(v)
        return {
            "success_key": 1,
            "doctype": doctype,
            "data": [row],
            "total": 1,
            "start": 0,
            "page_length": 1,
        }

    start = max(int(limit_start or 0), 0)
    page = min(max(int(limit_page_length or 50), 1), 500)

    rows = frappe.get_all(
        doctype,
        filters=clean_filters or None,
        or_filters=orf,
        fields=field_list,
        order_by=order_by or "creation desc",
        limit_start=start,
        limit_page_length=page,
    )
    total = frappe.db.count(doctype, filters=clean_filters or None)

    # stringify dates for JSON safety
    for r in rows:
        for k, v in list(r.items()):
            if v is not None and hasattr(v, "isoformat"):
                r[k] = str(v)
    return {
        "success_key": 1,
        "doctype": doctype,
        "data": rows,
        "total": total,
        "start": start,
        "page_length": page,
    }


@frappe.whitelist()
@jwt_required
@role_required(*MANAGER_ROLES)
def get_filter_options(doctype, field):
    """Distinct values for a Link/Data field — used by filter dropdowns."""
    _manager_guard()
    if doctype not in LISTABLE_DOCTYPES:
        frappe.throw(_("Doctype not allowed"), frappe.PermissionError)
    meta = frappe.get_meta(doctype)
    df = meta.get_field(field)
    if not df or df.fieldtype not in ("Link", "Select", "Data"):
        frappe.throw(_("Field not filterable"))
    if df.fieldtype == "Select":
        return {"success_key": 1, "options": [o for o in (df.options or "").split("\n") if o]}
    values = frappe.get_all(doctype, filters={field: ["is", "set"]},
                            pluck=field, distinct=True, limit_page_length=200)
    return {"success_key": 1, "options": sorted(set(values))}
