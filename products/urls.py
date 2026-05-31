from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, ResolveProductView, RegisterProductMappingView

router = DefaultRouter()
# Map full CRUD operations to the root of this sub-path /api/products/
router.register(r'', ProductViewSet, basename='product')

urlpatterns = [
    path('resolve/', ResolveProductView.as_view(), name='resolve-product'),
    path('register/', RegisterProductMappingView.as_view(), name='register-product'),
    path('', include(router.urls)),
]
