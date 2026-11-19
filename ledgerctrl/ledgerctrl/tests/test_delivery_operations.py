import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate


class TestDeliveryOperations(FrappeTestCase):
    def setUp(self):
        self.company = frappe.db.get_single_value("Global Defaults", "default_company") or frappe.db.get_value("Company", {})
        import uuid

        self.customer = frappe.get_doc(
            {
                "doctype": "Customer",
                "customer_name": "Test Customer " + uuid.uuid4().hex[:6],
                "customer_type": "Company",
            }
        ).insert(ignore_permissions=True)

    def _make_job(self, **kw):
        data = {
            "customer": self.customer.name,
            "scheduled_date": nowdate(),
            "status": "Pending",
        }
        data.update(kw)
        return frappe.get_doc({"doctype": "Delivery Job", **data}).insert(
            ignore_permissions=True
        )

    def test_attempt_numbering(self):
        job = self._make_job()
        a1 = frappe.get_doc(
            {
                "doctype": "Delivery Attempt",
                "delivery_job": job.name,
                "attempt_status": "Customer Unavailable",
                "attempt_date": nowdate(),
            }
        ).insert(ignore_permissions=True)
        a2 = frappe.get_doc(
            {
                "doctype": "Delivery Attempt",
                "delivery_job": job.name,
                "attempt_status": "Successful",
                "attempt_date": nowdate(),
            }
        ).insert(ignore_permissions=True)
        self.assertEqual(a1.attempt_number, 1)
        self.assertEqual(a2.attempt_number, 2)
        job.reload()
        self.assertEqual(job.number_of_attempts, 2)
        self.assertEqual(str(job.first_attempt_date), str(nowdate()))

    def test_fuel_log_total_and_idempotency(self):
        import uuid

        vehicle = frappe.get_doc(
            {
                "doctype": "Vehicle",
                "license_plate": "TST" + uuid.uuid4().hex[:6].upper(),
                "make": "Test",
                "model": "Bike",
            }
        ).insert(ignore_permissions=True)
        fl = frappe.get_doc(
            {
                "doctype": "Fuel Log",
                "vehicle": vehicle.name,
                "fuel_date": nowdate(),
                "quantity": 10,
                "unit_price": 150,
                "idempotency_key": "test-key-1",
            }
        ).insert(ignore_permissions=True)
        self.assertEqual(fl.total_cost, 1500)
        dup = frappe.get_doc(
            {
                "doctype": "Fuel Log",
                "vehicle": vehicle.name,
                "fuel_date": nowdate(),
                "quantity": 5,
                "unit_price": 150,
                "idempotency_key": "test-key-1",
            }
        )
        # unique constraint on idempotency_key triggers DuplicateEntryError
        self.assertRaises(frappe.DuplicateEntryError, dup.insert)

    def test_batch_stats(self):
        job = self._make_job()
        batch = frappe.get_doc(
            {
                "doctype": "Delivery Batch",
                "batch_date": nowdate(),
                "company": self.company,
                "jobs": [{"delivery_job": job.name}],
            }
        ).insert(ignore_permissions=True)
        batch.reload()
        self.assertEqual(batch.total_jobs, 1)
        self.assertEqual(batch.pending_jobs, 1)

    def test_delivery_revenue_calc(self):
        job = self._make_job(
            customer_delivery_charge=1000, actual_delivery_cost=200
        )
        self.assertEqual(job.delivery_revenue, 800)
