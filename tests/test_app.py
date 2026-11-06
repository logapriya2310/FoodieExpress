import os
import tempfile
import unittest
import uuid


_test_storage = tempfile.TemporaryDirectory()
os.environ["DATABASE_PATH"] = os.path.join(_test_storage.name, "test-foodieexpress.db")
os.environ["ADMIN_EMAIL"] = "admin@example.test"
os.environ["ADMIN_PASSWORD"] = "test-admin-password"
os.environ["CHEF_EMAIL"] = "chef@example.test"
os.environ["CHEF_PASSWORD"] = "test-chef-password"
os.environ["DELIVERY_EMAIL"] = "partner@example.test"
os.environ["DELIVERY_PASSWORD"] = "test-partner-password"

import app as foodie_app


class FoodieExpressTests(unittest.TestCase):
    def setUp(self):
        foodie_app.app.config.update(TESTING=True, SECRET_KEY="test-secret")
        self.client = foodie_app.app.test_client()

    def tearDown(self):
        with foodie_app.app.app_context():
            foodie_app.get_db().execute(
                "UPDATE foods SET price = 249, available = 1 WHERE id = 1"
            )
            foodie_app.get_db().commit()

    def register_customer(self):
        email = f"{uuid.uuid4().hex}@example.test"
        response = self.client.post(
            "/api/auth/register",
            json={"name": "Test Customer", "email": email, "password": "test-password-123"},
        )
        self.assertEqual(response.status_code, 201)
        return email

    def user_id(self, email):
        with foodie_app.app.app_context():
            return foodie_app.get_db().execute(
                "SELECT id FROM users WHERE email = ?", (email,)
            ).fetchone()["id"]

    def test_menu_filters_and_category_inventory(self):
        response = self.client.get("/api/menu?category=Vegetarian")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json)
        self.assertTrue(all(food["category"] == "Vegetarian" for food in response.json))
        categories = {food["category"] for food in self.client.get("/api/menu").json}
        self.assertTrue({"Breakfast", "Lunch", "Dinner", "Snacks", "Desserts", "Beverages", "Vegetarian", "Non-Vegetarian"} <= categories)

    def test_legal_pages_render(self):
        self.assertIn("Privacy Policy", self.client.get("/privacy").get_data(as_text=True))
        self.assertIn("Terms and Conditions", self.client.get("/terms").get_data(as_text=True))
        self.assertIn("loginPageForm", self.client.get("/login").get_data(as_text=True))
        self.assertIn("signupPageForm", self.client.get("/signup").get_data(as_text=True))

    def test_diwali_coupon_only_discounts_desserts(self):
        applied = self.client.post(
            "/api/coupons/apply",
            json={"code": "DIWALI20", "items": [{"id": 6, "quantity": 2}]},
        )
        self.assertEqual(applied.status_code, 200)
        self.assertEqual(applied.json["discount"], 40)
        self.assertEqual(applied.json["delivery_fee"], 39)
        rejected = self.client.post(
            "/api/coupons/apply",
            json={"code": "DIWALI20", "items": [{"id": 1, "quantity": 1}]},
        )
        self.assertEqual(rejected.status_code, 400)
        oversized = self.client.post(
            "/api/coupons/apply",
            json={
                "code": "WELCOME10",
                "items": [{"id": 1, "quantity": 20}, {"id": 1, "quantity": 1}],
            },
        )
        self.assertEqual(oversized.status_code, 400)

    def test_recommendation_price_matches_its_menu_items(self):
        foods = {food["id"]: food["price"] for food in self.client.get("/api/menu").json}
        combos = self.client.get("/api/recommendations").json
        self.assertTrue(combos)
        for combo in combos:
            self.assertEqual(combo["price"], sum(foods[item_id] for item_id in combo["items"]))

    def test_guest_tracking_requires_unpredictable_token(self):
        order = self.client.post(
            "/api/orders",
            json={
                "name": "Guest Customer",
                "address": "12 Market Road, Bengaluru 560001",
                "items": [{"id": 1, "quantity": 1}],
            },
        )
        self.assertEqual(order.status_code, 201)
        self.assertEqual(order.json["total"], 288)
        order_id = order.json["order_id"]
        self.assertEqual(self.client.get(f"/api/orders/{order_id}").status_code, 403)
        tracked = self.client.get(
            f"/api/orders/{order_id}?token={order.json['tracking_token']}"
        )
        self.assertEqual(tracked.status_code, 200)
        self.assertIn("simulated", tracked.json["tracking_note"])

    def test_customer_can_save_address_and_submit_review(self):
        self.register_customer()
        address = self.client.post(
            "/api/addresses",
            json={"label": "Home", "address": "12 Market Road, Bengaluru 560001"},
        )
        self.assertEqual(address.status_code, 201)
        self.assertEqual(len(self.client.get("/api/addresses").json), 1)
        order = self.client.post(
            "/api/orders",
            json={
                "address": "12 Market Road, Bengaluru 560001",
                "items": [{"id": 3, "quantity": 1}],
            },
        )
        self.assertEqual(order.status_code, 201)
        self.assertEqual(order.json["status"], "Pending")
        chef = foodie_app.app.test_client()
        chef_login = chef.post(
            "/api/auth/login",
            json={"email": "chef@example.test", "password": "test-chef-password", "role": "chef"},
        )
        self.assertEqual(chef_login.json["customer"]["role"], "chef")
        accepted = chef.post(
            f"/api/chef/orders/{order.json['order_id']}/status",
            json={"status": "Accepted"},
        )
        self.assertEqual(accepted.json["status"], "Accepted")
        preparing = chef.post(
            f"/api/chef/orders/{order.json['order_id']}/status",
            json={"status": "Preparing"},
        )
        self.assertEqual(preparing.json["status"], "Preparing")
        ready = chef.post(
            f"/api/chef/orders/{order.json['order_id']}/status",
            json={"status": "Ready for Pickup"},
        )
        self.assertEqual(ready.json["status"], "Ready for Pickup")
        admin = foodie_app.app.test_client()
        admin.post(
            "/api/auth/login",
            json={"email": "admin@example.test", "password": "test-admin-password", "role": "admin"},
        )
        assigned = admin.post(
            f"/api/admin/orders/{order.json['order_id']}/delivery",
            json={"partner_user_id": self.user_id("partner@example.test")},
        )
        self.assertEqual(assigned.status_code, 200)
        partner = foodie_app.app.test_client()
        partner.post(
            "/api/auth/login",
            json={"email": "partner@example.test", "password": "test-partner-password", "role": "delivery_partner"},
        )
        picked_up = partner.post(
            f"/api/partner/orders/{order.json['order_id']}/status",
            json={"status": "Picked Up"},
        )
        self.assertEqual(picked_up.status_code, 200)
        on_the_way = partner.post(
            f"/api/partner/orders/{order.json['order_id']}/status",
            json={"status": "On the Way"},
        )
        self.assertEqual(on_the_way.status_code, 200)
        delivered = partner.post(
            f"/api/partner/orders/{order.json['order_id']}/status",
            json={"status": "Delivered"},
        )
        self.assertEqual(delivered.status_code, 200)
        self.assertEqual(chef.get(f"/api/orders/{order.json['order_id']}").status_code, 403)
        self.assertEqual(
            chef.get(f"/api/chef/orders/{order.json['order_id']}").status_code,
            404,
        )
        self.assertEqual(
            chef.post(
                f"/api/chef/orders/{order.json['order_id']}/status",
                json={"status": "Accepted"},
            ).status_code,
            404,
        )
        review = self.client.post(
            "/api/reviews",
            json={"food": "Masala Dosa", "rating": 5, "feedback": "Fresh, crisp and delicious!"},
        )
        self.assertEqual(review.status_code, 201)
        deleted = self.client.delete(f"/api/addresses/{address.json['id']}")
        self.assertEqual(deleted.status_code, 200)

    def test_delivery_dashboard_requires_partner_login(self):
        self.assertEqual(self.client.get("/api/partner/orders").status_code, 401)
        login = self.client.post(
            "/api/auth/login",
            json={"email": "partner@example.test", "password": "test-partner-password", "role": "delivery_partner"},
        )
        self.assertEqual(login.status_code, 200)
        self.assertEqual(login.json["customer"]["role"], "delivery_partner")
        self.assertEqual(self.client.get("/api/partner/orders").status_code, 200)

    def test_admin_can_manage_menu_but_is_required(self):
        self.assertEqual(self.client.get("/api/admin/summary").status_code, 401)
        login = self.client.post(
            "/api/auth/login",
            json={"email": "admin@example.test", "password": "test-admin-password", "role": "admin"},
        )
        self.assertEqual(login.status_code, 200)
        self.assertEqual(login.json["customer"]["role"], "admin")
        self.assertEqual(self.client.get("/api/admin/summary").status_code, 200)
        updated = self.client.post(
            "/api/admin/foods/1", json={"price": 251, "available": True}
        )
        self.assertEqual(updated.status_code, 200)
        unavailable = self.client.post(
            "/api/admin/foods/1", json={"price": 251, "available": False}
        )
        self.assertEqual(unavailable.status_code, 200)
        food = next(food for food in self.client.get("/api/menu").json if food["id"] == 1)
        self.assertEqual(food["available"], 0)

    def test_role_login_redirect_and_dashboard_access(self):
        cases = [
            ("admin@example.test", "test-admin-password", "admin"),
            ("chef@example.test", "test-chef-password", "chef"),
            ("partner@example.test", "test-partner-password", "delivery_partner"),
        ]
        for email, password, role in cases:
            with self.subTest(role=role):
                client = foodie_app.app.test_client()
                response = client.post(
                    "/api/auth/login",
                    json={"email": email, "password": password, "role": role},
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json["redirect"], f"/dashboard/{role}")
                self.assertEqual(client.get(f"/dashboard/{role}").status_code, 200)
                self.assertEqual(client.get("/dashboard/customer").status_code, 403)
                self.assertEqual(client.get("/api/orders").status_code, 403)
                self.assertEqual(client.get("/api/admin/summary").status_code, 200 if role == "admin" else 403)
                client.get("/logout")
                self.assertEqual(client.get(f"/dashboard/{role}").status_code, 302)

        customer_email = self.register_customer()
        customer = self.client.post(
            "/api/auth/login",
            json={"email": customer_email, "password": "test-password-123", "role": "customer"},
        )
        self.assertEqual(customer.status_code, 200)
        self.assertEqual(customer.json["redirect"], "/dashboard/customer")

    def test_admin_can_create_staff_accounts_and_passwords_are_not_returned(self):
        admin = foodie_app.app.test_client()
        admin.post(
            "/api/auth/login",
            json={"email": "admin@example.test", "password": "test-admin-password", "role": "admin"},
        )
        created = admin.post(
            "/api/admin/users",
            json={
                "name": "Second Chef",
                "email": "second-chef@example.test",
                "password": "second-chef-password",
                "role": "chef",
            },
        )
        self.assertEqual(created.status_code, 201)
        self.assertNotIn("password", created.json)
        chef = foodie_app.app.test_client()
        self.assertEqual(chef.post(
            "/api/auth/login",
            json={"email": "second-chef@example.test", "password": "second-chef-password", "role": "chef"},
        ).status_code, 200)
        summary = admin.get("/api/admin/summary").json
        self.assertNotIn("password_hash", str(summary))
        self.assertEqual(
            admin.post(
                "/api/admin/offers",
                json={
                    "title": "Test dessert deal",
                    "description": "Test coupon",
                    "code": "TESTDESSERT",
                    "discount_percent": 15,
                    "category": "Desserts",
                    "minimum_subtotal": 0,
                    "free_delivery": False,
                },
            ).status_code,
            201,
        )
        self.assertEqual(
            self.client.post(
                "/api/coupons/apply",
                json={"code": "TESTDESSERT", "items": [{"id": 6, "quantity": 1}]},
            ).json["discount"],
            15,
        )

    def test_role_boundaries_order_cancellation_and_status_transitions(self):
        self.register_customer()
        customer_order = self.client.post(
            "/api/orders",
            json={
                "address": "12 Market Road, Bengaluru 560001",
                "items": [{"id": 3, "quantity": 1}],
            },
        )
        self.assertEqual(customer_order.status_code, 201)
        order_id = customer_order.json["order_id"]

        chef = foodie_app.app.test_client()
        chef.post(
            "/api/auth/login",
            json={"email": "chef@example.test", "password": "test-chef-password", "role": "chef"},
        )
        self.assertEqual(
            chef.post(
                f"/api/chef/orders/{order_id}/status", json={"status": "Ready for Pickup"}
            ).status_code,
            409,
        )
        self.assertEqual(
            chef.post(
                f"/api/chef/orders/{order_id}/status", json={"status": "Accepted"}
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.post(f"/api/customer/orders/{order_id}/cancel", json={}).json["status"],
            "Cancelled",
        )
        self.assertEqual(
            self.client.get(f"/api/orders/{order_id}").status_code,
            200,
        )
        self.assertEqual(
            self.client.post(
                "/api/auth/login",
                json={"email": "chef@example.test", "password": "test-chef-password", "role": "admin"},
            ).status_code,
            401,
        )

    def test_admin_can_rename_category_and_maintain_foreign_keys(self):
        admin = foodie_app.app.test_client()
        admin.post(
            "/api/auth/login",
            json={"email": "admin@example.test", "password": "test-admin-password", "role": "admin"},
        )
        created = admin.post("/api/admin/categories", json={"name": "Seasonal Specials"})
        self.assertEqual(created.status_code, 201)
        renamed = admin.put(
            f"/api/admin/categories/{created.json['id']}",
            json={"name": "Celebration Specials"},
        )
        self.assertEqual(renamed.status_code, 200)
        with foodie_app.app.app_context():
            db = foodie_app.get_db()
            foreign_key_errors = db.execute("PRAGMA foreign_key_check").fetchall()
            self.assertEqual(foreign_key_errors, [])
            item = db.execute(
                "SELECT c.name FROM food_items fi JOIN categories c ON c.id = fi.category_id LIMIT 1"
            ).fetchone()
            self.assertIsNotNone(item)

    def test_legacy_customer_records_are_migrated_without_replacement(self):
        with foodie_app.app.app_context():
            db = foodie_app.get_db()
            legacy_id = db.execute("SELECT COALESCE(MAX(id), 0) + 100 FROM customers").fetchone()[0]
            password_hash = foodie_app.generate_password_hash("legacy-password")
            db.execute(
                "INSERT INTO customers (id, name, email, password_hash) VALUES (?, ?, ?, ?)",
                (legacy_id, "Legacy Customer", f"legacy-{legacy_id}@example.test", password_hash),
            )
            db.commit()
            foodie_app.init_db()
            migrated = db.execute("SELECT id, role FROM users WHERE id = ?", (legacy_id,)).fetchone()
            self.assertEqual((migrated["id"], migrated["role"]), (legacy_id, "customer"))
            self.assertEqual(
                db.execute("SELECT COUNT(*) FROM customers WHERE id = ?", (legacy_id,)).fetchone()[0],
                1,
            )


if __name__ == "__main__":
    unittest.main()
