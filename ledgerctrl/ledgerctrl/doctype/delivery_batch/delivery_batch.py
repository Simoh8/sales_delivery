import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, nowdate
from frappe import _

ACTIVE_JOB_STATUSES = ["Pending", "Dispatched", "Accepted", "En Route", "Arrived", "In Progress"]


class DeliveryBatch(Document):
    def autoname(self):
        if not self.batch_id:
            self.batch_id = "DB-{0}-{1:04d}".format(
                nowdate().replace("-", ""), frappe.db.count("Delivery Batch") + 1
            )

    def validate(self):
        self.validate_jobs()
        self.compute_stats()

    def validate_jobs(self):
        if not self.jobs:
            frappe.throw(_("A delivery batch must contain at least one delivery job"))
        for row in self.jobs:
            job = frappe.db.get_value(
                "Delivery Job",
                row.delivery_job,
                ["status", "delivery_batch"],
                as_dict=True,
            )
            if not job:
                frappe.throw(_("Delivery Job {0} not found").format(row.delivery_job))
            if job.status in ["Completed", "Cancelled"]:
                frappe.throw(
                    _("Cannot add {0} job {1} to a batch").format(job.status, row.delivery_job)
                )
            if job.delivery_batch and job.delivery_batch != self.name:
                frappe.throw(
                    _("Delivery Job {0} is already in batch {1}").format(
                        row.delivery_job, job.delivery_batch
                    )
                )
            # Check other active batches containing this job
            other = frappe.db.exists(
                "Delivery Batch Item",
                {"delivery_job": row.delivery_job, "parent": ["!=", self.name or ""]},
            )
            if other:
                parent = frappe.db.get_value("Delivery Batch Item", other, "parent")
                parent_status = frappe.db.get_value(
                    "Delivery Batch", parent, "batch_status"
                )
                if parent_status not in ["Completed", "Cancelled"]:
                    frappe.throw(
                        _("Delivery Job {0} is already in active batch {1}").format(
                            row.delivery_job, parent
                        )
                    )

    def compute_stats(self):
        statuses = frappe.db.get_all(
            "Delivery Job",
            filters={"name": ["in", [r.delivery_job for r in self.jobs]]},
            fields=["status", "estimated_distance"],
        )
        completed = sum(1 for s in statuses if s.status == "Completed")
        failed = sum(1 for s in statuses if s.status == "Failed")
        pending = len(statuses) - completed - failed
        self.total_jobs = len(statuses)
        self.completed_jobs = completed
        self.failed_jobs = failed
        self.pending_jobs = pending
        self.total_estimated_distance = sum(float(s.estimated_distance or 0) for s in statuses)

        if self.batch_status == "Completed" and not self.completion_time:
            self.completion_time = now_datetime()
        if self.batch_status == "Dispatched" and not self.dispatch_time:
            self.dispatch_time = now_datetime()

    def on_update(self):
        # Reflect batch assignment onto member jobs
        for row in self.jobs:
            frappe.db.set_value(
                "Delivery Job",
                row.delivery_job,
                {
                    "delivery_batch": self.name,
                    "delivery_zone": self.delivery_zone or frappe.db.get_value(
                        "Delivery Job", row.delivery_job, "delivery_zone"
                    ),
                },
                update_modified=False,
            )

    @staticmethod
    def refresh_batch_stats(batch_name):
        """Recompute batch counters after a member job changes status."""
        batch = frappe.get_doc("Delivery Batch", batch_name)
        batch.compute_stats()
        # Determine overall status
        if batch.batch_status in ["Dispatched", "In Progress"]:
            if batch.completed_jobs + batch.failed_jobs >= batch.total_jobs:
                batch.batch_status = "Completed"
            elif batch.completed_jobs > 0 or batch.pending_jobs < batch.total_jobs:
                batch.batch_status = "In Progress"
        batch.db_update()
        return True

    def dispatch(self):
        """Dispatch the whole batch to the assigned rider."""
        if not self.assigned_rider:
            frappe.throw(_("Assign a rider before dispatching"))
        if not self.jobs:
            frappe.throw(_("Batch has no jobs"))
        now = now_datetime()
        self.batch_status = "Dispatched"
        self.dispatch_time = now
        for row in self.jobs:
            job = frappe.get_doc("Delivery Job", row.delivery_job)
            if job.status == "Pending":
                job.rider_profile = self.assigned_rider
                job.assigned_employee = self.assigned_employee
                if self.assigned_vehicle:
                    job.vehicle = self.assigned_vehicle
                if self.delivery_zone:
                    job.delivery_zone = self.delivery_zone
                job.db_set("status", "Dispatched")
                job.db_set("dispatched_at", now)
                frappe.get_doc(
                    {
                        "doctype": "Assignment History",
                        "delivery_job": job.name,
                        "driver": self.assigned_employee,
                        "vehicle": self.assigned_vehicle,
                        "assigned_at": now,
                        "assigned_via": "Batch",
                        "assignment_status": "Assigned",
                        "notes": "Dispatched via batch {0}".format(self.name),
                    }
                ).insert(ignore_permissions=True)
        self.save()
        # Rider goes busy
        from ledgerctrl.ledgerctrl.doctype.rider_availability.rider_availability import (
            RiderAvailability,
        )

        RiderAvailability.set_status(
            self.assigned_rider, "Busy", notes="Dispatched batch {0}".format(self.name)
        )
        return {"success": True, "batch": self.name, "status": self.batch_status}
