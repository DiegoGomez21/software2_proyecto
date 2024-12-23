from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponseBadRequest
from django.shortcuts import render, redirect
from django.contrib.auth import logout
from app.store_admin.models import Product, Provider
from app.customers.models import Order,Customer
import requests
from django.conf import settings
from datetime import datetime

def admin_required(function=None, login_url='/accounts/login/'):
    return user_passes_test(lambda u: u.is_superuser, login_url=login_url)(function)

@admin_required
def dashboard(request):
    return render(request, 'store_admin/dashboard.html')

@admin_required
def add_product(request):
    if request.method == 'POST':
        name = request.POST['name']
        description = request.POST['description']
        price = request.POST['price']
        quantity = request.POST['quantity']
        provider_id = request.POST['provider']
        image = request.FILES['image']

        provider = Provider.objects.get(id=provider_id)

        product = Product(name=name, description=description, price=price, quantity=quantity, provider=provider, image=image)
        product.save()

        return redirect('inventory')

    providers = Provider.objects.all()
    return render(request, 'store_admin/addProducts.html', {'providers': providers})

@admin_required
def inventory(request):
    products = Product.objects.all() 
    return render(request, 'store_admin/inventory.html', {'products': products})

@admin_required
def order_history(request):
    if request.method != 'GET':
        return HttpResponseBadRequest("Only GET requests are allowed.")

    api_url = [
        f"{settings.API_BASE_URL}/customers/api/orders/",
        f"http://20.197.225.198:8080/api/pedido/list"
    ]

    orders = []
    customers = set()

    # Parámetros del filtro
    selected_customer = request.GET.get('customer')
    selected_store = request.GET.get('sucursal')    
    selected_start_date = request.GET.get('start_date')
    selected_end_date = request.GET.get('end_date')
    selected_min_price = request.GET.get('min_price')
    selected_max_price = request.GET.get('max_price')

    for api in api_url:
        try:
            response = requests.get(api, timeout=5)  # Agregar timeout
            response.raise_for_status()
            api_orders = response.json()
            if isinstance(api_orders, list):  # Validar formato esperado
                orders.extend(api_orders)
            else:
                print(f"Respuesta inesperada de la API: {api}")
        except requests.RequestException as e:
            print(f"Error al conectar con la API {api}: {e}")
            # Continuar sin detenerse por fallos en una API

    # Obtener clientes únicos
    for order in orders:
        if 'customer_name' in order:
            customers.add(order['customer_name'])

    # Aplicar filtros
    if selected_customer:
        orders = [
            order for order in orders
            if selected_customer.lower() in (order.get('customer_name') or '').lower()
        ]

    if selected_store:
        orders = [
            order for order in orders
            if selected_store.lower() in (order.get('store') or '').lower()
        ]

    if selected_start_date:
        try:
            start_date_obj = datetime.strptime(selected_start_date.strip(), '%Y-%m-%d')
            orders = [
                order for order in orders
                if order.get('date') and datetime.strptime(order['date'], '%Y-%m-%d') >= start_date_obj
            ]
        except ValueError as e:
            print(f"Error al procesar fecha de inicio: {e}")

    if selected_end_date:
        try:
            end_date_obj = datetime.strptime(selected_end_date.strip(), '%Y-%m-%d')
            orders = [
                order for order in orders
                if order.get('date') and datetime.strptime(order['date'], '%Y-%m-%d') <= end_date_obj
            ]
        except ValueError as e:
            print(f"Error al procesar fecha de fin: {e}")

    if selected_min_price:
        try:
            min_price_val = float(selected_min_price)
            orders = [
                order for order in orders
                if float(order.get('total_price') or 0) >= min_price_val
            ]
        except ValueError:
            print("Error al procesar el precio mínimo.")

    if selected_max_price:
        try:
            max_price_val = float(selected_max_price)
            orders = [
                order for order in orders
                if float(order.get('total_price') or 0) <= max_price_val
            ]
        except ValueError:
            print("Error al procesar el precio máximo.")

    return render(request, 'store_admin/orders.html', {
        'orders': orders,
        'customers': customers,
        'selected_store': selected_store,
        'selected_customer': selected_customer,
        'selected_start_date': selected_start_date,
        'selected_end_date': selected_end_date,
        'selected_min_price': selected_min_price,
        'selected_max_price': selected_max_price,
    })

def exitAdmin(request):
    logout(request)
    return redirect('home')