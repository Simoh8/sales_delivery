import frappe
from frappe import _
from frappe.utils import nowdate, getdate, add_days
from ledgerctrl.ledgerctrl.api.decorators import jwt_required, role_required

ACTIVE_STATUSES = ["Pending", "Dispatched", "Accepted", "En Route", "Arrived", "In Progress"]
TERMINAL_STATUSES = ["Completed", "Failed", "Cancelled"]


def _filters(frm=None, to=None, **kw):
    """Build common Delivery Job filters from request/kwargs."""
    filters = {}
    if frm:
        filters["scheduled_date"] = [">=", getdate(frm)]
    if to:
        # include the whole 'to' day
        filters.setdefault("scheduled_date", ["<=", getdate(to)]) if not frm else None
        if frm:
            filters["scheduled_date"] = ["between", [getdate(frm), getdate(to)]]
    for field, col in [
        ("company", "company"),
        ("branch", "branch"),
        ("rider", "rider_profile"),
        ("vehicle", "vehicle"),
        ("delivery_zone", "zone"),
        ("delivery_zone", "delivery_zone"),
        ("status", "status"),
        ("delivery_type", "delivery_type"),
        ("delivery_batch", "delivery_batch"),
    ]:
        val = kw.get(field)
        if val:
            filters[col] = val
    return filters


def _job_query(filters):
    return frappe.get_all(
        "Delivery Job",
        filters=filters,
        fields=[
            "name", "status", "scheduled_date", "scheduled_delivery_end",
            "dispatched_at", "accepted_at", "completed_at", "cancelled_at",
            "actual_duration", "actual_distance", "estimated_distance",
            "customer_delivery_charge", "actual_delivery_cost",
            "delivery_revenue", "sla_status", "rider_profile", "vehicle",
            "delivery_zone", "delivery_batch", "number_of_attempts",
            "first_attempt_date", "delivery_type", "branch", "company",
            "grand_total", "delay_minutes",
        ],
    )


def _base_date_range(frm=None, to=None):
    frm = getdate(frm) if frm else add_days(nowdate(), -30)
    to = getdate(to) if to else nowdate()
    return frm, to


@frappe.whitelist()
@jwt_required
@role_required("Delivery Manager", "Delivery Dispatcher", "Delivery Supervisor",
               "Delivery Analyst", "System Manager", "Fleet Manager")
