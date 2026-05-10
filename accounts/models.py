from django.db import models
from django.contrib.auth.models import User

class AppUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='app_profile')
    firebase_uid = models.CharField(max_length=255, unique=True, null=True, blank=True)
    login_methods = models.JSONField(default=list)  # e.g., ["google", "email", "instagram"]
    created_at = models.DateTimeField(auto_now_add=True)
    
    # The active account working context
    active_instagram_account = models.ForeignKey(
        'InstagramAccount',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='active_for_user'
    )

    def __str__(self):
        return f"AppUser: {self.user.username}"

class InstagramAccount(models.Model):
    app_user = models.ForeignKey(AppUser, on_delete=models.CASCADE, related_name='instagram_accounts')
    instagram_user_id = models.CharField(max_length=255, unique=True)
    username = models.CharField(max_length=255)
    access_token = models.TextField()
    refresh_token = models.TextField(blank=True, null=True)
    profile_picture_url = models.URLField(max_length=500, blank=True, null=True)
    connected_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.username} ({self.instagram_user_id})"
