from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from inventory.forms import UserSignUpForm, ProductForm
from inventory.currency import format_currency
from inventory.models import Product, Category, StockTransaction, GlobalSettings, Company


class AccountProfileTests(TestCase):
    def test_profile_is_not_linked_from_sidebar(self):
        user = User.objects.create_user(
            username='sidebar-user',
            email='sidebar.user@example.com',
            password='test-password-123',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('dashboard_staff'))

        self.assertNotContains(response, f'href="{reverse("account_profile")}"')
        self.assertNotContains(response, 'data-en="ACCOUNT"')
        self.assertNotContains(response, 'data-en="Profile"')

    def test_avatar_position_is_saved_and_rendered(self):
        user = User.objects.create_user(
            username='avatar-user',
            email='avatar.user@example.com',
            password='test-password-123',
        )
        self.client.force_login(user)

        response = self.client.post(reverse('account_profile'), {
            'first_name': 'Avatar',
            'last_name': 'User',
            'email': 'avatar.user@example.com',
            'avatar_position_x': '25',
            'avatar_position_y': '70',
        })

        self.assertRedirects(response, reverse('account_profile'))
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.avatar_position_x, 25)
        self.assertEqual(user.profile.avatar_position_y, 70)
        response = self.client.get(reverse('account_profile'))
        self.assertContains(response, 'name="avatar_position_x" value="25"')
        self.assertContains(response, 'name="avatar_position_y" value="70"')

    def test_avatar_position_rejects_values_outside_range(self):
        user = User.objects.create_user(
            username='bounded-avatar-user',
            email='bounded.avatar@example.com',
            password='test-password-123',
        )
        self.client.force_login(user)

        response = self.client.post(reverse('account_profile'), {
            'first_name': 'Bounded',
            'last_name': 'Avatar',
            'email': 'bounded.avatar@example.com',
            'avatar_position_x': '101',
            'avatar_position_y': '-1',
        })

        self.assertEqual(response.status_code, 200)
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.avatar_position_x, 50)
        self.assertEqual(user.profile.avatar_position_y, 50)

    def test_signup_and_profile_forms_do_not_allow_username_editing(self):
        signup_response = self.client.get(reverse('signup'))
        self.assertNotContains(signup_response, 'name="username"')

        user = User.objects.create_user(
            username='newuser',
            email='new.user@example.com',
            password='test-password-123',
        )
        self.client.force_login(user)
        self.assertNotContains(self.client.get(reverse('account_profile')), 'name="username"')

        response = self.client.post(reverse('account_profile'), {
            'username': 'custom-username',
            'first_name': 'New',
            'last_name': 'User',
            'email': 'new.user@example.com',
        })
        self.assertRedirects(response, reverse('account_profile'))
        user.refresh_from_db()
        self.assertEqual(user.username, 'newuser')


class LoginFeatureEntryTests(TestCase):
    def test_public_auth_pages_do_not_show_user_management_promotion(self):
        for page in ('login', 'signup'):
            with self.subTest(page=page):
                response = self.client.get(reverse(page))
                self.assertNotContains(response, 'User Management')
                self.assertNotContains(response, 'Sign in to manage users')

    def test_sign_in_returns_admin_to_user_management_destination(self):
        admin = User.objects.create_user(
            username='entry-admin',
            email='entry-admin@example.com',
            password='admin-password',
        )
        admin.profile.role = 'ADMIN'
        admin.profile.save()

        response = self.client.post(
            f'{reverse("login")}?next={reverse("user_list")}',
            {'username': admin.email, 'password': 'admin-password'},
        )

        self.assertRedirects(
            response,
            f"{reverse('user_list')}#employees-table",
        )

    def test_login_rejects_external_next_destination(self):
        admin = User.objects.create_user(
            username='safe-admin',
            email='safe-admin@example.com',
            password='admin-password',
        )
        admin.profile.role = 'ADMIN'
        admin.profile.save()

        response = self.client.post(
            reverse('login'),
            {
                'username': admin.email,
                'password': 'admin-password',
                'next': 'https://example.com/',
            },
        )

        self.assertRedirects(response, reverse('dashboard_admin'))


class UserManagementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin', password='admin-password')
        self.admin.profile.role = 'ADMIN'
        self.admin.profile.save()
        self.client.force_login(self.admin)
        self.user = User.objects.create_user(username='team-member', password='user-password')

    def test_admin_can_remove_another_user_and_preserve_transaction_history(self):
        category = Category.objects.create(name='Test category')
        product = Product.objects.create(
            name='Test product',
            sku='TEST-1',
            category=category,
            price='1.00',
        )
        transaction = StockTransaction.objects.create(
            product=product,
            transaction_type='IN',
            quantity=1,
            user=self.user,
        )

        response = self.client.post(reverse('user_delete', args=[self.user.pk]))

        self.assertRedirects(response, reverse('user_list'))
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())
        transaction.refresh_from_db()
        self.assertIsNone(transaction.user)

    def test_admin_cannot_remove_own_account(self):
        response = self.client.post(reverse('user_delete', args=[self.admin.pk]))

        self.assertRedirects(response, reverse('user_list'))
        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())

    def test_get_request_does_not_toggle_user_role(self):
        response = self.client.get(reverse('user_toggle_role', args=[self.user.pk]))

        self.assertRedirects(response, reverse('user_list'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.profile.role, 'STAFF')

    def test_admin_can_toggle_user_role_with_post(self):
        response = self.client.post(reverse('user_toggle_role', args=[self.user.pk]))

        self.assertRedirects(response, reverse('user_list'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.profile.role, 'ADMIN')

    def test_user_list_shows_remove_action_only_for_other_accounts(self):
        response = self.client.get(reverse('user_list'))

        self.assertContains(response, reverse('user_delete', args=[self.user.pk]))
        self.assertNotContains(response, reverse('user_delete', args=[self.admin.pk]))
        self.assertContains(response, 'Employee')

    def test_admin_dashboard_team_card_links_to_team_list_and_counts_all_managed_users(self):
        company = Company.objects.create(name='Admin Company')
        self.admin.profile.company = company
        self.admin.profile.save()

        response = self.client.get(reverse('dashboard_admin'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['team_members_count'], User.objects.count())
        self.assertContains(
            response,
            f'href="{reverse("user_list")}" class="text-decoration-none text-primary"',
        )
        self.assertContains(response, 'Manage Team')

    def test_approving_request_shows_user_as_active_in_all_employees(self):
        pending_user = User.objects.create_user(
            username='new-manager',
            email='new.manager@example.com',
            password='manager-password',
            is_active=False,
            first_name='New',
            last_name='Manager',
        )
        pending_user.profile.role = 'MANAGER'
        pending_user.profile.save()

        response = self.client.post(reverse('user_approve', args=[pending_user.pk]))

        self.assertRedirects(
            response,
            f"{reverse('user_list')}#employees-table",
        )
        pending_user.refresh_from_db()
        self.assertTrue(pending_user.is_active)

        response = self.client.get(reverse('user_list'))
        self.assertContains(response, 'New Manager')
        self.assertContains(response, 'Active')
        self.assertNotContains(response, f'Approve {pending_user.username}')
        self.assertNotContains(response, 'Pending approval')

    def test_admin_user_edit_does_not_offer_or_accept_username_changes(self):
        response = self.client.get(reverse('user_edit', args=[self.user.pk]))
        self.assertNotContains(response, 'name="username"')

        response = self.client.post(reverse('user_edit', args=[self.user.pk]), {
            'username': 'changed-username',
            'email': self.user.email,
            'first_name': 'Team',
            'last_name': 'Member',
            'role': 'STAFF',
        })

        self.assertRedirects(response, reverse('user_list'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'team-member')

    def test_manager_role_is_saved_and_displayed_in_user_list(self):
        response = self.client.post(reverse('user_edit', args=[self.user.pk]), {
            'email': self.user.email,
            'first_name': 'Team',
            'last_name': 'Manager',
            'role': 'MANAGER',
        })

        self.assertRedirects(response, reverse('user_list'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.profile.role, 'MANAGER')
        response = self.client.get(reverse('user_list'))
        self.assertContains(response, 'badge-manager">Manager</span>')

    def test_admin_registration_hides_username_and_generates_it_from_email(self):
        response = self.client.get(reverse('register'))
        self.assertNotContains(response, 'name="username"')

        response = self.client.post(reverse('register'), {
            'email': 'new.member@example.com',
            'first_name': 'New',
            'last_name': 'Member',
            'role': 'STAFF',
            'password': 'new-password-123',
            'confirm_password': 'new-password-123',
        })

        self.assertRedirects(response, reverse('user_list'))
        user = User.objects.get(email='new.member@example.com')
        self.assertEqual(user.username, 'newmember')
        self.assertTrue(user.is_active)

    def test_get_request_does_not_remove_user(self):
        response = self.client.get(reverse('user_delete', args=[self.user.pk]))

        self.assertRedirects(response, reverse('user_list'))
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_staff_cannot_remove_users(self):
        staff = User.objects.create_user(username='staff', password='staff-password')
        self.client.force_login(staff)

        response = self.client.post(reverse('user_delete', args=[self.user.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('dashboard'))
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())


class SignupApprovalTests(TestCase):
    def test_signup_position_field_starts_with_required_placeholder(self):
        response = self.client.get(reverse('signup'))

        self.assertContains(response, '<option value="" selected>Select your position</option>', html=True)
        self.assertContains(response, 'name="role"')

    def test_message_requests_button_filters_pending_signups(self):
        admin = User.objects.create_user(username='request-admin', password='admin-password')
        admin.profile.role = 'ADMIN'
        admin.profile.save()
        pending_user = User.objects.create_user(
            username='pending-manager',
            email='pending.manager@example.com',
            password='pending-password-123',
            is_active=False,
        )
        pending_user.profile.role = 'MANAGER'
        pending_user.profile.save()
        active_user = User.objects.create_user(
            username='active-staff',
            email='active.staff@example.com',
            password='active-password-123',
        )
        self.client.force_login(admin)

        response = self.client.get(f"{reverse('user_list')}?status=pending")

        self.assertContains(response, 'aria-label="Message Requests: 1 pending"')
        self.assertContains(response, 'class="message-requests-count"')
        self.assertContains(response, 'pending.manager@example.com')
        self.assertContains(response, reverse('user_approve', args=[pending_user.pk]))
        self.assertNotContains(response, 'active.staff@example.com')
        self.assertNotContains(response, '<div class="text-muted small">@pending-manager</div>')

    def test_public_signup_form_does_not_allow_admin_role(self):
        roles = dict(UserSignUpForm().fields['role'].choices)

        self.assertIn('STAFF', roles)
        self.assertIn('MANAGER', roles)
        self.assertNotIn('ADMIN', roles)
        response = self.client.get(reverse('signup'))
        self.assertNotContains(response, '<option value="ADMIN">')

    def test_verified_signup_creates_inactive_account_and_requires_approval(self):
        session = self.client.session
        session['pending_signup'] = {
            'email': 'pending.manager@example.com',
            'first_name': 'Pending',
            'last_name': 'Manager',
            'role': 'MANAGER',
        }
        session['otp_verified'] = True
        session.save()

        response = self.client.post(reverse('set_password'), {
            'password': 'pending-password-123',
            'confirm_password': 'pending-password-123',
        })

        self.assertRedirects(response, reverse('approval_pending'))
        user = User.objects.get(email='pending.manager@example.com')
        self.assertFalse(user.is_active)
        self.assertEqual(user.profile.role, 'MANAGER')
        self.assertFalse(self.client.session.get('_auth_user_id'))
        self.assertRedirects(
            self.client.get(reverse('dashboard')),
            f"{reverse('login')}?next={reverse('dashboard')}",
        )

    def test_inactive_account_cannot_sign_in_and_sees_approval_message(self):
        user = User.objects.create_user(
            username='pending-staff',
            email='pending.staff@example.com',
            password='pending-password-123',
            is_active=False,
        )
        user.profile.role = 'STAFF'
        user.profile.save()

        response = self.client.post(reverse('login'), {
            'username': user.email,
            'password': 'pending-password-123',
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        self.assertContains(response, 'administrator must approve your account')

    def test_admin_can_approve_pending_staff_or_manager(self):
        admin = User.objects.create_user(username='approver', password='admin-password')
        admin.profile.role = 'ADMIN'
        admin.profile.save()
        pending_user = User.objects.create_user(
            username='pending-staff',
            email='pending.staff@example.com',
            password='pending-password-123',
            is_active=False,
        )
        pending_user.profile.role = 'STAFF'
        pending_user.profile.save()
        self.client.force_login(admin)
        self.assertContains(
            self.client.get(reverse('user_list')),
            reverse('user_approve', args=[pending_user.pk]),
        )

        response = self.client.post(reverse('user_approve', args=[pending_user.pk]))

        self.assertRedirects(
            response,
            f"{reverse('user_list')}#employees-table",
        )
        pending_user.refresh_from_db()
        self.assertTrue(pending_user.is_active)
        self.client.logout()
        login_response = self.client.post(reverse('login'), {
            'username': pending_user.email,
            'password': 'pending-password-123',
        })
        self.assertEqual(login_response.status_code, 302)
        self.assertEqual(login_response.url, reverse('dashboard_staff'))

    def test_non_admin_cannot_approve_pending_account(self):
        staff = User.objects.create_user(username='staff-approver', password='staff-password')
        pending_user = User.objects.create_user(
            username='pending-staff',
            email='pending.staff@example.com',
            password='pending-password-123',
            is_active=False,
        )
        self.client.force_login(staff)

        response = self.client.post(reverse('user_approve', args=[pending_user.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('dashboard'))
        pending_user.refresh_from_db()
        self.assertFalse(pending_user.is_active)


class SettingsAndCurrencyTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='settings-admin', password='admin-password')
        self.admin.profile.role = 'ADMIN'
        self.admin.profile.save()
        self.client.force_login(self.admin)

    def test_admin_can_choose_currency_and_edit_exchange_rate(self):
        response = self.client.post(reverse('settings'), {
            'currency_code': 'KHR',
            'usd_to_khr_rate': '4100.50',
        })

        self.assertRedirects(response, reverse('settings'))
        app_settings = GlobalSettings.get_solo()
        self.assertEqual(app_settings.currency_code, 'KHR')
        self.assertEqual(app_settings.usd_to_khr_rate, Decimal('4100.50'))

    def test_currency_settings_hides_redundant_card_heading_and_description(self):
        response = self.client.get(reverse('currency_settings'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Display currency')
        self.assertContains(response, 'KHR / $')
        self.assertContains(response, 'USD ($)')
        self.assertContains(response, 'KHR (៛)')
        self.assertNotContains(
            response,
            'Choose which currency is displayed throughout the application.',
        )

    def test_settings_contains_team_management_link_under_settings(self):
        response = self.client.get(reverse('settings'))

        self.assertContains(response, reverse('user_list'))
        self.assertEqual(reverse('user_list'), '/settings/users/')
        self.assertContains(response, 'Team Management')
        html = response.content.decode()
        self.assertIn(f'href="{reverse("user_list")}"', html)
        self.assertIn(f'href="{reverse("currency_settings")}"', html)
        self.assertIn('settings-card-link', html)
        self.assertNotContains(response, 'Manage Team')
        self.assertNotContains(response, 'Manage Currency')

    def test_non_admin_cannot_access_settings(self):
        staff = User.objects.create_user(username='settings-staff', password='staff-password')
        self.client.force_login(staff)

        response = self.client.get(reverse('settings'))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('dashboard'))

    def test_product_form_converts_khr_input_to_usd_and_displays_stored_usd_as_khr(self):
        category = Category.objects.create(name='Currency test')
        form = ProductForm(
            data={
                'name': 'KHR-priced product',
                'sku': 'KHR-1',
                'category': category.pk,
                'supplier': '',
                'description': '',
                'price': '4000',
                'quantity': '1',
                'min_stock_level': '0',
            },
            currency_code='KHR',
            usd_to_khr_rate=Decimal('4000.00'),
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['price'], Decimal('1.00'))

        product = Product.objects.create(
            name='USD-priced product',
            sku='USD-1',
            category=category,
            price=Decimal('1.00'),
        )
        edit_form = ProductForm(
            instance=product,
            currency_code='KHR',
            usd_to_khr_rate=Decimal('4000.00'),
        )
        self.assertEqual(edit_form['price'].value(), Decimal('4000'))

    def test_product_views_use_selected_currency_for_display_and_entry(self):
        app_settings = GlobalSettings.get_solo()
        app_settings.currency_code = 'KHR'
        app_settings.usd_to_khr_rate = Decimal('4000.00')
        app_settings.save()
        category = Category.objects.create(name='Displayed price category')
        product = Product.objects.create(
            name='Displayed price product',
            sku='DISPLAY-1',
            category=category,
            price=Decimal('2.00'),
            quantity=1,
        )

        list_response = self.client.get(reverse('product_list'))
        self.assertContains(list_response, '៛8,000')

        edit_response = self.client.get(reverse('product_update', args=[product.pk]))
        self.assertContains(edit_response, 'Price (៛) *')
        self.assertContains(edit_response, 'value="8000"')

        create_response = self.client.post(reverse('product_create'), {
            'name': 'Submitted in Riel',
            'sku': 'KHR-SUBMIT-1',
            'category': category.pk,
            'supplier': '',
            'description': '',
            'price': '12000',
            'quantity': '0',
            'min_stock_level': '0',
        })
        self.assertRedirects(create_response, reverse('product_list'))
        self.assertEqual(Product.objects.get(sku='KHR-SUBMIT-1').price, Decimal('3.00'))

    def test_currency_format_uses_selected_display_currency(self):
        self.assertEqual(
            format_currency(Decimal('1.50'), 'USD', Decimal('4000.00')),
            '$1.50',
        )
        self.assertEqual(
            format_currency(Decimal('1.50'), 'KHR', Decimal('4000.00')),
            '៛6,000',
        )