def executive_kpis(frm=None, to=None, **filters):
    """Executive KPI dashboard. All metrics computed via SQL aggregation."""
    frm, to = _base_date_range(frm, to)
    f = _filters(frm, to, **filters)
    vehicle_type = filters.get("vehicle_type")

    jobs = _job_query(f)
    if vehicle_type:
        vehicles = frappe.get_all(
            "Vehicle", filters={"vehicle_type": vehicle_type}, pluck="name"
        )
        jobs = [j for j in jobs if j.vehicle in vehicles]

    total = len(jobs)
    by_status = {}
    for j in jobs:
        by_status[j.status] = by_status.get(j.status, 0) + 1

    completed = by_status.get("Completed", 0)
    failed = by_status.get("Failed", 0)
    cancelled = by_status.get("Cancelled", 0)
    pending = sum(by_status.get(s, 0) for s in ["Pending", "Dispatched"])
    in_transit = sum(by_status.get(s, 0) for s in ["Accepted", "En Route", "Arrived", "In Progress"])

    # Eligible = total minus cancelled
    eligible = total - cancelled
    success_rate = round(completed / eligible * 100, 2) if eligible else 0

    # First attempt success: completed with <=1 attempt / jobs with >=1 attempt
    with_attempts = [j for j in jobs if (j.number_of_attempts or 0) > 0]
    first_attempt_ok = [
        j for j in with_attempts
        if j.status == "Completed" and (j.number_of_attempts or 0) <= 1
    ]
    first_attempt_rate = (
        round(len(first_attempt_ok) / len(with_attempts) * 100, 2) if with_attempts else 0
    )

    # On-time: completed within SLA
    sla_applicable = [j for j in jobs if j.sla_status and j.sla_status != "No SLA"]
    on_time = [j for j in sla_applicable if j.status == "Completed" and j.sla_status == "Met"]
    # fallback: use sla_status Met directly
    on_time = [j for j in jobs if j.sla_status == "Met"]
    on_time_rate = (
        round(len(on_time) / len([j for j in jobs if j.sla_status in ("Met", "Breached")]) * 100, 2)
        if any(j.sla_status in ("Met", "Breached") for j in jobs)
        else 0
    )

    completed_jobs = [j for j in jobs if j.status == "Completed" and j.actual_duration]
    avg_duration = (
        round(sum(j.actual_duration for j in completed_jobs) / len(completed_jobs), 1)
        if completed_jobs
        else 0
    )
    avg_cost = (
        round(sum(float(j.actual_delivery_cost or 0) for j in completed_jobs) / len(completed_jobs), 2)
        if completed_jobs
        else 0
    )
    total_expenses = frappe.db.sql(
        """
        SELECT COALESCE(SUM(amount),0) FROM `tabDelivery Expense`
        WHERE expense_status != 'Cancelled'
          AND expense_date BETWEEN %s AND %s
        """,
        (frm, to),
    )[0][0]
    total_revenue = sum(float(j.delivery_revenue or 0) for j in jobs)
    # Delivery revenue = charge - cost; if not set, use customer charge minus cost
    total_revenue = sum(
        float(j.delivery_revenue)
        if j.delivery_revenue is not None
        else float(j.customer_delivery_charge or j.grand_total or 0)
        - float(j.actual_delivery_cost or 0)
        for j in jobs
    )
    contribution = round(total_revenue - float(total_expenses or 0), 2)

    return {
        "success_key": 1,
        "date_from": str(frm),
        "date_to": str(to),
        "kpis": {
            "total_delivery_jobs": total,
            "completed_deliveries": completed,
            "pending_deliveries": pending,
            "in_transit_deliveries": in_transit,
            "failed_deliveries": failed,
            "cancelled_deliveries": cancelled,
            "delivery_success_rate": success_rate,
            "first_attempt_success_rate": first_attempt_rate,
            "on_time_delivery_rate": on_time_rate,
            "average_delivery_duration_min": avg_duration,
            "average_delivery_cost": avg_cost,
            "total_delivery_expenses": float(total_expenses or 0),
            "total_delivery_revenue": round(total_revenue, 2),
            "delivery_contribution": contribution,
        },
        "formulas": {
            "delivery_success_rate": "Completed / (Total - Cancelled) * 100",
            "first_attempt_success_rate": "Completed with <=1 attempt / Jobs with >=1 attempt * 100",
            "on_time_delivery_rate": "Jobs with sla_status=Met / Jobs with sla_status in (Met,Breached) * 100",
            "average_delivery_duration_min": "SUM(actual_duration) / Completed deliveries",
            "average_delivery_cost": "SUM(actual_delivery_cost) / Completed deliveries",
            "delivery_contribution": "Total delivery revenue - Total delivery expenses",
        },
    }


@frappe.whitelist()
@jwt_required
@role_required("Delivery Manager", "Delivery Dispatcher", "Delivery Supervisor",
               "Delivery Analyst", "System Manager")
