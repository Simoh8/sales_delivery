"""Generate conclusive demo data for the ledgerctrl delivery tracking app.

Run on a site where ledgerctrl is installed:

    bench --site <site> execute ledgerctrl.demo_data.run_demo_data

Creates master data (users, employees, rider profiles, vehicles, zones, SLAs)
and transactional data (delivery jobs walked through the real status flow,
batches, GPS logs, attempts, proofs of delivery, stops, expenses, fuel logs,
inspections, maintenance records, shifts, fleet assignments, availability,
documents, refresh tokens).

Idempotent: refuses to run twice unless `force=True` is passed.
"""

import hashlib
import os
import random
from datetime import timedelta

import frappe
from frappe.utils import (
    add_days,
    add_to_date,
    get_datetime,
    get_time,
    now_datetime,
)

random.seed(42)

COMPANY = "Delivery App"
DEPOT_LAT = -1.2921
DEPOT_LNG = 36.8219  # Nairobi depot

RIDER_DEFS = [
    {"first": "James", "last": "Mwangi", "gender": "Male", "phone": "+254711000001"},
    {"first": "Grace", "last": "Achieng", "gender": "Female", "phone": "+254711000002"},
    {"first": "Peter", "last": "Otieno", "gender": "Male", "phone": "+254711000003"},
    # third-party contractors: no Employee record
    {"first": "Faith", "last": "Njeri", "gender": "Female", "phone": "+254711000004", "contractor": True},
    {"first": "Kevin", "last": "Barasa", "gender": "Male", "phone": "+254711000005", "contractor": True},
]

# Drivers have a User + optional Employee; jobs link via `driver`/`driver_name`.
DRIVER_DEFS = [
    {"first": "Daniel", "last": "Kiptoo", "gender": "Male", "phone": "+254722000001"},
    {"first": "Mercy", "last": "Wanjiru", "gender": "Female", "phone": "+254722000002", "contractor": True},
    {"first": "Samuel", "last": "Mutiso", "gender": "Male", "phone": "+254722000003", "contractor": True},
]

# Sales people create/manage jobs from the web app; they don't deliver.
SALES_DEFS = [
    {"first": "Lucy", "last": "Chebet", "gender": "Female", "phone": "+254733000001"},
    {"first": "Brian", "last": "Odhiambo", "gender": "Male", "phone": "+254733000002"},
]

VEHICLE_DEFS = [
    {"plate": "KDJ 101A", "make": "Toyota", "model": "Hilux", "type": "Pickup", "fuel": "Diesel"},
    {"plate": "KDJ 202B", "make": "Isuzu", "model": "D-Max", "type": "Pickup", "fuel": "Diesel"},
    {"plate": "KDJ 303C", "make": "Suzuki", "model": "Carry", "type": "Van", "fuel": "Petrol"},
    {"plate": "KDJ 404D", "make": "Bajaj", "model": "RE", "type": "Motorcycle", "fuel": "Petrol"},
]

# zone_code -> (center_lat, center_lng, radius_m, default_charge)
ZONE_DEFS = [
    ("WEST", "Westlands", -1.2673, 36.8069, 3000, 350),
    ("KIL", "Kilimani", -1.2921, 36.7840, 2500, 300),
    ("CBD", "Nairobi CBD", -1.2833, 36.8167, 2000, 250),
    ("EMB", "Embakasi Industrial", -1.3167, 36.9167, 4000, 500),
]

SLA_DEFS = [
    # (sla_name, delivery_type, max_duration_min, pickup_min, delivery_min, grace_min, priority, active)
    ("Standard 4h", "Standard", 240, 60, 240, 30, "Normal", 1),
    ("Express 2h", "Express", 120, 30, 120, 15, "High", 1),
    ("Same Day", "Same Day", 480, 120, 480, 60, "Normal", 1),
]

CUSTOMER_DEFS = [
    {"name": "Demo Customer - Westlands Mart", "zone": "WEST", "contact": "0712 345 001"},
    {"name": "Demo Customer - Kilimani Pharmacy", "zone": "KIL", "contact": "0712 345 002"},
    {"name": "Demo Customer - CBD Supplies Ltd", "zone": "CBD", "contact": "0712 345 003"},
    {"name": "Demo Customer - Embakasi Textiles", "zone": "EMB", "contact": "0712 345 004"},
    {"name": "Demo Customer - Westlands Books", "zone": "WEST", "contact": "0712 345 005"},
    {"name": "Demo Customer - Kilimani Gym", "zone": "KIL", "contact": "0712 345 006"},
]

# (customer_idx, days_ago, target_status, priority, delivery_type, batch_day, actor)
# actor = ("R", rider_idx) for riders or ("D", driver_idx) for drivers.
JOB_PLAN = [
    # completed jobs across the last week - mix of riders and drivers
    (0, 6, "Completed", "Normal", "Standard", 6, ("R", 0)),
    (1, 6, "Completed", "High", "Express", 6, ("D", 0)),
    (2, 5, "Completed", "Normal", "Standard", 5, ("R", 1)),
    (3, 5, "Completed", "Urgent", "Same Day", 5, ("D", 1)),
    (4, 4, "Completed", "Normal", "Standard", 4, ("R", 2)),
    (5, 4, "Completed", "High", "Express", 4, ("D", 2)),
    (0, 3, "Completed", "Normal", "Standard", 3, ("R", 3)),
    (1, 3, "Completed", "Normal", "Same Day", 3, ("D", 0)),
    (2, 2, "Completed", "High", "Standard", 2, ("R", 4)),
    (3, 2, "Completed", "Normal", "Standard", 2, ("D", 1)),
    (4, 1, "Completed", "Normal", "Express", 1, ("R", 0)),
    (5, 1, "Completed", "High", "Standard", 1, ("D", 2)),
    (0, 0, "Completed", "Normal", "Standard", 0, ("R", 1)),
    (1, 0, "Completed", "Normal", "Standard", 0, ("D", 0)),
    # failed / cancelled
    (2, 1, "Failed", "Normal", "Standard", 1, ("R", 2)),
    (4, 2, "Failed", "Normal", "Standard", 2, ("D", 1)),
    (3, 1, "Cancelled", "Normal", "Standard", 1, ("D", 2)),
    (5, 3, "Cancelled", "Low", "Scheduled", 3, ("R", 3)),
    # active jobs today
    (0, 0, "Pending", "Normal", "Standard", 0, ("R", 0)),
    (1, 0, "Pending", "High", "Express", 0, ("D", 0)),
    (2, 0, "Pending", "Normal", "Same Day", 0, ("R", 4)),
    (3, 0, "Dispatched", "Normal", "Standard", 0, ("D", 1)),
    (4, 0, "Accepted", "Normal", "Standard", 0, ("R", 2)),
    (5, 0, "En Route", "High", "Express", 0, ("D", 2)),
    (0, 0, "Arrived", "Normal", "Standard", 0, ("R", 1)),
    (1, 0, "In Progress", "Normal", "Standard", 0, ("D", 0)),
]

