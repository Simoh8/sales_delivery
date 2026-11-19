// Copyright (c) 2026, ledgerctrl
// License: MIT

frappe.query_reports["Fuel Consumption Report"] = {
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
			fieldname: "Vehicle",
			label: "vehicle",
			fieldtype: "Link",
			options: "Vehicle",
			description: "",
			reqd: 0,
			on_change: function() {
			},
		}
	]
};
