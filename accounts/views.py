import logging

from django.conf import settings
from django.db import transaction

import requests
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from .models import SocialAccount, User
from .serializers import (
    DeleteAccountSerializer,
    LogoutSerializer,
    MessageResponseSerializer,
    SocialLoginResponseSerializer,
    SocialLoginSerializer,
    UserSerializer,
    UserUpdateSerializer,
)

logger = logging.getLogger(__name__)


@transaction.atomic
def get_or_create_user_by_social(
    provider: str,
    provider_user_oid: str,
    email: str,
    username: str,
    profile_image: str,
):
    """
    SocialAccount가 있으면 그 user 반환,
    없으면 email로 User 탐색:
        - 해당 email에 다른 provider가 연결되어 있으면 409 반환
        - 아니면 User 생성/재사용 후 SocialAccount 생성
    """
    try:
        social = SocialAccount.objects.select_related("user").get(
            provider=provider,
            provider_user_oid=provider_user_oid,
        )
        return social.user, False

    except SocialAccount.DoesNotExist:
        user = User.objects.filter(email=email).first()

        if user:
            other_social = user.social_accounts.exclude(provider=provider).first()
            if other_social:
                provider_name = "카카오" if other_social.provider == SocialAccount.Provider.KAKAO else "구글"
                raise ValueError(
                    f"이미 {provider_name} 계정으로 가입된 이메일입니다. {provider_name}으로 로그인 해주세요."
                )

            SocialAccount.objects.create(
                user=user,
                provider=provider,
                provider_user_oid=provider_user_oid,
            )
            return user, False

        user = User.objects.create(
            email=email,
            username=username,
            profile_image=profile_image,
        )
        SocialAccount.objects.create(
            user=user,
            provider=provider,
            provider_user_oid=provider_user_oid,
        )
        return user, True


def issue_jwt_response(user: User, is_created: bool) -> dict:
    refresh = RefreshToken.for_user(user)
    payload = {
        "access_token": str(refresh.access_token),
        "refresh_token": str(refresh),
        "user": UserSerializer(user).data,
        "is_created": is_created,
    }
    return Response(SocialLoginResponseSerializer(payload).data, status=status.HTTP_200_OK)