ITEMS = ["SKU001", "SKU003", "SKU005", "SKU007", "SKU009"]


def jitter(base, spread=0.01):
    return base + random.uniform(-spread, spread)


def job_coords(zone_code):
    for code, _name, lat, lng, _r, _c in ZONE_DEFS:
        if code == zone_code:
            return jitter(lat, 0.008), jitter(lng, 0.008)
    return DEPOT_LAT, DEPOT_LNG


# ---------------------------------------------------------------------------
# master data
# ---------------------------------------------------------------------------

def ensure_company():
    for candidate in ("Delivery App", "Delivery App (Demo)"):
        if frappe.db.exists("Company", candidate):
            return candidate
    company = frappe.db.get_value("Company", {})
    if not company:
        frappe.throw("No Company exists. Create one before running demo data.")
    return company


def ensure_settings():
    settings = frappe.get_single("Delivery Settings")
    settings.update(
        {
            "require_otp": 1,
            "require_signature": 1,
            "require_photograph": 1,
            "require_recipient_confirmation": 1,
            "allow_multiple_active_deliveries": 1,
            "allow_overlapping_shifts": 1,
            "allow_multiple_active_vehicle_assignments": 1,
            "maintenance_reminder_days": 30,
            "document_expiry_alert_days": 14,
            "sla_breach_alert_hours": 2,
        }
    )
    settings.save(ignore_permissions=True)
    return settings


def ensure_customers():
    customers = []
    # reuse existing ERPNext customers for realism
    existing = frappe.get_all("Customer", fields=["name", "customer_name"], limit=10)
    for c in existing:
        customers.append({"name": c.name, "contact": "0722 000 000", "zone": random.choice([z[0] for z in ZONE_DEFS]), "demo": False})
    for d in CUSTOMER_DEFS:
        if not frappe.db.exists("Customer", d["name"]):
            frappe.get_doc(
                {
                    "doctype": "Customer",
                    "customer_name": d["name"],
                    "customer_type": "Company",
                    "customer_group": "Commercial",
                    "territory": "Kenya",
                }
            ).insert(ignore_permissions=True)
        customers.append({"name": d["name"], "contact": d["contact"], "zone": d["zone"], "demo": True})
        customers[-1]["address"] = ensure_customer_address(d["name"], d["zone"])
    return customers


def ensure_customer_address(customer, zone_code):
    title = f"{customer} - Delivery"
    existing = frappe.db.get_value("Address", {"address_title": title}, "name")
    if existing:
        return existing
    frappe.get_doc(
        {
            "doctype": "Address",
            "address_title": title,
            "address_type": "Billing",
            "address_line1": f"{random.randint(1, 200)} Demo Avenue",
            "city": "Nairobi",
            "state": "Nairobi",
            "country": "Kenya",
            "pincode": "00100",
            "links": [{"link_doctype": "Customer", "link_name": customer}],
        }
    ).insert(ignore_permissions=True)
    return frappe.db.get_value("Address", {"address_title": title}, "name")


def ensure_zones(company):
    zones = {}
    for code, name, lat, lng, radius, charge in ZONE_DEFS:
        if frappe.db.exists("Delivery Zone", {"zone_code": code}):
            z = frappe.db.get_value("Delivery Zone", {"zone_code": code}, "name")
        else:
            z = frappe.get_doc(
                {
                    "doctype": "Delivery Zone",
                    "zone_name": name,
                    "zone_code": code,
                    "latitude": lat,
                    "longitude": lng,
                    "radius": radius,
                    "company": company,
                    "status": "Active",
                    "default_delivery_charge": charge,
                    "description": f"Demo zone covering {name}",
                }
            ).insert(ignore_permissions=True).name
        zones[code] = z
    return zones


def ensure_slas():
    slas = {}
    for name, dtype, max_dur, pickup, delivery, grace, prio, active in SLA_DEFS:
        if frappe.db.exists("Delivery SLA", {"sla_name": name}):
            slas[name] = frappe.db.get_value("Delivery SLA", {"sla_name": name}, "name")
        else:
            slas[name] = frappe.get_doc(
                {
                    "doctype": "Delivery SLA",
                    "sla_name": name,
                    "delivery_type": dtype,
                    "maximum_delivery_duration": max_dur,
                    "expected_pickup_duration": pickup,
                    "expected_delivery_duration": delivery,
                    "grace_period": grace,
                    "priority": prio,
                    "active": active,
                }
            ).insert(ignore_permissions=True).name
    return slas


def ensure_user(email, first, last, roles, phone=None):
    if frappe.db.exists("User", email):
        return email
    user = frappe.get_doc(
        {
            "doctype": "User",
            "email": email,
            "first_name": first,
            "last_name": last,
            "send_welcome_email": 0,
            "user_type": "System User",
            "new_password": "RiderFleet!2026#K3",
            "roles": [{"role": r} for r in roles],
        }
    )
    user.insert(ignore_permissions=True)
    return email


