from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from .firebase_auth import verify_firebase_token

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
        
        # In a real app, you would generate a JWT or session here.
        # For simplicity, we'll just return success.
        
        return Response({
            'message': 'Login successful',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'name': user.first_name
            }
        }, status=status.HTTP_200_OK)
