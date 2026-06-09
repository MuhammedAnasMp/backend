import os
import sys
import django

# Set up Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.products.models import Product

print("=== PRODUCTS IN DB ===")
products = Product.objects.all()
if not products.exists():
    print("No products found in database.")
for p in products:
    print(f"Product ID: {p.id}")
    print(f"  Title: {p.title}")
    print(f"  Source ID: {p.source_id}")
    print(f"  Source Type: {p.source_type}")
    print(f"  Permalink: {p.instagram_permalink}")
    print(f"  Main Media URL: {p.main_media_url}")
    print("  Gallery Media Items:")
    for m in p.gallery.all():
        print(f"    - Media ID: {m.id}")
        print(f"      Media URL: {m.media_url}")
        print(f"      Thumbnail URL: {m.thumbnail_url}")
        print(f"      Media Type: {m.media_type}")
    print("-" * 50)
