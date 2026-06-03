from django.contrib import admin
from .models import Product, ProductMedia, Category

class ProductMediaInline(admin.StackedInline):
    model = ProductMedia
    extra = 3
    readonly_fields = ('preview',)
    
    def preview(self, obj):
        from django.utils.html import format_html
        if obj.media_type == 'IMAGE':
            return format_html('<img src="{}" width="100" height="100" style="object-fit: cover;" />', obj.media_url)
        else:
            return format_html('<a href="{}" target="_blank">Play Video</a>', obj.media_url)
            
    preview.short_description = 'Preview'

class ProductAdmin(admin.ModelAdmin):
    list_display = ('title', 'seller', 'source_type', 'status', 'price')
    list_filter = ('source_type', 'status', 'seller')
    search_fields = ('title', 'description')
    inlines = [ProductMediaInline]
    readonly_fields = ('created_at', 'updated_at')

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'user')
    search_fields = ('name',)

admin.site.register(Product, ProductAdmin)
admin.site.register(ProductMedia)
admin.site.register(Category, CategoryAdmin)
