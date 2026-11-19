import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, getdate, get_datetime, time_diff_in_hours
from frappe import _


class RiderShift(Document):
    def validate(self):
        self.validate_no_overlap()
        self.compute_totals()

    def validate_no_overlap(self):
        """Prevent overlapping active shifts for the same rider."""
        settings = frappe.get_single("Delivery Settings")
        if getattr(settings, "allow_overlapping_shifts", 0):
            return
        if self.shift_status == "Cancelled":
            return
        if not self.rider or not self.shift_date:
            return

        overlaps = frappe.get_all(
            "Rider Shift",
            filters={
                "rider": self.rider,
                "shift_date": self.shift_date,
                "shift_status": ["in", ["Scheduled", "Active"]],
                "name": ["!=", self.name or ""],
            },
            fields=["name"],
        )
        if overlaps:
            frappe.throw(
                _("Rider {0} already has an active shift on {1} ({2})").format(
                    self.rider, self.shift_date, overlaps[0].name
                ),
                frappe.ValidationError,
            )

    def compute_totals(self):
        if self.actual_clock_in and self.actual_clock_out:
            diff = get_datetime(self.actual_clock_out) - get_datetime(self.actual_clock_in)
            self.total_working_hours = round(diff.total_seconds() / 3600, 2)
        if self.opening_odometer and self.closing_odometer:
            self.total_distance_travelled = self.closing_odometer - self.opening_odometer

    def on_update(self):
        if self.shift_status == "Active" and not self.actual_clock_in:
            self.db_set("actual_clock_in", now_datetime())

    @staticmethod
    def get_active_shift(rider):
        return frappe.db.get_value(
            "Rider Shift",
            {"rider": rider, "shift_status": "Active"},
            "name",
            order_by="creation desc",
        )

    @staticmethod
    def refresh_delivery_stats(shift_name):
        """Recompute delivery counters for a shift from its delivery jobs."""
        shift = frappe.get_doc("Rider Shift", shift_name)
        rider_profile = shift.rider
        employee = shift.employee

        jobs = frappe.get_all(
            "Delivery Job",
            filters={
                "rider_profile": rider_profile,
                "completed_at": ["between", [shift.shift_date, shift.shift_date]],
            },
            fields=["name", "status", "actual_duration", "actual_distance", "completed_at"],
        ) or []

        # Fall back to employee-based matching for jobs without rider_profile
        if not jobs and employee:
            jobs = frappe.get_all(
                "Delivery Job",
                filters={
                    "driver": employee,
                    "completed_at": ["between", [shift.shift_date, shift.shift_date]],
                },
                fields=["name", "status", "actual_duration", "actual_distance", "completed_at"],
            ) or []

        completed = [j for j in jobs if j.status == "Completed"]
        failed = [j for j in jobs if j.status == "Failed"]

        active_hours = 0.0
        for j in completed:
            if j.actual_duration:
                active_hours += j.actual_duration / 60.0

        frappe.db.set_value(
            "Rider Shift",
            shift_name,
            {
                "total_deliveries": len(jobs),
                "completed_deliveries": len(completed),
                "failed_deliveries": len(failed),
                "total_active_delivery_hours": round(active_hours, 2),
            },
            update_modified=False,
        )
        return True
