from django.shortcuts import render, redirect, get_object_or_404
# from django.contrib.auth.forms import UserCreationForm # No longer needed
from .forms import ShopOwnerSignUpForm, CustomerSignUpForm, CustomAuthenticationForm, ProductForm, ReviewForm # Import the new forms and CustomAuthenticationForm
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout # Import authenticate and logout
from django.contrib.auth.decorators import login_required # For restricting access
from django.conf import settings # To get Supabase credentials
from supabase import create_client, Client # Supabase client
import os # For path manipulation if needed
import uuid # For generating unique filenames
from .models import FoodStall, Product, Order, OrderItem, Payment, Notification, Review # Ensure Product, Order, and Payment are imported
from urllib.parse import urlparse # For parsing image URL to get path
from django.urls import reverse # For reverse URL resolution
from django.http import JsonResponse, HttpResponse # For potential AJAX responses, though redirecting for now
from django.utils import timezone # For current date
from django.db import transaction # For atomic operations
from django.views.decorators.http import require_POST
from django.db.utils import IntegrityError # For IntegrityError
from datetime import date, timedelta # For date calculations
from django.db.models import Sum, Count, Avg # Import Sum, Count, and Avg for aggregation
from decimal import Decimal # Import Decimal for financial calculations

# Helper function to delete image from Supabase Storage
def _delete_supabase_image(image_url):
    if not image_url or not settings.SUPABASE_URL or not settings.SUPABASE_KEY or not settings.SUPABASE_BUCKET:
        return
    try:
        # Attempt to parse the image_url to extract the path
        # Public URLs are typically SUPABASE_URL/storage/v1/object/public/BUCKET_NAME/path/to/file.jpg
        # We need to extract 'path/to/file.jpg'
        url_path_part = urlparse(image_url).path
        # Expected path format in Supabase URL: /storage/v1/object/public/your-bucket-name/actual-file-path
        # We need to strip the prefix to get the 'actual-file-path'
        prefix_to_strip = f"/storage/v1/object/public/{settings.SUPABASE_BUCKET}/"
        if url_path_part.startswith(prefix_to_strip):
            storage_path = url_path_part[len(prefix_to_strip):]
            if storage_path:
                supabase_client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
                supabase_client.storage.from_(settings.SUPABASE_BUCKET).remove([storage_path])
                # print(f"Successfully requested deletion of {storage_path} from Supabase.") # For debugging
    except Exception as e:
        # Log this error or handle it as appropriate for your application
        print(f"Error deleting image from Supabase: {e}") # For debugging

@login_required
def add_item_view(request):
    if request.user.user_type != 'shop':
        messages.error(request, "You are not authorized to add items.")
        return redirect('home')

    try:
        food_stall_instance = FoodStall.objects.get(owner=request.user)
    except FoodStall.DoesNotExist:
        messages.error(request, "Food stall not found for your account. Please set up your stall first.")
        return redirect('dashboard')

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.food_stall = food_stall_instance
            
            image_file = request.FILES.get('product_image')
            if image_file:
                try:
                    supabase_client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
                    file_extension = os.path.splitext(image_file.name)[1]
                    file_name = f"{uuid.uuid4()}{file_extension}"
                    bucket_path = f"{food_stall_instance.owner.id}/{file_name}"
                    image_bytes = image_file.read()
                    supabase_client.storage.from_(settings.SUPABASE_BUCKET).upload(
                        path=bucket_path,
                        file=image_bytes,
                        file_options={"content-type": image_file.content_type}
                    )
                    public_url_response = supabase_client.storage.from_(settings.SUPABASE_BUCKET).get_public_url(bucket_path)
                    product.image_url = public_url_response
                except Exception as e:
                    messages.error(request, f"Error uploading image to Supabase: {e}")
                    return render(request, 'add-item.html', {
                        'form': form, 
                        'page_title': 'Add New Item',
                        'food_stall_name': food_stall_instance.stall_name
                    })
            
            product.save()
            messages.success(request, f'Product "{product.product_name}" added successfully!')
            return redirect('food_list')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ProductForm()
    
    return render(request, 'add-item.html', {
        'form': form, 
        'page_title': 'Add New Item',
        'food_stall_name': food_stall_instance.stall_name
    })

@login_required
def edit_product_view(request, product_id):
    if request.user.user_type != 'shop':
        messages.error(request, "You are not authorized to edit items.")
        return redirect('home')

    try:
        food_stall_instance = FoodStall.objects.get(owner=request.user)
    except FoodStall.DoesNotExist:
        messages.error(request, "Food stall not found for your account.")
        return redirect('dashboard')

    product = get_object_or_404(Product, pk=product_id, food_stall=food_stall_instance)
    old_image_url = product.image_url

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            updated_product = form.save(commit=False)
            new_image_file = request.FILES.get('product_image')
            if new_image_file:
                if old_image_url:
                    _delete_supabase_image(old_image_url)
                try:
                    supabase_client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
                    file_extension = os.path.splitext(new_image_file.name)[1]
                    file_name = f"{uuid.uuid4()}{file_extension}"
                    bucket_path = f"{food_stall_instance.owner.id}/{file_name}"
                    image_bytes = new_image_file.read()
                    supabase_client.storage.from_(settings.SUPABASE_BUCKET).upload(
                        path=bucket_path,
                        file=image_bytes,
                        file_options={"content-type": new_image_file.content_type}
                    )
                    public_url_response = supabase_client.storage.from_(settings.SUPABASE_BUCKET).get_public_url(bucket_path)
                    updated_product.image_url = public_url_response
                except Exception as e:
                    messages.error(request, f"Error uploading new image to Supabase: {e}")
                    return render(request, 'edit-product.html', {
                        'form': form, 
                        'product': product, 
                        'page_title': f'Edit {product.product_name}',
                        'food_stall_name': food_stall_instance.stall_name
                    })
            updated_product.save()
            messages.success(request, f'Product "{updated_product.product_name}" updated successfully!')
            return redirect('food_list')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'edit-product.html', {
        'form': form, 
        'product': product, 
        'page_title': f'Edit {product.product_name}',
        'food_stall_name': food_stall_instance.stall_name
    })