def rider_performance(frm=None, to=None, rider_name=None, group_by="rider", **filters):
    """Rider performance metrics and leaderboard."""
    frm, to = _base_date_range(frm, to)
    f = _filters(frm, to, **filters)
    if rider_name:
        f["rider_profile"] = rider_name

    jobs = _job_query(f)
    riders = {}
    for j in jobs:
        key = j.rider_profile or j.driver or "Unassigned"
        r = riders.setdefault(
            key,
            {
                "rider": key,
                "assigned": 0, "accepted": 0, "completed": 0, "failed": 0,
                "attempted": 0, "first_attempt_ok": 0,
                "duration_total": 0, "duration_count": 0,
                "distance_total": 0.0,
            },
        )
        r["assigned"] += 1
        if j.accepted_at:
            r["accepted"] += 1
        if j.status == "Completed":
            r["completed"] += 1
        if j.status == "Failed":
            r["failed"] += 1
        if (j.number_of_attempts or 0) > 0:
            r["attempted"] += 1
            if j.status == "Completed" and j.number_of_attempts <= 1:
                r["first_attempt_ok"] += 1
        if j.status == "Completed" and j.actual_duration:
            r["duration_total"] += j.actual_duration
            r["duration_count"] += 1
        r["distance_total"] += float(j.actual_distance or j.estimated_distance or 0)

    # Rider names
    rider_names = {}
    rider_list = list(riders.keys())
    if rider_list:
        for rp in frappe.get_all(
            "Rider Profile", filters={"name": ["in", rider_list]},
            fields=["name", "rider_name", "employee"],
        ):
            rider_names[rp.name] = rp.rider_name or rp.employee

    leaderboard = []
    for key, r in riders.items():
        eligible = r["assigned"] - 0  # cancelled counted in assigned; refine:
        cancelled = sum(
            1 for j in jobs
            if (j.rider_profile or j.driver or "Unassigned") == key and j.status == "Cancelled"
        )
        eligible = r["assigned"] - cancelled
        leaderboard.append(
            {
                "rider": key,
                "rider_name": rider_names.get(key, key),
                "total_assigned": r["assigned"],
                "total_accepted": r["accepted"],
                "completed": r["completed"],
                "failed": r["failed"],
                "completion_rate": round(r["completed"] / eligible * 100, 2) if eligible else 0,
                "first_attempt_success_rate": round(
                    r["first_attempt_ok"] / r["attempted"] * 100, 2
                ) if r["attempted"] else 0,
                "avg_delivery_duration_min": round(
                    r["duration_total"] / r["duration_count"], 1
                ) if r["duration_count"] else 0,
                "total_distance_km": round(r["distance_total"], 2),
                "avg_distance_per_delivery": round(
                    r["distance_total"] / r["completed"], 2
                ) if r["completed"] else 0,
            }
        )
    # Composite score: success rate weighted with completion rate (not just volume)
    for row in leaderboard:
        row["performance_score"] = round(
            row["completion_rate"] * 0.6
            + row["first_attempt_success_rate"] * 0.4, 2
        )
    leaderboard.sort(key=lambda x: (-x["performance_score"], -x["completed"]))

    if rider_name:
        # Detailed single-rider view
        detail = leaderboard[0] if leaderboard else {}
        # Working hours from shifts
        shifts = frappe.get_all(
            "Rider Shift",
            filters={"rider": rider_name, "shift_date": ["between", [frm, to]]},
            fields=["total_working_hours", "total_active_delivery_hours", "total_distance_travelled"],
        )
        working_hours = sum(float(s.total_working_hours or 0) for s in shifts)
        detail["active_working_hours"] = round(working_hours, 2)
        detail["deliveries_per_working_hour"] = round(
            detail.get("completed", 0) / working_hours, 2
        ) if working_hours else 0
        detail["avg_customer_rating"] = None  # ratings not yet collected
        return {"success_key": 1, "rider": detail, "leaderboard": leaderboard}

    return {"success_key": 1, "leaderboard": leaderboard}


@frappe.whitelist()
@jwt_required
@role_required("Fleet Manager", "Fleet Supervisor", "Delivery Manager",
               "Delivery Analyst", "System Manager")
