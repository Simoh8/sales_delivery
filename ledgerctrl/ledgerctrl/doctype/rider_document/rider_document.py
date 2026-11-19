import frappe
from frappe.model.document import Document
from frappe.utils import today
from frappe import _


class RiderDocument(Document):
    def validate(self):
        self.validate_dates()
        self.update_expired_status()

    def validate_dates(self):
        if self.issue_date and self.expiry_date and self.expiry_date <= self.issue_date:
            frappe.throw(
                _("Expiry Date must be after Issue Date"), frappe.ValidationError
            )

    def update_expired_status(self):
        if (
            self.expiry_date
            and self.expiry_date < today()
            and self.verification_status != "Rejected"
        ):
            self.verification_status = "Expired"
