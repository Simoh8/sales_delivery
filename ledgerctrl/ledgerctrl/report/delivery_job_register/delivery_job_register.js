// Copyright (c) 2026, ledgerctrl
// License: MIT

frappe.query_reports["Delivery Job Register"] = {
	filters: [
		{
			fieldname: "Status",
			label: "status",
			fieldtype: "Select",
			options: "Pending\nDispatched\nAccepted\nEn Route\nArrived\nIn Progress\nCompleted\nFailed\nCancelled",
			description: "",
			reqd: 0,
			on_change: function() {
			},
		},
		{
			fieldname: "Rider",
			label: "rider",
			fieldtype: "Link",
			options: "Rider Profile",
			description: "",
			reqd: 0,
			on_change: function() {
			},
		},
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
		}
	]
};
