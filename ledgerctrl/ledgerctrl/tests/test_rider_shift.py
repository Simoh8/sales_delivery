import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate


class TestRiderShift(FrappeTestCase):
    def setUp(self):
        self.company = frappe.db.get_single_value("Global Defaults", "default_company") or frappe.db.get_value("Company", {})
        import uuid

        self.emp = frappe.get_doc(
            {
                "doctype": "Employee",
                "employee": "TST-" + uuid.uuid4().hex[:6].upper(),
                "first_name": "Shift",
                "last_name": "Rider",
                "company": self.company,
                "status": "Active",
                "date_of_joining": nowdate(),
                "gender": "Male",
                "date_of_birth": "1990-01-01",
            }
        ).insert(ignore_permissions=True)
        self.rider = frappe.get_doc(
            {
                "doctype": "Rider Profile",
                "rider_name": "Shift Rider",
                "employee": self.emp.name,
            }
        ).insert(ignore_permissions=True)

    def test_overlapping_shifts_blocked(self):
        frappe.get_doc(
            {
                "doctype": "Rider Shift",
                "rider": self.rider.name,
                "shift_date": nowdate(),
                "shift_status": "Scheduled",
            }
        ).insert(ignore_permissions=True)
        dup = frappe.get_doc(
            {
                "doctype": "Rider Shift",
                "rider": self.rider.name,
                "shift_date": nowdate(),
                "shift_status": "Active",
            }
        )
        self.assertRaises(frappe.ValidationError, dup.insert)

    def test_odometer_distance(self):
        shift = frappe.get_doc(
            {
                "doctype": "Rider Shift",
                "rider": self.rider.name,
                "shift_date": add_day(nowdate(), -1),
                "opening_odometer": 1000,
                "closing_odometer": 1050,
                "shift_status": "Completed",
            }
        ).insert(ignore_permissions=True)
        self.assertEqual(shift.total_distance_travelled, 50)


def add_day(d, n):
    from frappe.utils import add_days
    return add_days(d, n)
