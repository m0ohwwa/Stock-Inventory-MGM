# Stock Inventory Management System

A modern, full-featured **Stock Inventory Management System** built with **Django**, **SQLite / MySQL**, **Bootstrap 5**, and **Chart.js**.

---

## 🌟 Core Features

1. **Authentication & User Management**
   - User Registration, Login, Logout.
   - Dual User Roles: **Admin** (Full permissions & user management) and **Staff** (Inventory operations).

2. **Interactive Dashboard**
   - Live KPI cards: Total Products, Total Stock Units, Inventory Valuation ($), Low Stock Items, Out-of-Stock Items.
   - Dynamic **Chart.js** visualizations for Stock Movement history and Category Distribution.
   - Recent Stock Transaction Feed and Low-Stock Alert warning table.

3. **Category Management**
   - Full CRUD operations to organize products by category.

4. **Supplier Management**
   - Full CRUD operations for supplier company details, phone, email, and location address.

5. **Product Catalog**
   - Product fields: Name, SKU (unique), Category, Supplier, Description, Unit Price, Quantity, Min Stock Threshold, Image Upload, Date Added.
   - Real-time Stock Status calculation (`In Stock`, `Low Stock`, `Out of Stock`).
   - Advanced search (Name, SKU, Description), category filter, and stock status filter with pagination.

6. **Inventory Transactions (Stock In / Stock Out)**
   - Record **Stock In** (adds inventory) and **Stock Out** (removes inventory).
   - Atomic database transactions auto-updating product stock quantities.
   - Built-in validation preventing stock-out beyond available quantity.
   - Detailed transaction log history.

7. **Reports & Data Export Center**
   - Export Full Inventory, Low Stock, and Stock Movement reports to **CSV** or **PDF**.
   - Formatted PDF generation with custom tables using ReportLab.

---

## 🔑 Demo Account Credentials

| Role | Username | Password |
| :--- | :--- | :--- |
| **Admin** | `admin` | `admin123` |
| **Staff** | `staff` | `staff123` |

---

## 🚀 Quick Setup & Run Instructions

### 1. Prerequisites
- Python 3.10+ installed.

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Database Migrations
```bash
python manage.py makemigrations inventory
python manage.py migrate
```

### 4. Seed Initial Sample Data
Populates default Admin & Staff accounts, categories, suppliers, sample products, and stock movements:
```bash
python manage.py seed_data
```

### 5. Start Development Server
```bash
python manage.py runserver
```
Access the system at **`http://127.0.0.1:8000/`**.

---

## 🗄️ Database Configuration (SQLite & MySQL)

By default, the application runs using **SQLite** out-of-the-box (`db.sqlite3`).

To switch to **MySQL**:
1. Open `inventory_config/settings.py`.
2. Update the `DATABASES` section:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'inventory_db',
        'USER': 'root',
        'PASSWORD': 'your_mysql_password',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}
```
3. Run `python manage.py migrate` and `python manage.py seed_data`.
