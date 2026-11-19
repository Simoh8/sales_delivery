import frappe
from frappe.model.document import Document
from datetime import datetime
from frappe import _


class DeliveryEvent(Document):
    def before_save(self):
        """Validate event data before saving."""
        self.validate_status_change()
        self.set_timestamp_if_missing()

    def validate_status_change(self):
        """Ensure status change events have old and new status."""
        if self.event_type == "Status Change":
            if not self.old_status or not self.new_status:
                frappe.throw(
                    _("Status Change events must have both old_status and new_status"),
                    frappe.ValidationError
                )

    def set_timestamp_if_missing(self):
        """Set timestamp to current time if not provided."""
        if not self.timestamp:
            self.timestamp = datetime.utcnow()

    @staticmethod
    def log_event(delivery_job, event_type, notes=None, old_status=None, new_status=None,
                  latitude=None, longitude=None, created_by=None, created_via="Mobile App"):
        """Helper method to log a delivery event."""
        event_doc = frappe.get_doc({
            "doctype": "Delivery Event",
            "delivery_job": delivery_job,
            "event_type": event_type,
            "notes": notes,
            "old_status": old_status,
            "new_status": new_status,
            "latitude": latitude,
            "longitude": longitude,
            "created_by": created_by or frappe.session.user,
            "created_via": created_via,
            "timestamp": datetime.utcnow()
        })
        event_doc.insert()
        return event_doc

    @staticmethod
    def get_event_timeline(delivery_job):
        """Get all events for a delivery job in chronological order."""
        events = frappe.get_all(
            "Delivery Event",
            filters={"delivery_job": delivery_job},
            fields=[
                "name",
                "event_type",
                "timestamp",
                "old_status",
                "new_status",
                "notes",
                "latitude",
                "longitude",
                "created_by",
                "created_via"
            ],
            order_by="timestamp ASC"
        )
        return events

    @staticmethod
    def get_recent_events(driver=None, limit=10):
        """Get recent delivery events, optionally filtered by driver."""
        filters = {}
        if driver:
            filters["driver"] = driver

        events = frappe.get_all(
            "Delivery Event",
            filters=filters,
            fields=[
                "name",
                "delivery_job",
                "event_type",
                "timestamp",
                "old_status",
                "new_status",
                "notes"
            ],
            order_by="timestamp DESC",
            limit_page_length=limit
        )
        return events

    @staticmethod
    def get_events_by_type(delivery_job, event_type):
        """Get all events of a specific type for a delivery job."""
        events = frappe.get_all(
            "Delivery Event",
            filters={
                "delivery_job": delivery_job,
                "event_type": event_type
            },
            fields=["*"],
            order_by="timestamp DESC"
        )
        return events

    @staticmethod
    def cleanup_old_events(days_to_keep=90):
        """Delete delivery events older than specified days."""
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        frappe.db.delete("Delivery Event", {
            "timestamp": ["<", cutoff_date]
        })

        frappe.db.commit()


def cleanup_old_events(days_to_keep=90):
    """Scheduler entry point for deleting old delivery events."""
    DeliveryEvent.cleanup_old_events(days_to_keep=days_to_keep)
