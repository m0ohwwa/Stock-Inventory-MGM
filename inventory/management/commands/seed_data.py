from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from inventory.models import Category, Supplier, Product, StockTransaction, UserProfile
from decimal import Decimal
import random

class Command(BaseCommand):
    help = 'Seeds initial sample data for Stock Inventory Management System'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE('Starting database seed...'))

        # 1. Create Superuser / Admin & Staff
        admin_user, created_admin = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@inventory.com',
                'first_name': 'System',
                'last_name': 'Administrator',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created_admin:
            admin_user.set_password('admin123')
            admin_user.save()
            admin_user.profile.role = 'ADMIN'
            admin_user.profile.save()
            self.stdout.write(self.style.SUCCESS('Created Admin user: admin / admin123'))
        else:
            self.stdout.write('Admin user already exists.')

        staff_user, created_staff = User.objects.get_or_create(
            username='staff',
            defaults={
                'email': 'staff@inventory.com',
                'first_name': 'John',
                'last_name': 'Warehouse',
                'is_staff': False,
                'is_superuser': False
            }
        )
        if created_staff:
            staff_user.set_password('staff123')
            staff_user.save()
            staff_user.profile.role = 'STAFF'
            staff_user.profile.save()
            self.stdout.write(self.style.SUCCESS('Created Staff user: staff / staff123'))
        else:
            self.stdout.write('Staff user already exists.')

        # 2. Categories
        categories_data = [
            ('Electronics & Gadgets', 'Computing hardware, gadgets, mobile accessories, and electronic components.'),
            ('Office Furniture', 'Desks, ergonomic chairs, storage cabinets, and conference room fixtures.'),
            ('Stationery & Supplies', 'Paper, writing instruments, organizers, and everyday office consumables.'),
            ('Tools & Hardware', 'Power tools, safety equipment, maintenance machinery, and hand tools.'),
            ('Apparel & Safety Gear', 'High-visibility vests, protective helmets, gloves, and uniforms.')
        ]

        categories_dict = {}
        for name, desc in categories_data:
            cat, _ = Category.objects.get_or_create(name=name, defaults={'description': desc})
            categories_dict[name] = cat
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(categories_dict)} categories."))

        # 3. Suppliers
        suppliers_data = [
            ('TechSupply Global Ltd', '+1 (555) 234-5678', 'orders@techsupply.com', '100 Innovation Way, Silicon Valley, CA'),
            ('Apex Industrial Solutions', '+1 (555) 876-5432', 'sales@apexindustrial.com', '458 Logistics Blvd, Chicago, IL'),
            ('Horizon Office Supplies', '+1 (555) 345-6789', 'contact@horizonoffice.com', '789 Business Parkway, Atlanta, GA'),
            ('Metro Safety & Hardware', '+1 (555) 987-6543', 'info@metrosafety.com', '12 Industry Road, Dallas, TX'),
        ]

        suppliers_list = []
        for name, phone, email, addr in suppliers_data:
            sup, _ = Supplier.objects.get_or_create(
                name=name,
                defaults={'phone': phone, 'email': email, 'address': addr}
            )
            suppliers_list.append(sup)
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(suppliers_list)} suppliers."))

        # 4. Products (Including Normal, Low Stock, and Out of Stock)
        products_data = [
            # In Stock
            ('Dell UltraSharp 27" 4K Monitor', 'PROD-ELE-001', 'Electronics & Gadgets', 499.99, 45, 10, 'Ultra HD IPS Display with USB-C Hub'),
            ('Logitech MX Master 3S Mouse', 'PROD-ELE-002', 'Electronics & Gadgets', 99.99, 120, 15, 'Ergonomic wireless mouse with quiet click feature'),
            ('Ergonomic Mesh Task Chair', 'PROD-FUR-001', 'Office Furniture', 249.50, 30, 8, 'High back lumbar support office chair'),
            ('Standing Executive Desk', 'PROD-FUR-002', 'Office Furniture', 599.00, 15, 5, 'Dual motor electric height adjustable desk'),
            ('A4 Multipurpose Copy Paper (Box)', 'PROD-STA-001', 'Stationery & Supplies', 38.00, 200, 25, '10 reams per box, 80gsm bright white paper'),
            ('DeWalt 20V Cordless Drill Kit', 'PROD-TOO-001', 'Tools & Hardware', 179.00, 28, 5, 'Brushless drill/driver kit with 2 batteries'),
            ('Heavy-Duty Protective Helmet', 'PROD-APP-001', 'Apparel & Safety Gear', 29.99, 85, 15, 'ANSI certified hard hat with adjustable strap'),

            # Low Stock
            ('Mechanical Gaming Keyboard RGB', 'PROD-ELE-003', 'Electronics & Gadgets', 129.99, 4, 10, 'Tactile mechanical switches with custom lighting'),
            ('Steel Storage Filing Cabinet', 'PROD-FUR-003', 'Office Furniture', 189.00, 3, 5, '4-drawer lockable steel file organizer'),
            ('High-Vis Safety Vest (XL)', 'PROD-APP-002', 'Apparel & Safety Gear', 14.50, 5, 12, 'Reflective zipper security vest'),

            # Out of Stock
            ('MacBook Pro 16" M3 Max', 'PROD-ELE-004', 'Electronics & Gadgets', 3499.00, 0, 5, 'High performance workstation laptop'),
            ('Digital Laser Measure Tape', 'PROD-TOO-002', 'Tools & Hardware', 65.00, 0, 8, '165ft accuracy laser distance meter'),
        ]

        created_prods = []
        for name, sku, cat_name, price, qty, min_lvl, desc in products_data:
            prod, created = Product.objects.get_or_create(
                sku=sku,
                defaults={
                    'name': name,
                    'category': categories_dict[cat_name],
                    'supplier': random.choice(suppliers_list),
                    'price': Decimal(str(price)),
                    'quantity': qty,
                    'min_stock_level': min_lvl,
                    'description': desc
                }
            )
            created_prods.append(prod)

        self.stdout.write(self.style.SUCCESS(f"Seeded {len(created_prods)} sample products."))

        # 5. Stock Transactions
        # Initial Stock In for products
        for prod in created_prods:
            if prod.quantity > 0:
                StockTransaction.objects.get_or_create(
                    product=prod,
                    transaction_type='IN',
                    quantity=prod.quantity,
                    defaults={
                        'user': admin_user,
                        'notes': 'Initial inventory restock shipment'
                    }
                )

        # Add a couple of Stock Out transactions
        stock_out_samples = [
            (created_prods[0], 5, 'Dispatched to Engineering Dept'),
            (created_prods[1], 10, 'Sales order fulfillment #1042'),
            (created_prods[2], 2, 'New employee onboarding allocation'),
        ]

        for prod, qty, notes in stock_out_samples:
            StockTransaction.objects.create(
                product=prod,
                transaction_type='OUT',
                quantity=qty,
                user=staff_user,
                notes=notes
            )

        self.stdout.write(self.style.SUCCESS('Successfully completed database seeding!'))