def make_rider_profile(d, email, employee, company, vehicle, zones, idx, kind):
    """Create (or fetch) a Rider Profile. `employee` may be None for
    third-party contractors who are not on the company payroll."""
    if frappe.db.exists("Rider Profile", {"user": email}):
        return frappe.db.get_value("Rider Profile", {"user": email}, "name")
    profile_doc = frappe.get_doc(
        {
            "doctype": "Rider Profile",
            "rider_name": f"{d['first']} {d['last']}",
            "employee": employee,
            "user": email,
            "company": company,
            "mobile_number": d["phone"],
            "email": email,
            "identification_number": f"ID{idx:07d}",
            "default_vehicle": vehicle,
            "joining_date": add_days(now_datetime(), -400).date(),
            "employment_status": "Active",
            "verification_status": "Verified",
        }
    )
    profile_doc.append("operating_zones", {"zone": zones["WEST"], "is_primary": 1})
    profile_doc.append(
        "operating_zones",
        {"zone": zones[ZONE_DEFS[idx % len(ZONE_DEFS)][0]], "is_primary": 0},
    )
    return profile_doc.insert(ignore_permissions=True).name


def ensure_riders(company, vehicles, zones):
    riders = []
    for i, d in enumerate(RIDER_DEFS):
        idx = i + 1
        email = f"rider{idx}@demo.ledgerctrl"
        ensure_user(email, d["first"], d["last"], ["Delivery Rider"], d["phone"])

        employee = None
        if not d.get("contractor"):
            employee = ensure_employee(
                email, d["first"], d["last"], company, d["gender"], d["phone"]
            )

        vehicle = vehicles[i % len(vehicles)]["name"]
        profile = make_rider_profile(d, email, employee, company, vehicle, zones, idx, "rider")

        ensure_rider_documents(profile, d)
        riders.append(
            {
                "kind": "rider",
                "profile": profile,
                "employee": employee,
                "user": email,
                "vehicle": vehicle,
                "name": f"{d['first']} {d['last']}",
                "def": d,
            }
        )
    return riders


def ensure_rider_documents(profile, d):
    docs = [
        ("Driving Licence", f"DL-{random.randint(100000, 999999)}", -30, 335),
        ("National ID", f"ID-{random.randint(10000000, 99999999)}", -3000, 2000),
    ]
    for dtype, number, issue_days, expiry_days in docs:
        if frappe.db.exists("Rider Document", {"rider": profile, "document_type": dtype}):
            continue
        frappe.get_doc(
            {
                "doctype": "Rider Document",
                "rider": profile,
                "document_type": dtype,
                "document_number": number,
                "issue_date": add_days(now_datetime(), issue_days).date(),
                "expiry_date": add_days(now_datetime(), expiry_days).date(),
                "verification_status": "Verified",
                "notes": f"Demo {dtype.lower()} for {d['first']} {d['last']}",
            }
        ).insert(ignore_permissions=True)


def ensure_employee(email, first, last, company, gender, phone):
    employee = frappe.db.get_value("Employee", {"user_id": email})
    if employee:
        return employee
    return frappe.get_doc(
        {
            "doctype": "Employee",
            "first_name": first,
            "last_name": last,
            "company": company,
            "status": "Active",
            "gender": gender,
            "date_of_birth": "1990-05-15",
            "date_of_joining": add_days(now_datetime(), -400).date(),
            "user_id": email,
            "cell_number": phone,
        }
    ).insert(ignore_permissions=True).name


def ensure_plain_user(email, first, last, roles):
    ensure_user(email, first, last, roles)


def ensure_drivers(company, vehicles, zones):
    """Drivers: User + Rider Profile; Employee only for non-contractors."""
    drivers = []
    for i, d in enumerate(DRIVER_DEFS):
        idx = i + 1
        email = f"driver{idx}@demo.ledgerctrl"
        ensure_plain_user(email, d["first"], d["last"], ["Driver", "Delivery User"])
        employee = None
        if not d.get("contractor"):
            employee = ensure_employee(
                email, d["first"], d["last"], company, d["gender"], d["phone"]
            )
        vehicle = vehicles[(len(RIDER_DEFS) + i) % len(vehicles)]["name"]
        profile = make_rider_profile(d, email, employee, company, vehicle, zones, idx + 50, "driver")
        ensure_rider_documents(profile, d)
        drivers.append(
            {
                "kind": "driver",
                "profile": profile,
                "employee": employee,
                "user": email,
                "vehicle": vehicle,
                "name": f"{d['first']} {d['last']}",
                "def": d,
            }
        )
    return drivers


def ensure_sales(company):
    """Sales people: User + Employee + Sales Person record (Sales Person role)."""
    sales = []
    for i, d in enumerate(SALES_DEFS):
        idx = i + 1
        email = f"sales{idx}@demo.ledgerctrl"
        ensure_plain_user(email, d["first"], d["last"], ["Sales Person", "Sales User"])
        employee = ensure_employee(email, d["first"], d["last"], company, d["gender"], d["phone"])
        sp_name = f"{d['first']} {d['last']}"
        if not frappe.db.exists("Sales Person", {"employee": employee}):
            try:
                frappe.get_doc(
                    {
                        "doctype": "Sales Person",
                        "sales_person_name": sp_name,
                        "employee": employee,
                        "is_group": 0,
                        "enabled": 1,
                    }
                ).insert(ignore_permissions=True)
            except Exception:
                frappe.log_error(frappe.get_traceback(), "Demo Sales Person insert failed")
        sales.append(
            {
                "kind": "sales",
                "profile": None,
                "employee": employee,
                "user": email,
                "vehicle": None,
                "name": sp_name,
                "def": d,
            }
        )
    return sales


