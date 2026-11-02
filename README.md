# NOVA — Django E-commerce Store

A responsive portfolio e-commerce project built with Django, SQLite, HTML, CSS, JavaScript and Razorpay Checkout (test mode).

## 1. Requirements
- Python 3.10+
- VS Code
- Internet connection for Google Fonts, product image URLs and Razorpay Checkout

## 2. Open the project
Extract the ZIP, open the `nova_cart` folder in VS Code, then open the VS Code terminal.

Windows PowerShell:
```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
py manage.py migrate
py manage.py createsuperuser
py manage.py runserver
```
Open http://127.0.0.1:8000/

If PowerShell blocks activation, run:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

## 3. Add categories and products
Go to http://127.0.0.1:8000/admin/ and log in with the superuser account.
- Add categories first.
- Add products and select a category.
- Add a public image URL, price, stock and description.
- Mark a few products as Featured.

The Django admin is your store management panel. Never give customers staff/admin access.

## 4. Razorpay test mode
1. Create a Razorpay account and open its Test Mode dashboard.
2. Generate Test API Key ID and Key Secret.
3. Put them in `.env`:
```
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxx
RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxx
```
4. Restart the Django server.
5. Sign up as a customer, add products to the cart, and checkout.
6. Use Razorpay's current official test payment details from its documentation/dashboard. Do not use real card details or enable live mode for this demo.

## 5. Important routes
- `/` Home
- `/products/` Product catalogue
- `/cart/` Cart
- `/checkout/` Checkout (login required)
- `/orders/` Customer order history
- `/admin/` Django admin

## 6. Portfolio / production notes
This is a learning and portfolio starter, not a production-ready commerce system. Before public deployment:
- Set a strong `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=False`, and correct `ALLOWED_HOSTS`.
- Use PostgreSQL and HTTPS.
- Configure secure cookies, logging, backups, email and proper deployment static-file handling.
- Add payment webhooks and reconciliation. A customer browser callback alone is not a complete payment lifecycle.
- Add inventory reservation/locking and idempotent webhook handling for high-concurrency sales.
- Add tests for permissions, cart stock limits, order totals and payment verification.
- Add server-side validation for all checkout fields and order status transitions.
- Consider moving cart persistence from session-only storage to a database cart for cross-device persistence.

## 7. What to explain in an interview
- Django models represent Category, Product, Order and OrderItem.
- Django authentication handles registration and login.
- Sessions keep the shopping cart between page visits in the same browser.
- Django admin provides protected product and order management.
- Razorpay creates a server-side payment order; the server verifies the payment signature.
- SQLite is used locally; production apps commonly use PostgreSQL.