@login_required
def delete_product_view(request, product_id):
    if request.user.user_type != 'shop':
        messages.error(request, "You are not authorized to delete items.")
        return redirect('home')

    try:
        food_stall_instance = FoodStall.objects.get(owner=request.user)
    except FoodStall.DoesNotExist:
        messages.error(request, "Food stall not found for your account.")
        return redirect('dashboard')

    product = get_object_or_404(Product, pk=product_id, food_stall=food_stall_instance)

    if request.method == 'POST':
        product_name = product.product_name # Get name before deleting
        image_url_to_delete = product.image_url

        product.delete() # Delete product from DB

        if image_url_to_delete: # Delete image from Supabase
            _delete_supabase_image(image_url_to_delete)
            
        messages.success(request, f'Product "{product_name}" and its image have been deleted successfully.')
        return redirect('food_list')
    
    # GET request: show confirmation page
    return render(request, 'delete-product-confirm.html', {'product': product})

def dashboard_view(request):
    if not request.user.is_authenticated or request.user.user_type != 'shop':
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')

    food_stall = None
    running_orders_count = 0
    completed_orders_count = 0
    total_sales_amount = Decimal('0.00')

    try:
        food_stall = FoodStall.objects.get(owner=request.user)
        
        # Calculate running orders
        running_orders_count = Order.objects.filter(
            food_stall=food_stall,
            status__in=['Pending', 'Preparing', 'Ready']
        ).count()
        
        # Calculate completed orders
        completed_orders_queryset = Order.objects.filter(
            food_stall=food_stall,
            status='Completed'
        )
        completed_orders_count = completed_orders_queryset.count()
        
        # Calculate total sales from completed orders
        sales_aggregation = completed_orders_queryset.aggregate(total_sales=Sum('total_price'))
        total_sales_amount = sales_aggregation['total_sales'] if sales_aggregation['total_sales'] is not None else Decimal('0.00')

    except FoodStall.DoesNotExist:
        messages.warning(request, "Your food stall information is not set up yet. Some features might be limited.")

    context = {
        'current_user': request.user,
        'food_stall': food_stall,
        'running_orders_count': running_orders_count,
        'completed_orders_count': completed_orders_count,
        'total_sales_amount': total_sales_amount,
        'page_title': "Dashboard - Golden Bites"
    }
    return render(request, 'dashboard.html', context)

def favorites_view(request):
    return render(request, 'favorites.html')

@login_required
def food_list_view(request):
    if request.user.user_type != 'shop':
        messages.error(request, "You are not authorized to view this page.")
        return redirect('home') # Or wherever non-shop users should go

    try:
        food_stall_instance = FoodStall.objects.get(owner=request.user)
    except FoodStall.DoesNotExist:
        messages.error(request, "Food stall not found for your account. Please set up your stall first.")
        # Redirect to a page where they can create/manage their stall, or just dashboard
        return redirect('dashboard') 

    # Get all products for this food stall
    products_queryset = Product.objects.filter(food_stall=food_stall_instance).order_by('product_name')

    # Get unique categories for the filter tabs for this stall's products
    # Ensure that we only get categories that actually exist for this stall's products
    stall_categories_from_db = products_queryset.values_list('category', flat=True).distinct()
    
    # Normalize, ensure uniqueness, and sort categories
    unique_normalized_categories = set()
    for cat in stall_categories_from_db:
        if cat: # Ensure category is not None or empty
            normalized_cat = cat.strip().title() # Remove whitespace, convert to title case
            if normalized_cat: # Ensure not empty after stripping
                unique_normalized_categories.add(normalized_cat)
    
    categories_for_tabs = sorted(list(unique_normalized_categories))

    selected_category = request.GET.get('category', 'All') # Default to 'All'

    if selected_category != 'All':
        products_to_display = products_queryset.filter(category=selected_category)
    else:
        products_to_display = products_queryset # Show all products if 'All' or no category is selected

    context = {
        'products': products_to_display,
        'categories': categories_for_tabs, # Categories for the tabs
        'selected_category': selected_category,
        'food_stall_name': food_stall_instance.stall_name, # For display in template
        'total_items': products_to_display.count()
    }
    return render(request, 'food-list.html', context)

def forgot_password_view(request):
    return render(request, 'forgot-password.html')

