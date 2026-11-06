import hmac
import os
import secrets
import sqlite3
from functools import wraps
from pathlib import Path

from flask import Flask, abort, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = Path(__file__).resolve().parent
DATABASE = Path(os.environ.get("DATABASE_PATH", BASE_DIR / "foodieexpress.db"))
app = Flask(__name__)
configured_secret = os.environ.get("SECRET_KEY")
if (
    (os.environ.get("RENDER") or os.environ.get("FLASK_ENV") == "production")
    and not configured_secret
):
    raise RuntimeError("Set SECRET_KEY in the deployment environment before starting the app.")
app.secret_key = configured_secret or secrets.token_urlsafe(32)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get(
        "COOKIE_SECURE", "true" if os.environ.get("RENDER") else "false"
    ).lower() == "true",
)

FOODS = [
    ("Chicken Biryani", "Slow-cooked basmati, tender chicken & fragrant spices.", 249, "Non-Vegetarian", 4.9, "🍗", "https://images.unsplash.com/photo-1563379091339-03246963d96c?auto=format&fit=crop&w=800&q=85"),
    ("Paneer Butter Masala", "Creamy tomato gravy, fresh paneer & warm naan.", 219, "Vegetarian", 4.8, "🧀", "https://images.unsplash.com/photo-1631452180519-c014fe946bc7?auto=format&fit=crop&w=800&q=85"),
    ("Masala Dosa", "Crisp golden dosa with spiced potato and coconut chutney.", 149, "Breakfast", 4.7, "🥞", "https://images.unsplash.com/photo-1668236543090-82eba5ee5976?auto=format&fit=crop&w=800&q=85"),
    ("Gobi Manchurian", "Crispy cauliflower tossed in our signature Indo-Chinese sauce.", 169, "Snacks", 4.6, "🥦", "https://images.unsplash.com/photo-1603894584373-5ac82b2ae398?auto=format&fit=crop&w=800&q=85"),
    ("Margherita Pizza", "Stone-baked crust, basil, mozzarella & rich tomato.", 299, "Snacks", 4.8, "🍕", "https://images.unsplash.com/photo-1579751626657-72bc17010498?auto=format&fit=crop&w=800&q=85"),
    ("Gulab Jamun", "Soft, syrup-soaked khoya dumplings with a hint of cardamom.", 99, "Desserts", 4.9, "🍮", "https://images.unsplash.com/photo-1666190092159-12f89ad3c15f?auto=format&fit=crop&w=800&q=85"),
    ("Filter Coffee", "Freshly brewed South Indian coffee with frothy milk.", 69, "Beverages", 4.8, "☕", "https://images.unsplash.com/photo-1509042239860-f550ce710b93?auto=format&fit=crop&w=800&q=85"),
    ("Chicken 65", "Fiery, crispy chicken bites with curry leaves and lime.", 189, "Non-Vegetarian", 4.7, "🍗", "https://images.unsplash.com/photo-1603894584373-5ac82b2ae398?auto=format&fit=crop&w=800&q=85"),
    ("Veg Fried Rice", "Wok-tossed rice, garden vegetables & a little magic.", 179, "Lunch", 4.5, "🍚", "https://images.unsplash.com/photo-1603133872878-684f208fb84b?auto=format&fit=crop&w=800&q=85"),
    ("Chocolate Brownie", "Warm, fudgy chocolate brownie. Made for sharing (or not).", 129, "Desserts", 4.8, "🍫", "https://images.unsplash.com/photo-1606313564200-e75d5e30476c?auto=format&fit=crop&w=800&q=85"),
    ("Fresh Lime Soda", "Fresh lime, a sparkle of soda, your choice of sweet or salty.", 79, "Beverages", 4.5, "🍋", "https://images.unsplash.com/photo-1513558161293-cdab765edfd7?auto=format&fit=crop&w=800&q=85"),
    ("Grilled Chicken Bowl", "Juicy grilled chicken, greens and herby rice.", 229, "Dinner", 4.6, "🥗", "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=800&q=85"),
    ("Garlic Bread", "Warm, buttery bread with roasted garlic and herbs.", 89, "Snacks", 4.6, "🥖", "https://images.unsplash.com/photo-1619531040576-f9416740661c?auto=format&fit=crop&w=800&q=85"),
    ("Cold Coffee", "Chilled, creamy coffee blended for a little pick-me-up.", 99, "Beverages", 4.7, "🥤", "https://images.unsplash.com/photo-1461023058943-07fcbe16d735?auto=format&fit=crop&w=800&q=85"),
    ("Diwali Sweet Box", "A gift-ready box of festive Indian sweets, made for sharing.", 349, "Desserts", 4.9, "🎁", "https://images.unsplash.com/photo-1605197161470-5d4b8c2c0f49?auto=format&fit=crop&w=800&q=85"),
    ("Diwali Sweet Box Duo", "Two gift-ready sweet boxes for ₹99 less than buying them separately.", 599, "Desserts", 5.0, "🎁", "https://images.unsplash.com/photo-1605197161470-5d4b8c2c0f49?auto=format&fit=crop&w=800&q=85"),
]

COMBOS = [
    {"name": "The Biryani Feast", "description": "Chicken Biryani + Chicken 65 + Gulab Jamun", "items": [1, 8, 6], "price": 537, "image": "https://images.unsplash.com/photo-1563379091339-03246963d96c?auto=format&fit=crop&w=1000&q=85", "tag": "BESTSELLER"},
    {"name": "Veggie Wok Night", "description": "Veg Fried Rice + Gobi Manchurian", "items": [9, 4], "price": 348, "image": "https://images.unsplash.com/photo-1603133872878-684f208fb84b?auto=format&fit=crop&w=1000&q=85", "tag": "VEG FAVORITE"},
    {"name": "South Indian Start", "description": "Masala Dosa + Filter Coffee", "items": [3, 7], "price": 218, "image": "https://images.unsplash.com/photo-1668236543090-82eba5ee5976?auto=format&fit=crop&w=1000&q=85", "tag": "MORNING PICK"},
    {"name": "Pizza & Chill", "description": "Margherita Pizza + Garlic Bread + Cold Coffee", "items": [5, 13, 14], "price": 487, "image": "https://images.unsplash.com/photo-1579751626657-72bc17010498?auto=format&fit=crop&w=1000&q=85", "tag": "MOVIE NIGHT"},
    {"name": "Diwali Family Feast", "description": "Biryani + Chicken 65 + Veg Fried Rice + Gulab Jamun + Brownie", "items": [1, 8, 9, 6, 10], "price": 845, "image": "https://images.unsplash.com/photo-1563379091339-03246963d96c?auto=format&fit=crop&w=1000&q=85", "tag": "FESTIVE FEAST"},
]

