from django.urls import path

from rest_framework_simplejwt.views import TokenRefreshView

from accounts.views import (
    DeleteAccountAPIView,
    GoogleLoginAPIView,
    KakaoLoginAPIView,
    LogoutAPIView,
    UserProfileAPIView,
    UserUpdateAPIView,
)

urlpatterns = [
    path("kakao/login/", KakaoLoginAPIView.as_view(), name="kakao_login"),
    path("google/login/", GoogleLoginAPIView.as_view(), name="google_login"),
    path("profile/", UserProfileAPIView.as_view(), name="user_profile"),
    path("update/", UserUpdateAPIView.as_view(), name="user_update"),
    path("logout/", LogoutAPIView.as_view(), name="logout"),
    path("delete/", DeleteAccountAPIView.as_view(), name="delete_account"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