@login_required # Or remove if home is accessible to non-loggedIn users with different content
def home_view(request):
    user_first_name = request.user.first_name if request.user.is_authenticated else "Guest"
    
    all_products = Product.objects.select_related('food_stall').all().order_by('product_name')

    # Define all categories that should always be displayed
    ALL_DISPLAY_CATEGORIES = [
        'Breakfast', 'Lunch', 'Dinner', 'Chicken', 'Pork', 'Beef', 
        'Pasta', 'Rice', 'Snacks', 'Drinks & Beverages'
    ]

    selected_category = request.GET.get('category')
    products_to_display = all_products

    if selected_category and selected_category != 'All':
        products_to_display = all_products.filter(category=selected_category)
    
    recommended_products = products_to_display[:6]

    context = {
        'user_first_name': user_first_name,
        'categories': ALL_DISPLAY_CATEGORIES, # Use the complete list for display
        'selected_category_param': selected_category, 
        'products': products_to_display, 
        'recommended_products': recommended_products, # This will also be filtered by category if one is selected
        'page_title': "Home - Golden Bites"
    }
    return render(request, 'home.html', context)

def index_view(request):
    return render(request, 'index.html')

@login_required
def notifications_view(request):
    # Fetch all notifications for the logged-in user, newest first
    user_notifications = Notification.objects.filter(user=request.user).order_by('-timestamp')
    today = date.today()
    yesterday = today - timedelta(days=1)
    # Fetch all completed orders for the user
    completed_orders = Order.objects.filter(customer=request.user, status='Completed').order_by('-order_time')
    # Build review lookup for (product_id, order_id)
    user_reviews = Review.objects.filter(customer=request.user, order_id__in=completed_orders.values_list('id', flat=True))
    review_lookup = {}
    for review in user_reviews:
        key = f'{review.product_id}_{review.order_id}'
        review_lookup[key] = review
    context = {
        'notifications': user_notifications,
        'completed_orders': completed_orders,
        'review_lookup': review_lookup,
        'page_title': "Notifications - Golden Bites",
        'today_date': today,
        'yesterday_date': yesterday
    }
    return render(request, 'notifications.html', context)

def order_details_view(request):
    cart = request.session.get('cart', {})
    cart_items = []
    total_cart_price = Decimal('0.00')

    for product_id, item_data in cart.items():
        # Ensure price is a Decimal for calculations
        price = Decimal(str(item_data.get('price', '0.00')))
        quantity = int(item_data.get('quantity', 0))
        item_total = price * quantity
        
        cart_items.append({
            'id': product_id,
            'name': item_data.get('name', 'Unknown Product'),
            'stall_name': item_data.get('stall_name', 'N/A'),
            'price': price,
            'quantity': quantity,
            'image_url': item_data.get('image_url', ''),
            'item_total': item_total
        })
        total_cart_price += item_total

    context = {
        'cart_items': cart_items,
        'total_cart_price': total_cart_price,
        'page_title': "Order Details"
    }
    return render(request, 'order-details.html', context)

@login_required
def add_to_cart_view(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(Product.objects.select_related('food_stall'), pk=product_id)
        quantity = int(request.POST.get('quantity', 1))
        new_item_stall_id = product.food_stall.owner_id if product.food_stall else None

        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if quantity < 1:
            message_text = "Quantity must be at least 1."
            if is_ajax:
                return JsonResponse({'success': False, 'error': message_text}, status=400)
            else:
                messages.error(request, message_text)
                return redirect(reverse('product_detail', args=[product_id]))

        cart = request.session.get('cart', {})
        cart_stall_id = request.session.get('cart_stall_id')

        if cart and cart_stall_id is not None and new_item_stall_id != cart_stall_id:
            try:
                current_stall_in_cart = FoodStall.objects.get(owner_id=cart_stall_id) 
                stall_name_in_cart = current_stall_in_cart.stall_name
                message_text = f"Your cart contains items from '{stall_name_in_cart}'. You can only order from one stall at a time. Please clear your cart or complete that order first."
            except FoodStall.DoesNotExist:
                 message_text = "Your cart contains items from a different stall. You can only order from one stall at a time. Please clear your cart or complete that order first."
            
            if is_ajax:
                return JsonResponse({'success': False, 'error': message_text, 'action_required': 'clear_cart'}, status=400)
            else:
                messages.error(request, message_text)
                return redirect(reverse('product_detail', args=[product_id]))

        product_id_str = str(product.id) 

        cart_item = {
            'quantity': quantity,
            'name': product.product_name,
            'price': str(product.unit_price), 
            'image_url': product.image_url if product.image_url else '',
            'stall_name': product.food_stall.stall_name if product.food_stall else 'N/A',
            'stall_id': new_item_stall_id 
        }
        
        cart[product_id_str] = cart_item
        request.session['cart'] = cart
        
        if not cart_stall_id or new_item_stall_id == cart_stall_id:
            request.session['cart_stall_id'] = new_item_stall_id

        message_text = f"'{product.product_name}' has been added to your cart."
        if is_ajax:
            return JsonResponse({'success': True, 'message': message_text})
        else:
            messages.success(request, message_text)
            return redirect('order_details') 
    else:
        # Handle GET or other methods if needed, or raise error
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)
        else:
            messages.error(request, "Invalid request.")
            return redirect('home')

