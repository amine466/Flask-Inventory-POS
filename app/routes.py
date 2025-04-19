from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from .models import Category, Product, Sale, SaleItem
from flask import flash
from flask_login import login_required
from datetime import datetime, timedelta
import json
from . import db


bp = Blueprint('main', __name__)

@bp.route('/')
@login_required
def dashboard():
    categories_count = Category.query.count()
    products_count = Product.query.count()
    latest_sales = Sale.query.order_by(Sale.date.desc()).limit(5).all()

    # Get today's date range
    today = datetime.utcnow().date()
    start = datetime(today.year, today.month, today.day)
    end = start + timedelta(days=1)

    transactions_today = Sale.query.filter(Sale.date >= start, Sale.date < end).count()
    total_sales_today = db.session.query(db.func.sum(Sale.total)).filter(Sale.date >= start, Sale.date < end).scalar() or 0
    context = {
        "categories_count" : categories_count, 
        "products_count" : products_count,
        "transactions_today" : transactions_today,
        "total_sales_today" : total_sales_today,
        "latest_sales": latest_sales,
        "title": "Dashboard"
    }
    return render_template('dashboard.html', **context)

@bp.route('/categories')
@login_required
def categories():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    pagination = Category.query.paginate(page=page, per_page=per_page)
    start_index = (page - 1) * per_page
    context = {
        "pagination": pagination,
        "start_index": start_index,
        "title": "Categories"
    }
    return render_template('categories.html', **context)

