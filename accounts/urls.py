from django.urls import path
from .views import FirebaseLoginView, InstagramLoginView

urlpatterns = [
    path('auth/firebase/', FirebaseLoginView.as_view(), name='firebase-login'),
    path('auth/instagram/', InstagramLoginView.as_view(), name='instagram-login'),
]