@login_required # Or at least ensure session exists
def update_cart_item_quantity_view(request, product_id):
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        product_id_str = str(product_id)
        new_quantity = int(request.POST.get('quantity', 1))
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if product_id_str in cart:
            original_quantity = cart[product_id_str]['quantity'] # Store original quantity for potential revert
            if new_quantity > 0:
                cart[product_id_str]['quantity'] = new_quantity
                request.session['cart'] = cart
                return JsonResponse({'success': True, 'message': 'Quantity updated.'})
            else: # Quantity is 0 or less, effectively removing the item
                if is_ajax:
                    del cart[product_id_str]
                    request.session['cart'] = cart
                    if not cart: # If cart is now empty
                        if 'cart_stall_id' in request.session:
                            del request.session['cart_stall_id']
                    return JsonResponse({'success': True, 'message': 'Item removed from cart.', 'item_removed': True})
                else:
                    # For non-AJAX, delegate to the full remove view which handles messages and redirect
                    return remove_from_cart_view(request, product_id) 
        else:
            return JsonResponse({'success': False, 'error': 'Item not in cart.', 'original_quantity': 0}, status=404)
    return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=400)

@login_required # Or at least ensure session exists
def remove_from_cart_view(request, product_id):
    # This can be called via POST or internally from update_cart_item_quantity_view
    cart = request.session.get('cart', {})
    product_id_str = str(product_id)

    if product_id_str in cart:
        del cart[product_id_str]
        request.session['cart'] = cart
        if not cart: # If cart is now empty
            if 'cart_stall_id' in request.session:
                del request.session['cart_stall_id']
        messages.success(request, "Item removed from cart.") # For redirect scenario
        # If called via AJAX, client might prefer no redirect
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Item removed.'})
        return redirect('order_details') # For non-AJAX calls or if delegation occurs
    else:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Item not in cart.'}, status=404)
        messages.error(request, "Item not found in cart.")
        return redirect('order_details')

def order_summary_view(request):
    return render(request, 'order-summary.html')

@login_required
def order_tracking_view(request):
    order = None
    current_status_index = -1
    status_sequence = ['Pending', 'Preparing', 'Ready', 'Completed']

    # Try to find the latest unacknowledged active/completed order first
    order = Order.objects.filter(
        customer=request.user,
        status__in=['Pending', 'Preparing', 'Ready', 'Completed'], # Active statuses + Completed
    ).exclude(
        status='Completed',
        customer_acknowledged_at__isnull=False # Exclude completed orders that ARE acknowledged
    ).order_by('-order_time').first()

    # If no such order, it means either:
    # 1. No orders at all.
    # 2. All 'Completed' orders have been acknowledged, and no other active orders exist.
    # In this scenario, for the "reset" effect, we effectively treat it as no current order to track actively.
    # The template will show "No order found" if 'order' remains None.

    if order:
        try:
            current_status_index = status_sequence.index(order.status)
        except ValueError:
            pass # Status not in sequence (e.g., Cancelled, though our query filters for specific ones)

    context = {
        'order': order,
        'status_sequence': status_sequence,
        'current_status_index': current_status_index,
        'page_title': "Track Your Order"
    }
    return render(request, 'order-tracking.html', context)

@login_required
def orders_view(request):
    if request.user.user_type != 'shop':
        messages.error(request, "You are not authorized to view this page.")
        return redirect('home')

    try:
        food_stall = FoodStall.objects.get(owner=request.user)
    except FoodStall.DoesNotExist:
        messages.error(request, "No food stall found for your account.")
        return redirect('dashboard')

    # Group orders by status
    pending_orders = Order.objects.filter(food_stall=food_stall, status='Pending').order_by('-order_time')
    preparing_orders = Order.objects.filter(food_stall=food_stall, status='Preparing').order_by('-order_time')
    ready_orders = Order.objects.filter(food_stall=food_stall, status='Ready').order_by('-order_time')
    completed_orders = Order.objects.filter(food_stall=food_stall, status='Completed').order_by('-order_time')
    cancelled_orders = Order.objects.filter(food_stall=food_stall, status='Cancelled').order_by('-order_time')

    context = {
        'pending_orders': pending_orders,
        'preparing_orders': preparing_orders,
        'ready_orders': ready_orders,
        'completed_orders': completed_orders,
        'cancelled_orders': cancelled_orders,
        'food_stall': food_stall,
        'page_title': "Orders - Golden Bites"
    }
    return render(request, 'orders.html', context)

