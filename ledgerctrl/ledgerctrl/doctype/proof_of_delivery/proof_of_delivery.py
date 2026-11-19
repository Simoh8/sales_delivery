import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime
from frappe import _


class ProofOfDelivery(Document):
    def validate(self):
        self.check_idempotency()
        self.validate_proof_requirements()

    def check_idempotency(self):
        if self.idempotency_key and not self.is_new():
            existing = frappe.db.get_value(
                "Proof of Delivery",
                {"idempotency_key": self.idempotency_key, "name": ["!=", self.name]},
                "name",
            )
            if existing:
                frappe.throw(
                    _("Duplicate submission detected (idempotency key already used)"),
                    frappe.DuplicateEntryError,
                )

    def validate_proof_requirements(self):
        settings = frappe.get_single("Delivery Settings")
        if not settings:
            return
        if (
            settings.require_signature
            and not self.customer_signature
            and not self.delivery_photograph
        ):
            frappe.msgprint(
                _("Signature or photograph is recommended for proof of delivery"),
                indicator="orange",
            )

    def on_update(self):
        # Link the latest POD to the delivery job
        frappe.db.set_value(
            "Delivery Job",
            self.delivery_job,
            "proof_of_delivery",
            self.name,
            update_modified=False,
        )

    @staticmethod
    def verify_otp(pod_name, otp):
        """Verify an OTP for a Proof of Delivery record."""
        pod = frappe.get_doc("Proof of Delivery", pod_name)
        job = frappe.get_doc("Delivery Job", pod.delivery_job)
        dn = job.delivery_note
        expected = frappe.db.get_value("Delivery Note", dn, "custom_otp_code") if dn else None
        if not expected:
            frappe.throw(_("No OTP has been generated for this delivery"), frappe.ValidationError)
        if str(otp) != str(expected):
            frappe.db.set_value(
                "Proof of Delivery", pod_name, "otp_verification_status", "Failed"
            )
            frappe.throw(_("Invalid OTP"), frappe.ValidationError)
        frappe.db.set_value(
            "Proof of Delivery",
            pod_name,
            {"otp_verification_status": "Verified", "otp_verified_at": now_datetime()},
        )
        return {"success": True, "message": "OTP verified"}