def fleet_performance(frm=None, to=None, vehicle_type=None, **filters):
    """Fleet KPIs: utilization, fuel, maintenance, cost per delivery."""
    frm, to = _base_date_range(frm, to)

    vehicle_filters = {}
    if filters.get("vehicle"):
        vehicle_filters["name"] = filters["vehicle"]
    if vehicle_type:
        vehicle_filters["vehicle_type"] = vehicle_type
    vehicles = frappe.get_all(
        "Vehicle", filters=vehicle_filters, fields=["name", "vehicle_type", "license_plate"]
    )
    vehicle_names = [v.name for v in vehicles]

    jobs = _job_query(_filters(frm, to, **filters))
    jobs = [j for j in jobs if not vehicle_names or j.vehicle in vehicle_names]

    fuel = frappe.db.sql(
        """
        SELECT vehicle, SUM(quantity) qty, SUM(total_cost) cost, SUM(consumption_kmpl) kmpl_sum, COUNT(*) n
        FROM `tabFuel Log`
        WHERE fuel_date BETWEEN %s AND %s
        GROUP BY vehicle
        """,
        (frm, to), as_dict=True,
    )
    fuel_by_vehicle = {r.vehicle: r for r in fuel}

    maint = frappe.db.sql(
        """
        SELECT vehicle, SUM(total_cost) cost, COUNT(*) n
        FROM `tabVehicle Maintenance Record`
        WHERE maintenance_date BETWEEN %s AND %s AND status != 'Cancelled'
        GROUP BY vehicle
        """,
        (frm, to), as_dict=True,
    )
    maint_by_vehicle = {r.vehicle: r for r in maint}

    total_deliveries = len([j for j in jobs if j.status == "Completed"])
    total_distance = sum(float(j.actual_distance or 0) for j in jobs)
    total_fuel_cost = sum(float(r.cost or 0) for r in fuel)
    total_fuel_qty = sum(float(r.qty or 0) for r in fuel)
    maint_cost = sum(float(r.cost or 0) for r in maint)

    active_vehicles = len(
        set(j.vehicle for j in jobs if j.vehicle and j.status in ACTIVE_STATUSES + ["Completed"])
    )

    return {
        "success_key": 1,
        "fleet": {
            "total_registered_vehicles": len(vehicles),
            "active_vehicles": active_vehicles,
            "vehicles_on_delivery": len(
                set(j.vehicle for j in jobs if j.vehicle and j.status in ACTIVE_STATUSES)
            ),
            "vehicle_utilization_rate": round(
                active_vehicles / len(vehicles) * 100, 2
            ) if vehicles else 0,
            "total_distance_km": round(total_distance, 2),
            "total_fuel_consumption": round(total_fuel_qty, 2),
            "total_fuel_expenses": round(total_fuel_cost, 2),
            "fuel_cost_per_km": round(total_fuel_cost / total_distance, 2)
            if total_distance else 0,
            "average_deliveries_per_vehicle": round(
                total_deliveries / active_vehicles, 2
            ) if active_vehicles else 0,
            "maintenance_expenses": round(maint_cost, 2),
            "vehicle_cost_per_successful_delivery": round(
                (total_fuel_cost + maint_cost) / total_deliveries, 2
            )
            if total_deliveries else 0,
        },
        "by_vehicle": [
            {
                "vehicle": v.name,
                "vehicle_type": v.vehicle_type,
                "license_plate": v.license_plate,
                "deliveries": sum(1 for j in jobs if j.vehicle == v.name and j.status == "Completed"),
                "distance_km": round(sum(float(j.actual_distance or 0) for j in jobs if j.vehicle == v.name), 2),
                "fuel_cost": float(fuel_by_vehicle.get(v.name, {}).get("cost") or 0)
                if isinstance(fuel_by_vehicle.get(v.name), dict) else 0,
                "maintenance_cost": float(maint_by_vehicle.get(v.name, {}).get("cost") or 0)
                if isinstance(maint_by_vehicle.get(v.name), dict) else 0,
            }
            for v in vehicles
        ],
    }


@frappe.whitelist()
@jwt_required
@role_required("Delivery Manager", "Delivery Dispatcher", "Delivery Supervisor",
               "Delivery Analyst", "System Manager")
def operational_efficiency(frm=None, to=None, **filters):
    """Operational efficiency metrics from timestamps."""
    frm, to = _base_date_range(frm, to)
    jobs = _job_query(_filters(frm, to, **filters))

    def avg_minutes(pairs):
        diffs = [
            (getattr(j, end).replace(tzinfo=None) - getattr(j, start).replace(tzinfo=None)).total_seconds() / 60
            for j, start, end in pairs
            if getattr(j, start) and getattr(j, end)
        ]
        return round(sum(diffs) / len(diffs), 1) if diffs else 0

    from frappe.utils import get_datetime

    def minutes_between(a, b):
        if not a or not b:
            return None
        return (get_datetime(b) - get_datetime(a)).total_seconds() / 60

    assign_to_accept, dispatch_to_arrive, pickup_durations, delivery_durations = [], [], [], []
    waiting = []
    for j in jobs:
        m = minutes_between(j.dispatched_at, j.accepted_at)
        if m is not None:
            assign_to_accept.append(m)
        m = minutes_between(j.en_route_at, j.arrived_at)
        if m is not None:
            dispatch_to_arrive.append(m)
        m = minutes_between(j.started_delivery_at, j.completed_at)
        if m is not None:
            delivery_durations.append(m)
        m = minutes_between(j.arrived_at, j.started_delivery_at)
        if m is not None:
            waiting.append(m)
        m = minutes_between(j.actual_pickup_time, j.started_delivery_at)
        if m is not None:
            pickup_durations.append(m)

    batches = frappe.get_all(
        "Delivery Batch",
        filters={"batch_date": ["between", [frm, to]]},
        fields=["total_jobs"],
    )
    avg_jobs_per_batch = (
        round(sum(b.total_jobs for b in batches) / len(batches), 2) if batches else 0
    )

    stops = frappe.db.sql(
        """
        SELECT AVG(waiting_duration) FROM `tabDelivery Stop`
        WHERE stop_status = 'Completed'
        """,
    )[0][0]

    multi_attempt = [j for j in jobs if (j.number_of_attempts or 0) > 1]
    failed = [j for j in jobs if j.status == "Failed"]
    eligible = len(jobs) - len([j for j in jobs if j.status == "Cancelled"])

    return {
        "success_key": 1,
        "efficiency": {
            "avg_assignment_acceptance_min": round(sum(assign_to_accept) / len(assign_to_accept), 1) if assign_to_accept else 0,
            "avg_rider_arrival_min": round(sum(dispatch_to_arrive) / len(dispatch_to_arrive), 1) if dispatch_to_arrive else 0,
            "avg_pickup_duration_min": round(sum(pickup_durations) / len(pickup_durations), 1) if pickup_durations else 0,
            "avg_delivery_duration_min": round(sum(delivery_durations) / len(delivery_durations), 1) if delivery_durations else 0,
            "avg_customer_waiting_min": round(sum(waiting) / len(waiting), 1) if waiting else 0,
            "failed_delivery_rate": round(len(failed) / eligible * 100, 2) if eligible else 0,
            "multi_attempt_rate": round(len(multi_attempt) / eligible * 100, 2) if eligible else 0,
            "avg_jobs_per_batch": avg_jobs_per_batch,
            "avg_stops_per_trip": round(float(stops or 0), 1) if stops else 0,
            "avg_distance_per_delivery": round(
                sum(float(j.actual_distance or 0) for j in jobs) / len(jobs), 2
            ) if jobs else 0,
            "sla_breach_count": len([j for j in jobs if j.sla_status == "Breached"]),
        },
    }


