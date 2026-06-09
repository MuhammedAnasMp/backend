# urls.py

from django.urls import path
from .views import InstagramWebhookView

urlpatterns = [
path("webhooks/instagram/",InstagramWebhookView.as_view(),name="instagram-webhook"),
]
