from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, FoodStall, Product, Payment, Order,
    PickupOrder, DeliveryOrder, OrderItem, Review
)

# Custom User Admin
class CustomUserAdmin(BaseUserAdmin):
    list_display = (
        'username', 'email', 'first_name', 'last_name', 'is_staff', 
        'user_type', 'shop_name', 'contact_number', 'id_number'
    )
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Custom Info', {'fields': ('user_type', 'shop_name', 'id_number', 'contact_number')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Custom Info', {'fields': (
            'user_type', # Make sure to include all custom fields needed for user creation
            'shop_name',
            'id_number',
            'contact_number',
            # 'first_name', # Already in BaseUserAdmin.add_fieldsets usually
            # 'last_name',
            # 'email',
        )}),
    )
    search_fields = BaseUserAdmin.search_fields + ('shop_name', 'contact_number')
    list_filter = BaseUserAdmin.list_filter + ('user_type', 'is_staff', 'is_superuser', 'is_active')

admin.site.register(User, CustomUserAdmin)

@admin.register(FoodStall)
class FoodStallAdmin(admin.ModelAdmin):
    list_display = ['owner', 'stall_name', 'service_type']
    search_fields = ['stall_name', 'owner__username']
    list_filter = ['service_type']
    autocomplete_fields = ['owner']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['product_name', 'food_stall', 'unit_price', 'category']
    search_fields = ['product_name', 'food_stall__stall_name', 'category']
    list_filter = ['category', 'food_stall']
    autocomplete_fields = ['food_stall']

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'payment_method', 'payment_status', 'payment_time']
    search_fields = ['id', 'payment_method', 'payment_status']
    list_filter = ['payment_method', 'payment_status']
    readonly_fields = ['payment_time']
    date_hierarchy = 'payment_time'

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    autocomplete_fields = ['product', 'food_stall']
    # readonly_fields = ['price'] # Assuming price might be set based on product at time of adding

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'order_time', 'total_price', 'order_type', 'payment_status_display']
    search_fields = ['id', 'customer__username', 'customer__email']
    list_filter = ['order_type', 'order_time', 'payment__payment_status']
    readonly_fields = ['order_time', 'id', 'payment'] # payment is OneToOne, show its details or link
    date_hierarchy = 'order_time'
    inlines = [OrderItemInline]
    autocomplete_fields = ['customer', 'payment']

    def payment_status_display(self, obj):
        if obj.payment:
            return obj.payment.payment_status
        return "N/A (No Payment Link)"
    payment_status_display.short_description = 'Payment Status'

@admin.register(PickupOrder)
class PickupOrderAdmin(admin.ModelAdmin):
    list_display = ['order', 'pickup_store']
    search_fields = ['order__id', 'pickup_store']
    autocomplete_fields = ['order']

@admin.register(DeliveryOrder)
class DeliveryOrderAdmin(admin.ModelAdmin):
    list_display = ['order', 'delivery_address']
    search_fields = ['order__id', 'delivery_address']
    autocomplete_fields = ['order']

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'product', 'rating', 'created_at']
    search_fields = ['customer__username', 'product__product_name', 'comment']
    list_filter = ['rating', 'created_at']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    autocomplete_fields = ['customer', 'product']

# Customize admin site headers
admin.site.site_header = "GoldenBites Admin (New Schema)"
admin.site.site_title = "GoldenBites Admin Portal"
admin.site.index_title = "Welcome to GoldenBites Administration"