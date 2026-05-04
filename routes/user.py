"""
routes/user.py — All user-facing routes.

Features:
  - Menu browsing with category filter and search
  - Session-based cart (add, update, remove)
  - Order placement with stock validation
  - GST calculation and invoice generation
  - Order history

Access control: all routes require login.
"""
from datetime import datetime, timezone
import os

from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, session, abort
)
from flask_login import login_required, current_user

from models import db
from models.menu import MenuItem
from models.order import Order, OrderItem
from config import Config

user_bp = Blueprint("user", __name__)


# ── Cart helpers ──────────────────────────────────────────────────────────────
def get_cart() -> dict:
    """Return the current session cart (dict: item_id -> qty)."""
    return session.get("cart", {})


def save_cart(cart: dict) -> None:
    """Persist the cart dict back into the session."""
    session["cart"] = cart
    session.modified = True


def cart_item_count() -> int:
    """Return total number of items (units) in the cart."""
    return sum(get_cart().values())


# Make cart_item_count available in all templates via context processor
@user_bp.app_context_processor
def inject_cart_count():
    if current_user.is_authenticated and not current_user.is_admin:
        return {"cart_item_count": cart_item_count()}
    return {"cart_item_count": 0}


# ── Menu ──────────────────────────────────────────────────────────────────────
@user_bp.route("/menu")
@login_required
def menu():
    """
    Display all available menu items.
    Supports:
      - Category filter via ?category=
      - Text search via ?search=
    """
    if current_user.is_admin:
        return redirect(url_for("admin.dashboard"))

    category = request.args.get("category", "").strip()
    search   = request.args.get("search",   "").strip()

    query = MenuItem.query.filter_by(is_available=True)

    if category:
        query = query.filter_by(category=category)

    if search:
        query = query.filter(MenuItem.name.ilike(f"%{search}%"))

    items = query.order_by(MenuItem.category, MenuItem.name).all()

    # All distinct categories for the filter bar
    categories = [
        c[0] for c in
        db.session.query(MenuItem.category)
        .filter_by(is_available=True)
        .distinct()
        .order_by(MenuItem.category)
        .all()
    ]

    cart = get_cart()

    return render_template(
        "user/menu.html",
        items=items,
        categories=categories,
        selected_category=category,
        search=search,
        cart=cart,
    )


# ── Cart ──────────────────────────────────────────────────────────────────────
@user_bp.route("/cart")
@login_required
def view_cart():
    """Display the current cart with totals."""
    if current_user.is_admin:
        return redirect(url_for("admin.dashboard"))

    cart = get_cart()
    cart_items = []
    subtotal = 0.0

    for item_id_str, qty in cart.items():
        item = db.session.get(MenuItem, int(item_id_str))
        if item:
            line = item.price * qty
            subtotal += line
            cart_items.append({"item": item, "qty": qty, "line_total": round(line, 2)})

    gst_amount = round(subtotal * Config.GST_PERCENT / 100, 2)
    total      = round(subtotal + gst_amount, 2)

    return render_template(
        "user/cart.html",
        cart_items=cart_items,
        subtotal=round(subtotal, 2),
        gst_amount=gst_amount,
        gst_percent=Config.GST_PERCENT,
        total=total,
    )


@user_bp.route("/cart/add/<int:item_id>", methods=["POST"])
@login_required
def add_to_cart(item_id):
    """Add one unit of an item to the cart, or increment its quantity."""
    item = MenuItem.query.get_or_404(item_id)

    if not item.is_available:
        flash(f"'{item.name}' is currently not available.", "warning")
        return redirect(url_for("user.menu"))

    qty = int(request.form.get("quantity", 1))
    if qty < 1:
        qty = 1

    cart = get_cart()
    current_qty = cart.get(str(item_id), 0)

    # Check stock before adding
    if current_qty + qty > item.stock_quantity:
        flash(f"Cannot add {qty} more — only {item.stock_quantity} in stock.", "warning")
        return redirect(url_for("user.menu"))

    cart[str(item_id)] = current_qty + qty
    save_cart(cart)
    flash(f"'{item.name}' added to cart.", "success")
    return redirect(request.referrer or url_for("user.menu"))


@user_bp.route("/cart/update/<int:item_id>", methods=["POST"])
@login_required
def update_cart(item_id):
    """Update the quantity of a cart item, or remove it if qty ≤ 0."""
    cart = get_cart()
    qty  = int(request.form.get("quantity", 1))

    if qty <= 0:
        cart.pop(str(item_id), None)
        flash("Item removed from cart.", "info")
    else:
        item = db.session.get(MenuItem, item_id)
        if item and qty > item.stock_quantity:
            flash(f"Only {item.stock_quantity} units available for '{item.name}'.", "warning")
            qty = item.stock_quantity
        cart[str(item_id)] = qty

    save_cart(cart)
    return redirect(url_for("user.view_cart"))


@user_bp.route("/cart/remove/<int:item_id>", methods=["POST"])
@login_required
def remove_from_cart(item_id):
    """Remove an item from the cart entirely."""
    cart = get_cart()
    cart.pop(str(item_id), None)
    save_cart(cart)
    flash("Item removed from cart.", "info")
    return redirect(url_for("user.view_cart"))


