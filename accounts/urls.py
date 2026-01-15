from django.urls import include, path

from accounts.views import GoogleLoginAPIView, KakaoLoginAPIView, callback_view

urlpatterns = [
    path("kakao/login/", KakaoLoginAPIView.as_view(), name="kakao_login"),
    path("kakao/callback/", callback_view, name="kakao_callback"),
    path("google/login/", GoogleLoginAPIView.as_view(), name="google_login"),
    path("google/login/callback/", callback_view, name="google_callback"),
]
