import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime
from frappe import _


class DeliveryStop(Document):
    def before_save(self):
        self.populate_from_job()
        self.compute_waiting_duration()

    def populate_from_job(self):
        if self.delivery_job and not self.customer:
            job = frappe.db.get_value(
                "Delivery Job",
                self.delivery_job,
                ["customer", "customer_address", "latitude", "longitude"],
                as_dict=True,
            )
            if job:
                self.customer = job.customer
                self.address = job.customer_address
                self.latitude = self.latitude or job.latitude
                self.longitude = self.longitude or job.longitude
        if self.delivery_batch and not self.delivery_trip:
            self.delivery_trip = frappe.db.get_value(
                "Delivery Batch", self.delivery_batch, "delivery_trip"
            )

    def compute_waiting_duration(self):
        if self.actual_arrival and self.departure_time:
            diff = get_dt(self.departure_time) - get_dt(self.actual_arrival)
            self.waiting_duration = int(diff.total_seconds() / 60)

    @staticmethod
    def next_sequence(batch_name):
        last = frappe.db.get_value(
            "Delivery Stop",
            {"delivery_batch": batch_name},
            "stop_sequence",
            order_by="stop_sequence desc",
        )
        return (last or 0) + 1


def get_dt(value):
    return frappe.utils.get_datetime(value)
