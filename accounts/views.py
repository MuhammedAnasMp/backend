import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from .firebase_auth import verify_firebase_token
from .models import InstagramAccount, AppUser

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

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
        
        # 1. Resolve Django User
        user, created = User.objects.get_or_create(username=uid, defaults={'email': email, 'first_name': name})
        
        # 2. Resolve AppUser (Primary Identity)
        app_user, au_created = AppUser.objects.get_or_create(user=user, defaults={'firebase_uid': uid})
        
        # Update login methods
        method = "google" if "google" in decoded_token.get('firebase', {}).get('sign_in_provider', '') else "email"
        if method not in app_user.login_methods:
            app_user.login_methods.append(method)
            app_user.save()

        # 3. Load connected accounts info
        instagram_accounts = InstagramAccount.objects.filter(app_user=app_user)
        
        # 4. Generate JWT tokens
        tokens = get_tokens_for_user(user)
        
        return Response({
            'message': 'Login successful',
            'tokens': tokens,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'name': user.first_name,
                'login_methods': app_user.login_methods,
                'active_instagram_account_id': app_user.active_instagram_account_id
            },
            'connected_instagram_accounts': [
                {'id': acc.id, 'username': acc.username, 'instagram_id': acc.instagram_user_id}
                for acc in instagram_accounts
            ]
        }, status=status.HTTP_200_OK)

class InstagramLoginView(APIView):
    def post(self, request):
        access_token = request.data.get('access_token')
        
        if not access_token:
            return Response({'error': 'access_token is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Verify with Instagram
            response = requests.get(
                "https://graph.instagram.com/me",
                params={
                    'fields': 'id,username,account_type',
                    'access_token': access_token
                }
            )
            
            if response.status_code != 200:
                return Response({'error': 'Invalid Instagram token', 'details': response.json()}, status=status.HTTP_401_UNAUTHORIZED)
            
            data = response.json()
            ig_id = data.get('id')
            ig_username = data.get('username')
            
            # Check if this Instagram account is already known
            ig_account = InstagramAccount.objects.filter(instagram_user_id=ig_id).first()
            
            if request.user.is_authenticated:
                # Account Linking Mode
                app_user = getattr(request.user, 'app_profile', None)
                if not app_user:
                    app_user = AppUser.objects.create(user=request.user)
                
                if ig_account:
                    ig_account.access_token = access_token
                    ig_account.username = ig_username
                    ig_account.app_user = app_user 
                    ig_account.save()
                else:
                    ig_account = InstagramAccount.objects.create(
                        app_user=app_user,
                        instagram_user_id=ig_id,
                        username=ig_username,
                        access_token=access_token
                    )
            else:
                # Entry Login Mode
                if ig_account:
                    app_user = ig_account.app_user
                    user = app_user.user
                    ig_account.access_token = access_token
                    ig_account.username = ig_username
                    ig_account.save()
                else:
                    django_username = f"ig_{ig_username}_{ig_id}"
                    user, created = User.objects.get_or_create(username=django_username)
                    app_user, au_created = AppUser.objects.get_or_create(user=user)
                    
                    ig_account = InstagramAccount.objects.create(
                        app_user=app_user,
                        instagram_user_id=ig_id,
                        username=ig_username,
                        access_token=access_token
                    )
            
            # Update login methods
            if "instagram" not in app_user.login_methods:
                app_user.login_methods.append("instagram")
            
            # Auto-set active account if none selected
            if not app_user.active_instagram_account:
                app_user.active_instagram_account = ig_account
            
            app_user.save()
            
            # Generate JWT tokens
            tokens = get_tokens_for_user(app_user.user)

            return Response({
                'message': 'Instagram action successful',
                'tokens': tokens,
                'user': {
                    'id': app_user.user.id,
                    'username': app_user.user.username,
                    'active_instagram_account_id': app_user.active_instagram_account_id
                },
                'instagram_account': {
                    'id': ig_account.id,
                    'username': ig_account.username,
                    'instagram_id': ig_account.instagram_user_id
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