ROLES = {"admin", "chef", "delivery_partner", "customer"}


def get_db():
    if "db" not in g:
        DATABASE.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS foods (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL,
            price INTEGER NOT NULL, category TEXT NOT NULL, rating REAL NOT NULL,
            emoji TEXT NOT NULL, image TEXT NOT NULL, available INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER REFERENCES customers(id),
            customer_name TEXT NOT NULL, address TEXT NOT NULL, subtotal INTEGER NOT NULL,
            discount INTEGER NOT NULL DEFAULT 0, delivery_fee INTEGER NOT NULL DEFAULT 0,
            total INTEGER NOT NULL, tracking_token TEXT UNIQUE,
            coupon TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'Preparing',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            food_id INTEGER NOT NULL REFERENCES foods(id), name TEXT NOT NULL,
            quantity INTEGER NOT NULL, unit_price INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY, customer_id INTEGER REFERENCES customers(id),
            customer_name TEXT NOT NULL, food_name TEXT NOT NULL, rating INTEGER NOT NULL,
            feedback TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS customer_addresses (
            id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
            label TEXT NOT NULL, address TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('admin', 'chef', 'delivery_partner', 'customer')),
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS food_items (
            id INTEGER PRIMARY KEY, legacy_food_id INTEGER UNIQUE REFERENCES foods(id),
            category_id INTEGER NOT NULL REFERENCES categories(id),
            name TEXT NOT NULL, description TEXT NOT NULL, price INTEGER NOT NULL,
            rating REAL NOT NULL, emoji TEXT NOT NULL, image TEXT NOT NULL,
            available INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS offers (
            id INTEGER PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
            code TEXT NOT NULL UNIQUE, discount_percent INTEGER NOT NULL DEFAULT 0,
            category TEXT REFERENCES categories(name), minimum_subtotal INTEGER NOT NULL DEFAULT 0,
            free_delivery INTEGER NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1,
            starts_at TEXT, ends_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS delivery_assignments (
            id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL UNIQUE REFERENCES orders(id) ON DELETE CASCADE,
            partner_user_id INTEGER NOT NULL REFERENCES users(id),
            status TEXT NOT NULL DEFAULT 'Ready for Pickup',
            simulated_lat REAL NOT NULL DEFAULT 12.9716,
            simulated_lon REAL NOT NULL DEFAULT 77.5946,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    order_columns = {row["name"] for row in db.execute("PRAGMA table_info(orders)")}
    if "delivery_fee" not in order_columns:
        db.execute("ALTER TABLE orders ADD COLUMN delivery_fee INTEGER NOT NULL DEFAULT 0")
    if "tracking_token" not in order_columns:
        db.execute("ALTER TABLE orders ADD COLUMN tracking_token TEXT")
    if "chef_user_id" not in order_columns:
        db.execute("ALTER TABLE orders ADD COLUMN chef_user_id INTEGER REFERENCES users(id)")
    if "chef_status" not in order_columns:
        db.execute("ALTER TABLE orders ADD COLUMN chef_status TEXT NOT NULL DEFAULT 'Pending'")
    existing_foods = {
        row["name"] for row in db.execute("SELECT name FROM foods").fetchall()
    }
    db.executemany(
        """INSERT INTO foods (name, description, price, category, rating, emoji, image)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [food for food in FOODS if food[0] not in existing_foods],
    )
    db.execute("UPDATE foods SET category = 'Non-Vegetarian' WHERE name = 'Chicken Biryani' AND category = 'Biryani'")
    for row in db.execute("SELECT DISTINCT category FROM foods ORDER BY category").fetchall():
        db.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (row["category"],))
    for row in db.execute("SELECT * FROM foods ORDER BY id").fetchall():
        category_id = db.execute(
            "SELECT id FROM categories WHERE name = ?", (row["category"],)
        ).fetchone()["id"]
        db.execute(
            """INSERT INTO food_items
               (id, legacy_food_id, category_id, name, description, price, rating, emoji, image, available)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET legacy_food_id=excluded.legacy_food_id,
                 category_id=excluded.category_id, name=excluded.name,
                 description=excluded.description, price=excluded.price,
                 rating=excluded.rating, emoji=excluded.emoji,
                 image=excluded.image, available=excluded.available""",
            (row["id"], row["id"], category_id, row["name"], row["description"],
             row["price"], row["rating"], row["emoji"], row["image"], row["available"]),
        )
    for row in db.execute("SELECT * FROM customers ORDER BY id").fetchall():
        db.execute(
            """INSERT OR IGNORE INTO users (id, name, email, password_hash, role)
               VALUES (?, ?, ?, ?, 'customer')""",
            (row["id"], row["name"], row["email"], row["password_hash"]),
        )
    ensure_staff_account(
        db, os.environ.get("ADMIN_NAME", "FoodieExpress Admin"),
        os.environ.get("ADMIN_EMAIL", ""), os.environ.get("ADMIN_PASSWORD", ""), "admin",
    )
    ensure_staff_account(
        db, os.environ.get("CHEF_NAME", "FoodieExpress Chef"),
        os.environ.get("CHEF_EMAIL", ""), os.environ.get("CHEF_PASSWORD", ""), "chef",
    )
    ensure_staff_account(
        db, os.environ.get("DELIVERY_NAME", "Delivery Partner"),
        os.environ.get("DELIVERY_EMAIL", ""), os.environ.get("DELIVERY_PASSWORD", ""),
        "delivery_partner",
    )
    db.executemany(
        """INSERT OR IGNORE INTO offers
           (title, description, code, discount_percent, category, minimum_subtotal, free_delivery)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [
            ("Diwali sweets", "20% off selected sweets", "DIWALI20", 20, "Desserts", 0, 0),
            ("Welcome treat", "10% off your food subtotal", "WELCOME10", 10, None, 0, 0),
        ],
    )
    if db.execute("SELECT COUNT(*) FROM reviews").fetchone()[0] == 0:
        db.executemany(
            """INSERT INTO reviews (customer_name, food_name, rating, feedback)
               VALUES (?, ?, ?, ?)""",
            [
                ("Ananya R.", "Chicken Biryani", 5, "The biryani arrived piping hot and tasted like a Sunday at home. Already ordering again!"),
                ("Rahul M.", "Masala Dosa", 5, "Perfectly crisp, generous chutney, and the filter coffee is a must."),
                ("Sara K.", "Paneer Butter Masala", 4, "Really comforting food and the portions are great. Delivery was right on time."),
            ],
        )
    db.commit()


def ensure_staff_account(db, name, email, password, role):
    email = email.strip().lower()
    if not email and not password:
        return
    if not email or not password:
        raise RuntimeError(f"Configure both {role} email and password.")
    existing = db.execute("SELECT id, role FROM users WHERE email = ?", (email,)).fetchone()
    if existing and existing["role"] != role:
        raise RuntimeError(f"The configured {role} email belongs to a different account role.")
    db.execute(
        """INSERT INTO users (name, email, password_hash, role)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(email) DO UPDATE SET name=excluded.name,
             password_hash=excluded.password_hash, active=1""",
        (name.strip() or role.replace("_", " ").title(), email,
         generate_password_hash(password), role),
    )


def current_customer():
    user = current_user()
    if user is None or user["role"] != "customer":
        return None
    return get_db().execute(
        "SELECT id, name, email FROM customers WHERE id = ?", (user["id"],)
    ).fetchone()


def current_user():
    user_id = session.get("user_id")
    if user_id is None:
        return None
    user = get_db().execute(
        "SELECT id, name, email, role, active FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    if user is None or not user["active"] or session.get("role") != user["role"]:
        session.clear()
        return None
    return user


def role_required(*allowed_roles):
    def decorate(handler):
        @wraps(handler)
        def wrapped(*args, **kwargs):
            user = current_user()
            if user is None:
                return jsonify(error="Please sign in to continue."), 401
            if user["role"] not in allowed_roles:
                return jsonify(error="Your account does not have permission to access this resource."), 403
            return handler(*args, **kwargs)
        return wrapped
    return decorate


def login_required(handler):
    return role_required("customer")(handler)


def partner_required(handler):
    return role_required("delivery_partner")(handler)


@app.route("/")
def home():
    return render_template("index.html")


@app.get("/login")
def login_page():
    return render_template("login.html", selected_role=request.args.get("role", "customer"))


@app.get("/signup")
def signup_page():
    return render_template("signup.html")


@app.get("/logout")
def logout_page():
    session.clear()
    return redirect(url_for("home"))


@app.get("/dashboard/<role>")
def role_dashboard(role):
    if role not in ROLES:
        abort(404)
    user = current_user()
    if user is None:
        return redirect(url_for("login_page", role=role))
    if user["role"] != role:
        abort(403)
    return render_template("dashboard.html", user=dict(user), role=role)


@app.get("/privacy")
def privacy_policy():
    return render_template(
        "legal.html",
        title="Privacy Policy",
        sections=[
            ("Information you provide", "This demo stores account names, email addresses, password hashes, delivery addresses, order details and reviews in its SQLite database."),
            ("How information is used", "Information is used to sign in, fulfill orders, show order history and delivery status, manage saved addresses, and display reviews."),
            ("Security and demo limits", "Passwords are hashed and staff dashboards require configured credentials. This college-project demo is not a production payment service; do not enter payment card details or sensitive personal information."),
            ("Retention and contact", "Data remains in the configured SQLite database until it is removed by the site operator. Contact the operator using the email address shown on the storefront for data requests."),
        ],
    )


@app.get("/terms")
def terms_and_conditions():
    return render_template(
        "legal.html",
        title="Terms and Conditions",
        sections=[
            ("Demo service", "FoodieExpress is a college mini-project demonstrating online food ordering. Menu availability, prices and estimated delivery times are illustrative."),
            ("Orders and offers", "Orders are recorded in the demo database and do not trigger a real-world delivery or payment. Coupon eligibility and delivery fees are calculated by the application."),
            ("Delivery tracking", "The map and moving delivery marker are simulated. No live location or GPS data is collected."),
            ("Using the site", "Do not use the demo to submit payment details, sensitive personal information, or orders that require real fulfillment. The site operator may update demo menu content and availability."),
        ],
    )


@app.get("/api/menu")
def menu():
    db = get_db()
    clauses = ["1 = 1"]
    params = []
    category = request.args.get("category", "").strip()
    query = request.args.get("q", "").strip()
    max_price = request.args.get("max_price", "").strip()
    if len(query) > 120:
        return jsonify(error="Search text must be 120 characters or fewer."), 400
    if category and category != "All":
        clauses.append("category = ?")
        params.append(category)
    if query:
        clauses.append("(name LIKE ? OR description LIKE ?)")
        params.extend([f"%{query}%", f"%{query}%"])
    if max_price:
        try:
            clauses.append("price <= ?")
            params.append(max(0, int(max_price)))
        except ValueError:
            return jsonify(error="Price filter must be a number."), 400
    rows = db.execute(
        "SELECT * FROM foods WHERE " + " AND ".join(clauses) + " ORDER BY id",
        params,
    ).fetchall()
    return jsonify([dict(row) for row in rows])


@app.get("/api/categories")
def list_categories():
    rows = get_db().execute("SELECT id, name FROM categories ORDER BY name").fetchall()
    return jsonify([dict(row) for row in rows])


@app.get("/api/recommendations")
def recommendations():
    db = get_db()
    result = []
    for combo in COMBOS:
        placeholders = ",".join("?" for _ in combo["items"])
        rows = db.execute(
            f"SELECT price FROM foods WHERE available = 1 AND id IN ({placeholders})",
            combo["items"],
        ).fetchall()
        if len(rows) == len(combo["items"]):
            result.append({**combo, "price": sum(row["price"] for row in rows)})
    return jsonify(result)


@app.get("/api/offers")
def list_offers():
    rows = get_db().execute(
        """SELECT id, title, description, code, discount_percent, category,
                  minimum_subtotal, free_delivery
           FROM offers WHERE active = 1 ORDER BY id"""
    ).fetchall()
    return jsonify([dict(row) for row in rows])


@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    if len(name) < 2 or len(name) > 100 or "@" not in email or len(email) > 254 or not 8 <= len(password) <= 256:
        return jsonify(error="Enter your name, a valid email and a password of 8–256 characters."), 400
    db = get_db()
    try:
        db.execute("BEGIN")
        password_hash = generate_password_hash(password)
        cursor = db.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, 'customer')",
            (name, email, password_hash),
        )
        user_id = cursor.lastrowid
        db.execute(
            "INSERT INTO customers (id, name, email, password_hash) VALUES (?, ?, ?, ?)",
            (user_id, name, email, password_hash),
        )
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        return jsonify(error="An account with that email already exists."), 409
    session.clear()
    session["user_id"] = user_id
    session["role"] = "customer"
    return jsonify(
        customer={"id": user_id, "name": name, "email": email, "role": "customer"},
        redirect=url_for("role_dashboard", role="customer"),
    ), 201


@app.post("/api/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    requested_role = str(data.get("role", "customer")).strip()
    if requested_role not in ROLES or not email or not password:
        return jsonify(error="Choose a valid role and enter your email and password."), 400
    user = get_db().execute(
        "SELECT id, name, email, password_hash, role, active FROM users WHERE email = ?", (email,)
    ).fetchone()
    if (
        user is None or not user["active"] or user["role"] != requested_role
        or not check_password_hash(user["password_hash"], password)
    ):
        return jsonify(error="Email, password or selected role is incorrect."), 401
    session.clear()
    session["user_id"] = user["id"]
    session["role"] = user["role"]
    return jsonify(
        customer={"id": user["id"], "name": user["name"], "email": user["email"], "role": user["role"]},
        redirect=url_for("role_dashboard", role=user["role"]),
    )


@app.post("/api/auth/logout")
def logout():
    session.clear()
    return jsonify(ok=True)


@app.get("/api/auth/me")
def me():
    user = current_user()
    return jsonify(customer={
        "id": user["id"], "name": user["name"], "email": user["email"], "role": user["role"]
    } if user else None)


@app.get("/api/reviews")
def reviews():
    rows = get_db().execute(
        "SELECT customer_name AS name, food_name AS food, rating, feedback, created_at "
        "FROM reviews ORDER BY id DESC LIMIT 12"
    ).fetchall()
    return jsonify([dict(row) for row in rows])


@app.post("/api/reviews")
@login_required
def submit_review():
    data = request.get_json(silent=True) or {}
    food_name = str(data.get("food", "")).strip()
    feedback = str(data.get("feedback", "")).strip()
    try:
        rating = int(data.get("rating", 0))
    except (TypeError, ValueError):
        rating = 0
    customer = current_customer()
    if not food_name or len(food_name) > 100 or not 1 <= rating <= 5 or not 8 <= len(feedback) <= 500:
        return jsonify(error="Choose a food, a 1–5 star rating and write 8–500 characters of feedback."), 400
    has_delivered_item = get_db().execute(
        """SELECT 1 FROM orders o
           JOIN order_items oi ON oi.order_id = o.id
           WHERE o.customer_id = ? AND o.status = 'Delivered'
             AND LOWER(oi.name) = LOWER(?) LIMIT 1""",
        (customer["id"], food_name),
    ).fetchone()
    if has_delivered_item is None:
        return jsonify(error="You can review a dish after it has been delivered in one of your orders."), 400
    get_db().execute(
        "INSERT INTO reviews (customer_id, customer_name, food_name, rating, feedback) VALUES (?, ?, ?, ?, ?)",
        (customer["id"], customer["name"], food_name, rating, feedback),
    )
    get_db().commit()
    return jsonify(ok=True), 201


def calculate_order(items, coupon):
    db = get_db()
    if not isinstance(items, list) or not items or len(items) > 40:
        raise ValueError("Your cart is empty or contains too many items.")
    normalized = {}
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Invalid cart item.")
        try:
            food_id, quantity = int(item.get("id")), int(item.get("quantity"))
        except (TypeError, ValueError):
            raise ValueError("Invalid item quantity.")
        if quantity < 1 or quantity > 20:
            raise ValueError("Each item quantity must be between 1 and 20.")
        normalized[food_id] = normalized.get(food_id, 0) + quantity
        if normalized[food_id] > 20:
            raise ValueError("The total quantity of each item cannot exceed 20.")
    foods = {}
    for food_id in normalized:
        row = db.execute(
            "SELECT id, name, price, category FROM foods WHERE id = ? AND available = 1", (food_id,)
        ).fetchone()
        if row is None:
            raise ValueError("One of the items is no longer available.")
        foods[food_id] = row
    subtotal = sum(foods[key]["price"] * quantity for key, quantity in normalized.items())
    code = str(coupon or "").strip().upper()
    discount = 0
    free_delivery = False
    if code:
        offer = db.execute(
            """SELECT * FROM offers WHERE UPPER(code) = ? AND active = 1
               AND (starts_at IS NULL OR starts_at <= CURRENT_TIMESTAMP)
               AND (ends_at IS NULL OR ends_at >= CURRENT_TIMESTAMP)""",
            (code,),
        ).fetchone()
        if offer is None:
            raise ValueError("That coupon code isn't valid or is no longer active.")
        if subtotal < offer["minimum_subtotal"]:
            raise ValueError(f"Add {offer['minimum_subtotal'] - subtotal} more to use this coupon.")
        eligible_subtotal = sum(
            foods[key]["price"] * quantity
            for key, quantity in normalized.items()
            if offer["category"] is None or foods[key]["category"] == offer["category"]
        )
        if offer["category"] and not eligible_subtotal and offer["discount_percent"]:
            raise ValueError(f"{code} applies to {offer['category'].lower()} items.")
        discount = round(eligible_subtotal * offer["discount_percent"] / 100)
        free_delivery = bool(offer["free_delivery"])
    delivery_fee = 0 if subtotal >= 499 or free_delivery else 39
    return normalized, foods, subtotal, discount, delivery_fee, code


@app.post("/api/coupons/apply")
def apply_coupon():
    data = request.get_json(silent=True) or {}
    try:
        _, _, subtotal, discount, delivery_fee, code = calculate_order(data.get("items"), data.get("code"))
    except ValueError as error:
        return jsonify(error=str(error)), 400
    if not code:
        return jsonify(error="Enter a coupon code to apply."), 400
    return jsonify(code=code, subtotal=subtotal, discount=discount, delivery_fee=delivery_fee, total=subtotal - discount + delivery_fee)


@app.post("/api/orders")
def place_order():
    data = request.get_json(silent=True) or {}
    address = str(data.get("address", "")).strip()
    customer_name = str(data.get("name", "")).strip()
    if not 10 <= len(address) <= 500:
        return jsonify(error="Please enter a complete delivery address of up to 500 characters."), 400
    try:
        items, foods, subtotal, discount, delivery_fee, code = calculate_order(
            data.get("items"), data.get("coupon")
        )
    except ValueError as error:
        return jsonify(error=str(error)), 400
    user = current_user()
    if user is not None and user["role"] != "customer":
        return jsonify(error="Only customer accounts can place orders."), 403
    customer = current_customer()
    if customer:
        customer_name = customer["name"]
    if not 2 <= len(customer_name) <= 100:
        return jsonify(error="Please enter your name."), 400
    db = get_db()
    tracking_token = secrets.token_urlsafe(32)
    cursor = db.execute(
        """INSERT INTO orders
           (customer_id, customer_name, address, subtotal, discount, delivery_fee,
            total, tracking_token, coupon, status, chef_status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending', 'Pending')""",
        (customer["id"] if customer else None, customer_name, address, subtotal, discount, delivery_fee, subtotal - discount + delivery_fee, tracking_token, code),
    )
    order_id = cursor.lastrowid
    db.executemany(
        "INSERT INTO order_items (order_id, food_id, name, quantity, unit_price) VALUES (?, ?, ?, ?, ?)",
        [(order_id, food_id, foods[food_id]["name"], quantity, foods[food_id]["price"]) for food_id, quantity in items.items()],
    )
    db.commit()
    return jsonify(order_id=order_id, tracking_token=tracking_token, status="Pending", total=subtotal - discount + delivery_fee), 201


@app.get("/api/orders/<int:order_id>")
def get_order(order_id):
    db = get_db()
    order = db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if order is None:
        return jsonify(error="Order not found."), 404
    user = current_user()
    if user is None:
        if not order["tracking_token"] or not hmac.compare_digest(
            order["tracking_token"], request.args.get("token", "")
        ):
            return jsonify(error="A valid tracking link is required for this guest order."), 403
    elif user["role"] == "customer":
        if order["customer_id"] != user["id"]:
            return jsonify(error="Sign in with the account used for this order."), 403
    elif user["role"] == "delivery_partner":
        assignment = db.execute(
            "SELECT 1 FROM delivery_assignments WHERE order_id = ? AND partner_user_id = ?",
            (order_id, user["id"]),
        ).fetchone()
        if assignment is None:
            return jsonify(error="This order is not assigned to your account."), 403
    elif user["role"] == "chef":
        if (
            order["chef_user_id"] not in (None, user["id"])
            or order["status"] not in ("Pending", "Accepted", "Preparing", "Ready for Pickup")
        ):
            return jsonify(error="This order is assigned to another chef."), 403
    result = dict(order)
    result["items"] = [dict(row) for row in db.execute(
        "SELECT food_id, name, quantity, unit_price FROM order_items WHERE order_id = ?", (order_id,)
    ).fetchall()]
    assignment = db.execute(
        """SELECT da.status, da.simulated_lat AS latitude, da.simulated_lon AS longitude,
                  u.name AS partner_name
           FROM delivery_assignments da JOIN users u ON u.id = da.partner_user_id
           WHERE da.order_id = ?""",
        (order_id,),
    ).fetchone()
    result["delivery_assignment"] = {
        **dict(assignment), "simulated": True
    } if assignment else None
    result["tracking_note"] = "Demo map: partner location is simulated and does not use real GPS."
    return jsonify(result)


@app.get("/api/orders")
@login_required
def order_history():
    customer = current_customer()
    rows = get_db().execute(
        "SELECT id, total, status, created_at FROM orders WHERE customer_id = ? ORDER BY id DESC LIMIT 20",
        (customer["id"],),
    ).fetchall()
    return jsonify([dict(row) for row in rows])


@app.post("/api/customer/orders/<int:order_id>/cancel")
@role_required("customer")
def cancel_customer_order(order_id):
    user = current_user()
    cursor = get_db().execute(
        """UPDATE orders SET status = 'Cancelled', chef_status = 'Cancelled'
           WHERE id = ? AND customer_id = ? AND status IN ('Pending', 'Accepted')""",
        (order_id, user["id"]),
    )
    get_db().commit()
    if cursor.rowcount == 0:
        return jsonify(error="This order cannot be cancelled at its current status."), 409
    return jsonify(ok=True, status="Cancelled")


@app.get("/api/customer/summary")
@role_required("customer")
def customer_summary():
    user = current_user()
    db = get_db()
    orders = db.execute(
        """SELECT id, total, status, created_at FROM orders
           WHERE customer_id = ? ORDER BY id DESC LIMIT 20""",
        (user["id"],),
    ).fetchall()
    addresses = db.execute(
        "SELECT id, label, address FROM customer_addresses WHERE customer_id = ? ORDER BY id DESC",
        (user["id"],),
    ).fetchall()
    return jsonify(
        orders=[dict(row) for row in orders],
        addresses=[dict(row) for row in addresses],
    )


@app.get("/api/addresses")
@login_required
def addresses():
    customer = current_customer()
    rows = get_db().execute(
        "SELECT id, label, address FROM customer_addresses WHERE customer_id = ? ORDER BY id DESC",
        (customer["id"],),
    ).fetchall()
    return jsonify([dict(row) for row in rows])


@app.post("/api/addresses")
@login_required
def save_address():
    data = request.get_json(silent=True) or {}
    label = str(data.get("label", "")).strip()
    address = str(data.get("address", "")).strip()
    if not 1 <= len(label) <= 30 or not 10 <= len(address) <= 500:
        return jsonify(error="Enter an address label (up to 30 characters) and a complete address of up to 500 characters."), 400
    customer = current_customer()
    db = get_db()
    count = db.execute(
        "SELECT COUNT(*) FROM customer_addresses WHERE customer_id = ?", (customer["id"],)
    ).fetchone()[0]
    if count >= 5:
        return jsonify(error="You can save up to five delivery addresses."), 400
    cursor = db.execute(
        "INSERT INTO customer_addresses (customer_id, label, address) VALUES (?, ?, ?)",
        (customer["id"], label, address),
    )
    db.commit()
    return jsonify(id=cursor.lastrowid, label=label, address=address), 201


@app.delete("/api/addresses/<int:address_id>")
@login_required
def delete_address(address_id):
    customer = current_customer()
    cursor = get_db().execute(
        "DELETE FROM customer_addresses WHERE id = ? AND customer_id = ?",
        (address_id, customer["id"]),
    )
    get_db().commit()
    if cursor.rowcount == 0:
        return jsonify(error="Saved address not found."), 404
    return jsonify(ok=True)


def admin_required(handler):
    return role_required("admin")(handler)


@app.get("/api/admin/summary")
@admin_required
def admin_summary():
    db = get_db()
    stats = db.execute(
        """SELECT COUNT(*) AS order_count,
                  COALESCE(SUM(CASE WHEN status != 'Cancelled' THEN total ELSE 0 END), 0) AS sales,
                  SUM(CASE WHEN status IN ('Pending', 'Accepted', 'Preparing', 'Ready for Pickup',
                    'Picked Up', 'On the Way') THEN 1 ELSE 0 END) AS active_orders,
                  (SELECT COUNT(*) FROM users WHERE role = 'customer' AND active = 1) AS customers,
                  (SELECT COUNT(*) FROM users WHERE role = 'chef' AND active = 1) AS chefs,
                  (SELECT COUNT(*) FROM users WHERE role = 'delivery_partner' AND active = 1) AS partners
           FROM orders"""
    ).fetchone()
    users = db.execute(
        """SELECT id, name, email, role, active, created_at FROM users
           ORDER BY CASE role WHEN 'admin' THEN 0 WHEN 'chef' THEN 1
             WHEN 'delivery_partner' THEN 2 ELSE 3 END, id DESC"""
    ).fetchall()
    orders = db.execute(
        """SELECT o.id, o.customer_name, o.address, o.total, o.status, o.chef_status,
                  o.created_at, o.chef_user_id, chef.name AS chef_name,
                  da.partner_user_id, partner.name AS partner_name
           FROM orders o
           LEFT JOIN users chef ON chef.id = o.chef_user_id
           LEFT JOIN delivery_assignments da ON da.order_id = o.id
           LEFT JOIN users partner ON partner.id = da.partner_user_id
           ORDER BY o.id DESC LIMIT 50"""
    ).fetchall()
    return jsonify(
        foods=[dict(row) for row in db.execute("SELECT id, name, description, category, price, available FROM foods ORDER BY id")],
        categories=[dict(row) for row in db.execute("SELECT id, name FROM categories ORDER BY name")],
        offers=[dict(row) for row in db.execute("SELECT id, title, description, code, discount_percent, category, minimum_subtotal, free_delivery, active FROM offers ORDER BY id")],
        users=[dict(row) for row in users],
        customers=[dict(row) for row in users if row["role"] == "customer"],
        staff=[dict(row) for row in users if row["role"] in ("chef", "delivery_partner")],
        orders=[dict(row) for row in orders],
        stats=dict(stats),
    )


@app.post("/api/admin/foods/<int:food_id>")
@admin_required
def update_food(food_id):
    data = request.get_json(silent=True) or {}
    try:
        price = int(data.get("price"))
    except (TypeError, ValueError):
        return jsonify(error="Price must be a whole number."), 400
    available = data.get("available")
    category = str(data.get("category", "")).strip()
    name = str(data.get("name", "")).strip()
    description = str(data.get("description", "")).strip()
    db = get_db()
    food = db.execute("SELECT * FROM foods WHERE id = ?", (food_id,)).fetchone()
    if price < 1 or price > 100000 or not isinstance(available, bool):
        return jsonify(error="Enter a valid price and availability."), 400
    if food is None:
        return jsonify(error="Food item not found."), 404
    name = name or food["name"]
    description = description or food["description"]
    category = category or food["category"]
    if len(name) > 120 or len(description) > 500:
        return jsonify(error="Food name or description is too long."), 400
    db.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (category,))
    category_id = db.execute(
        "SELECT id FROM categories WHERE name = ?", (category,)
    ).fetchone()["id"]
    db.execute(
        "UPDATE foods SET name = ?, description = ?, category = ?, price = ?, available = ? WHERE id = ?",
        (name, description, category, price, int(available), food_id),
    )
    db.execute(
        """UPDATE food_items SET name = ?, description = ?, category_id = ?, price = ?, available = ?
           WHERE id = ?""",
        (name, description, category_id, price, int(available), food_id),
    )
    db.commit()
    return jsonify(ok=True)


@app.post("/api/admin/foods")
@admin_required
def create_food():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    description = str(data.get("description", "")).strip()
    category = str(data.get("category", "")).strip()
    image = str(data.get("image", "")).strip()
    emoji = str(data.get("emoji", "🍽️")).strip()[:12] or "🍽️"
    try:
        price = int(data.get("price"))
        rating = float(data.get("rating", 4.5))
    except (TypeError, ValueError):
        return jsonify(error="Price and rating must be numbers."), 400
    if not 2 <= len(name) <= 120 or not 1 <= len(description) <= 500:
        return jsonify(error="Enter a food name and description within the length limits."), 400
    if not 2 <= len(category) <= 60 or price < 1 or price > 100000 or not 1 <= rating <= 5:
        return jsonify(error="Enter a category, valid price and rating from 1 to 5."), 400
    if image and not image.startswith("https://"):
        return jsonify(error="Food image must use HTTPS."), 400
    db = get_db()
    db.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (category,))
    category_id = db.execute(
        "SELECT id FROM categories WHERE name = ?", (category,)
    ).fetchone()["id"]
    cursor = db.execute(
        """INSERT INTO foods (name, description, price, category, rating, emoji, image)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (name, description, price, category, rating, emoji, image),
    )
    food_id = cursor.lastrowid
    db.execute(
        """INSERT INTO food_items
           (id, legacy_food_id, category_id, name, description, price, rating, emoji, image, available)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
        (food_id, food_id, category_id, name, description, price, rating, emoji, image),
    )
    db.commit()
    return jsonify(id=food_id, name=name), 201


@app.post("/api/admin/users")
@admin_required
def create_staff_user():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    role = str(data.get("role", "")).strip()
    if role not in {"chef", "delivery_partner"}:
        return jsonify(error="Admins can create chef and delivery-partner accounts only."), 400
    if not 2 <= len(name) <= 100 or "@" not in email or len(email) > 254 or not 8 <= len(password) <= 256:
        return jsonify(error="Enter a valid name, email and password of 8–256 characters."), 400
    db = get_db()
    try:
        cursor = db.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
            (name, email, generate_password_hash(password), role),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify(error="An account with that email already exists."), 409
    return jsonify(id=cursor.lastrowid, name=name, email=email, role=role), 201


@app.post("/api/admin/users/<int:user_id>/active")
@admin_required
def set_user_active(user_id):
    data = request.get_json(silent=True) or {}
    active = data.get("active")
    if not isinstance(active, bool):
        return jsonify(error="Active must be true or false."), 400
    cursor = get_db().execute(
        "UPDATE users SET active = ? WHERE id = ? AND role != 'admin'",
        (int(active), user_id),
    )
    get_db().commit()
    if not cursor.rowcount:
        return jsonify(error="Account not found or cannot be disabled."), 404
    return jsonify(ok=True, active=active)


@app.post("/api/admin/categories")
@admin_required
def create_category():
    name = str((request.get_json(silent=True) or {}).get("name", "")).strip()
    if not 2 <= len(name) <= 60:
        return jsonify(error="Category names must be 2–60 characters."), 400
    try:
        cursor = get_db().execute("INSERT INTO categories (name) VALUES (?)", (name,))
        get_db().commit()
    except sqlite3.IntegrityError:
        return jsonify(error="That category already exists."), 409
    return jsonify(id=cursor.lastrowid, name=name), 201


@app.put("/api/admin/categories/<int:category_id>")
@admin_required
def rename_category(category_id):
    name = str((request.get_json(silent=True) or {}).get("name", "")).strip()
    if not 2 <= len(name) <= 60:
        return jsonify(error="Category names must be 2–60 characters."), 400
    db = get_db()
    category = db.execute("SELECT name FROM categories WHERE id = ?", (category_id,)).fetchone()
    if category is None:
        return jsonify(error="Category not found."), 404
    duplicate = db.execute(
        "SELECT id FROM categories WHERE name = ? AND id != ?", (name, category_id)
    ).fetchone()
    if duplicate is not None:
        return jsonify(error="That category already exists."), 409
    try:
        db.execute("INSERT INTO categories (name) VALUES (?)", (name,))
        new_category_id = db.execute(
            "SELECT id FROM categories WHERE name = ?", (name,)
        ).fetchone()["id"]
        db.execute("UPDATE foods SET category = ? WHERE category = ?", (name, category["name"]))
        db.execute(
            "UPDATE food_items SET category_id = ? WHERE category_id = ?",
            (new_category_id, category_id),
        )
        db.execute("UPDATE offers SET category = ? WHERE category = ?", (name, category["name"]))
        db.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        return jsonify(error="That category already exists."), 409
    return jsonify(id=new_category_id, name=name)


@app.post("/api/admin/offers")
@admin_required
def create_offer():
    data = request.get_json(silent=True) or {}
    try:
        title = str(data.get("title", "")).strip()
        code = str(data.get("code", "")).strip().upper()
        discount = int(data.get("discount_percent", 0))
        minimum = int(data.get("minimum_subtotal", 0))
    except (TypeError, ValueError):
        return jsonify(error="Discount and minimum subtotal must be whole numbers."), 400
    category = str(data.get("category", "")).strip() or None
    if not 2 <= len(title) <= 100 or not 3 <= len(code) <= 30 or not 0 <= discount <= 100 or minimum < 0:
        return jsonify(error="Enter a title, coupon code, 0–100% discount and non-negative minimum subtotal."), 400
    try:
        cursor = get_db().execute(
            """INSERT INTO offers
               (title, description, code, discount_percent, category, minimum_subtotal, free_delivery, active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (title, str(data.get("description", "")).strip()[:300], code, discount,
             category, minimum, int(bool(data.get("free_delivery"))),
             int(bool(data.get("active", True)))),
        )
        get_db().commit()
    except sqlite3.IntegrityError:
        return jsonify(error="That coupon code already exists."), 409
    return jsonify(id=cursor.lastrowid, code=code), 201


@app.post("/api/admin/offers/<int:offer_id>/active")
@admin_required
def set_offer_active(offer_id):
    active = (request.get_json(silent=True) or {}).get("active")
    if not isinstance(active, bool):
        return jsonify(error="Active must be true or false."), 400
    cursor = get_db().execute("UPDATE offers SET active = ? WHERE id = ?", (int(active), offer_id))
    get_db().commit()
    if not cursor.rowcount:
        return jsonify(error="Offer not found."), 404
    return jsonify(ok=True, active=active)


@app.get("/api/chef/orders")
@role_required("chef")
def chef_orders():
    user = current_user()
    rows = get_db().execute(
        """SELECT o.id, o.customer_name, o.address, o.total, o.status,
                  o.chef_status, o.created_at
           FROM orders o
           WHERE o.status IN ('Pending', 'Accepted', 'Preparing', 'Ready for Pickup')
             AND (o.chef_user_id IS NULL OR o.chef_user_id = ?)
           ORDER BY o.id""",
        (user["id"],),
    ).fetchall()
    return jsonify([dict(row) for row in rows])


@app.get("/api/chef/orders/<int:order_id>")
@role_required("chef")
def chef_order_detail(order_id):
    user = current_user()
    order = get_db().execute(
        """SELECT id, customer_name, address, total, status, chef_status
           FROM orders WHERE id = ?
             AND status IN ('Pending', 'Accepted', 'Preparing', 'Ready for Pickup')
             AND (chef_user_id IS NULL OR chef_user_id = ?)""",
        (order_id, user["id"]),
    ).fetchone()
    if order is None:
        return jsonify(error="Order not found or assigned to another chef."), 404
    result = dict(order)
    result["items"] = [dict(row) for row in get_db().execute(
        "SELECT food_id, name, quantity, unit_price FROM order_items WHERE order_id = ?",
        (order_id,),
    ).fetchall()]
    return jsonify(result)


@app.post("/api/chef/orders/<int:order_id>/status")
@role_required("chef")
def update_chef_order(order_id):
    user = current_user()
    status = str((request.get_json(silent=True) or {}).get("status", ""))
    transitions = {
        "Pending": {"Accepted", "Rejected"},
        "Accepted": {"Preparing", "Rejected"},
        "Preparing": {"Ready for Pickup"},
    }
    db = get_db()
    order = db.execute(
        "SELECT status, chef_status, chef_user_id FROM orders WHERE id = ?", (order_id,)
    ).fetchone()
    if (
        order is None or order["chef_user_id"] not in (None, user["id"])
        or order["status"] not in ("Pending", "Accepted", "Preparing", "Ready for Pickup")
    ):
        return jsonify(error="Order not found or assigned to another chef."), 404
    current = order["chef_status"]
    if status not in transitions.get(current, set()):
        return jsonify(error=f"Cannot move a {current.lower()} order to {status}."), 409
    order_status = "Rejected" if status == "Rejected" else status
    cursor = db.execute(
        """UPDATE orders SET chef_user_id = ?, chef_status = ?, status = ?
           WHERE id = ? AND status IN ('Pending', 'Accepted', 'Preparing', 'Ready for Pickup')
             AND (chef_user_id IS NULL OR chef_user_id = ?) AND chef_status = ?""",
        (user["id"], status, order_status, order_id, user["id"], current),
    )
    db.commit()
    if not cursor.rowcount:
        return jsonify(error="Order status changed. Refresh and try again."), 409
    if status == "Ready for Pickup":
        db.execute(
            """UPDATE delivery_assignments SET status = 'Ready for Pickup',
                 updated_at = CURRENT_TIMESTAMP
               WHERE order_id = ? AND status = 'Waiting for Pickup'""",
            (order_id,),
        )
        db.commit()
    return jsonify(ok=True, status=order_status, chef_status=status)


@app.post("/api/admin/orders/<int:order_id>/chef")
@admin_required
def assign_chef(order_id):
    data = request.get_json(silent=True) or {}
    try:
        chef_id = int(data.get("chef_user_id"))
    except (TypeError, ValueError):
        return jsonify(error="Choose a valid chef account."), 400
    db = get_db()
    chef = db.execute(
        "SELECT id FROM users WHERE id = ? AND role = 'chef' AND active = 1", (chef_id,)
    ).fetchone()
    if chef is None:
        return jsonify(error="Active chef account not found."), 404
    cursor = db.execute(
        "UPDATE orders SET chef_user_id = ? WHERE id = ? AND status NOT IN ('Delivered', 'Cancelled', 'Rejected')",
        (chef_id, order_id),
    )
    db.commit()
    if not cursor.rowcount:
        return jsonify(error="Order not found or no longer active."), 404
    return jsonify(ok=True, chef_user_id=chef_id)


@app.post("/api/admin/orders/<int:order_id>/status")
@admin_required
def set_admin_order_status(order_id):
    status = str((request.get_json(silent=True) or {}).get("status", ""))
    allowed = {
        "Cancelled", "Rejected", "Preparing", "Ready for Pickup",
        "Picked Up", "On the Way", "Delivered",
    }
    if status not in allowed:
        return jsonify(error="Choose a valid order status."), 400
    db = get_db()
    cursor = db.execute(
        "UPDATE orders SET status = ? WHERE id = ?", (status, order_id)
    )
    if not cursor.rowcount:
        return jsonify(error="Order not found."), 404
    if status in {"Cancelled", "Rejected"}:
        db.execute(
            "UPDATE delivery_assignments SET status = ? WHERE order_id = ?",
            (status, order_id),
        )
    elif status in {"Picked Up", "On the Way", "Delivered"}:
        db.execute(
            """UPDATE delivery_assignments SET status = ?, updated_at = CURRENT_TIMESTAMP
               WHERE order_id = ?""",
            (status, order_id),
        )
    db.commit()
    return jsonify(ok=True, status=status)


@app.get("/api/partner/orders")
@partner_required
def partner_orders():
    user = current_user()
    rows = get_db().execute(
        """SELECT o.id, o.customer_name, o.address, o.total, o.status, o.created_at,
                  da.status AS delivery_status, da.simulated_lat AS latitude,
                  da.simulated_lon AS longitude
           FROM delivery_assignments da JOIN orders o ON o.id = da.order_id
           WHERE da.partner_user_id = ? ORDER BY o.id DESC""",
        (user["id"],),
    ).fetchall()
    return jsonify([dict(row) for row in rows])


@app.post("/api/admin/orders/<int:order_id>/delivery")
@admin_required
def assign_delivery_partner(order_id):
    data = request.get_json(silent=True) or {}
    try:
        partner_id = int(data.get("partner_user_id"))
    except (TypeError, ValueError):
        return jsonify(error="Choose a valid delivery-partner account."), 400
    db = get_db()
    partner = db.execute(
        "SELECT id FROM users WHERE id = ? AND role = 'delivery_partner' AND active = 1",
        (partner_id,),
    ).fetchone()
    if partner is None:
        return jsonify(error="Active delivery-partner account not found."), 404
    order = db.execute(
        "SELECT status FROM orders WHERE id = ?", (order_id,)
    ).fetchone()
    if order is None or order["status"] in ("Cancelled", "Rejected", "Delivered"):
        return jsonify(error="Order not found or no longer active."), 404
    initial_status = "Ready for Pickup" if order["status"] == "Ready for Pickup" else "Waiting for Pickup"
    db.execute(
        """INSERT INTO delivery_assignments (order_id, partner_user_id, status)
           VALUES (?, ?, ?) ON CONFLICT(order_id) DO UPDATE SET
             partner_user_id=excluded.partner_user_id, status=excluded.status,
             updated_at=CURRENT_TIMESTAMP""",
        (order_id, partner_id, initial_status),
    )
    db.commit()
    return jsonify(ok=True, partner_user_id=partner_id)


@app.post("/api/partner/orders/<int:order_id>/status")
@partner_required
def update_delivery_status(order_id):
    status = str((request.get_json(silent=True) or {}).get("status", ""))
    transitions = {
        "Ready for Pickup": {"Picked Up"},
        "Picked Up": {"On the Way"},
        "On the Way": {"Delivered"},
    }
    user = current_user()
    db = get_db()
    assignment = db.execute(
        "SELECT status FROM delivery_assignments WHERE order_id = ? AND partner_user_id = ?",
        (order_id, user["id"]),
    ).fetchone()
    if assignment is None:
        return jsonify(error="This order is not assigned to your account."), 404
    current = assignment["status"]
    if status not in transitions.get(current, set()):
        return jsonify(error=f"Cannot move a {current.lower()} delivery to {status}."), 409
    locations = {
        "Picked Up": (12.9721, 77.5952),
        "On the Way": (12.9755, 77.6013),
        "Delivered": (12.9800, 77.6100),
    }
    latitude, longitude = locations[status]
    cursor = db.execute(
        """UPDATE delivery_assignments SET status = ?, simulated_lat = ?, simulated_lon = ?,
             updated_at = CURRENT_TIMESTAMP
           WHERE order_id = ? AND partner_user_id = ? AND status = ?""",
        (status, latitude, longitude, order_id, user["id"], current),
    )
    if cursor.rowcount:
        db.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    get_db().commit()
    if not cursor.rowcount:
        return jsonify(error="Delivery status changed. Refresh and try again."), 409
    return jsonify(ok=True, status=status)


with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
