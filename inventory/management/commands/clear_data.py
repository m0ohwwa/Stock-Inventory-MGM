from django.core.management.base import BaseCommand
from inventory.models import Category, Supplier, Product, StockTransaction

class Command(BaseCommand):
    help = 'Clears all inventory data (products, categories, suppliers, stock transactions) for a fresh start.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE('Clearing inventory data...'))
        
        tx_count, _ = StockTransaction.objects.all().delete()
        prod_count, _ = Product.objects.all().delete()
        cat_count, _ = Category.objects.all().delete()
        sup_count, _ = Supplier.objects.all().delete()

        self.stdout.write(self.style.SUCCESS(
            f"Cleared: {tx_count} transactions, {prod_count} products, {cat_count} categories, {sup_count} suppliers."
        ))