@login_required
def overview_view(request):
    if not request.user.is_authenticated or request.user.user_type != 'shop':
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')

    food_stall = None
    total_sales = Decimal('0.00')
    total_revenue = Decimal('0.00') # Assuming same as sales for now
    total_completed_orders = 0
    total_items_sold = 0
    top_items = []
    recent_orders = []

    try:
        food_stall = FoodStall.objects.get(owner=request.user)

        # Calculate Total Sales and Total Completed Orders
        completed_orders_qs = Order.objects.filter(food_stall=food_stall, status='Completed')
        sales_aggregation = completed_orders_qs.aggregate(sum_sales=Sum('total_price'))
        total_sales = sales_aggregation['sum_sales'] if sales_aggregation['sum_sales'] is not None else Decimal('0.00')
        total_revenue = total_sales # Assuming revenue is same as sales
        total_completed_orders = completed_orders_qs.count()

        # Calculate Total Items Sold
        items_sold_aggregation = OrderItem.objects.filter(
            order__food_stall=food_stall,
            order__status='Completed'
        ).aggregate(sum_items=Sum('quantity'))
        total_items_sold = items_sold_aggregation['sum_items'] if items_sold_aggregation['sum_items'] is not None else 0
        
        # Get Top Selling Items (Top 3)
        top_items = Product.objects.filter(
            orderitem__order__food_stall=food_stall,
            orderitem__order__status='Completed'
        ).annotate(
            total_sold=Sum('orderitem__quantity')
        ).filter(total_sold__gt=0).order_by('-total_sold')[:3]

        # Get Recent Orders (Last 3)
        recent_orders = Order.objects.filter(food_stall=food_stall).order_by('-order_time')[:3]

    except FoodStall.DoesNotExist:
        messages.warning(request, "Food stall not found. Some overview data may be unavailable.")
    except Exception as e:
        messages.error(request, f"An error occurred while fetching overview data: {e}")
        print(f"Error in overview_view: {e}") # For server logs

    context = {
        'page_title': "Overview - Golden Bites",
        'food_stall_name': food_stall.stall_name if food_stall else "Your Shop",
        'total_sales': total_sales,
        'total_revenue': total_revenue,
        'total_completed_orders': total_completed_orders,
        'total_items_sold': total_items_sold,
        'top_items': top_items,
        'recent_orders': recent_orders,
    }
    return render(request, 'overview.html', context)

def payment_view(request):
    cart = request.session.get('cart', {})
    cart_items_summary = []
    total_cart_price = Decimal('0.00')
    item_count = 0

    for product_id, item_data in cart.items():
        price = Decimal(str(item_data.get('price', '0.00')))
        quantity = int(item_data.get('quantity', 0))
        item_total = price * quantity
        
        cart_items_summary.append({
            'id': product_id,
            'name': item_data.get('name', 'Unknown Product'),
            'quantity': quantity,
            'price_per_item': price,
            'item_total': item_total
        })
        total_cart_price += item_total
        item_count += quantity

    if not cart:
        messages.error(request, "Your cart is empty. Please add items before proceeding to payment.")
        return redirect('order_details')

    # Generate a simple random queue number (for display only, not cryptographically secure)
    # Example: S1234, A5678. First letter + 4 digits.
    random_letter = chr(ord('A') + uuid.uuid4().int % 26) # Random letter A-Z
    random_digits = str(uuid.uuid4().int % 10000).zfill(4) # Random 4 digits
    queue_number = f"{random_letter}{random_digits}"

    current_date_formatted = timezone.now().strftime("%m · %d · %Y")
    user_email = request.user.email if request.user.is_authenticated else "guest@example.com"

    context = {
        'cart_items_summary': cart_items_summary, 
        'total_cart_price': total_cart_price,
        'item_count': item_count,
        'page_title': "Payment", # Browser tab title
        'header_title': "Order Details", # Title in the top bar as per screenshot
        'queue_number': queue_number,
        'current_date_formatted': current_date_formatted,
        'user_email': user_email,
    }
    return render(request, 'payment.html', context)

def policy_view(request):
    return render(request, 'policy.html')

def policy_admin_view(request):
    return render(request, 'policy-admin.html')

def product_detail_view(request, product_id):
    product = get_object_or_404(Product.objects.select_related('food_stall'), pk=product_id)
    # These attributes might be from the model or set elsewhere, retaining them for now.
    is_popular_tag = getattr(product, 'is_popular', True) 
    orders_display = getattr(product, 'total_orders', 2000)

    # Get sorting option from request query parameters
    sort_option = request.GET.get('sort_by', 'most_recent') # Default to 'most_recent'

    # Base queryset for reviews related to the current product
    reviews_queryset = Review.objects.filter(product=product).select_related('customer')

    # Apply sorting based on the sort_option
    if sort_option == 'highest_rating':
        reviews = reviews_queryset.order_by('-rating', '-created_at') # Primary sort by rating desc, secondary by date desc
    elif sort_option == 'lowest_rating':
        reviews = reviews_queryset.order_by('rating', '-created_at')  # Primary sort by rating asc, secondary by date desc
    elif sort_option == 'most_recent': 
        reviews = reviews_queryset.order_by('-created_at')
    else: # Fallback to 'most_recent' if an invalid sort_option is provided
        reviews = reviews_queryset.order_by('-created_at')
        sort_option = 'most_recent' # Explicitly set sort_option to the fallback for context

    # Calculate review statistics using Django ORM aggregation
    review_stats = reviews_queryset.aggregate(
        total_reviews_val=Count('id'),
        average_rating_val=Avg('rating')
    )
    
    total_reviews = review_stats.get('total_reviews_val', 0)
    average_rating = review_stats.get('average_rating_val')

    if average_rating is not None:
        average_rating = round(average_rating, 1) # Round to one decimal place
    else:
        average_rating = 0.0 # Default if no reviews or ratings

    # Calculate rating distribution (e.g., count of 5-star, 4-star, etc., reviews)
    rating_distribution_query = reviews_queryset.values('rating').annotate(count=Count('id')).order_by('-rating')
    
    # Initialize rating_distribution_dict with all possible ratings (1-5) having a count of 0
    rating_distribution_dict = {i: 0 for i in range(1, 6)}
    for item in rating_distribution_query:
        if item['rating'] is not None: # Ensure rating is not None (e.g. for reviews without a rating value)
            rating_distribution_dict[item['rating']] = item['count']
            
    context = {
        'product': product,
        'food_stall_name': product.food_stall.stall_name if product.food_stall else "Golden Bites",
        'is_popular_tag': is_popular_tag,
        'orders_display': orders_display,
        'page_title': product.product_name,
        'current_page_name': request.resolver_match.url_name,
        
        'reviews': reviews,  # Sorted list of reviews
        'total_reviews': total_reviews,
        'average_rating': average_rating,
        'rating_distribution': rating_distribution_dict, # Dict with rating counts, e.g., {5: 10, 4: 8, ...}
        'current_sort_option': sort_option, # To highlight the active sort option in the template
        'sort_options': { # To generate sort links/dropdown in the template
            'most_recent': 'Most Recent',
            'highest_rating': 'Highest Rating',
            'lowest_rating': 'Lowest Rating',
        }
    }
    return render(request, 'product-detail.html', context)

