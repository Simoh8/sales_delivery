// Copyright (c) 2026, ledgerctrl
// License: MIT

frappe.query_reports["Fleet Utilization Report"] = {
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
			fieldname: "Vehicle Type",
			label: "vehicle_type",
			fieldtype: "Select",
			options: "Motorcycle\nPickup\nVan\nTruck\nOther",
			description: "",
			reqd: 0,
			on_change: function() {
			},
		}
	]
};
