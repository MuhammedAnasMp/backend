from django.db import models
from django.conf import settings

class Product(models.Model):
    SOURCE_TYPES = [
        ('REEL', 'Instagram Reel'),
        ('POST', 'Instagram Post'),
        ('MANUAL', 'Manual Creation'),
    ]

    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="products")
    title = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    is_negotiable = models.BooleanField(default=True)
    
    # Unified Media Handling
    main_media_url = models.URLField(max_length=500, blank=True, null=True)
    
    # Source Tracking
    source_type = models.CharField(max_length=10, choices=SOURCE_TYPES, default='MANUAL')
    source_id = models.CharField(max_length=100, blank=True, null=True, unique=True, 
                                 help_text="Instagram shortcode or external ID")
    
    # Conversion Status
    is_published = models.BooleanField(default=False, help_text="True if converted to a sellable product")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title or f"Product {self.id} ({self.source_type})"

class ProductMedia(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="gallery")
    media_url = models.URLField(max_length=500)
    media_type = models.CharField(max_length=10, choices=[('IMAGE', 'Image'), ('VIDEO', 'Video')])
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Media for {self.product.title}"
