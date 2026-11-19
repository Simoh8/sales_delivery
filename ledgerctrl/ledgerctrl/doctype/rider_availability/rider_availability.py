import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, get_datetime
from frappe import _


class RiderAvailability(Document):
    def before_save(self):
        if not self.effective_from:
            self.effective_from = now_datetime()
        self.last_updated = now_datetime()

    def on_update(self):
        self.close_previous_availability()

    def close_previous_availability(self):
        """Close any open availability record for this rider."""
        previous = frappe.get_all(
            "Rider Availability",
            filters={
                "rider": self.rider,
                "name": ["!=", self.name],
                "effective_until": ["is", "not set"],
            },
            fields=["name", "effective_from"],
        )
        for prev in previous:
            if prev.name and prev.name != self.name:
                frappe.db.set_value(
                    "Rider Availability",
                    prev.name,
                    "effective_until",
                    min(self.effective_from, now_datetime()),
                    update_modified=False,
                )

    @staticmethod
    def get_current_status(rider):
        """Return the rider's current availability status."""
        now = now_datetime()
        record = frappe.db.get_value(
            "Rider Availability",
            {
                "rider": rider,
                "effective_from": ["<=", now],
                "effective_until": ["is", "not set"],
            },
            ["name", "availability_status", "current_delivery_job"],
            order_by="effective_from desc",
        )
        if record:
            return {
                "availability_id": record[0],
                "status": record[1],
                "current_delivery_job": record[2],
            }
        return {"availability_id": None, "status": "Offline", "current_delivery_job": None}

    @staticmethod
    def set_status(rider, status, current_delivery_job=None, lat=None, lng=None, notes=None):
        """Create a new availability record for the rider."""
        current = RiderAvailability.get_current_status(rider)
        if (
            current["status"] == status
            and current["current_delivery_job"] == current_delivery_job
        ):
            # Just update location/timestamp on the open record
            if current["availability_id"]:
                frappe.db.set_value(
                    "Rider Availability",
                    current["availability_id"],
                    {
                        "last_location_latitude": lat,
                        "last_location_longitude": lng,
                        "last_updated": now_datetime(),
                    },
                    update_modified=False,
                )
                return current["availability_id"]

        doc = frappe.get_doc(
            {
                "doctype": "Rider Availability",
                "rider": rider,
                "availability_status": status,
                "effective_from": now_datetime(),
                "current_delivery_job": current_delivery_job,
                "last_location_latitude": lat,
                "last_location_longitude": lng,
                "last_updated": now_datetime(),
                "notes": notes,
            }
        )
        doc.insert(ignore_permissions=True)
        return doc.name

    @staticmethod
    def is_rider_available(rider):
        status = RiderAvailability.get_current_status(rider)
        return status["status"] == "Available" and not status["current_delivery_job"]
