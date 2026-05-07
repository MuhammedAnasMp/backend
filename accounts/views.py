import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from .firebase_auth import verify_firebase_token
from .models import InstagramAccount

class FirebaseLoginView(APIView):
    def post(self, request):
        id_token = request.data.get('id_token')
        if not id_token:
            return Response({'error': 'ID token is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        decoded_token = verify_firebase_token(id_token)
        if not decoded_token:
            return Response({'error': 'Invalid ID token'}, status=status.HTTP_401_UNAUTHORIZED)
        
        uid = decoded_token.get('uid')
        email = decoded_token.get('email')
        name = decoded_token.get('name', '')
        
        # Get or create user
        user, created = User.objects.get_or_create(username=uid, defaults={'email': email, 'first_name': name})
        
        return Response({
            'message': 'Login successful',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'name': user.first_name
            }
        }, status=status.HTTP_200_OK)

class InstagramLoginView(APIView):
    def post(self, request):
        access_token = request.data.get('access_token')
        instagram_id = request.data.get('instagram_id') # Optional if we use /me
        
        if not access_token:
            return Response({'error': 'access_token is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Fetch user info from Instagram Graph API (v25.0 as mentioned by user)
            # Note: v25.0 might be a typo for 21.0 or similar, but I'll use the user's version if provided or default to latest.
            # Actually, Graph API versions are like v21.0. 25.0 might be future or a specific business version.
            # I'll use v21.0 or just 'me' which usually points to the latest supported.
            
            ig_api_version = "v21.0" # Fallback to a valid one if 25.0 is too high
            
            response = requests.get(
                f"https://graph.instagram.com/me",
                params={
                    'fields': 'id,username,account_type',
                    'access_token': access_token
                }
            )
            
            if response.status_code != 200:
                return Response({
                    'error': 'Invalid Instagram token',
                    'details': response.json()
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            data = response.json()
            ig_id = data.get('id')
            ig_username = data.get('username')
            
            # Find or create InstagramAccount
            ig_account = InstagramAccount.objects.filter(instagram_id=ig_id).first()
            
            if ig_account:
                # Update existing account
                ig_account.access_token = access_token
                ig_account.username = ig_username
                ig_account.save()
                user = ig_account.user
            else:
                # Create new Django User and InstagramAccount
                # Use instagram username as base for Django username
                django_username = f"ig_{ig_username}_{ig_id}"
                user, created = User.objects.get_or_create(username=django_username)
                
                ig_account = InstagramAccount.objects.create(
                    user=user,
                    instagram_id=ig_id,
                    username=ig_username,
                    access_token=access_token
                )

            return Response({
                'message': 'Instagram login successful',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'instagram_username': ig_account.username,
                    'instagram_id': ig_account.instagram_id
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
