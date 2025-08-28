from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from .cart import Cart
from .models import Product, Category, Order, OrderItem
from django.db import transaction
import stripe
from django.conf import settings
from django.http import JsonResponse
import json

# Create your views here.

def home(request):
    products = Product.objects.all()[:3]  # Show 3 featured products
    categories = Category.objects.all()
    return render(request, 'products/home.html', {
        'products': products,
        'categories': categories
    })

def product_detail(request, pk):
    product = Product.objects.get(pk=pk)
    return render(request, 'products/product_detail.html', {'product': product})

def product_list(request, category_slug=None):
    products = Product.objects.all()
    category = None
    
    if category_slug:
        category = Category.objects.get(slug=category_slug)
        products = products.filter(category=category)
    
    return render(request, 'products/product_list.html', {
        'products': products,
        'category': category
    })

def add_to_cart_view(request, product_id):
    cart = Cart(request)
    product = Product.objects.get(id=product_id)
    
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        cart.add(product=product, quantity=quantity)
        messages.success(request, 'Product added to cart!')
        return redirect('product_detail', pk=product_id)
    return redirect('product_list')

def cart_view(request):
    cart = Cart(request)
    return render(request, 'products/cart.html', {'cart': cart})

def checkout_view(request):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    
    if request.method == 'POST':
        try:
            # Get cart data from client-side
            cart_data = json.loads(request.POST.get('cart_data', '{}'))
            total_amount = int(float(request.POST.get('total_amount', 0)) * 100)  # Convert to cents
            
            # Create Stripe PaymentIntent
            intent = stripe.PaymentIntent.create(
                amount=total_amount,
                currency='aud',
                metadata={
                    'customer_email': request.POST.get('email'),
                    'customer_name': f"{request.POST.get('first_name')} {request.POST.get('last_name')}"
                }
            )
            
            # Create order in database
            with transaction.atomic():
                order = Order.objects.create(
                    first_name=request.POST['first_name'],
                    last_name=request.POST['last_name'],
                    email=request.POST['email'],
                    phone=request.POST['phone'],
                    address=request.POST['address'],
                    city=request.POST['city'],
                    postal_code=request.POST['postal_code'],
                    state=request.POST['state'],
                    total_price=total_amount / 100,
                    status='pending'
                )
                
                # Create order items from cart data
                for product_id, item in cart_data.items():
                    product = Product.objects.get(id=product_id)
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=item['quantity'],
                        price=item['price']
                    )
            
            return JsonResponse({
                'client_secret': intent.client_secret,
                'order_id': order.id
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return render(request, 'products/checkout.html', {
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY
    })

def order_confirmation(request, order_id):
    order = Order.objects.get(id=order_id)
    return render(request, 'products/order_confirmation.html', {'order': order})
