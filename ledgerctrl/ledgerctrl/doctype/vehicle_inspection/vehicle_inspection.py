import frappe
from frappe.model.document import Document
from frappe import _


class VehicleInspection(Document):
    def validate(self):
        self.auto_result()

    def auto_result(self):
        """Derive inspection result from individual condition checks."""
        checks = [
            self.tyre_condition,
            self.brakes_condition,
            self.lights_condition,
            self.engine_condition,
            self.general_condition,
        ]
        if any(c == "Poor" for c in checks):
            self.inspection_result = "Failed"
        elif any(c == "Fair" for c in checks):
            self.inspection_result = "Requires Attention"
        elif all(c in ("Good", "N/A", None) for c in checks):
            self.inspection_result = "Passed"

    def on_update(self):
        if self.inspection_result == "Failed":
            frappe.log_error(
                "Vehicle {0} failed inspection {1}. Defects: {2}".format(
                    self.vehicle, self.name, self.defects_identified or "none"
                ),
                "Failed Vehicle Inspection",
            )

    @staticmethod
    def is_vehicle_cleared(vehicle):
        """A vehicle is cleared for dispatch if its latest inspection passed
        (or it has no inspections)."""
        latest = frappe.db.get_value(
            "Vehicle Inspection",
            {"vehicle": vehicle},
            "inspection_result",
            order_by="inspection_date desc",
        )
        return latest in (None, "Passed")