@login_required # Or remove if shops list is public
def shops_list_view(request):
    # Fetch all food stalls. You might want to add ordering or filtering.
    # For example, to show only active stalls, or stalls with products.
    all_food_stalls = FoodStall.objects.all().order_by('stall_name')
    # Consider select_related('owner') if you need owner details in the template.

    # For active tab highlighting in bottom nav
    # Get the path of the current request
    current_path = request.path
    active_nav_item = None
    if current_path == reverse('shops_list'): # Use reverse to get the URL path
        active_nav_item = 'shops' 
    elif current_path == reverse('home'):
        active_nav_item = 'home'
    # Add more conditions for other nav items if needed

    context = {
        'food_stalls': all_food_stalls,
        'page_title': "Shops - Golden Bites",
        'active_nav_item': active_nav_item # Pass this to template for active state on nav
    }
    return render(request, 'shops-list.html', context)

def customer_signup_view(request):
    if request.method == 'POST':
        form = CustomerSignUpForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                login(request, user) # Log in the user
                messages.success(request, 'Registration successful! You are now logged in.')
                # Redirect to a customer-specific page or a general dashboard
                return redirect('home')  # Or wherever customers should go
            except Exception as e:
                messages.error(request, f'An error occurred during registration: {e}')
        else:
            # Form is not valid, errors will be in form.errors
            # Pass the form with errors back to the template
            # You might want to add more specific error messages to the template
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else: # GET request
        form = CustomerSignUpForm()
    return render(request, 'register.html', {'form': form})

