import frappe
from frappe.model.document import Document
from frappe import _


class FuelLog(Document):
    def validate(self):
        self.compute_total()
        self.compute_consumption()
        self.check_idempotency()
        self.check_odometer()

    def check_idempotency(self):
        if self.idempotency_key and not self.is_new():
            existing = frappe.db.get_value(
                "Fuel Log",
                {"idempotency_key": self.idempotency_key, "name": ["!=", self.name]},
                "name",
            )
            if existing:
                frappe.throw(
                    _("Duplicate fuel log submission detected"),
                    frappe.DuplicateEntryError,
                )

    def compute_total(self):
        if self.quantity and self.unit_price:
            self.total_cost = round(float(self.quantity) * float(self.unit_price), 2)

    def compute_consumption(self):
        """km/L between this fill and the previous fill for the vehicle."""
        self.consumption_kmpl = None
        self.flag_reason = None
        if not self.odometer_reading or not self.quantity:
            return
        prev = frappe.db.get_value(
            "Fuel Log",
            {
                "vehicle": self.vehicle,
                "odometer_reading": ["<", self.odometer_reading],
                "name": ["!=", self.name or ""],
            },
            ["odometer_reading", "quantity"],
            order_by="odometer_reading desc",
        )
        if not prev or not prev[0]:
            return
        distance = self.odometer_reading - prev[0]
        litres = self.quantity + (prev[1] or 0) * 0  # this fill's litres vs distance since last fill
        # consumption = distance travelled since previous fill / litres filled now
        if distance > 0 and self.quantity:
            kmpl = distance / self.quantity
            self.consumption_kmpl = round(kmpl, 2)
            if kmpl < 5:  # suspiciously low for most vehicles
                self.flag_reason = _("Unusually low fuel efficiency ({0} km/L)").format(
                    kmpl
                )

    def check_odometer(self):
        if not self.odometer_reading:
            return
        # odometer should not go backwards vs latest reading
        latest = frappe.db.get_value(
            "Fuel Log",
            {"vehicle": self.vehicle, "name": ["!=", self.name or ""]},
            "odometer_reading",
            order_by="odometer_reading desc",
        )
        if latest and self.odometer_reading < latest:
            self.flag_reason = (
                (self.flag_reason + "; ") if self.flag_reason else ""
            ) + _("Odometer reading is lower than the previous recorded reading")
