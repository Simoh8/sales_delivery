import frappe
from frappe.model.document import Document
from frappe.utils import nowdate, now_datetime
from frappe import _


class DeliveryAttempt(Document):
    def before_save(self):
        if not self.attempt_number:
            self.attempt_number = self._next_attempt_number()
        if not self.attempt_date:
            self.attempt_date = nowdate()
        if not self.rider:
            rider = frappe.db.get_value(
                "Delivery Job", self.delivery_job, "rider_profile"
            )
            if rider:
                self.rider = rider
        if not self.vehicle:
            vehicle = frappe.db.get_value(
                "Delivery Job", self.delivery_job, "vehicle"
            )
            if vehicle:
                self.vehicle = vehicle

    def on_update(self):
        self.update_delivery_job_attempts()

    def _next_attempt_number(self):
        last = frappe.db.get_value(
            "Delivery Attempt",
            {"delivery_job": self.delivery_job},
            "attempt_number",
            order_by="attempt_number desc",
        )
        return (last or 0) + 1

    def update_delivery_job_attempts(self):
        """Keep Delivery Job attempt counters in sync."""
        count, first_attempt = frappe.db.get_value(
            "Delivery Attempt",
            {"delivery_job": self.delivery_job},
            ["count(name)", "min(attempt_date)"],
        ) or (0, None)
        updates = {"number_of_attempts": count or 0}
        if first_attempt and not frappe.db.get_value(
            "Delivery Job", self.delivery_job, "first_attempt_date"
        ):
            updates["first_attempt_date"] = first_attempt
        frappe.db.set_value("Delivery Job", self.delivery_job, updates, update_modified=False)

    @staticmethod
    def log_attempt(delivery_job, status, rider=None, vehicle=None,
                    failure_reason=None, lat=None, lng=None, notes=None,
                    arrival_time=None, completion_time=None, attachment=None):
        """Helper used by APIs to record a delivery attempt."""
        doc = frappe.get_doc(
            {
                "doctype": "Delivery Attempt",
                "delivery_job": delivery_job,
                "attempt_status": status,
                "rider": rider,
                "vehicle": vehicle,
                "failure_reason": failure_reason,
                "gps_latitude": lat,
                "gps_longitude": lng,
                "notes": notes,
                "arrival_time": arrival_time or now_datetime(),
                "completion_time": completion_time or now_datetime(),
                "attachment": attachment,
            }
        )
        doc.insert(ignore_permissions=True)
        return doc.name
