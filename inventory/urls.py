from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('set-password/', views.set_password_view, name='set_password'),
    path('signup/pending-approval/', views.approval_pending_view, name='approval_pending'),
    path('resend-otp/', views.resend_otp_view, name='resend_otp'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('forgot-password/verify/', views.verify_forgot_password_otp_view, name='verify_forgot_password_otp'),
    path('forgot-password/prompt/', views.forgot_password_prompt_view, name='forgot_password_prompt'),
    path('forgot-password/reset/', views.forgot_password_reset_view, name='forgot_password_reset'),
    path('logout/', views.logout_view, name='logout'),
    path('account/profile/', views.account_profile, name='account_profile'),
    path('settings/', views.settings_view, name='settings'),
    path('settings/currency/', views.currency_settings_view, name='currency_settings'),
    path('settings/system-controls/', views.system_controls_view, name='system_controls'),
    path('settings/users/', views.user_list, name='user_list'),
    path('settings/users/register/', views.register_view, name='register'),
    path('settings/users/<int:pk>/approve/', views.user_approve, name='user_approve'),
    path('settings/users/<int:pk>/toggle-role/', views.user_toggle_role, name='user_toggle_role'),
    path('settings/users/<int:pk>/delete/', views.user_delete, name='user_delete'),
    path('settings/users/<int:pk>/edit/', views.user_edit, name='user_edit'),

    # Dashboard & Demo Data Controls
    path('', views.dashboard, name='dashboard'),
    path('admin-dashboard/', views.dashboard_admin, name='dashboard_admin'),
    path('manager-dashboard/', views.dashboard_manager, name='dashboard_manager'),
    path('staff-dashboard/', views.dashboard_staff, name='dashboard_staff'),
    path('demo/seed/', views.seed_demo_data_view, name='seed_demo_data'),
    path('demo/reset/', views.reset_demo_data_view, name='reset_demo_data'),

    # Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_update, name='category_update'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),

    # Suppliers
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/add/', views.supplier_create, name='supplier_create'),
    path('suppliers/<int:pk>/edit/', views.supplier_update, name='supplier_update'),
    path('suppliers/<int:pk>/delete/', views.supplier_delete, name='supplier_delete'),

    # Products
    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.product_create, name='product_create'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),
    path('products/<int:pk>/edit/', views.product_update, name='product_update'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),

    # Inventory Transactions
    path('transactions/', views.transaction_list, name='transaction_list'),
    path('transactions/add/', views.transaction_create, name='transaction_create'),
    path('transactions/stock-in/', views.stock_in_view, name='stock_in'),
    path('transactions/stock-out/', views.stock_out_view, name='stock_out'),
    path('transactions/transfer/', views.stock_transfer_view, name='stock_transfer'),

    # Reports & Exports
    path('reports/', views.reports_dashboard, name='reports_dashboard'),
    path('reports/inventory/csv/', views.export_inventory_csv, name='export_inventory_csv'),
    path('reports/inventory/pdf/', views.export_inventory_pdf, name='export_inventory_pdf'),
    path('reports/low-stock/csv/', views.export_low_stock_csv, name='export_low_stock_csv'),
    path('reports/low-stock/pdf/', views.export_low_stock_pdf, name='export_low_stock_pdf'),
    path('reports/transactions/csv/', views.export_transactions_csv, name='export_transactions_csv'),
    path('reports/transactions/pdf/', views.export_transactions_pdf, name='export_transactions_pdf'),
]
