// Copyright (c) 2026, ledgerctrl
// License: MIT

frappe.query_reports["Delivery Expense Report"] = {
	filters: [
		{
			fieldname: "Date From",
			label: "date_from",
			fieldtype: "Date",
			options: null,
			description: "",
			reqd: 0,
			on_change: function() {
			},
		},
		{
			fieldname: "Date To",
			label: "date_to",
			fieldtype: "Date",
			options: null,
			description: "",
			reqd: 0,
			on_change: function() {
			},
		},
		{
			fieldname: "Type",
			label: "expense_type",
			fieldtype: "Select",
			options: "Fuel\nParking\nToll\nLoading\nMaintenance\nOther",
			description: "",
			reqd: 0,
			on_change: function() {
			},
		}
	]
};
