def cart_count(request):
    cart = request.session.get("cart", {})
    return {"cart_count": sum(int(q) for q in cart.values())}
