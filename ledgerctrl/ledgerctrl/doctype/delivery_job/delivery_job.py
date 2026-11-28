import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, get_datetime, add_to_date, getdate, get_time
from datetime import datetime, timedelta
from frappe import _

ACTIVE_STATUSES = ["Pending", "Dispatched", "Accepted", "En Route", "Arrived", "In Progress"]


class DeliveryJob(Document):
    def before_save(self):
        """Validate and set timestamps before saving."""
        if not self.company:
            self.company = self._resolve_company()
        self.check_idempotency()
        self.validate_rider_availability()
        self.set_actual_duration()
        self.calculate_delay()
        self.calculate_revenue()
        self.update_sla_status()

    def on_update(self):
        """Log status changes as delivery events."""
        if self.get_doc_before_save():
            old_status = self.get_doc_before_save().status
            if old_status != self.status:
                self.log_status_change(old_status, self.status)
                self.handle_status_side_effects(old_status, self.status)

        # Keep batch counters in sync
        if self.delivery_batch:
            try:
                from ledgerctrl.ledgerctrl.doctype.delivery_batch.delivery_batch import (
                    DeliveryBatch,
                )

                DeliveryBatch.refresh_batch_stats(self.delivery_batch)
            except Exception:
                frappe.log_error(frappe.get_traceback(), "Batch stats refresh failed")

    def _resolve_company(self):
        """Resolve company from user default, assigned employee, or first company."""
        company = frappe.defaults.get_user_default("Company")
        if company:
            return company
        employee = self.assigned_employee or self.driver
        if not employee and self.rider_profile:
            employee = frappe.db.get_value("Rider Profile", self.rider_profile, "employee")
        if employee:
            company = frappe.db.get_value("Employee", employee, "company")
            if company:
                return company
        return frappe.db.get_value("Company", {}, "name")

    def check_idempotency(self):
        if self.idempotency_key and not self.is_new():
            existing = frappe.db.get_value(
                "Delivery Job",
                {"idempotency_key": self.idempotency_key, "name": ["!=", self.name]},
                "name",
            )
            if existing:
                frappe.throw(
                    _("Duplicate delivery submission detected (idempotency key already used)"),
                    frappe.DuplicateEntryError,
                )

    def validate_rider_availability(self):
        """Prevent assigning an occupied rider unless settings allow it."""
        if not self.rider_profile or self.status in ("Completed", "Cancelled"):
            return
        settings = frappe.get_single("Delivery Settings")
        if getattr(settings, "allow_multiple_active_deliveries", 0):
            return
        active_jobs = frappe.get_all(
            "Delivery Job",
            filters={
                "rider_profile": self.rider_profile,
                "status": ["in", ACTIVE_STATUSES],
                "name": ["!=", self.name or ""],
            },
            fields=["name"],
        )
        if active_jobs and self.status in ("Dispatched", "Accepted", "En Route", "In Progress"):
            frappe.throw(
                _("Rider {0} already has active delivery {1}").format(
                    self.rider_profile, active_jobs[0].name
                ),
                frappe.ValidationError,
            )

    def handle_status_side_effects(self, old_status, new_status):
        """Update rider availability and timestamps on status changes."""
        now = now_datetime()
        if new_status == "Accepted" and not self.accepted_at:
            self.db_set("accepted_at", now)
        if new_status == "En Route" and not self.en_route_at:
            self.db_set("en_route_at", now)
        if new_status == "Arrived" and not self.arrived_at:
            self.db_set("arrived_at", now)
        if new_status == "In Progress" and not self.started_delivery_at:
            self.db_set("started_delivery_at", now)
            if not self.actual_pickup_time:
                self.db_set("actual_pickup_time", now)
        if new_status == "Completed":
            self.db_set("completed_at", now)
            self.db_set("actual_delivery_time", now)
        if new_status in ("Completed", "Failed", "Cancelled") and self.rider_profile:
            self._update_rider_availability(new_status)

    def _update_rider_availability(self, new_status):
        try:
            from ledgerctrl.ledgerctrl.doctype.rider_availability.rider_availability import (
                RiderAvailability,
            )

            if new_status == "Completed":
                RiderAvailability.set_status(
                    self.rider_profile,
                    "Available",
                    current_delivery_job=None,
                    notes="Delivery {0} completed".format(self.name),
                )
            elif new_status in ("Failed", "Cancelled"):
                # Rider may still have other active jobs; mark busy only if none remain
                remaining = frappe.db.count(
                    "Delivery Job",
                    {
                        "rider_profile": self.rider_profile,
                        "status": ["in", ACTIVE_STATUSES],
                        "name": ["!=", self.name],
                    },
                )
                RiderAvailability.set_status(
                    self.rider_profile,
                    "Busy" if remaining else "Available",
                    notes="Delivery {0} {1}".format(self.name, new_status.lower()),
                )
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Rider availability update failed")

    def set_actual_duration(self):
        """Calculate actual duration from started to completed."""
        if self.started_delivery_at and self.completed_at:
            duration = self.completed_at - self.started_delivery_at
            self.actual_duration = int(duration.total_seconds() / 60)

    def calculate_delay(self):
        """Calculate delay in minutes."""
        if self.completed_at and self.scheduled_date and self.scheduled_time:
            scheduled_datetime = datetime.combine(
                getdate(self.scheduled_date),
                get_time(self.scheduled_time)
            )
            if scheduled_datetime.tzinfo is None:
                scheduled_datetime = scheduled_datetime.replace(tzinfo=self.completed_at.tzinfo)

            delay = self.completed_at - scheduled_datetime
            self.delay_minutes = int(delay.total_seconds() / 60)

    def calculate_revenue(self):
        charge = float(self.customer_delivery_charge or self.grand_total or 0)
        cost = float(self.actual_delivery_cost or 0)
        if charge or cost:
            self.delivery_revenue = round(charge - cost, 2)

    def update_sla_status(self):
        """Evaluate SLA status from scheduled window + SLA definition."""
        if not self.delivery_sla:
            if not self.sla_status or self.sla_status == "No SLA":
                self.sla_status = "No SLA"
            return
        sla = frappe.db.get_value(
            "Delivery SLA", self.delivery_sla, "maximum_delivery_duration", as_dict=True
        )
        if not sla or not sla.maximum_delivery_duration:
            self.sla_status = "On Track"
            return

        deadline = None
        if self.scheduled_delivery_end:
            deadline = get_datetime(self.scheduled_delivery_end)
        elif self.scheduled_delivery_start:
            deadline = get_datetime(self.scheduled_delivery_start) + timedelta(
                minutes=sla.maximum_delivery_duration
            )
        elif self.dispatched_at:
            deadline = get_datetime(self.dispatched_at) + timedelta(
                minutes=sla.maximum_delivery_duration
            )
        if not deadline:
            self.sla_status = "On Track"
            return

        now = now_datetime()
        if self.completed_at:
            self.sla_status = "Met" if get_datetime(self.completed_at) <= deadline else "Breached"
        elif now > deadline:
            self.sla_status = "Breached"
        else:
            remaining = (deadline - now).total_seconds() / 60
            self.sla_status = "At Risk" if remaining <= 30 else "On Track"

    def log_status_change(self, old_status, new_status):
        """Create a delivery event for status changes."""
        frappe.get_doc({
            "doctype": "Delivery Event",
            "delivery_job": self.name,
            "event_type": "Status Change",
            "old_status": old_status,
            "new_status": new_status,
            "timestamp": datetime.utcnow(),
            "notes": f"Status changed from {old_status} to {new_status}"
        }).insert(ignore_permissions=True)

    def update_status(self, new_status, notes=None):
        """Update delivery job status with validation."""
        valid_transitions = {
            "Pending": ["Dispatched", "Cancelled"],
            "Dispatched": ["Accepted", "Cancelled"],
            "Accepted": ["En Route", "Cancelled"],
            "En Route": ["Arrived", "Cancelled"],
            "Arrived": ["In Progress", "Cancelled"],
            "In Progress": ["Completed", "Failed"],
            "Completed": [],
            "Cancelled": [],
            "Failed": ["Pending", "Cancelled"]
        }

        if new_status not in valid_transitions.get(self.status, []):
            frappe.throw(
                _(f"Cannot transition from {self.status} to {new_status}"),
                frappe.ValidationError
            )

        self.status = new_status

        # Set timestamp based on status
        timestamp_field = {
            "Dispatched": "dispatched_at",
            "Accepted": "accepted_at",
            "En Route": "en_route_at",
            "Arrived": "arrived_at",
            "In Progress": "started_delivery_at",
            "Completed": "completed_at",
            "Cancelled": "cancelled_at"
        }.get(new_status)

        if timestamp_field:
            setattr(self, timestamp_field, datetime.utcnow())

        if notes:
            self.delivery_notes = notes

        self.save()

    def add_gps_log(self, latitude, longitude, accuracy=None, speed=None):
        """Add a GPS log entry for this delivery job."""
        frappe.get_doc({
            "doctype": "GPS Log",
            "delivery_job": self.name,
            "latitude": latitude,
            "longitude": longitude,
            "accuracy": accuracy,
            "speed": speed,
            "timestamp": datetime.utcnow()
        }).insert(ignore_permissions=True)

    def assign_driver(self, driver_id, vehicle_id=None):
        """Assign a driver to this delivery job."""
        old_driver = self.driver

        self.driver = driver_id
        if vehicle_id:
            self.vehicle = vehicle_id

        self.save()

        # Log assignment history
        frappe.get_doc({
            "doctype": "Assignment History",
            "delivery_job": self.name,
            "driver": driver_id,
            "vehicle": vehicle_id,
            "assigned_at": datetime.utcnow(),
            "notes": f"Assigned to driver {driver_id}"
        }).insert(ignore_permissions=True)

        # Log event if driver changed
        if old_driver and old_driver != driver_id:
            frappe.get_doc({
                "doctype": "Delivery Event",
                "delivery_job": self.name,
                "event_type": "Reassignment",
                "old_status": f"Driver: {old_driver}",
                "new_status": f"Driver: {driver_id}",
                "timestamp": datetime.utcnow(),
                "notes": f"Driver reassigned from {old_driver} to {driver_id}"
            }).insert(ignore_permissions=True)