def ensure_vehicles(company):
    vehicles = []
    odometer = 45000
    for d in VEHICLE_DEFS:
        if frappe.db.exists("Vehicle", d["plate"]):
            v = frappe.db.get_value("Vehicle", d["plate"], "name")
        else:
            v = frappe.get_doc(
                {
                    "doctype": "Vehicle",
                    "license_plate": d["plate"],
                    "make": d["make"],
                    "model": d["model"],
                    "vehicle_type": d["type"],
                    "fuel_type": d["fuel"],
                    "uom": "Nos",
                    "last_odometer": odometer,
                    "acquisition_date": add_days(now_datetime(), -500),
                    "location": "Nairobi Depot",
                    "vehicle_value": random.randint(2500000, 6000000),
                    "color": random.choice(["White", "Silver", "Blue", "Grey"]),
                }
            ).insert(ignore_permissions=True).name
        vehicles.append({"name": v, "def": d})
        odometer += 12000
    return vehicles


def ensure_fleet_assignments(actors, vehicles, company):
    for i, r in enumerate(actors):
        # Fleet Assignment.employee is required, so third-party contractors
        # (no Employee record) are skipped here.
        if not r.get("employee"):
            continue
        v = vehicles[i % len(vehicles)]["name"]
        if frappe.db.exists("Fleet Assignment", {"employee": r["employee"], "assignment_status": "Active"}):
            continue
        frappe.get_doc(
            {
                "doctype": "Fleet Assignment",
                "employee": r["employee"],
                "rider": r["profile"],
                "vehicle": v,
                "assignment_start": add_days(now_datetime(), -380),
                "opening_odometer": 40000 + i * 9000,
                "assignment_status": "Active",
                "assigned_by": "Administrator",
                "notes": "Demo fleet assignment",
            }
        ).insert(ignore_permissions=True)
        # completed historical assignment for variety
        if i % 2 == 0:
            frappe.get_doc(
                {
                    "doctype": "Fleet Assignment",
                    "employee": r["employee"],
                    "rider": r["profile"],
                    "vehicle": vehicles[(i + 1) % len(vehicles)]["name"],
                    "assignment_start": add_days(now_datetime(), -400),
                    "assignment_end": add_days(now_datetime(), -390),
                    "opening_odometer": 35000 + i * 9000,
                    "closing_odometer": 35500 + i * 9000,
                    "assignment_status": "Completed",
                    "assigned_by": "Administrator",
                    "notes": "Demo previous assignment",
                }
            ).insert(ignore_permissions=True)


def ensure_items():
    items = frappe.get_all("Item", fields=["name", "item_name", "stock_uom"], limit=20)
    return [i for i in items if i.name in ITEMS] or items[:5]


# ---------------------------------------------------------------------------
# transactional data
# ---------------------------------------------------------------------------

def make_job(actor, customer, zone, company, sla_name, plan):
    cust_idx, days_ago, status, priority, dtype, _batch, _actor = plan
    zone_code = customer["zone"]
    zone_doc = frappe.db.get_value("Delivery Zone", {"zone_code": zone_code}, ["name", "latitude", "longitude", "default_delivery_charge"], as_dict=True)
    lat, lng = job_coords(zone_code)

    if days_ago == 0:
        sched_date = now_datetime().date()
        sched_time = get_time(
            add_to_date(now_datetime(), minutes=-random.randint(30, 600))
        )
    else:
        sched_date = add_days(now_datetime(), -days_ago).date()
        sched_time = get_time(f"{random.randint(8, 17)}:{random.choice(['00','15','30','45'])}:00")

    items = ensure_items_cache()
    lines = []
    for it in random.sample(items, k=min(3, len(items))):
        qty = random.randint(1, 5)
        rate = round(random.uniform(500, 5000), 2)
        lines.append({"item_code": it.name, "item_name": it.item_name or it.name, "qty": qty, "uom": it.stock_uom or "Nos", "rate": rate, "amount": qty * rate})
    grand_total = sum(l["amount"] for l in lines)

    delivery_charge = float(zone_doc.default_delivery_charge or 300)
    cost = round(delivery_charge * random.uniform(0.35, 0.6), 2)

    job = frappe.get_doc(
        {
            "doctype": "Delivery Job",
            "customer": customer["name"],
            "customer_name": frappe.db.get_value("Customer", customer["name"], "customer_name") or customer["name"],
            "customer_address": customer.get("address"),
            "customer_contact": customer["contact"],
            "driver": actor["employee"],
            "driver_name": actor["name"],
            "rider_profile": actor["profile"],
            "assigned_employee": actor["employee"],
            "vehicle": actor["vehicle"],
            "scheduled_date": sched_date,
            "scheduled_time": sched_time,
            "scheduled_delivery_start": add_to_date(f"{sched_date} {sched_time}", hours=-1),
            "scheduled_delivery_end": add_to_date(f"{sched_date} {sched_time}", hours=4),
            "delivery_type": dtype,
            "delivery_zone": zone_doc.name if zone_doc else None,
            "delivery_sla": sla_name,
            "company": company,
            "status": "Pending",
            "priority": priority,
            "estimated_distance": round(random.uniform(4, 25), 1),
            "estimated_duration": random.randint(30, 120),
            "latitude": lat,
            "longitude": lng,
            "location_accuracy": random.randint(5, 30),
            "actual_distance": round(random.uniform(4, 25), 1),
            "customer_delivery_charge": delivery_charge,
            "actual_delivery_cost": cost,
            "cod_expected": grand_total,
            "payment_status": random.choice(["Unpaid", "Paid", "Partial"]),
            "grand_total": grand_total,
            "delivery_notes": "Demo delivery job",
            "created_via": "Mobile App",
            "items": lines,
        }
    )
    job.insert(ignore_permissions=True)
    return job


_items_cache = None


def ensure_items_cache():
    global _items_cache
    if _items_cache is None:
        _items_cache = ensure_items()
    return _items_cache


