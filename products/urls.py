from django.urls import path
from .views import ResolveProductView, RegisterProductMappingView

urlpatterns = [
    path('resolve/', ResolveProductView.as_view(), name='resolve-product'),
    path('register/', RegisterProductMappingView.as_view(), name='register-product'),
]
