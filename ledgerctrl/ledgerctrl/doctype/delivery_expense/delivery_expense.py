import frappe
from frappe.model.document import Document
from frappe import _


class DeliveryExpense(Document):
    def validate(self):
        self.check_idempotency()

    def check_idempotency(self):
        if self.idempotency_key and not self.is_new():
            existing = frappe.db.get_value(
                "Delivery Expense",
                {"idempotency_key": self.idempotency_key, "name": ["!=", self.name]},
                "name",
            )
            if existing:
                frappe.throw(
                    _("Duplicate expense submission detected"),
                    frappe.DuplicateEntryError,
                )