def backdate_job(job, days_ago, status):
    """After walking the status flow (timestamps = now), backdate them to the
    scheduled window so reports look realistic."""
    sched = get_datetime(f"{job.scheduled_date} {job.scheduled_time or '09:00:00'}")
    seq = {
        "Dispatched": sched,
        "Accepted": sched + timedelta(minutes=random.randint(5, 20)),
        "En Route": sched + timedelta(minutes=random.randint(20, 60)),
        "Arrived": sched + timedelta(minutes=random.randint(60, 150)),
        "In Progress": sched + timedelta(minutes=random.randint(150, 200)),
        "Completed": sched + timedelta(minutes=random.randint(200, 300)),
        "Failed": sched + timedelta(minutes=random.randint(150, 260)),
        "Cancelled": sched + timedelta(minutes=random.randint(10, 90)),
    }
    fields = {}
    order = ["Dispatched", "Accepted", "En Route", "Arrived", "In Progress", "Completed", "Failed", "Cancelled"]
    idx = order.index(status) if status in order else 0
    for step in order[: idx + 1]:
        f = {
            "Dispatched": "dispatched_at",
            "Accepted": "accepted_at",
            "En Route": "en_route_at",
            "Arrived": "arrived_at",
            "In Progress": "started_delivery_at",
            "Completed": "completed_at",
            "Failed": "completed_at",
            "Cancelled": "cancelled_at",
        }[step]
        fields[f] = seq[step]
    if "started_delivery_at" in fields:
        fields["actual_pickup_time"] = fields["started_delivery_at"]
    if status in ("Completed", "Failed"):
        fields["actual_delivery_time"] = fields.get("completed_at")
        if "completed_at" in fields and "started_delivery_at" in fields:
            fields["actual_duration"] = int((fields["completed_at"] - fields["started_delivery_at"]).total_seconds() / 60)
    fields["cod_collected"] = job.cod_expected if job.payment_status == "Paid" else (job.cod_expected * 0.5 if job.payment_status == "Partial" else 0)
    job.db_set(fields, update_modified=False)


def create_gps_logs(job, actor):
    start = job.dispatched_at or get_datetime(f"{job.scheduled_date} {job.scheduled_time}")
    end = job.completed_at or job.cancelled_at or now_datetime()
    if isinstance(start, str):
        start = get_datetime(start)
    if isinstance(end, str):
        end = get_datetime(end)
    points = random.randint(8, 14)
    span = max((end - start).total_seconds(), 600)
    for i in range(points):
        frac = i / (points - 1)
        lat = DEPOT_LAT + (job.latitude - DEPOT_LAT) * frac + random.uniform(-0.004, 0.004)
        lng = DEPOT_LNG + (job.longitude - DEPOT_LNG) * frac + random.uniform(-0.004, 0.004)
        ts = start + timedelta(seconds=span * frac)
        frappe.get_doc(
            {
                "doctype": "GPS Log",
                "delivery_job": job.name,
                "driver": actor["employee"],
                "driver_name": actor["name"],
                "vehicle": actor["vehicle"],
                "timestamp": ts,
                "created_via": "Mobile App",
                "latitude": round(lat, 6),
                "longitude": round(lng, 6),
                "location_accuracy": random.randint(5, 40),
                "altitude": round(random.uniform(1600, 1900), 1),
                "heading": round(random.uniform(0, 360), 1),
                "speed": round(random.uniform(10, 65), 1),
                "battery_level": random.randint(30, 100),
                "location_provider": random.choice(["GPS", "Fused", "Network"]),
                "satellite_count": random.randint(6, 14),
                "address": "Nairobi, Kenya",
            }
        ).insert(ignore_permissions=True)


def create_assignment_history(job, actor, days_ago):
    assigned = job.dispatched_at or add_days(now_datetime(), -days_ago)
    frappe.get_doc(
        {
            "doctype": "Assignment History",
            "delivery_job": job.name,
            "driver": actor["employee"],
            "driver_name": actor["name"],
            "vehicle": actor["vehicle"],
            "assigned_by": "Administrator",
            "assigned_at": assigned,
            "assigned_via": "Auto-Assignment",
            "assignment_status": (
                "Completed"
                if job.status == "Completed"
                else "Accepted"
                if job.status not in ("Pending", "Cancelled")
                else "Assigned"
            ),
            "accepted_at": assigned + timedelta(minutes=random.randint(2, 15)),
            "distance_to_job": round(random.uniform(2, 18), 1),
            "estimated_arrival_time": random.randint(10, 45),
        }
    ).insert(ignore_permissions=True)


def create_attempts_pod_stops(job, actor):
    customer = job.customer
    if job.status == "Failed":
        reasons = ["Customer Unavailable", "Wrong Address", "Customer Refused"]
        for n, reason in enumerate(random.sample(reasons, k=random.randint(1, 2)), start=1):
            att_time = (job.started_delivery_at or now_datetime()) + timedelta(minutes=(n - 1) * 45)
            att = frappe.get_doc(
                {
                    "doctype": "Delivery Attempt",
                    "delivery_job": job.name,
                    "attempt_number": n,
                    "rider": actor["profile"],
                    "vehicle": actor["vehicle"],
                    "attempt_date": att_time.date(),
                    "arrival_time": att_time,
                    "attempt_status": "Failed",
                    "failure_reason": reason,
                    "gps_latitude": job.latitude,
                    "gps_longitude": job.longitude,
                    "notes": f"Demo failed attempt {n}",
                }
            ).insert(ignore_permissions=True)
        return

    if job.status != "Completed":
        # stops for in-flight jobs
        make_stops(job, actor, completed=False)
        return

    # successful attempt + POD
    att_time = job.started_delivery_at or now_datetime()
    attempt = frappe.get_doc(
        {
            "doctype": "Delivery Attempt",
            "delivery_job": job.name,
            "attempt_number": 1,
            "rider": actor["profile"],
            "vehicle": actor["vehicle"],
            "attempt_date": att_time.date(),
            "arrival_time": job.arrived_at or att_time,
            "completion_time": job.completed_at or now_datetime(),
            "attempt_status": "Successful",
            "gps_latitude": job.latitude,
            "gps_longitude": job.longitude,
        }
    ).insert(ignore_permissions=True)

    recipient = frappe.db.get_value("Customer", customer, "customer_name") or customer
    pod_time = job.completed_at or now_datetime()
    pod = frappe.get_doc(
        {
            "doctype": "Proof of Delivery",
            "delivery_job": job.name,
            "delivery_attempt": attempt.name,
            "customer": customer,
            "recipient_name": f"Receiver at {recipient}",
            "recipient_phone": job.customer_contact,
            "received_by": "Store Manager",
            "delivery_timestamp": pod_time,
            "gps_latitude": job.latitude,
            "gps_longitude": job.longitude,
            "otp_verification_status": "Verified",
            "otp_verified_at": pod_time,
            "notes": "Demo proof of delivery",
        }
    ).insert(ignore_permissions=True)
    job.db_set("proof_of_delivery", pod.name, update_modified=False)
    job.reload()

    make_stops(job, actor, completed=True)


