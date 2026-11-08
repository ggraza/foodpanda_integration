// Copyright (c) 2026, Ghulam Ghous and contributors
// For license information, please see license.txt

frappe.ui.form.on("Foodpanda Restaurant", {
	setup(frm) {
		// Only show records that belong to the selected company.
		const by_company = () => ({ filters: { company: frm.doc.company } });
		frm.set_query("warehouse", () => ({ filters: { company: frm.doc.company, is_group: 0 } }));
		frm.set_query("cost_center", () => ({ filters: { company: frm.doc.company, is_group: 0 } }));
		frm.set_query("pos_profile", by_company);
		frm.set_query("price_list", () => ({ filters: { selling: 1 } }));
	},
	company(frm) {
		frm.set_value("warehouse", null);
		frm.set_value("cost_center", null);
		frm.set_value("pos_profile", null);
	},
});
