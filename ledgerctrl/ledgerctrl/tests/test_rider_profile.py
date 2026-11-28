import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate, add_days, now_datetime


class TestRiderProfile(FrappeTestCase):
    def setUp(self):
        self.company = frappe.db.get_single_value("Global Defaults", "default_company")
        if not self.company:
            self.company = frappe.db.get_value("Company", {})
        self.employee = self._make_employee()

    def _make_employee(self):
        import uuid

        name = "TEST-EMP-" + uuid.uuid4().hex[:6].upper()
        emp = frappe.get_doc(
            {
                "doctype": "Employee",
                "employee": name,
                "first_name": "Test",
                "last_name": "Rider",
                "company": self.company,
                "status": "Active",
                "date_of_joining": nowdate(),
                "gender": "Male",
                "date_of_birth": "1990-01-01",
            }
        )
        emp.insert(ignore_permissions=True)
        return emp.name

    def test_create_rider_profile(self):
        rp = frappe.get_doc(
            {
                "doctype": "Rider Profile",
                "rider_name": "Test Rider",
                "employee": self.employee,
            }
        )
        rp.insert(ignore_permissions=True)
        self.assertTrue(rp.name)
        self.assertEqual(rp.employment_status, "Active")

    def test_duplicate_employee_blocked(self):
        frappe.get_doc(
            {
                "doctype": "Rider Profile",
                "rider_name": "Rider One",
                "employee": self.employee,
            }
        ).insert(ignore_permissions=True)
        dup = frappe.get_doc(
            {
                "doctype": "Rider Profile",
                "rider_name": "Rider Two",
                "employee": self.employee,
            }
        )
        self.assertRaises(frappe.UniqueValidationError, dup.insert)

    def test_get_rider_for_user(self):
        from ledgerctrl.ledgerctrl.doctype.rider_profile.rider_profile import (
            RiderProfile,
        )

        self.assertIsNone(RiderProfile.get_rider_for_user("Administrator"))
