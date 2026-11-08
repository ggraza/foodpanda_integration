// Copyright (c) 2026, Ghulam Ghous and contributors
// For license information, please see license.txt

frappe.ui.form.on("Foodpanda Settings", {
	enable_live_api(frm) {
		if (frm.doc.enable_live_api) {
			frappe.confirm(
				__("Turn on the live Foodpanda API? Do this only after Foodpanda has approved your integration and you have entered the official credentials and endpoint paths."),
				null,
				() => frm.set_value("enable_live_api", 0)
			);
		}
	},
});
