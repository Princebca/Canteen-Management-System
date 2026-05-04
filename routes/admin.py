"""
routes/admin.py — All admin-facing routes.

Features covered:
  - Dashboard with KPI cards (orders today, revenue, items, low-stock)
  - CRUD for menu items (add / edit / delete)
  - View all orders with date filter
  - Daily sales report
  - CSV export of sales data
  - Low-stock alert list

Access control: every route requires login AND admin role.
"""
import csv
import io
import os
from datetime import datetime, date, timedelta, timezone
from functools import wraps

from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, abort, Response
)
from flask_login import login_required, current_user
from sqlalchemy import func
from werkzeug.utils import secure_filename

from models import db
from models.menu import MenuItem
from models.order import Order, OrderItem
from models.user import User
from config import Config

admin_bp = Blueprint("admin", __name__)


# ── Access-control decorator ─────────────────────────────────────────────────
def admin_required(f):
    """Decorator: ensures the current user is authenticated AND is an admin."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return login_required(decorated)


# ── Dashboard ─────────────────────────────────────────────────────────────────
@admin_bp.route("/")
@admin_required
def dashboard():
    """
    Admin dashboard showing:
      - Total orders placed today
      - Total revenue today
      - Number of available menu items
      - Number of low-stock items
      - Recent orders (last 10)
      - Low-stock items list
    """
    today_start = datetime.combine(date.today(), datetime.min.time(), tzinfo=timezone.utc)
    today_end   = datetime.combine(date.today(), datetime.max.time(), tzinfo=timezone.utc)

    # Orders placed today
    orders_today = Order.query.filter(
        Order.order_date.between(today_start, today_end)
    ).count()

    # Revenue today
    revenue_today = db.session.query(func.sum(Order.total_amount)).filter(
        Order.order_date.between(today_start, today_end)
    ).scalar() or 0.0

    # Total distinct menu items available
    available_items = MenuItem.query.filter_by(is_available=True).count()

    # Low-stock items
    low_stock_items = MenuItem.query.filter(
        MenuItem.stock_quantity <= Config.LOW_STOCK_THRESHOLD
    ).order_by(MenuItem.stock_quantity.asc()).all()

    # Recent orders
    recent_orders = (
        Order.query.order_by(Order.order_date.desc()).limit(10).all()
    )

    return render_template(
        "admin/dashboard.html",
        orders_today=orders_today,
        revenue_today=revenue_today,
        available_items=available_items,
        recent_orders=recent_orders,
        low_stock_threshold=Config.LOW_STOCK_THRESHOLD,
        now=datetime.now(timezone.utc),
    )


# ── Menu Item Management ──────────────────────────────────────────────────────
@admin_bp.route("/items", methods=["GET", "POST"])
@admin_required
def items():
    """List all menu items and handle adding a new item."""
    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        price    = request.form.get("price", "")
        stock    = request.form.get("stock_quantity", "")
        image    = request.files.get("image")

        # ── Validation ────────────────────────────────────────────────────────
        errors = []
        if not name:
            errors.append("Item name is required.")
        if not category:
            errors.append("Category is required.")
        try:
            price = float(price)
            if price < 0:
                errors.append("Price cannot be negative.")
        except (ValueError, TypeError):
            errors.append("Enter a valid price.")
        try:
            stock = int(stock)
            if stock < 0:
                errors.append("Stock cannot be negative.")
        except (ValueError, TypeError):
            errors.append("Enter a valid stock quantity.")

        if errors:
            for e in errors:
                flash(e, "danger")
        else:
            image_filename = None
            if image and image.filename:
                filename = secure_filename(image.filename)
                if filename:
                    timestamp = int(datetime.now().timestamp())
                    image_filename = f"{timestamp}_{filename}"
                    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
                    image.save(os.path.join(Config.UPLOAD_FOLDER, image_filename))

            item = MenuItem(name=name, category=category, price=price, stock_quantity=stock, image_filename=image_filename)
            db.session.add(item)
            db.session.commit()
            flash(f"Menu item '{name}' added successfully!", "success")
            return redirect(url_for("admin.items"))

    all_items = MenuItem.query.order_by(MenuItem.category, MenuItem.name).all()
    categories = db.session.query(MenuItem.category).distinct().all()
    categories = [c[0] for c in categories]
    return render_template(
        "admin/items.html",
        items=all_items,
        categories=categories,
        low_stock_threshold=Config.LOW_STOCK_THRESHOLD,
    )


@admin_bp.route("/items/<int:item_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_item(item_id):
    """Edit an existing menu item."""
    item = db.session.get(MenuItem, item_id)
    if not item:
        abort(404)

    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        price    = request.form.get("price", "")
        stock    = request.form.get("stock_quantity", "")
        available = request.form.get("is_available") == "on"
        image    = request.files.get("image")

        errors = []
        if not name:
            errors.append("Item name is required.")
        if not category:
            errors.append("Category is required.")
        try:
            price = float(price)
            if price < 0:
                errors.append("Price cannot be negative.")
        except (ValueError, TypeError):
            errors.append("Enter a valid price.")
        try:
            stock = int(stock)
            if stock < 0:
                errors.append("Stock cannot be negative.")
        except (ValueError, TypeError):
            errors.append("Enter a valid stock quantity.")

        if errors:
            for e in errors:
                flash(e, "danger")
        else:
            if image and image.filename:
                filename = secure_filename(image.filename)
                if filename:
                    timestamp = int(datetime.now().timestamp())
                    image_filename = f"{timestamp}_{filename}"
                    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
                    image.save(os.path.join(Config.UPLOAD_FOLDER, image_filename))
                    item.image_filename = image_filename

            item.name           = name
            item.category       = category
            item.price          = price
            item.stock_quantity = stock
            item.is_available   = available
            db.session.commit()
            flash(f"'{item.name}' updated successfully.", "success")
            return redirect(url_for("admin.items"))

    return render_template("admin/edit_item.html", item=item)


@admin_bp.route("/items/<int:item_id>/delete", methods=["POST"])
@admin_required
def delete_item(item_id):
    """Delete a menu item by ID."""
    item = db.session.get(MenuItem, item_id)
    if not item:
        abort(404)
    name = item.name
    db.session.delete(item)
    db.session.commit()
    flash(f"Menu item '{name}' has been deleted.", "warning")
    return redirect(url_for("admin.items"))


@admin_bp.route("/items/<int:item_id>/toggle", methods=["POST"])
@admin_required
def toggle_item(item_id):
    """Toggle the availability of a menu item."""
    item = db.session.get(MenuItem, item_id)
    if not item:
        abort(404)
    item.is_available = not item.is_available
    db.session.commit()
    status = "enabled" if item.is_available else "disabled"
    flash(f"'{item.name}' has been {status}.", "info")
    return redirect(url_for("admin.items"))


# ── Orders ────────────────────────────────────────────────────────────────────
@admin_bp.route("/orders")
@admin_required
def orders():
    """View all orders with optional date and status filters."""
    filter_date   = request.args.get("date", "")
    filter_status = request.args.get("status", "")

    query = Order.query.order_by(Order.order_date.desc())

    if filter_date:
        try:
            d = datetime.strptime(filter_date, "%Y-%m-%d").date()
            query = query.filter(
                Order.order_date.between(
                    datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc),
                    datetime.combine(d, datetime.max.time(), tzinfo=timezone.utc),
                )
            )
        except ValueError:
            flash("Invalid date format.", "warning")

    if filter_status:
        query = query.filter_by(payment_status=filter_status)

    all_orders = query.all()
    return render_template(
        "admin/orders.html",
        orders=all_orders,
        filter_date=filter_date,
        filter_status=filter_status,
    )


# ── Sales Report ──────────────────────────────────────────────────────────────
@admin_bp.route("/report")
@admin_required
def report():
    """
    Daily sales report for a selected date range (default: last 7 days).
    Shows per-day order count and revenue.
    """
    # Date range — default last 7 days
    end_date_str   = request.args.get("end",   date.today().strftime("%Y-%m-%d"))
    start_date_str = request.args.get("start", (date.today() - timedelta(days=6)).strftime("%Y-%m-%d"))

    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date   = datetime.strptime(end_date_str,   "%Y-%m-%d").date()
    except ValueError:
        start_date = date.today() - timedelta(days=6)
        end_date   = date.today()

    # Build day-by-day report
    report_data = []
    current = start_date
    while current <= end_date:
        day_start = datetime.combine(current, datetime.min.time(), tzinfo=timezone.utc)
        day_end   = datetime.combine(current, datetime.max.time(), tzinfo=timezone.utc)
        count  = Order.query.filter(Order.order_date.between(day_start, day_end)).count()
        revenue = db.session.query(func.sum(Order.total_amount)).filter(
            Order.order_date.between(day_start, day_end)
        ).scalar() or 0.0
        report_data.append({"date": current, "orders": count, "revenue": round(revenue, 2)})
        current += timedelta(days=1)

    total_orders  = sum(r["orders"]  for r in report_data)
    total_revenue = sum(r["revenue"] for r in report_data)

    # Top-selling items in the period
    top_items = (
        db.session.query(
            OrderItem.item_name,
            func.sum(OrderItem.quantity).label("total_qty"),
            func.sum(OrderItem.quantity * OrderItem.item_price).label("total_sales"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .filter(Order.order_date.between(
            datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc),
            datetime.combine(end_date,   datetime.max.time(), tzinfo=timezone.utc),
        ))
        .group_by(OrderItem.item_name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(10)
        .all()
    )

    return render_template(
        "admin/report.html",
        report_data=report_data,
        total_orders=total_orders,
        total_revenue=total_revenue,
        top_items=top_items,
        start_date=start_date_str,
        end_date=end_date_str,
    )


@admin_bp.route("/report/export")
@admin_required
def export_report():
    """Download sales data as a CSV file for the selected date range."""
    start_date_str = request.args.get("start", (date.today() - timedelta(days=6)).strftime("%Y-%m-%d"))
    end_date_str   = request.args.get("end",   date.today().strftime("%Y-%m-%d"))

    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date   = datetime.strptime(end_date_str,   "%Y-%m-%d").date()
    except ValueError:
        start_date = date.today() - timedelta(days=6)
        end_date   = date.today()

    # Fetch orders in range
    orders_in_range = (
        Order.query.filter(
            Order.order_date.between(
                datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc),
                datetime.combine(end_date,   datetime.max.time(), tzinfo=timezone.utc),
            )
        )
        .order_by(Order.order_date)
        .all()
    )

    # Write CSV to in-memory buffer
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Order ID", "User", "Date & Time", "Subtotal (₹)", "GST (₹)", "Total (₹)", "Status"])
    for o in orders_in_range:
        writer.writerow([
            o.id,
            o.user.username if o.user else "N/A",
            o.order_date.strftime("%Y-%m-%d %H:%M:%S"),
            f"{o.subtotal:.2f}",
            f"{o.gst_amount:.2f}",
            f"{o.total_amount:.2f}",
            o.payment_status,
        ])

    output.seek(0)
    filename = f"sales_report_{start_date_str}_to_{end_date_str}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
