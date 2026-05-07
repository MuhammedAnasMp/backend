from django.db import models
from django.contrib.auth.models import User

class InstagramAccount(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='instagram_account')
    instagram_id = models.CharField(max_length=255, unique=True)
    username = models.CharField(max_length=255)
    access_token = models.TextField()
    profile_picture_url = models.URLField(max_length=500, blank=True, null=True)
    full_name = models.CharField(max_length=255, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.username} ({self.instagram_id})"