def shop_owner_signup_view(request):
    if request.method == 'POST':
        form = ShopOwnerSignUpForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                login(request, user) # Log in the user
                messages.success(request, 'Shop registration successful! You are now logged in.')
                # Redirect to a shop owner-specific page or a general dashboard
                return redirect('dashboard')  # Or wherever shop owners should go
            except Exception as e:
                messages.error(request, f'An error occurred during shop registration: {e}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else: # GET request
        form = ShopOwnerSignUpForm()
    return render(request, 'sign-up.html', {'form': form}) # Assuming sign-up.html is for shop owners

def reset_password_view(request):
    return render(request, 'reset-password.html')

def review_view(request):
    from django.shortcuts import redirect
    from django.contrib import messages
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            product_id = form.cleaned_data['product_id']
            order_id = form.cleaned_data['order_id']
            rating = form.cleaned_data['rating']
            comment = form.cleaned_data['comment']
            # Validate product_id and order_id
            if not product_id or not order_id:
                messages.error(request, "Invalid review submission: missing product or order information.")
                return redirect('home')
            product = Product.objects.filter(pk=product_id).first()
            order = Order.objects.filter(pk=order_id).first()
            if not product or not order:
                messages.error(request, "Invalid product or order for review.")
                return redirect('home')
            review = Review.objects.filter(customer=request.user, product_id=product_id, order_id=order_id).first()
            if review:
                review.rating = rating
                review.comment = comment
                review.save()
                messages.success(request, "Your review has been updated!")
            else:
                Review.objects.create(
                    customer=request.user,
                    product_id=product_id,
                    order_id=order_id,
                    rating=rating,
                    comment=comment
                )
                messages.success(request, "Thank you for your review!")
            return redirect('notifications')
        else:
            # Form is invalid: get IDs from POST and fetch product/order for rendering
            product_id = request.POST.get('product_id')
            order_id = request.POST.get('order_id')
            product = Product.objects.filter(pk=product_id).first() if product_id else None
            order = Order.objects.filter(pk=order_id).first() if order_id else None
            messages.error(request, "There was an error with your review submission. Please check the form and try again.")
            return render(request, 'review.html', {'form': form, 'product': product, 'order': order})
    else:
        product_id = request.GET.get('product_id')
        order_id = request.GET.get('order_id')
        # Validate product_id and order_id
        if not product_id or not order_id:
            messages.error(request, "Missing product or order. Please access the review page from your orders.")
            return redirect('home')
        product = Product.objects.filter(pk=product_id).first()
        order = Order.objects.filter(pk=order_id).first()
        if not product or not order:
            messages.error(request, "Invalid product or order. Please access the review page from your orders.")
            return redirect('home')
        review = Review.objects.filter(customer=request.user, product_id=product_id, order_id=order_id).first()
        if review:
            form = ReviewForm(initial={
                'product_id': product_id,
                'order_id': order_id,
                'rating': review.rating,
                'comment': review.comment
            })
        else:
            form = ReviewForm(initial={'product_id': product_id, 'order_id': order_id})
    return render(request, 'review.html', {'form': form, 'product': product, 'order': order})

def sign_in_view(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {username}!')
                # Redirect to a success page, e.g., dashboard or home
                # You might want to redirect based on user_type if needed
                if user.user_type == 'shop':
                    return redirect('dashboard') 
                else:
                    return redirect('home')
            else: # User authentication failed (user is None)
                # Check for specific non-field errors first (e.g., inactive account)
                non_field_errors = form.non_field_errors()
                if non_field_errors:
                    for error in non_field_errors:
                        messages.error(request, error)
                else:
                    # Generic error if no specific non-field error but auth failed
                    messages.error(request, 'Please enter a correct username and password. Note that both fields may be case-sensitive.')
        else: # Form is not valid
            # Add field-specific errors
            for field in form.errors:
                for error in form.errors[field]:
                    if field == '__all__':
                        messages.error(request, error) # Non-field errors already handled if user was None
                    else:
                        messages.error(request, f"{form.fields[field].label}: {error}")

    else: # GET request
        form = CustomAuthenticationForm()
    return render(request, 'sign-in.html', {'form': form})

def login_view(request):
    # This is a placeholder if you have a separate /login URL that needs Django auth.
    # If sign_in_view handles all logins, this can be removed from views and urls.py.
    # For now, let's make it an alias or redirect to sign_in_view to avoid confusion.
    return sign_in_view(request) # Or redirect('sign_in')

def welcome_view(request):
    return render(request, 'welcome.html')

def landing_view(request):
    return render(request, 'landing.html')

def logout_view(request):
    logout(request)
    messages.success(request, "You have been successfully logged out.")
    return redirect('login') # Or your desired page after logout, e.g., 'welcome' or 'landing'

@login_required
@transaction.atomic # Ensures all database operations are committed together or rolled back
def place_order_view(request):
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        cart_stall_id = request.session.get('cart_stall_id')

        if not cart or not cart_stall_id:
            messages.error(request, "Your cart is empty or stall information is missing. Please add items to your cart.")
            return redirect('payment')

        payment_method_str = request.POST.get('payment_method')
        pickup_method_form = request.POST.get('pickup_method')
        notes = request.POST.get('order_note', '') # name from payment.html textarea
        queue_number_from_form = request.POST.get('queue_number')

        if not payment_method_str or not pickup_method_form:
            messages.error(request, "Payment method and pickup method are required.")
            return redirect('payment')
        
        try:
            food_stall_instance = FoodStall.objects.get(owner_id=cart_stall_id)
        except FoodStall.DoesNotExist:
            messages.error(request, "The selected food stall could not be found. Please try again.")
            return redirect('payment')

        total_cart_price = Decimal('0.00')
        for item_data in cart.values():
            price = Decimal(str(item_data.get('price', '0.00')))
            quantity = int(item_data.get('quantity', 0))
            total_cart_price += price * quantity
        
        # Create Payment object first
        # Assuming initial payment status is 'Pending' or 'Awaiting Payment' for non-cash
        # For 'Cash', it might be considered 'Paid' upon order, or 'Pending Collection'
        current_payment_status = 'Pending' # Default, adjust based on logic
        if payment_method_str == 'Cash':
            current_payment_status = 'Pending on Collection' # Or 'Paid' if you prefer

        new_payment = Payment.objects.create(
            payment_method=payment_method_str,
            payment_status=current_payment_status 
            # payment_time is auto_now_add
        )

        # Map pickup_method to order_type
        order_type_value = 'P' if pickup_method_form == 'pickup' else 'D'

        # Create the Order
        new_order = Order.objects.create(
            customer=request.user,
            food_stall=food_stall_instance, 
            order_price=total_cart_price, # Ensuring order_price gets a value
            total_price=total_cart_price, 
            order_summary=notes,          
            order_type=order_type_value,  
            queue_id=queue_number_from_form, 
            payment=new_payment,           
            status='Pending'               
            # order_time is auto_now_add
        )

        # Create OrderItems
        for product_id_str, item_data in cart.items():
            product = get_object_or_404(Product, pk=int(product_id_str))
            OrderItem.objects.create(
                order=new_order,
                product=product,
                quantity=int(item_data['quantity']),
                price=Decimal(str(item_data['price'])), # Corrected field name from price_at_order
                food_stall=food_stall_instance # OrderItem has food_stall
            )
        
        request.session['cart'] = {}
        if 'cart_stall_id' in request.session:
            del request.session['cart_stall_id']
        if 'cart_total_price' in request.session:
            del request.session['cart_total_price']

        request.session['last_order_id'] = new_order.id
        request.session['last_queue_number'] = new_order.queue_id # Use queue_id from the order

        messages.success(request, "Order placed successfully!")
        return redirect('order_confirmation')

    else:
        messages.error(request, "Invalid request method.")
        return redirect('payment')

@login_required
def order_confirmation_view(request):
    order_id = request.session.pop('last_order_id', None) # Pop to remove after retrieval
    queue_number = request.session.pop('last_queue_number', None)

    if not order_id or not queue_number:
        messages.warning(request, "No order confirmation details found. Perhaps you haven't placed an order yet?")
        return redirect('home') # Or 'order_history' if you have one

    context = {
        'order_id': order_id,
        'queue_number': queue_number,
        'page_title': "Order Confirmation"
    }
    return render(request, 'order-confirmation.html', context)

@login_required
@require_POST
def update_order_status_view(request, order_id):
    if request.user.user_type != 'shop':
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    try:
        # Eager load customer for the notification
        order = Order.objects.select_related('customer', 'food_stall').get(pk=order_id, food_stall__owner=request.user)
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Order not found'}, status=404)
    
    new_status = request.POST.get('status')
    
    # Validate status against model choices (which should align with DB constraints now for 'Ready')
    if new_status not in dict(Order.STATUS_CHOICES):
        return JsonResponse({'success': False, 'error': 'Invalid status value provided.'}, status=400)

    # Check DB constraint before saving (optional, but good for immediate feedback if there's a new mismatch)
    # This is more complex to do directly for CHECK constraints without trying to save.
    # The save() call will raise IntegrityError if the DB constraint fails.

    order.status = new_status
    try:
        order.save()
        print(f"[DEBUG] Order {order.id} status saved as: {new_status}") # DEBUG
        
        # Create notification for the customer
        customer_to_notify = order.customer
        food_stall_name = order.food_stall.stall_name if order.food_stall else "The shop"
        message = f"The status of your order #{order.id} from {food_stall_name} has been updated to: {new_status}."
        
        print(f"[DEBUG] Attempting to create notification for user: {customer_to_notify.username} (ID: {customer_to_notify.id})") # DEBUG
        print(f"[DEBUG] Notification message: {message}") # DEBUG

        try:
            notification = Notification.objects.create(
                user=customer_to_notify,
                order=order,
                message=message
                # link=notification_link # Uncomment and set if you have a relevant link
            )
            print(f"[DEBUG] Notification created with ID: {notification.id} for order {order.id}") # DEBUG
        except Exception as e_notif:
            print(f"[ERROR] Failed to create notification for order {order.id}: {e_notif}") # DEBUG
        
        return JsonResponse({'success': True, 'new_status': new_status})
    except IntegrityError as e:
        # This will catch violations of the chk_order_status if it's still not aligned or for other statuses
        if 'chk_order_status' in str(e):
            return JsonResponse({'success': False, 'error': f'Database constraint violation: The status "{new_status}" is not allowed by the database for this order.'}, status=400)
        else:
            # Handle other potential integrity errors
            return JsonResponse({'success': False, 'error': 'A database error occurred while updating the order.'}, status=500)
    except Exception as e:
        # Catch any other unexpected errors during save or notification creation
        # Log the error e for debugging
        return JsonResponse({'success': False, 'error': 'An unexpected error occurred.'}, status=500)

def order_details_modal_view(request, order_id):
    if not request.user.is_authenticated or request.user.user_type != 'shop':
        return HttpResponse('Unauthorized', status=403)
    order = get_object_or_404(Order, pk=order_id, food_stall__owner=request.user)
    return render(request, 'order_details_modal.html', {'order': order})

@login_required
def shop_products_view(request, stall_owner_id):
    food_stall = get_object_or_404(FoodStall, owner_id=stall_owner_id)
    
    # Get all products for this specific stall
    all_stall_products = Product.objects.filter(food_stall=food_stall).order_by('product_name')

    # Get unique categories for the filter tabs for this stall's products
    stall_categories_from_db = all_stall_products.values_list('category', flat=True).distinct()
    # Filter out None or empty string categories, normalize, ensure uniqueness, and sort them
    unique_normalized_categories = set()
    for cat in stall_categories_from_db:
        if cat: # Ensure category is not None or empty
            normalized_cat = cat.strip().title() # Remove whitespace, convert to title case
            if normalized_cat: # Ensure not empty after stripping
                 unique_normalized_categories.add(normalized_cat)
    categories_for_tabs = sorted(list(unique_normalized_categories))

    selected_category_filter = request.GET.get('category', 'All') # Default to 'All'

    products_to_display = all_stall_products
    if selected_category_filter != 'All':
        products_to_display = all_stall_products.filter(category=selected_category_filter)

    context = {
        'food_stall': food_stall,
        'products': products_to_display, # Products to display after category filter
        'categories': categories_for_tabs, # Categories for the filter tabs
        'selected_category': selected_category_filter, # The currently selected category filter
        'page_title': f"{food_stall.stall_name} - Products",
        'current_page_name': 'shop_products' 
    }
    return render(request, 'shop_products.html', context)

@login_required
@require_POST # Ensures this view only accepts POST requests
def acknowledge_order_receipt_view(request, order_id):
    try:
        order = Order.objects.get(pk=order_id, customer=request.user)
        if order.status == 'Completed' and order.customer_acknowledged_at is None:
            order.customer_acknowledged_at = timezone.now()
            order.save()
            return JsonResponse({'success': True, 'message': 'Order receipt acknowledged.'})
        elif order.customer_acknowledged_at is not None:
            return JsonResponse({'success': False, 'error': 'Order already acknowledged.'}, status=400)
        else:
            return JsonResponse({'success': False, 'error': 'Order not yet completed or invalid.'}, status=400)
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Order not found.'}, status=404)
    except Exception as e:
        # Log the exception e
        print(f"Error in acknowledge_order_receipt_view: {e}") # Basic logging
        return JsonResponse({'success': False, 'error': 'An unexpected error occurred.'}, status=500)