# FoodieExpress

A responsive Flask + SQLite food delivery mini-project with a menu, search and filters, favorites, recommendations, reviews, checkout, coupon validation, saved addresses, order history, simulated delivery tracking, and role-based dashboards for Admin, Chef, Delivery Partner, and Customer.

## Run locally

Requires Python 3.9 or newer.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`. The SQLite database is created and seeded automatically. A random session key is generated for local development; set a persistent `SECRET_KEY` before deploying or using real accounts. Demo coupons: `DIWALI20` gives 20% off dessert items; `WELCOME10` takes 10% off the food subtotal. Delivery is free for food subtotals of ₹499 or more; otherwise ₹39.

Admin, Chef, and Delivery Partner accounts are created on first startup from environment variables. Set credentials before running the app:

```powershell
$env:SECRET_KEY = "use-a-long-random-secret"
$env:ADMIN_EMAIL = "admin@example.com"
$env:ADMIN_PASSWORD = "set-a-strong-admin-password"
$env:CHEF_EMAIL = "chef@example.com"
$env:CHEF_PASSWORD = "set-a-strong-chef-password"
$env:DELIVERY_EMAIL = "partner@example.com"
$env:DELIVERY_PASSWORD = "set-a-strong-partner-password"
python app.py
```

Open `/login` to choose a role and sign in with its email and password. Customers can create accounts at `/signup`; Admins can add Chef and Delivery Partner accounts from the admin dashboard. On an existing database, startup adds the role-based tables and migrates legacy customers while retaining the original customer, food, and order records.

Admins manage accounts, food, categories, offers, and orders. Chefs process kitchen orders through Ready for Pickup; Delivery Partners only see orders assigned to them and update pickup/delivery progress. Customers can browse the existing storefront, place orders, and view their own order history and tracking. Dashboards are available at `/dashboard/admin`, `/dashboard/chef`, `/dashboard/delivery_partner`, and `/dashboard/customer`; each requires a matching authenticated role. Guest orders continue to use a private tracking token. The illustrated map and moving delivery marker are simulations, not GPS.

## Deploy to Render

1. Push this project to a GitHub repository and create a Render **Web Service** from it.
2. Use `pip install -r requirements.txt` for the build command and `gunicorn app:app` for the start command (also available in `Procfile`).
3. Configure `SECRET_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `CHEF_EMAIL`, `CHEF_PASSWORD`, `DELIVERY_EMAIL`, and `DELIVERY_PASSWORD` in the service environment. Set `COOKIE_SECURE=true` when deploying behind HTTPS; Render's `RENDER` environment variable enables this by default.
4. The service uses SQLite. Render's ephemeral filesystem does not preserve SQLite data across redeploys or restarts; use a persistent disk and set `DATABASE_PATH` to a file on that disk, or replace SQLite with a managed database for durable production data.
5. After deployment, open the HTTPS URL Render assigns to the service. This repository does not include hosting credentials, so a public deployment must be created from the account that owns the hosting service.

## Tests

```powershell
python -m unittest discover -s tests -v
```
