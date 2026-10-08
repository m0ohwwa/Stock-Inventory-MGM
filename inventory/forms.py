from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from .models import Category, Supplier, Product, StockTransaction, UserProfile, GlobalSettings
from .currency import from_usd, to_usd

class UserLoginForm(AuthenticationForm):
    username = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter your email address',
        'autocomplete': 'email'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter your password',
        'autocomplete': 'current-password'
    }))

class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter your password',
        'autocomplete': 'new-password'
    }))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Confirm your password',
        'autocomplete': 'new-password'
    }))
    role = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES, widget=forms.Select(attrs={
        'class': 'form-select'
    }))

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter first name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter last name'}),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your email address',
                'autocomplete': 'off'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match!")
        return cleaned_data

class UserSignUpForm(forms.ModelForm):
    role = forms.ChoiceField(
        choices=(
            ('', 'Select your position'),
            *(choice for choice in UserProfile.ROLE_CHOICES if choice[0] != 'ADMIN'),
        ),
        widget=forms.Select(attrs={'class': 'form-select position-select'})
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your first name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your last name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email address'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise forms.ValidationError("Email address is required.")
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email address already exists.")
        return email

class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter your email address'
    }))

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("No account is associated with this email address.")
        return email

class SetPasswordForm(forms.Form):
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter your password'
    }))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Confirm your password'
    }))

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match!")
        return cleaned_data

class UserAccountForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your first name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your last name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email address'}),
        }

    def clean_email(self):
        email = self.cleaned_data['email']
        qs = User.objects.filter(email__iexact=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("An account with this email address already exists.")
        return email


class AvatarPositionForm(forms.Form):
    avatar_position_x = forms.IntegerField(
        min_value=0,
        max_value=100,
        widget=forms.HiddenInput(),
    )
    avatar_position_y = forms.IntegerField(
        min_value=0,
        max_value=100,
        widget=forms.HiddenInput(),
    )


class OTPVerifyForm(forms.Form):
    otp_code = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control text-center fs-3 font-monospace tracking-widest',
            'maxlength': '6',
            'autocomplete': 'off',
            'autofocus': 'autofocus'
        })
    )

class UserProfileForm(forms.ModelForm):
    role = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    phone = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}))

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your first name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your last name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email address'}),
        }

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter category name (e.g., Electronics)'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter category description...'}),
        }

class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'phone', 'email', 'address']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter supplier company name'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter supplier phone number'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter supplier email address'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter full address...'}),
        }

class ProductForm(forms.ModelForm):
    def __init__(self, *args, currency_code='USD', usd_to_khr_rate=4000, **kwargs):
        super().__init__(*args, **kwargs)
        self.currency_code = currency_code
        self.usd_to_khr_rate = usd_to_khr_rate
        self.fields['price'].max_digits = 16
        if self.instance.pk and currency_code == 'KHR' and not self.is_bound:
            self.initial['price'] = from_usd(
                self.instance.price,
                currency_code,
                usd_to_khr_rate,
            )
        if currency_code == 'KHR':
            self.fields['price'].widget.attrs['step'] = '1'

    def clean_price(self):
        return to_usd(
            self.cleaned_data['price'],
            self.currency_code,
            self.usd_to_khr_rate,
        )

    class Meta:
        model = Product
        fields = ['name', 'sku', 'category', 'supplier', 'description', 'price', 'quantity', 'min_stock_level', 'image']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter product title'}),
            'sku': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter product SKU (e.g., PROD-1001)'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'supplier': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter product specifications...'}),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
            }),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'min_stock_level': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

class GlobalSettingsForm(forms.ModelForm):
    currency_code = forms.ChoiceField(
        choices=(
            ('USD', 'USD ($)'),
            ('KHR', 'KHR (៛)'),
        ),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = GlobalSettings
        fields = ['currency_code', 'usd_to_khr_rate']
        widgets = {
            'currency_code': forms.Select(attrs={'class': 'form-select'}),
            'usd_to_khr_rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0.01',
                'step': '0.01',
            }),
        }

class StockTransactionForm(forms.ModelForm):
    class Meta:
        model = StockTransaction
        fields = ['product', 'transaction_type', 'quantity', 'notes']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select'}),
            'transaction_type': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Reason or reference note (e.g. Order #123, Restock from supplier)...'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        transaction_type = cleaned_data.get('transaction_type')
        quantity = cleaned_data.get('quantity')

        if product and transaction_type == 'OUT' and quantity:
            if product.quantity < quantity:
                self.add_error('quantity', f"Cannot process Stock Out! Requested {quantity}, but current available stock is only {product.quantity}.")
        return cleaned_data


class StockInForm(forms.ModelForm):
    """Stock In — transaction_type is always IN, hidden from user."""
    class Meta:
        model = StockTransaction
        fields = ['product', 'quantity', 'notes']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                                          'placeholder': 'Reason or reference note (e.g. Restock from supplier, Order #123)...'}),
        }


class StockOutForm(forms.ModelForm):
    """Stock Out — transaction_type is always OUT, hidden from user."""
    class Meta:
        model = StockTransaction
        fields = ['product', 'quantity', 'notes']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                                          'placeholder': 'Reason or reference note (e.g. Dispatched, Customer Order #456)...'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        quantity = cleaned_data.get('quantity')
        if product and quantity and product.quantity < quantity:
            self.add_error('quantity', f"Insufficient stock! Available: {product.quantity}, requested: {quantity}.")
        return cleaned_data


class StockTransferForm(forms.Form):
    """Transfer stock from one product to another."""
    from_product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Source Product',
    )
    to_product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Destination Product',
    )
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                                    'placeholder': 'Reason for transfer (optional)...'}),
    )

    def clean(self):
        cleaned_data = super().clean()
        from_product = cleaned_data.get('from_product')
        to_product = cleaned_data.get('to_product')
        quantity = cleaned_data.get('quantity')

        if from_product and to_product and from_product == to_product:
            raise forms.ValidationError("Source and destination products must be different.")
        if from_product and quantity and from_product.quantity < quantity:
            self.add_error('quantity', f"Insufficient stock in source product! Available: {from_product.quantity}, requested: {quantity}.")
        return cleaned_data
