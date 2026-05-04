"""
models/order.py — Order and OrderItem models.

Order       : parent record storing totals, GST, status, and timestamp.
OrderItem   : child records with per-item price snapshot (guards against future price changes).
"""
from datetime import datetime
from models import db


class Order(db.Model):
    """
    A single completed (or pending) purchase transaction by a user.
    """
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)

    # Foreign key to the user who placed this order
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # Financial summary
    subtotal = db.Column(db.Float, nullable=False, default=0.0)
    gst_amount = db.Column(db.Float, nullable=False, default=0.0)
    total_amount = db.Column(db.Float, nullable=False, default=0.0)

    # Metadata
    order_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    payment_method = db.Column(db.String(20), nullable=True) # 'Cash', 'UPI', 'Card'
    payment_status = db.Column(db.String(20), nullable=False, default="pending")  # 'pending' | 'paid' | 'failed'

    # Relationships
    user = db.relationship("User", back_populates="orders")
    items = db.relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Order #{self.id} user={self.user_id} ₹{self.total_amount}>"


class OrderItem(db.Model):
    """
    An individual line in an order — links an Order to a MenuItem
    and records the price paid at the time of ordering.
    """
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)

    # Parent order
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)

    # Menu item reference (nullable on delete to preserve history)
    menu_id = db.Column(db.Integer, db.ForeignKey("menu_items.id"), nullable=True)

    quantity = db.Column(db.Integer, nullable=False, default=1)

    # Price snapshot — stored so historical orders remain correct if price changes later
    item_price = db.Column(db.Float, nullable=False)

    # Item name snapshot — stored so history is preserved even if item is deleted
    item_name = db.Column(db.String(120), nullable=False, default="")

    # Computed on demand
    @property
    def line_total(self) -> float:
        return round(self.item_price * self.quantity, 2)

    # Relationships
    order = db.relationship("Order", back_populates="items")
    menu_item = db.relationship("MenuItem", back_populates="order_items")

    def __repr__(self) -> str:
        return f"<OrderItem order={self.order_id} item={self.menu_id} qty={self.quantity}>"
