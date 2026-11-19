import frappe
from frappe.model.document import Document
from datetime import datetime


class RefreshToken(Document):
    def before_save(self):
        """Validate and set timestamps before saving."""
        if self.is_revoked and not self.revoked_at:
            self.revoked_at = datetime.utcnow()

    def mark_as_used(self):
        """Update last_used_at timestamp."""
        self.last_used_at = datetime.utcnow()
        self.save()

    def revoke(self):
        """Revoke this refresh token."""
        self.is_revoked = 1
        self.revoked_at = datetime.utcnow()
        self.save()
