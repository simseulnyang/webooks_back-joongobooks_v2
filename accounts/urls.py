from django.urls import include, path

from accounts.views import (
    GoogleLoginAPIView,
    KakaoLoginAPIView,
    UserProfileAPIView,
    UserUpdateAPIView,
    LogoutAPIView,
    DeleteAccountAPIView,
)

urlpatterns = [
    path("kakao/login/", KakaoLoginAPIView.as_view(), name="kakao_login"),
    path("google/login/", GoogleLoginAPIView.as_view(), name="google_login"),
    path("profile/", UserProfileAPIView.as_view(), name="user_profile"),
    path("update/", UserUpdateAPIView.as_view(), name="user_update"),
    path("logout/", LogoutAPIView.as_view(), name="logout"),
    path("delete/", DeleteAccountAPIView.as_view(), name="delete_account"),
]
