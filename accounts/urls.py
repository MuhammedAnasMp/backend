from django.urls import path
from .views import (
    FirebaseLoginView, 
    InstagramLoginView, 
    ToggleInstagramLoginView, 
    GetConnectedInstagramAccountsView,
    UpdateProfileView,
    InstagramDeauthorizeView,
    InstagramDataDeletionView,
    RemoveInstagramAccountView,
    ToggleInstagramEnabledView,
    SetActiveInstagramAccountView
)

urlpatterns = [
    path('auth/firebase/', FirebaseLoginView.as_view(), name='firebase-login'),
    path('auth/instagram/', InstagramLoginView.as_view(), name='instagram-login'),
    path('auth/instagram/toggle-login/', ToggleInstagramLoginView.as_view(), name='instagram-toggle-login'),
    path('auth/instagram/accounts/', GetConnectedInstagramAccountsView.as_view(), name='instagram-accounts'),
    path('profile/update/', UpdateProfileView.as_view(), name='profile-update'),
    path('auth/instagram/deauthorize/', InstagramDeauthorizeView.as_view(), name='instagram-deauthorize'),
    path('auth/instagram/delete-data/', InstagramDataDeletionView.as_view(), name='instagram-delete-data'),
    path('auth/instagram/remove/', RemoveInstagramAccountView.as_view(), name='instagram-remove'),
    path('auth/instagram/toggle-enabled/', ToggleInstagramEnabledView.as_view(), name='instagram-toggle-enabled'),
    path('auth/instagram/set-active/', SetActiveInstagramAccountView.as_view(), name='instagram-set-active'),
]
