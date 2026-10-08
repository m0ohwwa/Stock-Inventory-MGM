from django.contrib import admin
from .models import Category, Supplier, Product, StockTransaction, UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'phone')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__email', 'phone')

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name',)

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'created_at')
    search_fields = ('name', 'email', 'phone')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('sku', 'name', 'category', 'supplier', 'price', 'quantity', 'min_stock_level', 'stock_status')
    list_filter = ('category', 'supplier')
    search_fields = ('name', 'sku', 'description')
    ordering = ('-date_added',)

@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ('product', 'transaction_type', 'quantity', 'user', 'timestamp')
    list_filter = ('transaction_type', 'timestamp')
    search_fields = ('product__name', 'product__sku', 'notes')
