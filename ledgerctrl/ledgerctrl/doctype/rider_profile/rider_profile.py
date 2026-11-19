import frappe
from frappe.model.document import Document
from frappe import _


class RiderProfile(Document):
    def validate(self):
        self.validate_employee()
        self.sync_user_from_employee()

    def validate_employee(self):
        if self.employee:
            employee = frappe.db.get_value(
                "Employee", self.employee, ["name", "status", "company"], as_dict=True
            )
            if not employee:
                frappe.throw(_("Linked Employee {0} does not exist").format(self.employee))
            if self.company and employee.company and self.company != employee.company:
                frappe.throw(
                    _("Company mismatch: employee belongs to {0}").format(employee.company)
                )
            if not self.company:
                self.company = employee.company

    def sync_user_from_employee(self):
        if not self.user and self.employee:
            user_id = frappe.db.get_value("Employee", self.employee, "user_id")
            if user_id:
                self.user = user_id
        if not self.mobile_number and self.employee:
            mobile = frappe.db.get_value("Employee", self.employee, "cell_number")
            if mobile:
                self.mobile_number = mobile

    def on_update(self):
        # Keep linked Delivery Jobs' rider name in sync implicitly via link;
        # nothing else required here.
        pass

    @staticmethod
    def get_rider_for_user(user=None):
        """Return the Rider Profile linked to a User (defaults to session user)."""
        user = user or frappe.session.user
        employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
        if not employee:
            return None
        return frappe.db.get_value(
            "Rider Profile",
            {"employee": employee, "employment_status": "Active"},
            "name",
        )
