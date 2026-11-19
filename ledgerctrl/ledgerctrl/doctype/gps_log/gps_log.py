import frappe
from frappe.model.document import Document
from datetime import datetime
from frappe import _


class GPSLog(Document):
    def before_save(self):
        """Validate GPS data before saving."""
        self.validate_coordinates()
        self.set_driver_from_delivery_job()

    def validate_coordinates(self):
        """Validate latitude and longitude values."""
        if not (-90 <= self.latitude <= 90):
            frappe.throw(_("Latitude must be between -90 and 90"), frappe.ValidationError)

        if not (-180 <= self.longitude <= 180):
            frappe.throw(_("Longitude must be between -180 and 180"), frappe.ValidationError)

    def set_driver_from_delivery_job(self):
        """Auto-populate driver from delivery job if not set."""
        if self.delivery_job and not self.driver:
            delivery_job = frappe.get_doc("Delivery Job", self.delivery_job)
            self.driver = delivery_job.driver
            self.vehicle = delivery_job.vehicle

    def calculate_distance_to(self, target_lat, target_lon):
        """Calculate distance from this GPS point to target coordinates using Haversine formula."""
        from math import radians, sin, cos, sqrt, atan2

        R = 6371  # Earth's radius in km

        lat1 = radians(self.latitude)
        lon1 = radians(self.longitude)
        lat2 = radians(target_lat)
        lon2 = radians(target_lon)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        distance = R * c
        return distance

    @staticmethod
    def get_latest_location(driver, delivery_job=None):
        """Get the latest GPS location for a driver."""
        filters = {"driver": driver}
        if delivery_job:
            filters["delivery_job"] = delivery_job

        log = frappe.get_last_doc("GPS Log", filters=filters)
        if log:
            return {
                "latitude": log.latitude,
                "longitude": log.longitude,
                "timestamp": log.timestamp,
                "accuracy": log.location_accuracy,
                "speed": log.speed,
                "heading": log.heading
            }
        return None

    @staticmethod
    def get_location_history(delivery_job, start_time=None, end_time=None):
        """Get GPS log history for a delivery job within a time range."""
        filters = {"delivery_job": delivery_job}

        if start_time:
            filters["timestamp"] = [">=", start_time]
        if end_time:
            if "timestamp" in filters:
                filters["timestamp"].append("<=", end_time)
            else:
                filters["timestamp"] = ["<=", end_time]

        logs = frappe.get_all(
            "GPS Log",
            filters=filters,
            fields=["latitude", "longitude", "timestamp", "speed", "heading", "accuracy"],
            order_by="timestamp ASC"
        )

        return logs

    @staticmethod
    def cleanup_old_logs(days_to_keep=30):
        """Delete GPS logs older than specified days to manage storage."""
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        frappe.db.delete("GPS Log", {
            "timestamp": ["<", cutoff_date]
        })

        frappe.db.commit()


def cleanup_old_logs(days_to_keep=30):
    """Scheduler entry point for deleting old GPS logs."""
    GPSLog.cleanup_old_logs(days_to_keep=days_to_keep)
