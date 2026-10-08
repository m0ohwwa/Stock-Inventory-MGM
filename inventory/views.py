from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, F, Count, Q
from django.core.paginator import Paginator
from django.db import transaction
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils.http import url_has_allowed_host_and_scheme
from functools import wraps

from smtplib import SMTPException
from django.utils import timezone
from django.http import JsonResponse
import json
from .models import Category, Supplier, Product, StockTransaction, UserProfile, GlobalSettings
from .forms import (
    UserLoginForm, UserRegistrationForm, UserSignUpForm, OTPVerifyForm, CategoryForm, 
    SupplierForm, ProductForm, StockTransactionForm, StockInForm, StockOutForm, StockTransferForm,
    UserProfileForm, UserAccountForm, AvatarPositionForm, SetPasswordForm,
    ForgotPasswordForm, GlobalSettingsForm
)
from .utils import generate_csv_report, generate_pdf_report
from .currency import format_currency

# Decorator to restrict access to Admin role
def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        profile = getattr(request.user, 'profile', None)
        if not (request.user.is_superuser or (profile and profile.is_admin)):
            messages.error(request, "Permission denied. Admin access required.")
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def manager_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        profile = getattr(request.user, 'profile', None)
        if not (request.user.is_superuser or (profile and profile.role in ['ADMIN', 'MANAGER'])):
            messages.error(request, "Permission denied. Manager access required.")
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def generate_username_from_email(email):
    base_username = slugify(email.partition('@')[0])[:140] or 'user'
    username = base_username
    suffix = 2
    while User.objects.filter(username__iexact=username).exists():
        username = f"{base_username[:140 - len(str(suffix))]}-{suffix}"
        suffix += 1
    return username

# Helper to redirect a user to their role-specific dashboard
def redirect_to_role_dashboard(user):
    role = user.profile.role if hasattr(user, 'profile') else 'STAFF'
    if role == 'ADMIN':
        return redirect('dashboard_admin')
    elif role == 'MANAGER':
        return redirect('dashboard_manager')
    else:
        return redirect('dashboard_staff')

@login_required
@admin_required
def settings_view(request):
    app_settings = GlobalSettings.get_solo()
    if request.method == 'POST':
        form = GlobalSettingsForm(request.POST, instance=app_settings)
        if form.is_valid():
            form.save()
            messages.success(request, "Settings saved successfully.")
            return redirect('settings')
    else:
        form = GlobalSettingsForm(instance=app_settings)

    pending_approval_count = User.objects.filter(
        is_active=False,
        profile__role__in=('STAFF', 'MANAGER'),
    ).count()
    return render(request, 'inventory/settings.html', {
        'form': form,
        'pending_approval_count': pending_approval_count,
    })

def currency_settings_view(request):
    app_settings = GlobalSettings.get_solo()
    if request.method == 'POST':
        form = GlobalSettingsForm(request.POST, instance=app_settings)
        if form.is_valid():
            form.save()
            messages.success(request, "Currency settings saved successfully.")
            return redirect('currency_settings')
    else:
        form = GlobalSettingsForm(instance=app_settings)
    return render(request, 'inventory/currency_settings.html', {
        'form': form,
    })

@login_required
@admin_required
def system_controls_view(request):
    return render(request, 'inventory/system_controls.html')

