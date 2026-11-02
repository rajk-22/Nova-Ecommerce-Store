import json
from decimal import Decimal
import razorpay
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .models import Category, Product, Order, OrderItem

def _cart(request):
    return request.session.setdefault("cart", {})

def _cart_items(request):
    cart = _cart(request)
    products = Product.objects.filter(id__in=cart.keys(), active=True)
    rows, total = [], Decimal("0.00")
    for product in products:
        quantity = int(cart.get(str(product.id), 0))
        if quantity > 0:
            line_total = product.price * quantity
            rows.append({"product": product, "quantity": quantity, "line_total": line_total})
            total += line_total
    return rows, total

def home(request):
    featured = Product.objects.filter(active=True, featured=True)[:8]
    categories = Category.objects.all()[:6]
    return render(request, "store/home.html", {"featured": featured, "categories": categories})

def product_list(request):
    products = Product.objects.filter(active=True).select_related("category")
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    if query:
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))
    if category:
        products = products.filter(category__slug=category)
    return render(request, "store/product_list.html", {
        "products": products, "categories": Category.objects.all(),
        "selected_category": category, "query": query
    })

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, active=True)
    return render(request, "store/product_detail.html", {"product": product})

@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id, active=True)
    cart = _cart(request)
    key = str(product.id)
    current = int(cart.get(key, 0))
    if current + 1 > product.stock:
        messages.error(request, "Sorry, there is not enough stock available.")
    else:
        cart[key] = current + 1
        request.session.modified = True
        messages.success(request, f"{product.name} added to your cart.")
    return redirect(request.POST.get("next") or "cart")

def cart_view(request):
    rows, total = _cart_items(request)
    return render(request, "store/cart.html", {"rows": rows, "total": total})

@require_POST
def update_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id, active=True)
    quantity = int(request.POST.get("quantity", 1))
    cart = _cart(request)
    if quantity <= 0:
        cart.pop(str(product_id), None)
    elif quantity <= product.stock:
        cart[str(product_id)] = quantity
    else:
        messages.error(request, "Requested quantity exceeds available stock.")
    request.session.modified = True
    return redirect("cart")

@require_POST
def remove_from_cart(request, product_id):
    cart = _cart(request)
    cart.pop(str(product_id), None)
    request.session.modified = True
    return redirect("cart")

@login_required
def checkout(request):
    rows, total = _cart_items(request)
    if not rows:
        messages.info(request, "Your cart is empty.")
        return redirect("product_list")
    if request.method == "POST":
        if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
            messages.error(request, "Add your Razorpay TEST keys to the .env file first.")
            return redirect("checkout")
        for row in rows:
            if row["quantity"] > row["product"].stock:
                messages.error(request, f"Insufficient stock for {row['product'].name}.")
                return redirect("cart")
        order = Order.objects.create(
            user=request.user,
            full_name=request.POST.get("full_name", "").strip(),
            email=request.POST.get("email", "").strip(),
            phone=request.POST.get("phone", "").strip(),
            address=request.POST.get("address", "").strip(),
            city=request.POST.get("city", "").strip(),
            postal_code=request.POST.get("postal_code", "").strip(),
            total=total,
        )
        for row in rows:
            OrderItem.objects.create(
                order=order, product=row["product"], product_name=row["product"].name,
                price=row["product"].price, quantity=row["quantity"]
            )
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        rp_order = client.order.create({
            "amount": int(total * 100), "currency": "INR",
            "receipt": f"nova-{order.id}",
            "notes": {"local_order_id": str(order.id)}
        })
        order.razorpay_order_id = rp_order["id"]
        order.save(update_fields=["razorpay_order_id"])
        return render(request, "store/payment.html", {
            "order": order, "razorpay_order_id": rp_order["id"],
            "razorpay_key": settings.RAZORPAY_KEY_ID,
            "amount_paise": int(total * 100),
        })
    return render(request, "store/checkout.html", {"rows": rows, "total": total})

@login_required
@require_POST
def verify_payment(request):
    try:
        data = json.loads(request.body)
        order = get_object_or_404(Order, id=int(data["local_order_id"]), user=request.user)
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        client.utility.verify_payment_signature({
            "razorpay_order_id": data["razorpay_order_id"],
            "razorpay_payment_id": data["razorpay_payment_id"],
            "razorpay_signature": data["razorpay_signature"],
        })
        if order.razorpay_order_id != data["razorpay_order_id"]:
            return JsonResponse({"ok": False, "error": "Order mismatch."}, status=400)
        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=order.pk)
            if order.status != "PAID":
                for item in order.items.select_related("product"):
                    product = Product.objects.select_for_update().get(pk=item.product_id)
                    if product.stock < item.quantity:
                        order.status = "FAILED"
                        order.save(update_fields=["status"])
                        return JsonResponse({"ok": False, "error": "Stock changed. Contact store support."}, status=409)
                    product.stock -= item.quantity
                    product.save(update_fields=["stock"])
                order.status = "PAID"
                order.razorpay_payment_id = data["razorpay_payment_id"]
                order.save(update_fields=["status", "razorpay_payment_id"])
        request.session["cart"] = {}
        return JsonResponse({"ok": True, "redirect": f"/orders/{order.id}/"})
    except Exception:
        return JsonResponse({"ok": False, "error": "Payment verification failed. Please contact support."}, status=400)

@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user)
    return render(request, "store/order_history.html", {"orders": orders})

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, "store/order_detail.html", {"order": order})

def register(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("home")
    else:
        form = UserCreationForm()
    return render(request, "store/register.html", {"form": form})
