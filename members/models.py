from django.db import models
from django.contrib.auth.models import AbstractUser

# Models based on the provided SQL script

class User(AbstractUser):
    # Inherits username, first_name, last_name, email, password,
    # is_staff, is_active, is_superuser, last_login, date_joined from AbstractUser.

    # Additional fields from your SQL:
    USER_TYPE_CHOICES = [
        ('shop', 'Shop Owner'),
        ('customer', 'Customer'),
    ]
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='customer')
    shop_name = models.CharField(max_length=100, blank=True, null=True) # Used if user_type is 'shop'
    id_number = models.CharField(max_length=50, blank=True, null=True) # National ID or business ID
    contact_number = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'user' # Using lowercase 'user' as in your SQL

    def __str__(self):
        return self.username

class FoodStall(models.Model):
    owner = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True) # owner_id in SQL, made PK here
    stall_name = models.CharField(max_length=100)
    staff_name = models.CharField(max_length=100, blank=True, null=True)
    SERVICE_TYPE_CHOICES = [
        ('Pickup', 'Pickup'),
        ('Delivery', 'Delivery'),
        ('Both', 'Both'),
    ]
    service_type = models.CharField(max_length=20, choices=SERVICE_TYPE_CHOICES, default='Pickup')

    class Meta:
        managed = False
        db_table = 'food_stall'

    def __str__(self):
        return self.stall_name

class Product(models.Model):
    # id will be added automatically by Django as primary key
    product_name = models.CharField(max_length=100)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=50, blank=True, null=True) # From your SQL
    food_stall = models.ForeignKey(FoodStall, on_delete=models.CASCADE) # food_stall_id in SQL
    image_url = models.URLField(max_length=2048, blank=True, null=True) # To store image URL from Supabase Storage
    ingredients = models.TextField(blank=True, null=True) # Based on UI screenshot
    details = models.TextField(blank=True, null=True) # Based on UI screenshot

    class Meta:
        managed = False
        db_table = 'product'

    def __str__(self):
        return self.product_name

class Payment(models.Model):
    # id will be added automatically by Django
    payment_method = models.CharField(max_length=50)
    payment_status = models.CharField(max_length=50)
    payment_time = models.DateTimeField(auto_now_add=True) # Corresponds to TIMESTAMPTZ DEFAULT now()

    class Meta:
        managed = False
        db_table = 'payment'

    def __str__(self):
        return f"{self.id} - {self.payment_method} - {self.payment_status}"

class Order(models.Model):
    # id will be added automatically by Django
    customer = models.ForeignKey(User, on_delete=models.CASCADE) # customer_id in SQL
    order_time = models.DateTimeField(auto_now_add=True) # Corresponds to TIMESTAMPTZ DEFAULT now()
    order_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    order_summary = models.TextField(blank=True, null=True)
    ORDER_TYPE_CHOICES = [
        ('P', 'Pickup'),
        ('D', 'Delivery'),
    ]
    order_type = models.CharField(max_length=1, choices=ORDER_TYPE_CHOICES)
    queue_id = models.CharField(max_length=50, blank=True, null=True)
    payment = models.OneToOneField(Payment, on_delete=models.SET_NULL, blank=True, null=True, unique=True) # payment_id in SQL
    food_stall = models.ForeignKey(FoodStall, on_delete=models.SET_NULL, null=True, blank=True)
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Preparing', 'Preparing'),
        ('Ready', 'Ready'),
        ('Out for Delivery', 'Out for Delivery'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    customer_acknowledged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = '"order"' # Quoted because 'order' is often a reserved keyword

    def __str__(self):
        return f"Order ID: {self.pk} by {self.customer.username}"

class PickupOrder(models.Model):
    order = models.OneToOneField(Order, primary_key=True, on_delete=models.CASCADE) # order_id in SQL, made PK here
    pickup_store = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'pickup_order'

    def __str__(self):
        return f"Pickup for Order {self.order_id} at {self.pickup_store}"

class DeliveryOrder(models.Model):
    order = models.OneToOneField(Order, primary_key=True, on_delete=models.CASCADE) # order_id in SQL, made PK here
    delivery_address = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'delivery_order'

    def __str__(self):
        return f"Delivery for Order {self.order_id} to {self.delivery_address}"

class OrderItem(models.Model):
    # id will be added automatically by Django
    order = models.ForeignKey(Order, on_delete=models.CASCADE) # order_id in SQL
    product = models.ForeignKey(Product, on_delete=models.CASCADE) # product_id in SQL
    quantity = models.IntegerField() # Your SQL has CHECK (quantity > 0)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    food_stall = models.ForeignKey(FoodStall, on_delete=models.CASCADE) # food_stall_id in SQL

    class Meta:
        managed = False
        db_table = 'order_item'
        # Consider adding validators for quantity in Django forms/serializers

    def __str__(self):
        return f"{self.quantity} of {self.product.product_name} for Order {self.order.id}"

class Review(models.Model):
    customer = models.ForeignKey(User, on_delete=models.CASCADE) # customer_id in SQL
    product = models.ForeignKey(Product, on_delete=models.CASCADE) # product_id in SQL
    order = models.ForeignKey(Order, on_delete=models.CASCADE) # order_id in SQL (added)
    rating = models.SmallIntegerField() # Your SQL has CHECK (rating >= 1 AND rating <= 5)
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True) # Corresponds to TIMESTAMPTZ DEFAULT now()

    class Meta:
        managed = False
        db_table = 'review'
        # Consider adding validators for rating in Django forms/serializers

    def __str__(self):
        return f"Review by {self.customer.username} for {self.product.product_name} (Rating: {self.rating})"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications') # The user to notify (customer)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications') # Optional, if notification is about an order
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    link = models.URLField(blank=True, null=True) # Optional link, e.g., to the order tracking page

    class Meta:
        managed = False # You will need to create this table in Supabase
        db_table = 'notification'
        ordering = ['-timestamp']

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message[:50]}"