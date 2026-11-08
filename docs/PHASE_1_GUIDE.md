# Phase 1 Guide: Foundation (Mock mode)

This guide walks you through installing Phase 1 and checking that it works. You don't need any Foodpanda credentials. Everything runs in **Mock mode**, which is a fake Foodpanda that never sends data anywhere.

## What Phase 1 adds

| What | Where to find it in ERPNext | What it is for |
| --- | --- | --- |
| Foodpanda Settings | Search "Foodpanda Settings" | Main on/off switch, plus the separate switch for the live Foodpanda API (keep it OFF) |
| Foodpanda Account | Search "Foodpanda Account" | One login to Foodpanda: provider (Mock or Delivery Hero), credentials, endpoint paths, status mapping |
| Foodpanda Restaurant | Search "Foodpanda Restaurant" | One Foodpanda branch, linked to a Company, Warehouse, Price List and Customer |
| Foodpanda API Log | Search "Foodpanda API Log" | Every call to Foodpanda (or to the Mock), with passwords and customer details hidden |
| Roles | Foodpanda Manager, Foodpanda Operator, Foodpanda Viewer | Who can see and do what |

## Step 1: Install

Open a terminal on your server and go to your bench folder:

```bash
cd ~/frappe-bench
```

Download the app:

```bash
bench get-app https://github.com/ggraza/foodpanda_integration
```

Install it on your site (replace `your-site` with your site name, for example `erp.mycompany.com`):

```bash
bench --site your-site install-app foodpanda_integration
bench --site your-site migrate
```

If you run a production setup (with supervisor/nginx), restart:

```bash
bench restart
```

**Check:** run `bench --site your-site list-apps`. You should see `foodpanda_integration 0.1.0`.

## Step 2: Check the settings

1. Log in to ERPNext as Administrator.
2. Type **Foodpanda Settings** in the search bar at the top and open it.
3. Make sure **Enable Foodpanda Integration** is ticked.
4. Make sure **Enable Live Foodpanda API** is **not** ticked. If you try to tick it, ERPNext asks you to confirm. Click "No".

## Step 3: Create a Mock account

1. Search for **Foodpanda Account** and click **+ Add Foodpanda Account**.
2. Fill in:
   - **Account Name:** `Foodpanda Pakistan Test`
   - **Provider:** `Mock`
3. Click **Save** (or press Ctrl+S).
4. Open the **Status Mapping** section. You should see 10 rows, from *Received* to *Failed*. *Accepted* maps to `order_accepted` and *Rejected* maps to `order_rejected`.
5. Click **Test Connection** at the top. You should get a green message: "Mock connection successful. No data was sent to Foodpanda."
6. Scroll down to **Connection Status**. *Last Test Result* should say `Success`.

**Try an error:** tick **Mock: Simulate Failure**, save, and click **Test Connection** again. You should get a red "Connection Failed" message. Untick it afterwards and save.

## Step 4: Create restaurants

1. Search for **Foodpanda Restaurant** and click **+ Add Foodpanda Restaurant**.
2. Fill in:
   - **Restaurant Name:** `Lahore Gulberg`
   - **Foodpanda Account:** `Foodpanda Pakistan Test`
   - **Company:** your company
   - **POS Vendor ID (remoteId):** `PK-TEST-001` (any test value works in Mock mode)
   - **Warehouse**, **Price List**, **Customer**: optional for now
3. Save.

**Check the safety rules:**

- Create a second restaurant with the **same** POS Vendor ID on the same account. Saving should fail with "POS Vendor ID PK-TEST-001 is already used".
- If you have two companies, choose Company A and a Warehouse from Company B. Saving should fail with "Warehouse ... belongs to company ...". The Warehouse list only offers warehouses of the chosen company.

## Step 5: Look at the API log

1. Open your Foodpanda Account and click **API Logs**.
2. Open a row. The URL starts with `mock://`, which shows that nothing left your server.
3. Request and response bodies are shown with passwords and tokens replaced by `***`.

## Step 6: Check permissions (optional)

1. Create a test user and give them only the **Foodpanda Operator** role.
2. Log in as that user. They can open **Foodpanda Restaurant** but cannot edit it. They cannot open **Foodpanda Account**, because it holds credentials.

To limit a user to one company, open the user and add a **User Permission** with *Allow = Company* and the company name.

## Step 7: Run the automated tests (optional)

```bash
bench --site your-site set-config allow_tests true
bench --site your-site run-tests --app foodpanda_integration
```

You should see `Ran 26 tests ... OK`. Run tests on a test site, not on your live site.

## How the real Foodpanda adapter is kept separate

- `foodpanda_integration/providers/mock.py` is the fake Foodpanda used now.
- `foodpanda_integration/providers/delivery_hero.py` is the real adapter. It is only used when **both** of these are true:
  1. the account's Provider is `Delivery Hero`, and
  2. **Enable Live Foodpanda API** is ticked in Foodpanda Settings.
- Endpoint paths that Foodpanda does not publish (login, order status, catalog submit, availability updates) are empty on purpose. You will copy them from the official spec after approval. Until then the adapter refuses to send anything.

## Troubleshooting

| Problem | Fix |
| --- | --- |
| `App foodpanda_integration not in apps.txt` | Run `bench get-app` again from the bench folder, then install. |
| "Foodpanda Integration is disabled" | Tick *Enable Foodpanda Integration* in Foodpanda Settings. |
| "The live Foodpanda API is switched off" | Expected while you use Delivery Hero without approval. Switch the account to Mock. |
| "... is not set on Foodpanda Account" | A path marked "from official spec" is empty. Fill it in only after Foodpanda gives you the spec. |
| Doctypes not found after `git pull` | Run `bench --site your-site migrate`. |

## Files in Phase 1

```
foodpanda_integration/
├── hooks.py                 app settings, install hooks, daily log cleanup
├── install.py               creates roles and default settings
├── constants.py             statuses, default status map, public endpoint paths
├── exceptions.py            error types
├── tasks.py                 daily job: delete old API logs
├── client/
│   ├── http.py              HTTP client: timeouts, retries, token header, logging
│   ├── masking.py           hides secrets and customer data in logs
│   └── api_log.py           writes Foodpanda API Log rows
├── providers/
│   ├── __init__.py          get_provider(): picks Mock or Delivery Hero, enforces the live switch
│   ├── base.py              list of operations every provider offers
│   ├── mock.py              fake Foodpanda
│   └── delivery_hero.py     real Foodpanda adapter (off by default)
├── foodpanda_integration/doctype/
│   ├── foodpanda_settings/
│   ├── foodpanda_account/   includes the Test Connection button
│   ├── foodpanda_restaurant/
│   ├── foodpanda_status_map/
│   ├── foodpanda_reject_reason/
│   └── foodpanda_api_log/
└── tests/                   automated tests
```
