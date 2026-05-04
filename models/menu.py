"""
models/menu.py — MenuItem model representing food/drink products sold in the canteen.
"""
from models import db


class MenuItem(db.Model):
    """
    Represents a product available for sale in the canteen.
    Stock is decremented automatically when an order is placed.
    """
    __tablename__ = "menu_items"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(60), nullable=False)   # e.g. 'Meals', 'Snacks', 'Beverages'
    price = db.Column(db.Float, nullable=False)
    stock_quantity = db.Column(db.Integer, nullable=False, default=0)
    is_available = db.Column(db.Boolean, default=True)    # manually disable without deleting
    image_filename = db.Column(db.String(255), nullable=True)

    # Relationships
    order_items = db.relationship("OrderItem", back_populates="menu_item", lazy="dynamic")

    # ── Convenience ──────────────────────────────────────────────────────────
    @property
    def in_stock(self) -> bool:
        return self.stock_quantity > 0

    def reduce_stock(self, qty: int) -> None:
        """Decrement stock; raises ValueError if insufficient."""
        if self.stock_quantity < qty:
            raise ValueError(
                f"Insufficient stock for '{self.name}'. "
                f"Available: {self.stock_quantity}, Requested: {qty}"
            )
        self.stock_quantity -= qty

    def __repr__(self) -> str:
        return f"<MenuItem {self.name!r} ₹{self.price} (stock={self.stock_quantity})>"
