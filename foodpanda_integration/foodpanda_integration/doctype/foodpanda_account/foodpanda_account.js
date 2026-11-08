// Copyright (c) 2026, Ghulam Ghous and contributors
// For license information, please see license.txt

frappe.ui.form.on("Foodpanda Account", {
	refresh(frm) {
		if (frm.doc.provider === "Mock") {
			frm.dashboard.set_headline_alert(
				__("Mock mode: this account never contacts Foodpanda. Safe for testing."),
				"blue"
			);
		} else {
			frm.dashboard.set_headline_alert(
				__("Live Foodpanda API. It works only when 'Enable Live Foodpanda API' is ticked in Foodpanda Settings."),
				"orange"
			);
		}

		if (!frm.is_new()) {
			frm.add_custom_button(__("Test Connection"), () => {
				frm.call({
					doc: frm.doc,
					method: "test_connection",
					freeze: true,
					freeze_message: __("Testing connection..."),
				}).then((r) => {
					const result = r.message || {};
					frappe.msgprint({
						title: result.ok ? __("Connection OK") : __("Connection Failed"),
						message: frappe.utils.escape_html(result.message || ""),
						indicator: result.ok ? "green" : "red",
					});
					frm.reload_doc();
				});
			});

			frm.add_custom_button(__("API Logs"), () => {
				frappe.set_route("List", "Foodpanda API Log", { account: frm.doc.name });
			});
		}
	},
});
