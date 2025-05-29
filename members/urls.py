"""
URL configuration for goldenbites project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# members/urls.py
from django.urls import path
from . import views # . means from the current package/app

urlpatterns = [
    path('', views.welcome_view, name='welcome'), # For your main landing page if it exists
    path('sign-in/', views.sign_in_view, name='sign_in'), # This is the crucial line for sign-in
    path('login/', views.login_view, name='login'), # Now effectively an alias for sign_in_view
    path('logout/', views.logout_view, name='logout'), # Added logout URL
    path('sign-up/', views.shop_owner_signup_view, name='sign_up'), # For Shop Owners (merchants)
    path('register/', views.customer_signup_view, name='register'),  # For Customers
    path('policy/', views.policy_view, name='policy'), # As seen in previous context
    path('policy-admin/', views.policy_admin_view, name='policy_admin'),
    path('favorites/', views.favorites_view, name='favorites'),
    path('food-list/', views.food_list_view, name='food_list'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('home/', views.home_view, name='home'),
    path('notifications/', views.notifications_view, name='notifications'),
    path('order-details/', views.order_details_view, name='order_details'),
    path('order-summary/', views.order_summary_view, name='order_summary'),
    path('order-tracking/', views.order_tracking_view, name='order_tracking'),
    path('orders/', views.orders_view, name='orders'),
    path('overview/', views.overview_view, name='overview'),
    path('payment/', views.payment_view, name='payment'),
    path('product/<int:product_id>/', views.product_detail_view, name='product_detail'),
    path('shops/', views.shops_list_view, name='shops_list'),
    path('shop/<int:stall_owner_id>/products/', views.shop_products_view, name='shop_products'),
    path('reset-password/', views.reset_password_view, name='reset_password_confirm'),
    path('review/', views.review_view, name='review'),
    path('landing/', views.landing_view, name='landing'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('add-item/', views.add_item_view, name='add-item'),
    path('product/<int:product_id>/edit/', views.edit_product_view, name='edit_product'),
    path('product/<int:product_id>/delete/', views.delete_product_view, name='delete_product'),
    path('add_to_cart/<int:product_id>/', views.add_to_cart_view, name='add_to_cart'),
    path('cart/update/<int:product_id>/', views.update_cart_item_quantity_view, name='update_cart_item_quantity'),
    path('cart/remove/<int:product_id>/', views.remove_from_cart_view, name='remove_from_cart'),
    path('place_order/', views.place_order_view, name='place_order'),
    path('order_confirmation/', views.order_confirmation_view, name='order_confirmation'),
    path('orders/update_status/<int:order_id>/', views.update_order_status_view, name='update_order_status'),
    path('orders/details/<int:order_id>/', views.order_details_modal_view, name='order_details_modal'),
    path('acknowledge_order_receipt/<int:order_id>/', views.acknowledge_order_receipt_view, name='acknowledge_order_receipt'),
]