# Authentication Views
def login_view(request):
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url and not url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = ''

    if request.user.is_authenticated:
        if next_url:
            return redirect(next_url)
        return redirect_to_role_dashboard(request.user)
    
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if request.POST.get('remember_me'):
                request.session.set_expiry(1209600)  # 2 weeks
            else:
                request.session.set_expiry(0)        # Browser session
            messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")
            if next_url:
                return redirect(next_url)
            return redirect_to_role_dashboard(user)
        else:
            email = request.POST.get('username', '').strip()
            password = request.POST.get('password', '')
            pending_user = User.objects.filter(email__iexact=email, is_active=False).first()
            if pending_user and pending_user.check_password(password):
                messages.info(request, "Your email is verified, but an administrator must approve your account before you can sign in.")
            else:
                messages.error(request, "Invalid username/email or password.")
    else:
        form = UserLoginForm()
    return render(request, 'inventory/login.html', {'form': form, 'next': next_url})

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = UserSignUpForm(request.POST)
        if form.is_valid():
            from .otp_utils import OTPGenerator
            otp_code = OTPGenerator.generate_code()
            email = form.cleaned_data['email']
            username = generate_username_from_email(email)

            # Store registration state in session via OTPGenerator
            OTPGenerator.store_in_session(
                request,
                key_prefix='signup',
                email=email,
                otp_code=otp_code,
                extra_data={
                    'username': username,
                    'email': email,
                    'first_name': form.cleaned_data.get('first_name', ''),
                    'last_name': form.cleaned_data.get('last_name', ''),
                    'role': form.cleaned_data.get('role', 'STAFF'),
                }
            )
            # Also keep legacy session keys for verify_otp_view compatibility
            request.session['pending_signup'] = {
                'username': username,
                'email': email,
                'first_name': form.cleaned_data.get('first_name', ''),
                'last_name': form.cleaned_data.get('last_name', ''),
                'role': form.cleaned_data.get('role', 'STAFF'),
            }
            request.session['otp_code'] = otp_code
            request.session['otp_timestamp'] = timezone.now().timestamp()

            try:
                from django.core.mail import send_mail
                from django.conf import settings
                full_name = f"{form.cleaned_data.get('first_name', '')} {form.cleaned_data.get('last_name', '')}".strip()
                display_name = full_name or username
                sent_count = send_mail(
                    "Your Stock Inventory verification code",
                    f"Hi {display_name},\n\nYour verification code is:\n\n  {otp_code}\n\nExpires in 10 minutes.\n\n— Stock Inventory Team",
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
            except (OSError, SMTPException):
                sent_count = 0

            if not sent_count:
                OTPGenerator.clear_session_otp(request, 'signup')
                request.session.pop('pending_signup', None)
                request.session.pop('otp_code', None)
                request.session.pop('otp_timestamp', None)
                messages.error(request, "We couldn't send the verification email. Please check the email address and try again.")
                return render(request, 'inventory/signup.html', {'form': form})

            messages.info(request, f"Verification code sent to {email}. Please enter the OTP to complete registration.")
            return redirect('verify_otp')
    else:
        form = UserSignUpForm()
    return render(request, 'inventory/signup.html', {'form': form})

from django.http import JsonResponse
import json

def verify_otp_view(request):
    if request.user.is_authenticated:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
            return JsonResponse({'success': True, 'redirect_url': '/'})
        return redirect('dashboard')

    pending_data = request.session.get('pending_signup')
    if not pending_data:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
            return JsonResponse({'success': False, 'message': 'No pending registration found. Please sign up again.', 'redirect_url': '/signup/'})
        messages.warning(request, "No pending registration found. Please sign up first.")
        return redirect('signup')

    if request.method == 'POST':
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json'
        
        if is_ajax and request.body:
            try:
                body_data = json.loads(request.body.decode('utf-8'))
                input_otp = str(body_data.get('otp_code', '')).strip()
            except Exception:
                input_otp = request.POST.get('otp_code', '').strip()
        else:
            input_otp = request.POST.get('otp_code', '').strip()

        stored_otp = request.session.get('otp_code')
        otp_timestamp = request.session.get('otp_timestamp', 0)
        now_ts = timezone.now().timestamp()

        # Check 10-minute validity (600s)
        if stored_otp and input_otp == stored_otp and (now_ts - otp_timestamp <= 600):
            # Mark OTP as verified in session
            request.session['otp_verified'] = True
            
            # Clean up OTP fields but keep pending_signup for next step
            request.session.pop('otp_code', None)
            request.session.pop('otp_timestamp', None)
            
            if is_ajax:
                return JsonResponse({'success': True, 'message': 'Verification successful! Redirecting to set password...', 'redirect_url': '/set-password/'})
            messages.success(request, "Email verified successfully! Please set your password.")
            return redirect('set_password')
        else:
            error_msg = "Invalid or expired OTP code! Please check your code and try again."
            if is_ajax:
                return JsonResponse({'success': False, 'message': error_msg})
            messages.error(request, error_msg)
            form = OTPVerifyForm(request.POST)
    else:
        form = OTPVerifyForm()

    otp_email = pending_data.get('email', '')

    return render(request, 'inventory/verify_otp.html', {
        'form': form,
        'email': otp_email,
    })

def set_password_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    pending_data = request.session.get('pending_signup')
    otp_verified = request.session.get('otp_verified')
    
    if not pending_data or not otp_verified:
        messages.warning(request, "Please verify your email first.")
        return redirect('signup')
        
    if request.method == 'POST':
        form = SetPasswordForm(request.POST)
        if form.is_valid():
            # Create user account now
            final_username = generate_username_from_email(pending_data['email'])
            user = User.objects.create_user(
                username=final_username,
                email=pending_data['email'],
                password=form.cleaned_data['password'],
                first_name=pending_data.get('first_name', ''),
                last_name=pending_data.get('last_name', ''),
                is_active=False
            )
            requested_role = pending_data.get('role', 'STAFF')
            user.profile.role = requested_role if requested_role in ('STAFF', 'MANAGER') else 'STAFF'
            user.profile.save()

            # Clean up session
            request.session.pop('pending_signup', None)
            request.session.pop('otp_verified', None)

            messages.success(request, "Your account is created. An administrator must approve it before you can sign in.")
            return redirect('approval_pending')
    else:
        form = SetPasswordForm()
        
    return render(request, 'inventory/set_password.html', {'form': form})

def approval_pending_view(request):
    return render(request, 'inventory/approval_pending.html')


def resend_otp_view(request):
    pending_data = request.session.get('pending_signup')
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json'

    if not pending_data:
        if is_ajax:
            return JsonResponse({'success': False, 'message': 'Session expired. Please sign up again.'})
        messages.warning(request, "No pending registration session found.")
        return redirect('signup')

    from .otp_utils import OTPGenerator
    new_otp = OTPGenerator.generate_code()
    email = pending_data['email']
    username = pending_data['username']

    try:
        from django.core.mail import send_mail
        from django.conf import settings
        full_name = f"{pending_data.get('first_name', '')} {pending_data.get('last_name', '')}".strip()
        display_name = full_name or username
        send_mail(
            "Your Stock Inventory verification code",
            f"Hi {display_name},\n\nYour verification code is:\n\n  {new_otp}\n\nExpires in 10 minutes.\n\n— Stock Inventory Team",
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
    except (OSError, SMTPException):
        msg = "We couldn't send the verification email. Please try again."
        if is_ajax:
            return JsonResponse({'success': False, 'message': msg}, status=503)
        messages.error(request, msg)
        return redirect('verify_otp')

    request.session['otp_code'] = new_otp
    request.session['otp_timestamp'] = timezone.now().timestamp()

    msg = f"A new OTP verification code has been sent to {email}."
    if is_ajax:
        return JsonResponse({'success': True, 'message': msg})

    messages.success(request, msg)
    return redirect('verify_otp')

def forgot_password_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            from .otp_utils import OTPGenerator
            otp_code = OTPGenerator.generate_code()
            
            request.session['forgot_password_email'] = email
            request.session['forgot_password_otp'] = otp_code
            request.session['forgot_password_timestamp'] = timezone.now().timestamp()
            
            try:
                from django.core.mail import send_mail
                from django.conf import settings
                send_mail(
                    "Your Password Reset Code",
                    f"Your password reset code is:\n\n  {otp_code}\n\nExpires in 10 minutes.",
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
            except (OSError, SMTPException):
                messages.error(request, "We couldn't send the password reset email. Please try again later.")
                return render(request, 'inventory/forgot_password.html', {'form': form})
                
            messages.info(request, f"Password reset code sent to {email}.")
            return redirect('verify_forgot_password_otp')
    else:
        form = ForgotPasswordForm()
    return render(request, 'inventory/forgot_password.html', {'form': form})

def verify_forgot_password_otp_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    email = request.session.get('forgot_password_email')
    if not email:
        messages.warning(request, "Password reset session expired.")
        return redirect('forgot_password')
        
    if request.method == 'POST':
        form = OTPVerifyForm(request.POST)
        if form.is_valid():
            user_otp = form.cleaned_data['otp_code']
            session_otp = request.session.get('forgot_password_otp')
            timestamp = request.session.get('forgot_password_timestamp', 0)
            
            if not session_otp:
                messages.error(request, "OTP session expired. Please request a new one.")
                return redirect('forgot_password')
                
            if timezone.now().timestamp() - timestamp > 600:
                messages.error(request, "OTP has expired. Please request a new one.")
                return redirect('forgot_password')
                
            if user_otp == session_otp:
                request.session['forgot_password_verified'] = True
                request.session.pop('forgot_password_otp', None)
                messages.success(request, "Email verified!")
                return redirect('forgot_password_prompt')
            else:
                messages.error(request, "Invalid OTP code. Please try again.")
    else:
        form = OTPVerifyForm()
    return render(request, 'inventory/verify_forgot_password_otp.html', {'form': form, 'email': email})

def forgot_password_prompt_view(request):
    if request.user.is_authenticated:
        return redirect_to_role_dashboard(request.user)
        
    if not request.session.get('forgot_password_verified'):
        messages.warning(request, "Please verify your email first.")
        return redirect('forgot_password')
        
    email = request.session.get('forgot_password_email')
    
    if request.method == 'POST':
        # User chose to skip password update and login directly
        try:
            # Use filter+first to handle edge case of duplicate emails in DB
            user = User.objects.filter(email__iexact=email).order_by('-date_joined').first()
            if not user:
                raise User.DoesNotExist
        except User.DoesNotExist:
            messages.error(request, "Account not found. Please try again.")
            return redirect('forgot_password')

        # Must specify backend when calling login() without authenticate()
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)
        request.session.pop('forgot_password_email', None)
        request.session.pop('forgot_password_verified', None)
        messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")
        return redirect_to_role_dashboard(user)
        
    return render(request, 'inventory/prompt_reset_password.html', {'email': email})

def forgot_password_reset_view(request):
    # Allow authenticated users (e.g. admin) to set a new password via the prompt flow
    is_authenticated_user = request.user.is_authenticated

    if not is_authenticated_user and not request.session.get('forgot_password_verified'):
        messages.warning(request, "Please verify your email first.")
        return redirect('forgot_password')

    email = request.session.get('forgot_password_email') if not is_authenticated_user else request.user.email

    if request.method == 'POST':
        form = SetPasswordForm(request.POST)
        if form.is_valid():
            if is_authenticated_user:
                user = request.user
            else:
                # Use filter+first to handle edge case of duplicate emails in DB
                user = User.objects.filter(email__iexact=email).order_by('-date_joined').first()
                if not user:
                    messages.error(request, "Account not found. Please try again.")
                    return redirect('forgot_password')

            user.set_password(form.cleaned_data['password'])
            user.save()

            # Clean up session flags (no-op if keys don't exist)
            request.session.pop('forgot_password_email', None)
            request.session.pop('forgot_password_verified', None)

            messages.success(request, "Password updated successfully!")

            if is_authenticated_user:
                # Re-authenticate so the session stays valid after password change
                from django.contrib.auth import update_session_auth_hash
                update_session_auth_hash(request, user)
                return redirect_to_role_dashboard(user)
            else:
                messages.success(request, "You can now log in with your new password.")
                return redirect('login')
    else:
        form = SetPasswordForm()

    return render(request, 'inventory/reset_password.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('login')

@login_required
@admin_required
def register_view(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.username = generate_username_from_email(user.email)
            user.set_password(form.cleaned_data['password'])
            user.save()
            role = form.cleaned_data.get('role', 'STAFF')
            user.profile.role = role
            if role == 'ADMIN':
                user.is_staff = True
            user.profile.save()
            messages.success(request, f"User {user.username} created successfully!")
            return redirect('user_list')
    else:
        form = UserRegistrationForm()
    return render(request, 'inventory/register.html', {'form': form})

# Dashboard View
@login_required
def account_profile(request):
    if request.method == 'POST':
        form = UserAccountForm(request.POST, request.FILES, instance=request.user)
        position_data = request.POST.copy()
        position_data.setdefault(
            'avatar_position_x',
            str(request.user.profile.avatar_position_x),
        )
        position_data.setdefault(
            'avatar_position_y',
            str(request.user.profile.avatar_position_y),
        )
        position_form = AvatarPositionForm(position_data)
        if form.is_valid() and position_form.is_valid():
            form.save()
            profile = request.user.profile
            if 'avatar' in request.FILES:
                profile.avatar = request.FILES['avatar']
            profile.avatar_position_x = position_form.cleaned_data['avatar_position_x']
            profile.avatar_position_y = position_form.cleaned_data['avatar_position_y']
            profile.save()
            messages.success(request, "Your profile has been updated.")
            return redirect('account_profile')
    else:
        form = UserAccountForm(instance=request.user)
        position_form = AvatarPositionForm(initial={
            'avatar_position_x': request.user.profile.avatar_position_x,
            'avatar_position_y': request.user.profile.avatar_position_y,
        })
    return render(request, 'inventory/account_profile.html', {
        'form': form,
        'position_form': position_form,
    })

@login_required
@admin_required
@login_required
def seed_demo_data_view(request):
    from django.core.management import call_command
    try:
        call_command('seed_data')
        messages.success(request, "Sample demo data loaded successfully!")
    except Exception as e:
        messages.error(request, f"Failed to seed demo data: {e}")
    return redirect('dashboard')

@login_required
def reset_demo_data_view(request):
    from django.core.management import call_command
    try:
        call_command('clear_data')
        messages.info(request, "Inventory reset to fresh state! You can now experience the app as a first-time user.")
    except Exception as e:
        messages.error(request, f"Failed to reset data: {e}")
    return redirect('dashboard')

@login_required
def dashboard(request):
    return redirect_to_role_dashboard(request.user)

@login_required
@admin_required
def dashboard_admin(request):
    company = getattr(request.user.profile, 'company', None) if hasattr(request.user, 'profile') else None
    
    if company:
        products_qs = Product.objects.filter(company=company)
        categories_qs = Category.objects.filter(company=company)
        suppliers_qs = Supplier.objects.filter(company=company)
        transactions_qs = StockTransaction.objects.filter(company=company)
    else:
        products_qs = Product.objects.all()
        categories_qs = Category.objects.all()
        suppliers_qs = Supplier.objects.all()
        transactions_qs = StockTransaction.objects.all()
    team_members_count = UserProfile.objects.count()

    total_products = products_qs.count()
    category_count = categories_qs.count()
    supplier_count = suppliers_qs.count()

    total_stock_qty = products_qs.aggregate(total=Sum('quantity'))['total'] or 0
    total_valuation = products_qs.aggregate(
        total=Sum(F('price') * F('quantity'))
    )['total'] or 0

    all_products = products_qs.all()
    out_of_stock_count = sum(1 for p in all_products if p.stock_status == 'OUT_OF_STOCK')
    low_stock_count = sum(1 for p in all_products if p.stock_status == 'LOW_STOCK')
    in_stock_count = sum(1 for p in all_products if p.stock_status == 'IN_STOCK')

    low_stock_products = [p for p in all_products if p.stock_status in ['LOW_STOCK', 'OUT_OF_STOCK']][:5]

    recent_transactions = transactions_qs.select_related('product', 'user').order_by('-timestamp')[:8]

    categories = categories_qs.annotate(product_count=Count('products'))
    cat_names = [c.name for c in categories]
    cat_counts = [c.product_count for c in categories]

    stock_in_total = transactions_qs.filter(transaction_type='IN').aggregate(Sum('quantity'))['quantity__sum'] or 0
    stock_out_total = transactions_qs.filter(transaction_type='OUT').aggregate(Sum('quantity'))['quantity__sum'] or 0

    context = {
        'company': company,
        'total_products': total_products,
        'category_count': category_count,
        'supplier_count': supplier_count,
        'total_stock_qty': total_stock_qty,
        'total_valuation': total_valuation,
        'out_of_stock_count': out_of_stock_count,
        'low_stock_count': low_stock_count,
        'in_stock_count': in_stock_count,
        'low_stock_products': low_stock_products,
        'recent_transactions': recent_transactions,
        'cat_names': cat_names,
        'cat_counts': cat_counts,
        'stock_in_total': stock_in_total,
        'stock_out_total': stock_out_total,
        'team_members_count': team_members_count,
        'pending_approval_count': User.objects.filter(
            is_active=False,
            profile__role__in=('STAFF', 'MANAGER'),
        ).count(),
        'role_title': 'Administrator Control Dashboard',
    }
    return render(request, 'inventory/dashboard_admin.html', context)

@login_required
@manager_required
def dashboard_manager(request):
    company = getattr(request.user.profile, 'company', None) if hasattr(request.user, 'profile') else None

    if company:
        products_qs = Product.objects.filter(company=company)
        categories_qs = Category.objects.filter(company=company)
        suppliers_qs = Supplier.objects.filter(company=company)
        transactions_qs = StockTransaction.objects.filter(company=company)
    else:
        products_qs = Product.objects.all()
        categories_qs = Category.objects.all()
        suppliers_qs = Supplier.objects.all()
        transactions_qs = StockTransaction.objects.all()

    total_products = products_qs.count()
    category_count = categories_qs.count()
    supplier_count = suppliers_qs.count()

    total_stock_qty = products_qs.aggregate(total=Sum('quantity'))['total'] or 0
    total_valuation = products_qs.aggregate(
        total=Sum(F('price') * F('quantity'))
    )['total'] or 0

    all_products = products_qs.all()
    out_of_stock_count = sum(1 for p in all_products if p.stock_status == 'OUT_OF_STOCK')
    low_stock_count = sum(1 for p in all_products if p.stock_status == 'LOW_STOCK')

    recent_transactions = transactions_qs.select_related('product', 'user').order_by('-timestamp')[:6]
    low_stock_products = [p for p in all_products if p.stock_status in ['LOW_STOCK', 'OUT_OF_STOCK']][:5]

    categories = categories_qs.annotate(product_count=Count('products'))
    cat_names = [c.name for c in categories]
    cat_counts = [c.product_count for c in categories]

    stock_in_total = transactions_qs.filter(transaction_type='IN').aggregate(Sum('quantity'))['quantity__sum'] or 0
    stock_out_total = transactions_qs.filter(transaction_type='OUT').aggregate(Sum('quantity'))['quantity__sum'] or 0

    context = {
        'company': company,
        'total_products': total_products,
        'category_count': category_count,
        'supplier_count': supplier_count,
        'total_stock_qty': total_stock_qty,
        'total_valuation': total_valuation,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'recent_transactions': recent_transactions,
        'low_stock_products': low_stock_products,
        'cat_names': cat_names,
        'cat_counts': cat_counts,
        'stock_in_total': stock_in_total,
        'stock_out_total': stock_out_total,
        'role_title': 'Manager Operations Workspace',
    }
    return render(request, 'inventory/dashboard_manager.html', context)

@login_required
def dashboard_staff(request):
    company = getattr(request.user.profile, 'company', None) if hasattr(request.user, 'profile') else None

    if company:
        products_qs = Product.objects.filter(company=company)
        categories_qs = Category.objects.filter(company=company)
        suppliers_qs = Supplier.objects.filter(company=company)
        transactions_qs = StockTransaction.objects.filter(company=company)
    else:
        products_qs = Product.objects.all()
        categories_qs = Category.objects.all()
        suppliers_qs = Supplier.objects.all()
        transactions_qs = StockTransaction.objects.all()

    total_products = products_qs.count()
    total_stock_qty = products_qs.aggregate(total=Sum('quantity'))['total'] or 0
    
    my_transactions = transactions_qs.filter(user=request.user).select_related('product').order_by('-timestamp')[:5]
    recent_transactions = transactions_qs.select_related('product', 'user').order_by('-timestamp')[:6]

    all_products = products_qs.all()
    low_stock_products = [p for p in all_products if p.stock_status in ['LOW_STOCK', 'OUT_OF_STOCK']][:5]

    context = {
        'company': company,
        'total_products': total_products,
        'total_stock_qty': total_stock_qty,
        'my_transactions': my_transactions,
        'recent_transactions': recent_transactions,
        'low_stock_products': low_stock_products,
        'role_title': 'Staff Operations Portal',
    }
    return render(request, 'inventory/dashboard_staff.html', context)

# Category Management Views
@login_required
def category_list(request):
    query = request.GET.get('q', '')
    categories = Category.objects.annotate(product_count=Count('products'))
    if query:
        categories = categories.filter(name__icontains=query)
    
    paginator = Paginator(categories, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'inventory/category_list.html', {'page_obj': page_obj, 'query': query})

@login_required
@manager_required
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Category created successfully.")
            return redirect('category_list')
    else:
        form = CategoryForm()
    return render(request, 'inventory/category_form.html', {'form': form, 'title': 'Add Category'})

@login_required
@manager_required
def category_update(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, "Category updated successfully.")
            return redirect('category_list')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'inventory/category_form.html', {'form': form, 'title': 'Edit Category', 'category': category})

@login_required
@admin_required
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        category.delete()
        messages.success(request, "Category deleted successfully.")
        return redirect('category_list')
    return render(request, 'inventory/category_confirm_delete.html', {'category': category})

# Supplier Management Views
@login_required
def supplier_list(request):
    query = request.GET.get('q', '')
    suppliers = Supplier.objects.all()
    if query:
        suppliers = suppliers.filter(
            Q(name__icontains=query) | Q(email__icontains=query) | Q(phone__icontains=query)
        )
    
    paginator = Paginator(suppliers, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'inventory/supplier_list.html', {'page_obj': page_obj, 'query': query})

@login_required
@manager_required
def supplier_create(request):
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Supplier added successfully.")
            return redirect('supplier_list')
    else:
        form = SupplierForm()
    return render(request, 'inventory/supplier_form.html', {'form': form, 'title': 'Add Supplier'})

@login_required
@manager_required
def supplier_update(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            messages.success(request, "Supplier updated successfully.")
            return redirect('supplier_list')
    else:
        form = SupplierForm(instance=supplier)
    return render(request, 'inventory/supplier_form.html', {'form': form, 'title': 'Edit Supplier', 'supplier': supplier})

@login_required
@admin_required
def supplier_delete(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        supplier.delete()
        messages.success(request, "Supplier deleted successfully.")
        return redirect('supplier_list')
    return render(request, 'inventory/supplier_confirm_delete.html', {'supplier': supplier})

# Product Management Views
@login_required
def product_list(request):
    query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
    supplier_id = request.GET.get('supplier', '')
    status_filter = request.GET.get('status', '')

    products = Product.objects.select_related('category', 'supplier').all()

    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(sku__icontains=query) | Q(description__icontains=query)
        )
    if category_id:
        products = products.filter(category_id=category_id)
    if supplier_id:
        products = products.filter(supplier_id=supplier_id)

    # Filter in Python for status property if specified
    if status_filter:
        products = [p for p in products if p.stock_status == status_filter]

    paginator = Paginator(products, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    categories = Category.objects.all()
    suppliers = Supplier.objects.all()

    context = {
        'page_obj': page_obj,
        'query': query,
        'category_id': category_id,
        'supplier_id': supplier_id,
        'status_filter': status_filter,
        'categories': categories,
        'suppliers': suppliers,
    }
    return render(request, 'inventory/product_list.html', context)

@login_required
def product_detail(request, pk):
    product = get_object_or_404(Product.objects.select_related('category', 'supplier'), pk=pk)
    transactions = product.transactions.select_related('user').all()[:15]
    return render(request, 'inventory/product_detail.html', {
        'product': product,
        'transactions': transactions
    })

@login_required
@manager_required
def product_create(request):
    app_settings = GlobalSettings.get_solo()
    if request.method == 'POST':
        form = ProductForm(
            request.POST,
            request.FILES,
            currency_code=app_settings.currency_code,
            usd_to_khr_rate=app_settings.usd_to_khr_rate,
        )
        if form.is_valid():
            product = form.save()
            # If initial quantity > 0, log an initial stock transaction
            if product.quantity > 0:
                StockTransaction.objects.create(
                    product=product,
                    transaction_type='IN',
                    quantity=product.quantity,
                    user=request.user,
                    notes='Initial Stock Entry'
                )
            messages.success(request, f"Product '{product.name}' created successfully.")
            return redirect('product_list')
    else:
        form = ProductForm(
            currency_code=app_settings.currency_code,
            usd_to_khr_rate=app_settings.usd_to_khr_rate,
        )
    return render(request, 'inventory/product_form.html', {'form': form, 'title': 'Add Product'})

@login_required
@manager_required
def product_update(request, pk):
    app_settings = GlobalSettings.get_solo()
    product = get_object_or_404(Product, pk=pk)
    old_qty = product.quantity
    if request.method == 'POST':
        form = ProductForm(
            request.POST,
            request.FILES,
            instance=product,
            currency_code=app_settings.currency_code,
            usd_to_khr_rate=app_settings.usd_to_khr_rate,
        )
        if form.is_valid():
            updated_product = form.save()
            new_qty = updated_product.quantity
            # Record manual quantity adjustment if changed via edit form
            if new_qty != old_qty:
                diff = new_qty - old_qty
                ttype = 'IN' if diff > 0 else 'OUT'
                StockTransaction.objects.create(
                    product=updated_product,
                    transaction_type=ttype,
                    quantity=abs(diff),
                    user=request.user,
                    notes=f"Manual quantity adjustment in edit view ({old_qty} -> {new_qty})"
                )
            messages.success(request, f"Product '{product.name}' updated successfully.")
            return redirect('product_detail', pk=product.pk)
    else:
        form = ProductForm(
            instance=product,
            currency_code=app_settings.currency_code,
            usd_to_khr_rate=app_settings.usd_to_khr_rate,
        )
    return render(request, 'inventory/product_form.html', {'form': form, 'title': 'Edit Product', 'product': product})

@login_required
@admin_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.delete()
        messages.success(request, "Product deleted successfully.")
        return redirect('product_list')
    return render(request, 'inventory/product_confirm_delete.html', {'product': product})

# Inventory Stock Transaction Views
@login_required
def transaction_list(request):
    query = request.GET.get('q', '')
    ttype = request.GET.get('type', '')

    transactions_qs = StockTransaction.objects.select_related('product', 'user').all()

    if query:
        transactions_qs = transactions_qs.filter(
            Q(product__name__icontains=query) | Q(product__sku__icontains=query) | Q(notes__icontains=query)
        )
    if ttype:
        transactions_qs = transactions_qs.filter(transaction_type=ttype)

    paginator = Paginator(transactions_qs, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'inventory/transaction_list.html', {
        'page_obj': page_obj,
        'query': query,
        'ttype': ttype,
    })

@login_required
def transaction_create(request):
    if request.method == 'POST':
        form = StockTransactionForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                trans = form.save(commit=False)
                trans.user = request.user
                prod = trans.product

                if trans.transaction_type == 'IN':
                    prod.quantity += trans.quantity
                elif trans.transaction_type == 'OUT':
                    prod.quantity -= trans.quantity
                
                prod.save()
                trans.save()

            messages.success(request, f"Transaction recorded! {trans.get_transaction_type_display()} of {trans.quantity} x {prod.name}.")
            return redirect('transaction_list')
    else:
        initial_prod = request.GET.get('product')
        form = StockTransactionForm(initial={'product': initial_prod} if initial_prod else None)
    
    return render(request, 'inventory/transaction_form.html', {'form': form, 'title': 'Record Stock Transaction'})

@login_required
def stock_in_view(request):
    if request.method == 'POST':
        form = StockInForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                trans = form.save(commit=False)
                trans.transaction_type = 'IN'
                trans.user = request.user
                trans.product.quantity += trans.quantity
                trans.product.save()
                trans.save()
            messages.success(request, f"Stock In recorded: +{trans.quantity} × {trans.product.name}.")
            return redirect('stock_in')
    else:
        form = StockInForm()
    return render(request, 'inventory/stock_in.html', {'form': form})

@login_required
def stock_out_view(request):
    if request.method == 'POST':
        form = StockOutForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                trans = form.save(commit=False)
                trans.transaction_type = 'OUT'
                trans.user = request.user
                trans.product.quantity -= trans.quantity
                trans.product.save()
                trans.save()
            messages.success(request, f"Stock Out recorded: -{trans.quantity} × {trans.product.name}.")
            return redirect('stock_out')
    else:
        form = StockOutForm()
    return render(request, 'inventory/stock_out.html', {'form': form})

@login_required
def stock_transfer_view(request):
    if request.method == 'POST':
        form = StockTransferForm(request.POST)
        if form.is_valid():
            from_product = form.cleaned_data['from_product']
            to_product   = form.cleaned_data['to_product']
            qty          = form.cleaned_data['quantity']
            notes        = form.cleaned_data.get('notes', '')
            with transaction.atomic():
                # Deduct from source
                from_product.quantity -= qty
                from_product.save()
                StockTransaction.objects.create(
                    product=from_product, transaction_type='OUT',
                    quantity=qty, user=request.user,
                    notes=f"Transfer OUT → {to_product.name}. {notes}".strip('. '),
                )
                # Add to destination
                to_product.quantity += qty
                to_product.save()
                StockTransaction.objects.create(
                    product=to_product, transaction_type='IN',
                    quantity=qty, user=request.user,
                    notes=f"Transfer IN ← {from_product.name}. {notes}".strip('. '),
                )
            messages.success(request, f"Transferred {qty} units from '{from_product.name}' to '{to_product.name}'.")
            return redirect('stock_transfer')
    else:
        form = StockTransferForm()
    return render(request, 'inventory/stock_transfer.html', {'form': form})

# Reports and Export Views
def _report_currency(amount, app_settings, pdf=False):
    rendered = format_currency(
        amount,
        app_settings.currency_code,
        app_settings.usd_to_khr_rate,
    )
    if pdf and app_settings.currency_code == 'KHR':
        return rendered.replace('៛', 'KHR ', 1)
    return rendered


@login_required
def reports_dashboard(request):
    all_products = Product.objects.select_related('category', 'supplier').all()
    low_stock_products = [p for p in all_products if p.stock_status in ['LOW_STOCK', 'OUT_OF_STOCK']]

    return render(request, 'inventory/reports.html', {
        'low_stock_count': len(low_stock_products),
        'total_products': len(all_products),
        'low_stock_products': low_stock_products,
    })

@login_required
def export_inventory_csv(request):
    app_settings = GlobalSettings.get_solo()
    currency_name = 'KHR' if app_settings.currency_code == 'KHR' else 'USD'
    products = Product.objects.select_related('category', 'supplier').all()
    headers = ['SKU', 'Product Name', 'Category', 'Supplier', f'Price ({currency_name})', 'Quantity', 'Status', f'Total Value ({currency_name})']
    rows = [
        [p.sku, p.name, p.category.name, p.supplier.name if p.supplier else 'N/A',
         _report_currency(p.price, app_settings), p.quantity, p.stock_status_display,
         _report_currency(p.total_value, app_settings)]
        for p in products
    ]
    return generate_csv_report('inventory_report', headers, rows)

@login_required
def export_inventory_pdf(request):
    app_settings = GlobalSettings.get_solo()
    currency_name = 'KHR' if app_settings.currency_code == 'KHR' else 'USD'
    products = Product.objects.select_related('category', 'supplier').all()
    headers = ['SKU', 'Product Name', 'Category', f'Price ({currency_name})', 'Qty', 'Status', f'Total Value ({currency_name})']
    rows = [
        [p.sku, p.name[:25], p.category.name[:15], _report_currency(p.price, app_settings, pdf=True),
         str(p.quantity), p.stock_status_display, _report_currency(p.total_value, app_settings, pdf=True)]
        for p in products
    ]
    return generate_pdf_report('Full Inventory Stock Report', headers, rows, 'inventory_report')

@login_required
def export_low_stock_csv(request):
    products = [p for p in Product.objects.select_related('category', 'supplier').all() if p.stock_status in ['LOW_STOCK', 'OUT_OF_STOCK']]
    headers = ['SKU', 'Product Name', 'Category', 'Quantity', 'Min Stock Level', 'Status']
    rows = [
        [p.sku, p.name, p.category.name, p.quantity, p.min_stock_level, p.stock_status_display]
        for p in products
    ]
    return generate_csv_report('low_stock_report', headers, rows)

@login_required
def export_low_stock_pdf(request):
    products = [p for p in Product.objects.select_related('category', 'supplier').all() if p.stock_status in ['LOW_STOCK', 'OUT_OF_STOCK']]
    headers = ['SKU', 'Product Name', 'Category', 'Qty', 'Min Req.', 'Status']
    rows = [
        [p.sku, p.name[:25], p.category.name[:15], str(p.quantity), str(p.min_stock_level), p.stock_status_display]
        for p in products
    ]
    return generate_pdf_report('Low Stock & Out of Stock Report', headers, rows, 'low_stock_report')

@login_required
def export_transactions_csv(request):
    transactions = StockTransaction.objects.select_related('product', 'user').all()
    headers = ['Date & Time', 'Product Name', 'SKU', 'Type', 'Quantity', 'User', 'Notes']
    rows = [
        [t.timestamp.strftime('%Y-%m-%d %H:%M'), t.product.name, t.product.sku, t.get_transaction_type_display(), t.quantity, t.user.username if t.user else 'System', t.notes or '']
        for t in transactions
    ]
    return generate_csv_report('stock_transactions_report', headers, rows)

@login_required
def export_transactions_pdf(request):
    transactions = StockTransaction.objects.select_related('product', 'user').all()[:100] # Cap top 100 for PDF layout
    headers = ['Timestamp', 'Product', 'Type', 'Qty', 'User', 'Notes']
    rows = [
        [t.timestamp.strftime('%Y-%m-%d %H:%M'), t.product.name[:20], t.get_transaction_type_display(), str(t.quantity), t.user.username if t.user else 'N/A', (t.notes or '')[:20]]
        for t in transactions
    ]
    return generate_pdf_report('Stock Movement Transaction History', headers, rows, 'stock_transactions_report')

# User Management Views (Admin only)
@login_required
@admin_required
def user_list(request):
    pending_users = User.objects.filter(
        is_active=False,
        profile__role__in=('STAFF', 'MANAGER'),
    )
    pending_approval_count = pending_users.count()
    showing_requests = request.GET.get('status') == 'pending'
    users = User.objects.select_related('profile').all()
    if showing_requests:
        users = users.filter(
            is_active=False,
            profile__role__in=('STAFF', 'MANAGER'),
        )
    users = users.order_by('-date_joined')
    return render(request, 'inventory/user_list.html', {
        'users': users,
        'pending_approval_count': pending_approval_count,
        'showing_requests': showing_requests,
    })

@login_required
@admin_required
def user_approve(request, pk):
    if request.method != 'POST':
        return redirect('user_list')

    user_obj = get_object_or_404(
        User.objects.select_related('profile'),
        pk=pk,
        is_active=False,
        profile__role__in=('STAFF', 'MANAGER'),
    )
    user_obj.is_active = True
    user_obj.save(update_fields=['is_active'])
    messages.success(request, f"Account for @{user_obj.username} has been approved.")
    return redirect(f"{reverse('user_list')}#employees-table")

@login_required
@admin_required
def user_toggle_role(request, pk):
    if request.method != 'POST':
        return redirect('user_list')

    user_obj = get_object_or_404(User, pk=pk)
    if user_obj == request.user:
        messages.error(request, "You cannot modify your own role!")
        return redirect('user_list')
    
    profile = user_obj.profile
    if profile.role == 'ADMIN':
        profile.role = 'STAFF'
        user_obj.is_staff = False
    else:
        profile.role = 'ADMIN'
        user_obj.is_staff = True

    profile.save()
    user_obj.save()
    messages.success(request, f"Role for {user_obj.username} updated to {profile.get_role_display()}.")
    return redirect('user_list')

@login_required
@admin_required
def user_delete(request, pk):
    if request.method != 'POST':
        return redirect('user_list')

    user_obj = get_object_or_404(User, pk=pk)
    if user_obj == request.user:
        messages.error(request, "You cannot delete your own account!")
        return redirect('user_list')

    username = user_obj.username
    user_obj.delete()
    messages.success(request, f"User @{username} was removed.")
    return redirect('user_list')

@login_required
@admin_required
def user_edit(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    from .models import UserProfile
    profile = user_obj.profile

    if request.method == 'POST':
        # Update user fields
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        role = request.POST.get('role', '').strip()

        # Email uniqueness check (allow blank)
        if email and User.objects.filter(email__iexact=email).exclude(pk=pk).exists():
            messages.error(request, "An account with that email already exists.")
            return render(request, 'inventory/user_edit.html', {'u': user_obj, 'profile': profile, 'role_choices': UserProfile.ROLE_CHOICES})

        user_obj.email = email
        user_obj.first_name = first_name
        user_obj.last_name = last_name
        user_obj.save()

        # Update avatar
        if 'avatar' in request.FILES:
            profile.avatar = request.FILES['avatar']

        # Update role
        if role in dict(UserProfile.ROLE_CHOICES):
            profile.role = role
            user_obj.is_staff = (role == 'ADMIN')
            user_obj.save()

        profile.save()
        messages.success(request, f"Profile for @{user_obj.username} updated successfully.")
        return redirect('user_list')

    return render(request, 'inventory/user_edit.html', {
        'u': user_obj,
        'profile': profile,
        'role_choices': UserProfile.ROLE_CHOICES,
    })