@user_bp.route("/cart/clear", methods=["POST"])
@login_required
def clear_cart():
    """Empty the entire cart."""
    save_cart({})
    flash("Cart cleared.", "info")
    return redirect(url_for("user.menu"))


# ── Order Placement ───────────────────────────────────────────────────────────
@user_bp.route("/order/place", methods=["POST"])
@login_required
def place_order():
    """
    Validate cart, reduce stock, create Order and OrderItem records,
    clear cart, and redirect to the invoice page.
    """
    cart = get_cart()

    if not cart:
        flash("Your cart is empty. Please add items before placing an order.", "warning")
        return redirect(url_for("user.menu"))

    subtotal   = 0.0
    order_items_data = []

    # ── Validate all items before touching the DB ─────────────────────────────
    for item_id_str, qty in cart.items():
        item = db.session.get(MenuItem, int(item_id_str))
        if not item or not item.is_available:
            flash(f"Item is no longer available. Please update your cart.", "danger")
            return redirect(url_for("user.view_cart"))
        if item.stock_quantity < qty:
            flash(
                f"Insufficient stock for '{item.name}'. "
                f"Available: {item.stock_quantity}, In cart: {qty}.",
                "danger"
            )
            return redirect(url_for("user.view_cart"))
        subtotal += item.price * qty
        order_items_data.append((item, qty))

    # ── Calculate totals ──────────────────────────────────────────────────────
    gst_amount   = round(subtotal * Config.GST_PERCENT / 100, 2)
    total_amount = round(subtotal + gst_amount, 2)

    # ── Persist order ─────────────────────────────────────────────────────────
    order = Order(
        user_id=current_user.id,
        subtotal=round(subtotal, 2),
        gst_amount=gst_amount,
        total_amount=total_amount,
        order_date=datetime.now(timezone.utc),
        payment_status="pending",  # Default to pending for online payment
    )
    db.session.add(order)
    db.session.flush()  # get order.id before committing

    for item, qty in order_items_data:
        oi = OrderItem(
            order_id=order.id,
            menu_id=item.id,
            quantity=qty,
            item_price=item.price,
            item_name=item.name,
        )
        db.session.add(oi)
        # Reduce stock
        item.stock_quantity -= qty

    db.session.commit()

    # Clear cart after successful order placement (before payment)
    save_cart({})
    
    # Redirect to payment page instead of invoice
    flash("Order placed! Please complete payment to confirm. 💳", "info")
    return redirect(url_for("user.payment_page", order_id=order.id))


# ── Invoice ───────────────────────────────────────────────────────────────────
@user_bp.route("/order/<int:order_id>/invoice")
@login_required
def invoice(order_id):
    """Display a printable invoice for a given order."""
    order = Order.query.get_or_404(order_id)

    # Users can only see their own invoices; admins can see all
    if not current_user.is_admin and order.user_id != current_user.id:
        abort(403)

    return render_template("user/invoice.html", order=order, gst_percent=Config.GST_PERCENT)


# ── Order History ─────────────────────────────────────────────────────────────
@user_bp.route("/order/history")
@login_required
def order_history():
    """Display the current user's past orders, most recent first."""
    if current_user.is_admin:
        return redirect(url_for("admin.orders"))

    orders = (
        Order.query
        .filter_by(user_id=current_user.id)
        .order_by(Order.order_date.desc())
        .all()
    )
    return render_template("user/order_history.html", orders=orders)


# ── Payment Processing ────────────────────────────────────────────────────────
@user_bp.route("/order/<int:order_id>/payment")
@login_required
def payment_page(order_id):
    """
    Generate dynamic UPI QR code and display payment page.
    """
    import qrcode

    order = db.session.get(Order, order_id)

    # Security check
    if order.user_id != current_user.id:
        abort(403)

    if order.payment_status == "paid":
        flash("Order already paid.", "info")
        return redirect(url_for("user.invoice", order_id=order.id))

    # Generate UPI URI
    # upi://pay?pa=canteen@upi&pn=CanteenMS&am=<amount>&cu=INR&tn=Order_<order_id>
    upi_id = "canteen@upi"
    amount = order.total_amount
    order_tn = f"Order_{order.id}"
    upi_uri = f"upi://pay?pa={upi_id}&pn=CanteenMS&am={amount}&cu=INR&tn={order_tn}"

    # Create QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(upi_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    # Save temp QR code
    qr_filename = f"qr_{order.id}.png"
    qr_path = os.path.join(Config.BASE_DIR, "static", "qrcodes", qr_filename)
    
    # Ensure directory exists (redundant but safe)
    os.makedirs(os.path.dirname(qr_path), exist_ok=True)
    
    img.save(qr_path)

    return render_template(
        "user/payment.html", 
        order=order, 
        qr_filename=qr_filename,
        upi_id=upi_id
    )


@user_bp.route("/order/<int:order_id>/payment/confirm", methods=["POST"])
@login_required
def confirm_payment(order_id):
    """
    Simulate payment confirmation and update order status.
    """
    order = Order.query.get_or_404(order_id)

    if order.user_id != current_user.id:
        abort(403)

    # ── Simulate successful payment ───────────────────────────────────────────
    order.payment_status = "paid"
    order.payment_method = "UPI"
    db.session.commit()

    flash("Payment confirmed! Your order is being prepared. 🍽️", "success")
    return redirect(url_for("user.invoice", order_id=order.id))
