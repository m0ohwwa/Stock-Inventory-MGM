from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from decimal import Decimal

class Company(models.Model):
    name = models.CharField(max_length=150)
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=30, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    currency = models.CharField(max_length=10, default='USD')
    timezone = models.CharField(max_length=50, default='UTC')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class GlobalSettings(models.Model):
    CURRENCY_CHOICES = (
        ('USD', 'US Dollar ($)'),
        ('KHR', 'Khmer Riel (៛)'),
    )
    currency_code = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='USD')
    usd_to_khr_rate = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('4000.00'),
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Number of Khmer Riel for 1 US Dollar.',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'global setting'
        verbose_name_plural = 'global settings'

    def __str__(self):
        return f"Currency settings ({self.currency_code})"

    @classmethod
    def get_solo(cls):
        settings, _ = cls.objects.get_or_create(pk=1)
        return settings

class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('ADMIN', 'Admin'),
        ('MANAGER', 'Manager'),
        ('STAFF', 'Employee'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='employees', null=True, blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='STAFF')
    phone = models.CharField(max_length=20, blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    avatar_position_x = models.PositiveSmallIntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    avatar_position_y = models.PositiveSmallIntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    @property
    def is_admin(self):
        return self.role == 'ADMIN' or self.user.is_superuser

class Category(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='categories', null=True, blank=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']
        unique_together = ('company', 'name')

    def __str__(self):
        return self.name

class Supplier(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='suppliers', null=True, blank=True)
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30)
    email = models.EmailField()
    address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class Product(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='products', null=True, blank=True)
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=50, help_text="Stock Keeping Unit code")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.IntegerField(default=0)
    min_stock_level = models.IntegerField(default=5, help_text="Threshold for low stock warnings")
    image = models.ImageField(upload_to='product_images/', null=True, blank=True)
    is_archived = models.BooleanField(default=False, help_text="Soft-delete: archived products are hidden but history is preserved")
    date_added = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_added']
        unique_together = ('company', 'sku')

    def __str__(self):
        return f"{self.name} ({self.sku})"

    def archive(self):
        """Soft-delete: never hard-delete products that have transaction history."""
        self.is_archived = True
        self.save(update_fields=['is_archived'])

    @property
    def stock_status(self):
        if self.quantity <= 0:
            return 'OUT_OF_STOCK'
        elif self.quantity <= self.min_stock_level:
            return 'LOW_STOCK'
        return 'IN_STOCK'

    @property
    def stock_status_display(self):
        status_map = {
            'OUT_OF_STOCK': 'Out of Stock',
            'LOW_STOCK': 'Low Stock',
            'IN_STOCK': 'In Stock'
        }
        return status_map.get(self.stock_status, 'Unknown')

    @property
    def total_value(self):
        return self.price * self.quantity

class StockTransaction(models.Model):
    TRANSACTION_TYPES = (
        ('IN', 'Stock In'),
        ('OUT', 'Stock Out'),
    )
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='transactions', null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=3, choices=TRANSACTION_TYPES)
    quantity = models.PositiveIntegerField()
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.product.name} ({self.quantity})"

    def clean(self):
        if self.transaction_type == 'OUT' and self.product:
            if self.product.quantity < self.quantity:
                raise ValidationError({
                    'quantity': f"Insufficient stock! Available: {self.product.quantity}, requested: {self.quantity}."
                })

# Signals to manage UserProfile automatically
@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        role = 'ADMIN' if instance.is_superuser else 'STAFF'
        UserProfile.objects.create(user=instance, role=role)
    else:
        if hasattr(instance, 'profile'):
            instance.profile.save()