class KakaoLoginAPIView(APIView):
    """
    카카오 소셜 로그인 API

    Flutter에서 카카오 SDK로 받은 access_token을 token으로 전송하면
    → /v2/user/me 호출로 사용자 정보 획득
    → (필수) 이메일 없으면 실패
    → User & SocialAccount 연결 후 우리 서비스 JWT 발급
    """

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Auth - KakaoSocial"],
        summary="카카오 소셜 로그인",
        description=(
            "1. 요청: provider='kakao', token=카카오 access_token\n"
            "2. 처리: kakao /v2/user/me로 사용자 정보 조회 후 JWT 발급\n"
            "3. 제약: 이메일 제공 동의 필수(미제공 시 400)\n"
        ),
        request=SocialLoginSerializer,
        responses={
            200: SocialLoginResponseSerializer,
            400: MessageResponseSerializer,
            409: MessageResponseSerializer,
            503: MessageResponseSerializer,
        },
        examples=[
            OpenApiExample(
                "성공 예시",
                value={
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6...",
                    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6...",
                    "user": {
                        "id": 1,
                        "email": "test@example.com",
                        "username": "심슬냥",
                        "profile_image": "https://...",
                        "created_at": "2025-11-17T12:34:56Z",
                    },
                    "is_created": True,
                },
                response_only=True,
            )
        ],
    )
    def post(self, request, *args, **kwargs):
        serializer = SocialLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        provider = serializer.validated_data["provider"]
        token = serializer.validated_data["token"]

        if provider != SocialAccount.Provider.KAKAO:
            return Response(
                {"message": "이 엔드포인트는 provider='kakao' 전용입니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            headers = {"Authorization": f"Bearer {token}"}
            profile_res = requests.get(
                "https://kapi.kakao.com/v2/user/me",
                headers=headers,
                timeout=10,
            )
            if profile_res.status_code != 200:
                logger.error(f"kakao profile error: {profile_res.status_code}, {profile_res.text}")
                return Response(
                    {"message": "카카오 사용자 정보 조회 실패"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            profile_json = profile_res.json()

        except requests.exceptions.Timeout:
            logger.error("Kakao API Timeout")
            return Response({"message": "카카오 서버 응답 시간 초과"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except requests.exceptions.RequestException as e:
            logger.error(f"Kakao API Request failed: {str(e)}")
            return Response(
                {"message": "카카오 서버 요청 실패"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        kakao_oid = str(profile_json.get("id"))
        properties = profile_json.get("properties", {})
        kakao_account = profile_json.get("kakao_account", {})

        email = kakao_account.get("email")
        nickname = properties.get("nickname") or email or "Kakao유저"
        profile_image = properties.get("profile_image", "")

        if not kakao_oid:
            return Response({"message": "카카오 사용자 ID를 가져올 수 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

        if not email:
            return Response(
                {
                    "message": "카카오 로그인 시 이메일 제공 동의가 필요합니다.",
                    "errors": {
                        "email": "카카오에서 이메일을 제공하지 않았습니다. 카카오 앱에서 이메일 제공에 동의해주세요."
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user, is_created = get_or_create_user_by_social(
                provider=SocialAccount.Provider.KAKAO,
                provider_user_oid=kakao_oid,
                email=email,
                username=nickname or email or "Kakao유저",
                profile_image=profile_image,
            )
        except ValueError as e:
            return Response(
                {"message": str(e), "errors": {"email": str(e)}},
                status=status.HTTP_409_CONFLICT,
            )

        return issue_jwt_response(user, is_created)


class GoogleLoginAPIView(APIView):
    """
    구글 소셜 로그인 API

    Flutter에서 구글 SDK로 받은 id_Token을 전송하면
    → 서버에서 id_token 검증 후 (sub, email, name, picture) 추출
    → (필수) 이메일 없으면 실패
    → User & SocialAccount 연결 후 JWT 발급

    **참고**:
    Google은 서버에서 ID 토큰 검증이 권장됨 :contentReference[oaicite:3]{index=3}
    """

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Auth - GoogleSocial"],
        summary="구글 소셜 로그인",
        description=(
            "1. 요청: provider='google', token=Google id_token\n"
            "2. 처리: 서버에서 id_token 검증 후 JWT 발급\n"
            "3. 제약: 이메일 제공 필수"
        ),
        request=SocialLoginSerializer,
        responses={
            200: SocialLoginResponseSerializer,
            400: MessageResponseSerializer,
            409: MessageResponseSerializer,
            503: MessageResponseSerializer,
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = SocialLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        provider = serializer.validated_data["provider"]
        token = serializer.validated_data["token"]

        if provider != SocialAccount.Provider.GOOGLE:
            return Response(
                {"message": "이 엔드포인트는 provider='google' 전용입니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ID 토큰 검증 (권장: google-auth 사용)
        #   - 공식 문서도 서버에서 검증을 권장 : contentReference[oaicite:4]{index=4}

        google_oid = None
        email = None
        name = None
        picture = ""

        try:
            from google.auth.transport import requests as google_requests
            from google.oauth2 import id_token as google_id_token

            idinfo = google_id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID,
            )

            google_oid = idinfo.get("sub")
            email = idinfo.get("email")
            email_verified = idinfo.get("email_verified", False)
            name = idinfo.get("name") or email or "Google 유저"
            picture = idinfo.get("picture", "")

            if not email_verified:
                return Response(
                    {
                        "message": "구글 로그인 시 이메일 인증이 필요합니다.",
                        "errors": {"email": "email_verified=False"},
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            logger.error("Google id_token verify failed: %s", str(e))
            return Response({"message": "구글 토큰 검증 실패"}, status=status.HTTP_400_BAD_REQUEST)

        if not google_oid:
            return Response({"message": "구글 사용자 ID를 가져올 수 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

        if not email:
            return Response(
                {
                    "message": "구글 로그인 시 이메일 제공이 필요합니다.",
                    "errors": {"email": "구글에서 이메일을 제공하지 않았습니다."},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user, is_created = get_or_create_user_by_social(
                provider=SocialAccount.Provider.GOOGLE,
                provider_user_oid=str(google_oid),
                email=email,
                username=name or email or "Google유저",
                profile_image=picture,
            )
        except ValueError as e:
            return Response(
                {"message": str(e), "errors": {"email": str(e)}},
                status=status.HTTP_409_CONFLICT,
            )

        return issue_jwt_response(user, is_created)


class UserProfileAPIView(APIView):
    """
    사용자 프로필 조회 API

    현재 로그인한 사용자의 정보를 반환합니다.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["User - Profile"],
        summary="사용자 프로필 조회",
        description="현재 로그인한 사용자의 프로필 정보를 반환합니다.",
        responses={
            200: UserSerializer,
            401: MessageResponseSerializer,
        },
    )
    def get(self, request):
        serialzer = UserSerializer(request.user)
        return Response(serialzer.data, status=status.HTTP_200_OK)


class UserUpdateAPIView(APIView):
    """
    사용자 정보 수정 API

    현재 로그인한 사용자의 닉네임과 프로필 이미지를 수정합니다.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["User - Update"],
        summary="사용자 정보 수정",
        description=("사용자 정보를 수정합니다.\n" "**수정 가능:** username (2~20자), profile_image"),
        request=UserUpdateSerializer,
        responses={
            200: UserSerializer,
            400: MessageResponseSerializer,
            401: MessageResponseSerializer,
        },
    )
    def patch(self, request):
        if not request.data:
            return Response(
                {"message": "수정할 데이터가 없습니다.", "errors": {"non_field_errors": "빈 요청"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        serializer = UserUpdateSerializer(
            user,
            data=request.data,
            partial=True,
        )

        if not serializer.is_valid():
            return Response(
                {"message": "입력값이 올바르지 않습니다.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer.save()
        return Response(UserSerializer(serializer.instance).data, status=status.HTTP_200_OK)


class LogoutAPIView(APIView):
    """로그아웃 API"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth - Logout"],
        summary="로그아웃",
        description="Refresh Token을 블랙리스트에 추가하여 로그아웃 처리합니다.",
        request=LogoutSerializer,
        responses={200: MessageResponseSerializer, 400: MessageResponseSerializer, 401: MessageResponseSerializer},
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        refresh_token = serializer.validated_data["refresh_token"]

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError as e:
            logger.warning(f"Logout token error: {e}")
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return Response(
                {"message": "로그아웃 처리 중 오류가 발생했습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({"message": "로그아웃이 완료되었습니다."}, status=status.HTTP_200_OK)


class DeleteAccountAPIView(APIView):
    """회원탈퇴 API"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth - DeleteAccount"],
        summary="회원탈퇴",
        description="현재 로그인한 사용자의 계정을 삭제합니다. confirm=true 필수.",
        request=DeleteAccountSerializer,
        responses={200: MessageResponseSerializer, 400: MessageResponseSerializer, 401: MessageResponseSerializer},
    )
    @transaction.atomic
    def delete(self, request):
        serializer = DeleteAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        user_email = user.email

        try:
            for outstanding in OutstandingToken.objects.filter(user=user):
                BlacklistedToken.objects.get_or_create(token=outstanding)

            user.delete()
            logger.info(f"User account deleted: {user_email} (ID: {user.id})")

            return Response({"message": "회원탈퇴가 완료되었습니다."}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Delete account error: {e}")
            return Response(
                {"message": "회원탈퇴 처리 중 오류가 발생했습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