@frappe.whitelist()
@jwt_required
@role_required("Delivery Manager", "Delivery Dispatcher", "Delivery Supervisor",
               "Delivery Analyst", "System Manager")
def geographic_analytics(frm=None, to=None, **filters):
    """Zone-level delivery analytics + rider locations for the map."""
    frm, to = _base_date_range(frm, to)
    jobs = _job_query(_filters(frm, to, **filters))

    zones = {}
    for j in jobs:
        z = j.delivery_zone or "Unzoned"
        zc = zones.setdefault(
            z, {"zone": z, "total": 0, "completed": 0, "failed": 0,
                "duration_total": 0, "duration_count": 0}
        )
        zc["total"] += 1
        if j.status == "Completed":
            zc["completed"] += 1
            if j.actual_duration:
                zc["duration_total"] += j.actual_duration
                zc["duration_count"] += 1
        if j.status == "Failed":
            zc["failed"] += 1

    zone_names = [k for k in zones if k != "Unzoned"]
    zone_info = {
        r.name: r
        for r in frappe.get_all(
            "Delivery Zone",
            filters={"name": ["in", zone_names]},
            fields=["name", "zone_name", "latitude", "longitude"],
        )
    } if zone_names else {}

    zone_stats = []
    for z, d in zones.items():
        zone_stats.append(
            {
                "zone": z,
                "zone_name": zone_info.get(z, {}).zone_name if hasattr(zone_info.get(z, {}), "zone_name") else z,
                "latitude": getattr(zone_info.get(z), "latitude", None) if zone_info.get(z) else None,
                "longitude": getattr(zone_info.get(z), "longitude", None) if zone_info.get(z) else None,
                "total": d["total"],
                "completed": d["completed"],
                "failed": d["failed"],
                "avg_duration_min": round(d["duration_total"] / d["duration_count"], 1)
                if d["duration_count"] else 0,
            }
        )

    # Rider live locations from latest availability records
    riders = frappe.db.sql(
        """
        SELECT ra.rider, rp.rider_name, ra.last_location_latitude lat,
               ra.last_location_longitude lng, ra.last_updated, ra.availability_status
        FROM `tabRider Availability` ra
        LEFT JOIN `tabRider Profile` rp ON rp.name = ra.rider
        WHERE ra.last_location_latitude IS NOT NULL
          AND ra.name IN (
              SELECT MAX(name) FROM `tabRider Availability` GROUP BY rider
          )
        """,
        as_dict=True,
    )

    # Hotspots: grid cells with most completed deliveries
    hotspots = frappe.db.sql(
        """
        SELECT ROUND(latitude,2) lat, ROUND(longitude,2) lng, COUNT(*) cnt
        FROM `tabDelivery Job`
        WHERE status = 'Completed' AND latitude IS NOT NULL AND longitude IS NOT NULL
          AND scheduled_date BETWEEN %s AND %s
        GROUP BY lat, lng
        ORDER BY cnt DESC
        LIMIT 20
        """,
        (frm, to), as_dict=True,
    )

    return {
        "success_key": 1,
        "zones": zone_stats,
        "rider_locations": riders,
        "hotspots": hotspots,
    }


