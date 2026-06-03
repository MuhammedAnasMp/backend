from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

class User(AbstractUser):
    firebase_uid = models.CharField(max_length=255, unique=True, null=True, blank=True)
    login_methods = models.JSONField(default=list)  # e.g., ["google", "email", "instagram"]
    
    # The active account working context
    active_instagram_account = models.ForeignKey(
        'InstagramAccount',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='active_for_user'
    )

    def __str__(self):
        return f"User: {self.username}"

class InstagramAccount(models.Model): # sellers
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='instagram_accounts', null=True, blank=True)
    instagram_scoped_id = models.CharField(max_length=255, unique=True, null=True, blank=True) # The SID/PSID tied to the platform
    instagram_user_id = models.CharField(max_length=255, blank=True, null=True) # The global IGID (starts with 17)
    username = models.CharField(max_length=255)
    full_name = models.CharField(max_length=255, blank=True, null=True)
    access_token = models.TextField()
    refresh_token = models.TextField(blank=True, null=True)
    profile_picture_url = models.URLField(max_length=500, blank=True, null=True)
    used_for_login = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    is_enabled = models.BooleanField(default=True)
    connected_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.username} ({self.instagram_user_id})"