_DEPOT_ADDRESS = None


def ensure_depot_address():
    global _DEPOT_ADDRESS
    if _DEPOT_ADDRESS:
        return _DEPOT_ADDRESS
    title = "Fleet Depot - Industrial Area"
    _DEPOT_ADDRESS = frappe.db.get_value("Address", {"address_title": title}, "name")
    if not _DEPOT_ADDRESS:
        frappe.get_doc(
            {
                "doctype": "Address",
                "address_title": title,
                "address_type": "Office",
                "address_line1": "Mombasa Road, Industrial Area",
                "city": "Nairobi",
                "state": "Nairobi",
                "country": "Kenya",
                "pincode": "00100",
            }
        ).insert(ignore_permissions=True)
        _DEPOT_ADDRESS = frappe.db.get_value("Address", {"address_title": title}, "name")
    return _DEPOT_ADDRESS


def make_stops(job, actor, completed):
    base = job.dispatched_at or get_datetime(f"{job.scheduled_date} 08:00:00")
    frappe.get_doc(
        {
            "doctype": "Delivery Stop",
            "delivery_job": job.name,
            "delivery_batch": job.delivery_batch,
            "stop_sequence": 1,
            "stop_type": "Pickup",
            "customer": None,
            "address": ensure_depot_address(),
            "latitude": DEPOT_LAT,
            "longitude": DEPOT_LNG,
            "actual_arrival": base,
            "departure_time": base + timedelta(minutes=20),
            "stop_status": "Completed",
            "distance_from_previous_stop": 0,
            "notes": "Picked up at depot",
        }
    ).insert(ignore_permissions=True)
    frappe.get_doc(
        {
            "doctype": "Delivery Stop",
            "delivery_job": job.name,
            "delivery_batch": job.delivery_batch,
            "stop_sequence": 2,
            "stop_type": "Delivery",
            "customer": job.customer,
            "address": job.customer_address,
            "latitude": job.latitude,
            "longitude": job.longitude,
            "actual_arrival": job.arrived_at,
            "departure_time": job.completed_at if completed else None,
            "stop_status": "Completed" if completed else "Arrived",
            "distance_from_previous_stop": job.estimated_distance,
            "notes": "Demo customer stop",
        }
    ).insert(ignore_permissions=True)


def create_expenses(job, actor):
    if job.status not in ("Completed", "Failed"):
        return
    n = random.randint(1, 3)
    for i in range(n):
        etype = random.choice(["Toll", "Parking", "Loading", "Other"])
        frappe.get_doc(
            {
                "doctype": "Delivery Expense",
                "delivery_job": job.name,
                "delivery_batch": job.delivery_batch,
                "vehicle": actor["vehicle"],
                "rider": actor["profile"],
                "expense_date": (job.completed_at or now_datetime()).date(),
                "expense_type": etype,
                "amount": round(random.uniform(100, 1500), 2),
                "description": f"Demo {etype.lower()} expense for {job.name}",
                "expense_status": random.choice(["Approved", "Submitted", "Reimbursed"]),
                "idempotency_key": f"demo-exp-{job.name}-{i}",
            }
        ).insert(ignore_permissions=True)


def make_batches(jobs_by_day, riders, company, zones, slas):
    batches = {}
    for days_ago in sorted(jobs_by_day.keys(), reverse=True):
        jobs = jobs_by_day[days_ago]
        if not jobs:
            continue
        day = add_days(now_datetime(), -days_ago).date()
        batch_status = "Completed" if days_ago > 0 else "In Progress"
        if any(j.status in ("Pending",) for j in jobs) and days_ago == 0:
            batch_status = "In Progress"
        zone = zones[random.choice(list(zones.keys()))]
        rider = riders[days_ago % len(riders)]
        batch = frappe.get_doc(
            {
                "doctype": "Delivery Batch",
                "batch_id": f"DEMO-BATCH-{day.strftime('%Y%m%d')}",
                "batch_date": day,
                "company": company,
                "assigned_rider": rider["profile"],
                "assigned_employee": rider["employee"],
                "assigned_vehicle": rider["vehicle"],
                "delivery_zone": zone,
                "dispatcher": "Administrator",
                "batch_status": batch_status,
                "total_jobs": len(jobs),
                "completed_jobs": sum(1 for j in jobs if j.status == "Completed"),
                "pending_jobs": sum(1 for j in jobs if j.status in ("Pending", "Dispatched", "Accepted", "En Route", "Arrived", "In Progress")),
                "failed_jobs": sum(1 for j in jobs if j.status in ("Failed", "Cancelled")),
                "dispatch_time": add_to_date(f"{day} 07:30:00", hours=0),
                "jobs": [{"delivery_job": j.name, "stop_sequence": i + 1} for i, j in enumerate(jobs)],
                "notes": "Demo delivery batch",
            }
        )
        batch.insert(ignore_permissions=True)
        batches[days_ago] = batch.name
        for i, j in enumerate(jobs):
            j.db_set("delivery_batch", batch.name, update_modified=False)
    return batches