@bp.route('/category/create', methods=['POST'])
@login_required
def create_category():
    name = request.form.get('name')

    existing = Category.query.filter_by(name=name).first()
    if existing:
        flash("Category name already exists.", "warning")
        return redirect(url_for('main.categories'))
    category = Category(name=name)
    db.session.add(category)

    try:    
        db.session.commit()
        flash("Category added successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash("Error adding category.", "danger")

    return redirect(url_for('main.categories'))

@bp.route('/category/update/<int:id>', methods=['POST'])
@login_required
def update_category(id):
    category = Category.query.get_or_404(id)
    name = request.form.get('name')

    if category.name != name:
        existing = Category.query.filter_by(name=name).first()
        if existing:
            flash("Category name already exists.", "warning")
            return redirect(url_for('main.categories'))
        
    try:
        category.name = name
        db.session.commit()
        flash("Category updated successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash("Error updating category.", "danger")

    return redirect(url_for('main.categories'))

@bp.route('/category/delete/<int:id>', methods=['POST'])
@login_required
def delete_category(id):
    category = Category.query.get_or_404(id)
    try:
        db.session.delete(category)
        db.session.commit()
        flash("Category deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash("Error deleting category.", "danger")
    return redirect(url_for('main.categories'))

@bp.route('/products')
@login_required
def products():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    pagination = Product.query.paginate(page=page, per_page=per_page)
    start_index = (page - 1) * per_page
    categories = Category.query.all()
    context = {
        "pagination": pagination,
        "start_index": start_index,
        "categories": categories,
        "title": "Products"
    }
    return render_template('products.html', **context)

@bp.route('/product/create', methods=['POST'])
@login_required
def create_product():
    name = request.form.get('name')
    sku = request.form.get('sku')
    price = request.form.get('price')
    quantity = request.form.get('quantity')
    category_id = request.form.get('category_id')
    
    if len(name) < 3 or len(name) > 100:
        flash("Product name must be between 3 and 100 characters.", "danger")
        return redirect(url_for('main.products'))

    if Product.query.filter((Product.name == name) | (Product.sku == sku)).first():
        flash("Product with this name or SKU already exists.", "warning")
        return redirect(url_for('main.products'))
    
    product = Product(name=name, sku=sku, price=float(price), quantity=quantity, category_id=category_id)
    db.session.add(product)
    try:
        db.session.commit()
        flash("Product added successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash("Error adding product.", "danger")
    return redirect(url_for('main.products'))
    
@bp.route('/product/update/<int:id>', methods=['POST'])
@login_required
def update_product(id):
    product = Product.query.get_or_404(id)

    name = request.form.get('name')
    sku = request.form.get('sku')
    category_id = request.form.get('category_id')
    quantity = request.form.get('quantity')
    price = request.form.get('price')

    if product.name != name or product.sku != sku:
        if Product.query.filter((Product.name == name) | (Product.sku == sku)).first():
            flash("Product with this name or SKU already exists.", "warning")
            return redirect(url_for('main.products'))
        
        if len(name) < 3 or len(name) > 100:
            flash("Product name must be between 3 and 100 characters.", "danger")
            return redirect(url_for('main.products'))

    product.name = name
    product.sku = sku
    product.category_id = category_id
    product.quantity = quantity
    product.price = float(price)

    try:
        db.session.commit()
        flash("Product updated successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash("Error updating product.", "danger")

    return redirect(url_for('main.products'))

@bp.route('/product/delete/<int:id>', methods=['POST'])
@login_required
def delete_product(id):
    product = Product.query.get_or_404(id)
    try:
        db.session.delete(product)
        db.session.commit()
        flash("Product deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash("Error deleting product.", "danger")
    return redirect(url_for('main.products'))

@bp.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    if request.method == 'POST':
        cart_data = request.form.get('cart_data')

        if not cart_data:
            flash("Cart is empty!", "danger")
            return redirect(url_for('main.checkout'))

        cart = json.loads(cart_data)

        if not cart:
            flash("Cart is empty!", "danger")
            return redirect(url_for('main.checkout'))

        total = 0
        sale = Sale(total=0)
        db.session.add(sale)
        db.session.flush()

        for item in cart:
            product = Product.query.get(item['id'])
            if not product:
                flash(f"Product with ID {item['id']} not found.", "danger")
                db.session.rollback()
                return redirect(url_for('main.checkout'))

            if product.quantity < item['quantity']:
                flash(f"Not enough stock for {product.name}. Available: {product.quantity}", "warning")
                db.session.rollback()
                return redirect(url_for('main.checkout'))

            product.quantity -= item['quantity']

            total += item['price'] * item['quantity']

            sale_item = SaleItem(
                sale_id=sale.id,
                product_id=product.id,
                quantity=item['quantity'],
                price=item['price']
            )
            db.session.add(sale_item)

        sale.total = total
        db.session.commit()

        flash(f"Sale recorded! Total: ${total:.2f}", "success")
        return redirect(url_for('main.checkout'))

    categories = Category.query.all()
    context = {
        "categories": categories,
        "title": "Point Of Sale"
    }
    return render_template('sales/checkout.html', **context)

@bp.route('/get-products/<int:category_id>')
@login_required
def get_products(category_id):
    products = Product.query.filter_by(category_id=category_id).all()
    product_list = [{'id': product.id, 'name': product.name} for product in products]
    return jsonify(product_list)

@bp.route('/product/<int:product_id>')
@login_required
def get_product(product_id):
    product = Product.query.get_or_404(product_id)
    return jsonify({'id': product.id, 'name': product.name, 'price': float(product.price)})

@bp.route('/sales')
@login_required
def sales():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    pagination = Sale.query.order_by(Sale.date.desc()).paginate(page=page, per_page=per_page)
    start_index = (page - 1) * per_page
    context = {
        "pagination": pagination,
        "start_index": start_index,
        "title": "Sales"
    }
    return render_template("sales/sales.html", **context)

@bp.route('/sales/<int:sale_id>')
@login_required
def get_sale_details(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    data = {
        "id": sale.id,
        "date": sale.date.strftime('%Y-%m-%d %H:%M'),
        "total": sale.total,
        "items": [
            {
                "product_name": item.product.name,
                "quantity": item.quantity,
                "price": item.price
            } for item in sale.items
        ]
    }
    return jsonify(data)

@bp.route('/sales/delete/<int:sale_id>', methods=['POST'])
@login_required
def delete_sale(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    SaleItem.query.filter_by(sale_id=sale.id).delete()
    try:
        db.session.delete(sale)
        db.session.commit()
        flash("Sale deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash("Error deleting sale.", "danger")
    return redirect(url_for('main.sales')) 