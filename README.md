# Foodpanda Integration for ERPNext

`foodpanda_integration` is a Frappe app that connects Foodpanda restaurant (merchant) accounts to ERPNext.

- Works with **Frappe / ERPNext v14, v15 and v16**.
- Supports **many restaurants and many companies**.
- Includes a **Mock mode**, a fake Foodpanda, so you can build and test everything before Foodpanda approves your API access.
- The **real Foodpanda adapter** (Delivery Hero POS Integration Middleware) is kept separate and **switched off** until you turn it on after approval.
- **POSAwesome** support is optional. The app also works when POSAwesome is not installed.
- No ERPNext or POSAwesome core files are changed.

> **Status:** Phase 1 (Foundation) is done. See the [roadmap](#roadmap).

## Install

Run these commands from your bench folder (usually `~/frappe-bench`):

```bash
# 1. Download the app
bench get-app https://github.com/ggraza/foodpanda_integration

# 2. Install it on your site (ERPNext must already be installed)
bench --site your-site install-app foodpanda_integration

# 3. Apply database changes and rebuild assets
bench --site your-site migrate
bench build --app foodpanda_integration

# 4. Restart (production setups only)
bench restart
```

## Update

```bash
cd ~/frappe-bench/apps/foodpanda_integration
git pull
cd ~/frappe-bench
bench --site your-site migrate
bench build --app foodpanda_integration
bench restart
```

## First steps after install

1. Search for **Foodpanda Settings** in the awesome bar. Check that *Enable Foodpanda Integration* is ticked. Leave *Enable Live Foodpanda API* **off**.
2. Create a **Foodpanda Account** with *Provider = Mock*. Save it, then click **Test Connection**. You should see "Mock connection successful".
3. Create a **Foodpanda Restaurant** for each branch. Choose the Account and Company, and enter any test POS Vendor ID (for example `PK-TEST-001`).
4. Open **Foodpanda API Log** to see every call. Passwords, tokens and customer details are masked.

For a step-by-step test checklist, see [docs/PHASE_1_GUIDE.md](docs/PHASE_1_GUIDE.md).

## Roles

| Role | Can do |
| --- | --- |
| Foodpanda Manager | Everything: settings, accounts and credentials, restaurants, logs |
| Foodpanda Operator | See restaurants. Later phases add order handling. |
| Foodpanda Viewer | Read-only access to restaurants. Later phases add orders and reports. |

To limit a user to one company, add a standard ERPNext **User Permission** for that Company.

## Going live with Foodpanda

The real API needs approval from Foodpanda (Delivery Hero). See <https://integration.foodpanda.com/en/documentation/>.
When you have credentials:

1. Enter the base URL, chain code, username and password on a Foodpanda Account with *Provider = Delivery Hero*.
2. Copy the endpoint paths marked "from official spec" from the API specification Foodpanda gives you.
3. Tick **Enable Live Foodpanda API** in Foodpanda Settings, then click **Test Connection**.

## Run the tests

```bash
bench --site your-site set-config allow_tests true
bench --site your-site run-tests --app foodpanda_integration
```

## Roadmap

1. Foundation: settings, accounts, restaurants, API client, Mock provider (**done**)
2. Receiving orders (webhook endpoints, duplicate protection)
3. Order actions and status sync
4. Orders screen in Desk and POSAwesome
5. Menu and price sync
6. Stock and store availability
7. Accounting: Sales Invoices and reconciliation
8. Dashboard and reports
9. Go-live with the official Foodpanda API

## License

MIT