def ensure_shifts(actors, company):
    supervisor_employee = frappe.db.get_value("Employee", {"status": "Active"}, "name")
    for r in actors:
        for d in range(1, 6):
            day = add_days(now_datetime(), -d).date()
            if frappe.db.exists("Rider Shift", {"rider": r["profile"], "shift_date": day}):
                continue
            start = get_datetime(f"{day} 08:00:00")
            end = get_datetime(f"{day} 17:00:00")
            frappe.get_doc(
                {
                    "doctype": "Rider Shift",
                    "rider": r["profile"],
                    "employee": r["employee"],
                    "shift_date": day,
                    "shift_start": start,
                    "shift_end": end,
                    "actual_clock_in": start + timedelta(minutes=random.randint(-10, 15)),
                    "actual_clock_out": end + timedelta(minutes=random.randint(-30, 45)),
                    "total_working_hours": 8.5,
                    "total_break_duration": 1.0,
                    "total_active_delivery_hours": round(random.uniform(5.5, 7.5), 1),
                    "total_deliveries": random.randint(2, 5),
                    "completed_deliveries": random.randint(2, 5),
                    "failed_deliveries": random.choice([0, 0, 1]),
                    "total_distance_travelled": round(random.uniform(60, 180), 1),
                    "opening_odometer": 45000 + d * 25,
                    "closing_odometer": 45000 + d * 25 + random.randint(40, 120),
                    "shift_status": "Completed",
                    "supervisor": supervisor_employee,
                    "notes": "Demo rider shift",
                }
            ).insert(ignore_permissions=True)


def ensure_fuel_logs(riders, vehicles):
    for i, v in enumerate(vehicles):
        odometer = 46000 + i * 12000
        for d in range(1, 15, 3):
            if frappe.db.exists("Fuel Log", {"vehicle": v["name"], "fuel_date": add_days(now_datetime(), -d).date()}):
                odometer += 900
                continue
            qty = round(random.uniform(30, 55), 1)
            price = random.randint(170, 195)
            rider = riders[i % len(riders)]
            frappe.get_doc(
                {
                    "doctype": "Fuel Log",
                    "vehicle": v["name"],
                    "rider": rider["profile"],
                    "fuel_date": add_days(now_datetime(), -d).date(),
                    "fuel_type": v["def"]["fuel"],
                    "quantity": qty,
                    "unit_price": price,
                    "total_cost": round(qty * price, 2),
                    "odometer_reading": odometer,
                    "fuel_station": random.choice(["Rubis", "Rubis", "TotalEnergies", "Shell", "Nazo"]),
                    "payment_method": random.choice(["Company Account", "Card", "Cash"]),
                    "consumption_kmpl": round(random.uniform(8, 14), 1),
                    "idempotency_key": f"demo-fuel-{v['name']}-{d}",
                }
            ).insert(ignore_permissions=True)
            odometer += 900


def ensure_vehicle_records(riders, vehicles):
    for i, v in enumerate(vehicles):
        rider = riders[i % len(riders)]
        # recent pre-trip inspections
        for d in range(0, 5):
            day = add_days(now_datetime(), -d).date()
            result = "Passed" if random.random() > 0.2 else "Requires Attention"
            if frappe.db.exists("Vehicle Inspection", {"vehicle": v["name"], "inspection_date": day, "inspection_type": "Pre-Trip"}):
                continue
            frappe.get_doc(
                {
                    "doctype": "Vehicle Inspection",
                    "vehicle": v["name"],
                    "rider": rider["profile"],
                    "inspection_date": day,
                    "inspection_type": "Pre-Trip",
                    "odometer_reading": 46000 + i * 12000 + d * 30,
                    "fuel_level": random.choice(["Full", "3/4", "1/2"]),
                    "tyre_condition": "Good",
                    "brakes_condition": "Good",
                    "lights_condition": "Good" if result == "Passed" else "Fair",
                    "engine_condition": "Good",
                    "general_condition": "Good" if result == "Passed" else "Fair",
                    "inspection_result": result,
                    "defects_identified": None if result == "Passed" else "Minor oil seepage noted",
                    "inspected_by": rider["user"],
                }
            ).insert(ignore_permissions=True)
        # maintenance records
        if not frappe.db.exists("Vehicle Maintenance Record", {"vehicle": v["name"]}):
            frappe.get_doc(
                {
                    "doctype": "Vehicle Maintenance Record",
                    "vehicle": v["name"],
                    "maintenance_type": "Service",
                    "maintenance_date": add_days(now_datetime(), -20).date(),
                    "odometer_reading": 44000 + i * 12000,
                    "description": "Demo scheduled service - oil, filters, brake check",
                    "service_provider": "Demo AutoCare Ltd",
                    "total_cost": random.randint(8000, 25000),
                    "next_service_date": add_days(now_datetime(), 160).date(),
                    "next_service_odometer": 53000 + i * 12000,
                    "status": "Completed",
                }
            ).insert(ignore_permissions=True)
            frappe.get_doc(
                {
                    "doctype": "Vehicle Maintenance Record",
                    "vehicle": v["name"],
                    "maintenance_type": "Repair",
                    "maintenance_date": add_days(now_datetime(), -2).date(),
                    "odometer_reading": 48000 + i * 12000,
                    "description": "Demo repair - wiper motor replacement",
                    "service_provider": "Demo AutoCare Ltd",
                    "total_cost": random.randint(3000, 8000),
                    "status": random.choice(["In Progress", "Open"]),
                }
            ).insert(ignore_permissions=True)


