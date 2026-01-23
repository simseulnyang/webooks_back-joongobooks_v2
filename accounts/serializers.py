from rest_framework import serializers

from accounts.models import User, SocialAccount


class SocialLoginSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=SocialAccount.Provider.values)
    token = serializers.CharField(help_text="kakao: access_token / google: id_token")


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "profile_image",
            "created_at",
        )
        read_only_fields = fields
        
        
class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "username",
            "profile_image",
        )
    
    def validate_username(self, value):
        if len(value) < 2:
            raise serializers.ValidationError("닉네임은 최소 2자 이상이어야 합니다.")
        if len(value) > 20:
            raise serializers.ValidationError("닉네임은 최대 20자 이하여야 합니다.")

        user = getattr(self, "instance", None)
        if User.objects.exclude(id=user.id).filter(username=value).exists():
            raise serializers.ValidationError("이미 사용중인 닉네임입니다. 다른 닉네임을 사용해주세요.")

        return value

class SocialLoginResponseSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    user = UserSerializer()
    is_created = serializers.BooleanField(
        help_text="소셜 로그인으로 회원가입이 처음 이루어진 경우 True, 기존 회원인 경우 False"
    )


class LogoutSerializer(serializers.Serializer):
    """
    로그아웃 시 Refresh 토큰을 블랙리스트에 추가합니다.
    
    Fields: 
        refresh_token: 블랙리스트에 추가할 Refresh Token
        
    Note:
        - Access Token은 헤더(Authorization: Bearer {token})로 전송
        - Refresh Token은 요청 본문(body)으로 전송
    """
    refresh_token = serializers.CharField(
        help_text="블랙리스트에 추가할 Refresh Token",
        required=True,
        allow_blank=False,
    )
    

class DeleteAccountSerializer(serializers.Serializer):
    confirm = serializers.BooleanField(
        required=True,
        help_text="회원탈퇴 확인. 반드시 True를 전송해야 탈퇴가 진행됨."
    )
    
    def validate_confirm(self, value):
        if not value:
            raise serializers.ValidationError("탈퇴를 진행하려면 confirm 필드를 True로 설정해야 합니다.")
        return value
    
    
class MessageResponseSerializer(serializers.Serializer):
    message = serializers.CharField(help_text="응답 메시지")
    errors = serializers.DictField(required=False, help_text="오류 상세 정보")