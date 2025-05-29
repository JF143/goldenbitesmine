from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User, FoodStall, Product

class CustomUserCreationForm(UserCreationForm):
    """
    A base user creation form that includes common fields like first_name, last_name,
    email, and contact_number. It overrides the default UserCreationForm.
    """
    username = forms.CharField(
        max_length=150,
        required=True,
        help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.',
        widget=forms.TextInput(attrs={'placeholder': 'Enter your username'})
    )
    first_name = forms.CharField(
        max_length=150, 
        required=True, 
        help_text='Required.',
        widget=forms.TextInput(attrs={'placeholder': 'Enter your first name'})
    )
    last_name = forms.CharField(
        max_length=150, 
        required=True, 
        help_text='Required.',
        widget=forms.TextInput(attrs={'placeholder': 'Enter your last name'})
    )
    email = forms.EmailField(
        required=True, 
        help_text='Required. Enter a valid email address.',
        widget=forms.EmailInput(attrs={'placeholder': 'Enter your email'})
    )
    contact_number = forms.CharField(
        max_length=20, 
        required=False, 
        label="Phone Number",
        widget=forms.TextInput(attrs={'placeholder': '09XXXXXXXXX'})
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "first_name", "last_name", "contact_number")

    def clean_email(self):
        """
        Validate that the email is unique.
        """
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email address is already in use. Please use a different one.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        user.contact_number = self.cleaned_data["contact_number"]
        # user_type will be set by subclasses
        if commit:
            user.save()
        return user

class ShopOwnerSignUpForm(CustomUserCreationForm):
    """
    Form for shop owners to sign up. Includes a shop_name field
    and sets user_type to 'shop'.
    """
    shop_name = forms.CharField(
        max_length=100, 
        required=True, 
        label="Shop Name",
        widget=forms.TextInput(attrs={'placeholder': 'Enter your shop name'})
    )
    # If you want to include id_number (National ID or Business ID) uncomment below
    # id_number = forms.CharField(max_length=50, required=False, label="National ID or Business ID")

    class Meta(CustomUserCreationForm.Meta):
        model = User
        fields = CustomUserCreationForm.Meta.fields + ('shop_name',) # Add shop_name field
        # If adding id_number, include it here:
        # fields = CustomUserCreationForm.Meta.fields + ('shop_name', 'id_number',)


    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = 'shop'
        user.shop_name = self.cleaned_data['shop_name']
        # If id_number is used:
        # user.id_number = self.cleaned_data.get('id_number')
        if commit:
            user.save()
            # Create FoodStall instance for the shop owner
            FoodStall.objects.create(
                owner=user, 
                stall_name=user.shop_name, # Use the shop_name from the user
                # staff_name can be left blank or collected in the form
                # service_type will use its default 'Pickup' as per your model
            )
        return user

class CustomerSignUpForm(CustomUserCreationForm):
    """
    Form for customers to sign up. Sets user_type to 'customer'.
    """
    class Meta(CustomUserCreationForm.Meta):
        model = User
        fields = CustomUserCreationForm.Meta.fields # Uses fields from CustomUserCreationForm

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = 'customer'
        if commit:
            user.save()
        return user

    # Removed clean_shop_name method as it's not applicable here 

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'placeholder': 'Enter your username or email',
        'class': 'form-input' # Optional: if you want to reuse specific CSS class for inputs
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder': 'Enter your password',
        'class': 'form-input' # Optional
    })) 

class ProductForm(forms.ModelForm):
    # Define choices for category or fetch them dynamically if needed
    CATEGORY_CHOICES = [
        ('', 'Select a category'), # Placeholder
        ('Breakfast', 'Breakfast'),
        ('Lunch', 'Lunch'),
        ('Dinner', 'Dinner'),
        ('Chicken', 'Chicken'),
        ('Pork', 'Pork'),
        ('Beef', 'Beef'),
        ('Pasta', 'Pasta'),
        ('Rice', 'Rice'),
        ('Snacks', 'Snacks'),
        ('Drinks & Beverages', 'Drinks & Beverages'),
    ]
    category = forms.ChoiceField(choices=CATEGORY_CHOICES, required=True)
    # Make product_image not required for editing, as an image might already exist.
    # The view logic will handle new uploads and deletions.
    product_image = forms.ImageField(required=False, label="Product Image") 
    ingredients = forms.CharField(widget=forms.Textarea(attrs={'placeholder': 'List ingredients separated by commas...', 'rows': 3}), required=False)
    details = forms.CharField(widget=forms.Textarea(attrs={'placeholder': 'Enter item details...', 'rows': 3}), required=False)

    class Meta:
        model = Product
        fields = ['product_name', 'unit_price', 'category', 'product_image', 'ingredients', 'details']
        widgets = {
            'product_name': forms.TextInput(attrs={'placeholder': 'Enter item name'}),
            'unit_price': forms.NumberInput(attrs={'placeholder': 'Enter price'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].label = "Category *"
        self.fields['product_name'].label = "Item Name *"
        self.fields['unit_price'].label = "Price (₱) *"
        self.fields['product_image'].label = "Item Image *"
        # Ensure labels for ingredients and details are set if not using *args from screenshot
        self.fields['ingredients'].label = "Ingredients"
        self.fields['details'].label = "Details" 

class ReviewForm(forms.Form):
    rating = forms.ChoiceField(
        choices=[(i, str(i)) for i in range(1, 6)],
        widget=forms.RadioSelect,
        label="Rating *"
    )
    comment = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'Write your review...', 'rows': 3}),
        required=False,
        label="Comment"
    )
    product_id = forms.IntegerField(widget=forms.HiddenInput())
    order_id = forms.IntegerField(widget=forms.HiddenInput()) 