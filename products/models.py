from django.db import models
from django.conf import settings


class Category(models.Model):
    name = models.CharField(max_length=100)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="categories", null=True, blank=True)

    class Meta:
        unique_together = ('name', 'user')

    def __str__(self):
        return self.name


class Product(models.Model):
    SOURCE_TYPES = [
        ('REEL', 'Instagram Reel'),
        ('POST', 'Instagram Post'),
        ('MANUAL', 'Manual Creation'),
    ]

    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('ACTIVE', 'Active'),
        ('SOLD', 'Sold'),
        ('ARCHIVED', 'Archived'),
    ]

    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="products"
    )

    instagram_account = models.ForeignKey(
        'accounts.InstagramAccount',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products"
    )

    title = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )

    original_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Original price before any discounts or offers."
    )

    currency = models.CharField(
        max_length=3,
        default="KWD"
    )

    stock = models.PositiveIntegerField(default=1)

    is_negotiable = models.BooleanField(default=True)

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    location = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    main_media_url = models.URLField(
        max_length=2000,
        blank=True,
        null=True
    )

    source_type = models.CharField(
        max_length=10,
        choices=SOURCE_TYPES,
        default='MANUAL'
    )

    source_id = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    instagram_permalink = models.URLField(
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='DRAFT'
    )

    cloudinary_metadata = models.JSONField(
        blank=True,
        null=True,
        help_text="Metadata stored when uploading to Cloudinary"
    )

    metadata = models.JSONField(
        blank=True,
        null=True,
        default=dict,
        help_text="Dynamic key-value specifications for the product."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['seller', 'source_id'],
                name='unique_source_per_seller'
            )
        ]

    def __str__(self):
        return self.title or f"Product {self.id}"


class ProductMedia(models.Model):
    MEDIA_TYPES = [
        ('IMAGE', 'Image'),
        ('VIDEO', 'Video'),
    ]

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="gallery"
    )

    media_url = models.URLField(max_length=2000)

    thumbnail_url = models.URLField(
        max_length=2000,
        blank=True,
        null=True
    )

    media_type = models.CharField(
        max_length=10,
        choices=MEDIA_TYPES
    )

    width = models.PositiveIntegerField(
        blank=True,
        null=True
    )

    height = models.PositiveIntegerField(
        blank=True,
        null=True
    )

    duration = models.FloatField(
        blank=True,
        null=True
    )

    order = models.PositiveIntegerField(default=0)

    cloudinary_metadata = models.JSONField(
        blank=True,
        null=True,
        help_text="Metadata stored when uploading to Cloudinary"
    )

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Media #{self.id} for Product #{self.product_id}"