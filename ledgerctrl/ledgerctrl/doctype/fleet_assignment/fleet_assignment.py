import frappe
from frappe.model.document import Document
from frappe import _


class FleetAssignment(Document):
    def validate(self):
        self.validate_dates()
        self.validate_no_conflict()

    def validate_dates(self):
        if self.assignment_end and self.assignment_end < self.assignment_start:
            frappe.throw(
                _("Assignment End cannot be before Assignment Start"),
                frappe.ValidationError,
            )
        if self.closing_odometer and self.opening_odometer:
            if self.closing_odometer < self.opening_odometer:
                frappe.throw(
                    _("Closing Odometer cannot be less than Opening Odometer"),
                    frappe.ValidationError,
                )

    def validate_no_conflict(self):
        settings = frappe.get_single("Delivery Settings")
        if getattr(settings, "allow_multiple_active_vehicle_assignments", 0):
            return
        if self.assignment_status != "Active":
            return

        # Conflict: same vehicle already actively assigned in overlapping period
        conflicts = frappe.get_all(
            "Fleet Assignment",
            filters={
                "vehicle": self.vehicle,
                "assignment_status": "Active",
                "name": ["!=", self.name or ""],
            },
            fields=["name", "employee", "assignment_start", "assignment_end"],
        )
        for c in conflicts:
            c_end = c.assignment_end or frappe.utils.add_days(frappe.utils.today(), 36500)
            my_end = self.assignment_end or frappe.utils.add_days(frappe.utils.today(), 36500)
            if c.assignment_start <= my_end and self.assignment_start <= c_end:
                frappe.throw(
                    _("Vehicle {0} already has an active assignment ({1}) overlapping this period").format(
                        self.vehicle, c.name
                    ),
                    frappe.ValidationError,
                )