@frappe.whitelist()
@jwt_required
@role_required("Delivery Manager", "Delivery Dispatcher", "Delivery Supervisor",
               "Delivery Analyst", "System Manager")
def delivery_trends(frm=None, to=None, group_by="day", **filters):
    """Time-series delivery trends for charts."""
    frm, to = _base_date_range(frm, to)
    date_fmt = {"day": "%Y-%m-%d", "week": "%x-W%v", "month": "%Y-%m"}[group_by].replace("%", "%%")

    rows = frappe.db.sql(
        f"""
        SELECT DATE_FORMAT(scheduled_date, '{date_fmt}') period,
               COUNT(*) total,
               SUM(status='Completed') completed,
               SUM(status='Failed') failed,
               SUM(status='Cancelled') cancelled,
               SUM(COALESCE(actual_delivery_cost,0)) cost,
               SUM(COALESCE(delivery_revenue, customer_delivery_charge, grand_total, 0)
                   - COALESCE(actual_delivery_cost,0)) revenue
        FROM `tabDelivery Job`
        WHERE scheduled_date BETWEEN %s AND %s
        GROUP BY period
        ORDER BY period
        """,
        (frm, to), as_dict=True,
    )
    return {"success_key": 1, "group_by": group_by, "data": rows}


@frappe.whitelist()
@jwt_required
@role_required("Delivery Manager", "Delivery Dispatcher", "Delivery Supervisor",
               "Delivery Analyst", "System Manager")
def sla_compliance(frm=None, to=None, **filters):
    frm, to = _base_date_range(frm, to)
    rows = frappe.db.sql(
        """
        SELECT sla_status, COUNT(*) cnt
        FROM `tabDelivery Job`
        WHERE scheduled_date BETWEEN %s AND %s
          AND sla_status != 'No SLA'
        GROUP BY sla_status
        """,
        (frm, to), as_dict=True,
    )
    return {"success_key": 1, "data": rows}


@frappe.whitelist()
@jwt_required
@role_required("Delivery Manager", "Delivery Dispatcher", "Delivery Supervisor",
               "Delivery Analyst", "System Manager")
def fuel_trends(frm=None, to=None, **filters):
    frm, to = _base_date_range(frm, to)
    rows = frappe.db.sql(
        """
        SELECT DATE_FORMAT(fuel_date, '%%Y-%%m-%%d') period,
               SUM(quantity) qty, SUM(total_cost) cost
        FROM `tabFuel Log`
        WHERE fuel_date BETWEEN %s AND %s
        GROUP BY period ORDER BY period
        """,
        (frm, to), as_dict=True,
    )
    return {"success_key": 1, "data": rows}


@frappe.whitelist()
@jwt_required
@role_required("Delivery Manager", "Delivery Dispatcher", "Delivery Supervisor",
               "Delivery Analyst", "System Manager")
def status_distribution(frm=None, to=None, **filters):
    frm, to = _base_date_range(frm, to)
    rows = frappe.db.sql(
        """
        SELECT status, COUNT(*) cnt
        FROM `tabDelivery Job`
        WHERE scheduled_date BETWEEN %s AND %s
        GROUP BY status
        """,
        (frm, to), as_dict=True,
    )
    return {"success_key": 1, "data": rows}


@frappe.whitelist()
@jwt_required
@role_required("Delivery Manager", "Delivery Dispatcher", "Delivery Supervisor",
               "Delivery Analyst", "System Manager")
def dashboard_summary(frm=None, to=None, **filters):
    """Single-call aggregate for the main dashboard."""
    kpis = executive_kpis(frm=frm, to=to, **filters)
    riders = rider_performance(frm=frm, to=to, **filters)
    fleet = fleet_performance(frm=frm, to=to, **filters)
    eff = operational_efficiency(frm=frm, to=to, **filters)
    geo = geographic_analytics(frm=frm, to=to, **filters)
    trends = delivery_trends(frm=frm, to=to, group_by="day", **filters)
    return {
        "success_key": 1,
        "kpis": kpis["kpis"],
        "rider_leaderboard": riders.get("leaderboard", [])[:10],
        "fleet": fleet.get("fleet", {}),
        "efficiency": eff.get("efficiency", {}),
        "zones": geo.get("zones", []),
        "rider_locations": geo.get("rider_locations", []),
        "trend": trends.get("data", []),
    }
