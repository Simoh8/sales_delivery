import frappe
from frappe.model.document import Document
from datetime import datetime
from frappe import _


class AssignmentHistory(Document):
    def before_save(self):
        """Validate assignment history before saving."""
        self.validate_assignment_status()

    def validate_assignment_status(self):
        """Ensure status changes are valid."""
        if self.get_doc_before_save():
            old_status = self.get_doc_before_save().assignment_status
            new_status = self.assignment_status

            valid_transitions = {
                "Assigned": ["Accepted", "Rejected", "Unassigned"],
                "Accepted": ["Unassigned", "Completed"],
                "Rejected": ["Unassigned"],
                "Unassigned": [],
                "Completed": []
            }

            if new_status not in valid_transitions.get(old_status, []):
                frappe.throw(
                    _(f"Cannot transition from {old_status} to {new_status}"),
                    frappe.ValidationError
                )

            # Set timestamp based on status
            if new_status == "Accepted" and not self.accepted_at:
                self.accepted_at = datetime.utcnow()
            elif new_status == "Rejected" and not self.rejected_at:
                self.rejected_at = datetime.utcnow()
            elif new_status == "Unassigned" and not self.unassigned_at:
                self.unassigned_at = datetime.utcnow()

    def mark_accepted(self):
        """Mark assignment as accepted by driver."""
        self.assignment_status = "Accepted"
        self.accepted_at = datetime.utcnow()
        self.save()

        # Update delivery job status
        if self.delivery_job:
            delivery_job = frappe.get_doc("Delivery Job", self.delivery_job)
            delivery_job.update_status("Accepted", f"Assignment accepted by {self.driver_name}")

    def mark_rejected(self, reason=None):
        """Mark assignment as rejected by driver."""
        self.assignment_status = "Rejected"
        self.rejected_at = datetime.utcnow()
        if reason:
            self.reason_for_change = reason
        self.save()

        # Log delivery event
        if self.delivery_job:
            frappe.get_doc({
                "doctype": "Delivery Event",
                "delivery_job": self.delivery_job,
                "event_type": "Assignment Rejected",
                "old_status": "Assigned",
                "new_status": "Unassigned",
                "timestamp": datetime.utcnow(),
                "notes": f"Assignment rejected by {self.driver_name}. Reason: {reason or 'Not specified'}"
            }).insert()

    def mark_unassigned(self, reason=None):
        """Mark assignment as unassigned (reassignment)."""
        self.assignment_status = "Unassigned"
        self.unassigned_at = datetime.utcnow()
        if reason:
            self.reason_for_change = reason
        self.save()
