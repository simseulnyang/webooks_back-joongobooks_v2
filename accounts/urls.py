from django.urls import path, include
from accounts.views import KakaoLoginAPIView, callback_view, GoogleLoginAPIView

urlpatterns = [
    path('kakao/login/', KakaoLoginAPIView.as_view(), name="kakao_login"),
    path('kakao/callback/', callback_view, name="kakao_callback"),
    
    path('google/login/', GoogleLoginAPIView.as_view(), name="google_login"),
    path('google/login/callback/', callback_view, name="google_callback"),
]
