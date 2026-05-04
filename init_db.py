"""
init_db.py — Database initialization and seed data script.

Run ONCE before starting the application:
    python init_db.py

Creates all tables and populates:
  - 1 admin account
  - 2 staff/user accounts
  - 20 sample menu items across 4 categories
"""
from app import create_app
from models import db
from models.user import User
from models.menu import MenuItem

app = create_app()

with app.app_context():
    # ── Create schema ─────────────────────────────────────────────────────────
    db.create_all()
    print("✅  Database tables created.")

    # ── Seed users (only if none exist) ──────────────────────────────────────
    if User.query.count() == 0:
        users_data = [
            {"username": "admin",  "password": "admin123",  "role": "admin"},
            {"username": "user1",  "password": "user123",   "role": "user"},
            {"username": "user2",  "password": "user456",   "role": "user"},
        ]
        for ud in users_data:
            u = User(username=ud["username"], role=ud["role"])
            u.set_password(ud["password"])
            db.session.add(u)
        db.session.commit()
        print("✅  Sample users created.")
        print("    Admin  → username: admin  | password: admin123")
        print("    User 1 → username: user1  | password: user123")
        print("    User 2 → username: user2  | password: user456")
    else:
        print("ℹ️   Users already exist — skipping seed.")

    # ── Seed menu items ───────────────────────────────────────────────────────
    if MenuItem.query.count() == 0:
        items_data = [
            # Meals
            {"name": "Veg Thali",         "category": "Meals",      "price": 80.0,  "stock_quantity": 50},
            {"name": "Chicken Biryani",   "category": "Meals",      "price": 120.0, "stock_quantity": 40},
            {"name": "Paneer Rice",        "category": "Meals",      "price": 100.0, "stock_quantity": 30},
            {"name": "Dal Tadka & Rice",   "category": "Meals",      "price": 70.0,  "stock_quantity": 4},
            {"name": "Egg Fried Rice",     "category": "Meals",      "price": 90.0,  "stock_quantity": 35},
            # Snacks
            {"name": "Samosa (2 pcs)",     "category": "Snacks",     "price": 20.0,  "stock_quantity": 100},
            {"name": "Veg Sandwich",       "category": "Snacks",     "price": 35.0,  "stock_quantity": 60},
            {"name": "Bread Omelette",     "category": "Snacks",     "price": 40.0,  "stock_quantity": 8},
            {"name": "Puffs",              "category": "Snacks",     "price": 25.0,  "stock_quantity": 80},
            {"name": "French Fries",       "category": "Snacks",     "price": 60.0,  "stock_quantity": 50},
            {"name": "Spring Rolls",       "category": "Snacks",     "price": 55.0,  "stock_quantity": 3},
            # Beverages
            {"name": "Tea",                "category": "Beverages",  "price": 10.0,  "stock_quantity": 200},
            {"name": "Coffee",             "category": "Beverages",  "price": 15.0,  "stock_quantity": 150},
            {"name": "Cold Coffee",        "category": "Beverages",  "price": 40.0,  "stock_quantity": 50},
            {"name": "Fresh Lime Soda",    "category": "Beverages",  "price": 30.0,  "stock_quantity": 70},
            {"name": "Mango Lassi",        "category": "Beverages",  "price": 45.0,  "stock_quantity": 5},
            # Desserts
            {"name": "Gulab Jamun (2 pcs)","category": "Desserts",   "price": 30.0,  "stock_quantity": 60},
            {"name": "Ice Cream Cup",      "category": "Desserts",   "price": 35.0,  "stock_quantity": 9},
            {"name": "Halwa",              "category": "Desserts",   "price": 25.0,  "stock_quantity": 40},
            {"name": "Kheer",              "category": "Desserts",   "price": 30.0,  "stock_quantity": 30},
        ]
        for d in items_data:
            db.session.add(MenuItem(**d))
        db.session.commit()
        print("✅  Sample menu items created (20 items across 4 categories).")
    else:
        print("ℹ️   Menu items already exist — skipping seed.")

    print("\n🚀  Setup complete. Run:  python app.py")
    print("    Open: http://127.0.0.1:5000")