def ensure_availability_and_tokens(riders, jobs):
    active_by_rider = {}
    for j in jobs:
        if j.status in ("Pending", "Dispatched", "Accepted", "En Route", "Arrived", "In Progress"):
            active_by_rider[j.rider_profile] = j.name
    for r in riders:
        current = active_by_rider.get(r["profile"])
        status = "Busy" if current else "Available"
        if frappe.db.exists("Rider Availability", {"rider": r["profile"]}):
            doc = frappe.get_doc("Rider Availability", {"rider": r["profile"]})
        else:
            doc = frappe.get_doc({"doctype": "Rider Availability", "rider": r["profile"]})
        doc.update(
            {
                "availability_status": status,
                "effective_from": now_datetime(),
                "current_delivery_job": current,
                "last_location_latitude": DEPOT_LAT,
                "last_location_longitude": DEPOT_LNG,
                "last_updated": now_datetime(),
                "notes": "Demo availability",
            }
        )
        try:
            doc.save(ignore_permissions=True)
        except frappe.DuplicateEntryError:
            pass
        # refresh token for mobile app login
        ensure_refresh_token(r["user"])


def ensure_refresh_token(user):
    if frappe.db.exists("Refresh Token", {"user": user}):
        return
    raw = os.urandom(48).hex()
    frappe.get_doc(
        {
            "doctype": "Refresh Token",
            "user": user,
            "token_hash": hashlib.sha256(raw.encode()).hexdigest(),
            "device_info": "Demo Android Device",
            "expires_at": add_days(now_datetime(), 30),
            "is_revoked": 0,
            "last_used_at": now_datetime(),
        }
    ).insert(ignore_permissions=True)


def extra_events(job, actor):
    """Add a few non-status events for realism on completed jobs."""
    if job.status != "Completed":
        return
    ts = job.completed_at or now_datetime()
    events = [
        ("Delivery Attempt", "Attempted delivery to customer", "Delivery Attempt", job.arrived_at or ts),
        ("Delivery Success", "Customer signed and OTP verified", "Delivery Success", ts),
    ]
    for etype, notes, reason, when in events:
        frappe.get_doc(
            {
                "doctype": "Delivery Event",
                "delivery_job": job.name,
                "event_type": etype,
                "timestamp": when,
                "created_by": actor["user"],
                "notes": notes,
                "reason": reason,
                "latitude": job.latitude,
                "longitude": job.longitude,
                "created_via": "Mobile App",
                "customer_notified": 1,
                "notification_method": random.choice(["SMS", "WhatsApp", "Push Notification"]),
            }
        ).insert(ignore_permissions=True)


# ---------------------------------------------------------------------------
# orchestration
# ---------------------------------------------------------------------------

def run_demo_data(force=False):
    if not force and frappe.db.exists("Rider Profile", {"rider_name": "James Mwangi"}):
        frappe.throw(
            "Demo data already exists. Pass force=True to regenerate "
            "(note: force only bypasses the guard; it does not delete existing data)."
        )
    frappe.set_user("Administrator")

    company = ensure_company()
    print(f"Using company: {company}")
    ensure_settings()
    zones = ensure_zones(company)
    slas = ensure_slas()
    customers = ensure_customers()
    vehicles = ensure_vehicles(company)
    riders = ensure_riders(company, vehicles, zones)
    drivers = ensure_drivers(company, vehicles, zones)
    sales = ensure_sales(company)
    actors = riders + drivers  # field workers: riders + drivers
    ensure_fleet_assignments(actors, vehicles, company)

    # build jobs
    jobs = []
    jobs_by_day = {}
    for i, plan in enumerate(JOB_PLAN):
        cust = customers[plan[0] % len(customers)]
        kind, aidx = plan[6]
        pool = riders if kind == "R" else drivers
        actor = pool[aidx % len(pool)]
        sla_name = slas["Standard 4h"] if plan[4] == "Standard" else (slas["Express 2h"] if plan[4] == "Express" else slas["Same Day"])
        job = make_job(actor, cust, zones[cust["zone"]], company, sla_name, plan)
        # every third job is created by a sales person from the desk app
        if i % 3 == 0:
            creator = sales[i // 3 % len(sales)]
            job.db_set({"created_by": creator["user"], "created_via": "Manual"}, update_modified=False)
        jobs.append((job, actor, plan))
        jobs_by_day.setdefault(plan[5], []).append(job)

    # create batches first so jobs can link to them
    batches = make_batches(jobs_by_day, riders, company, zones, slas)

    # walk each job through its status flow
    FLOW = {
        "Pending": [],
        "Dispatched": ["Dispatched"],
        "Accepted": ["Dispatched", "Accepted"],
        "En Route": ["Dispatched", "Accepted", "En Route"],
        "Arrived": ["Dispatched", "Accepted", "En Route", "Arrived"],
        "In Progress": ["Dispatched", "Accepted", "En Route", "Arrived", "In Progress"],
        "Failed": ["Dispatched", "Accepted", "En Route", "Arrived", "In Progress", "Failed"],
        "Cancelled": ["Dispatched", "Cancelled"],
        "Completed": ["Dispatched", "Accepted", "En Route", "Arrived", "In Progress", "Completed"],
    }

    final_jobs = []
    for job, actor, plan in jobs:
        _cust_idx, days_ago, status, _prio, _dt, _b, _actor = plan
        for step in FLOW[status]:
            job.update_status(step)
        backdate_job(job, days_ago, status)
        job.reload()
        create_assignment_history(job, actor, days_ago)
        create_gps_logs(job, actor)
        create_attempts_pod_stops(job, actor)
        create_expenses(job, actor)
        extra_events(job, actor)
        final_jobs.append(job)
        print(f"  {job.name}: {status} -> {customer_label(job)}")

    ensure_shifts(actors, company)
    ensure_fuel_logs(actors, vehicles)
    ensure_vehicle_records(actors, vehicles)
    ensure_availability_and_tokens(actors, final_jobs)
    for s in sales:
        ensure_refresh_token(s["user"])

    frappe.db.commit()
    print("\nDemo data generation complete.")
    print(f"  Riders: {len(riders)} | Drivers: {len(drivers)} | Sales: {len(sales)} | Vehicles: {len(vehicles)} | Customers: {len(customers)}")
    print(f"  Jobs: {len(final_jobs)} | Batches: {len(batches)}")
    print("  Logins: rider1..5@, driver1..3@, sales1..2@demo.ledgerctrl / RiderFleet!2026#K3")


def customer_label(job):
    return job.customer
