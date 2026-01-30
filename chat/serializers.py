# chat/serializers.py

from rest_framework import serializers

from books.models import Book
from books.serializers import BookListSerializer
from chat.models import ChatRoom, Message


def safe_image_url(value) -> str:
    """
    value가 ImageFieldFile 또는 그냥 문자열 또는 None 이어도
    안전하게 URL 문자열만 반환
    """
    if not value:
        return ""

    if hasattr(value, "url"):
        try:
            return value.url or ""
        except Exception:
            return ""

    if isinstance(value, str):
        return value

        return ""


class MessageSerializer(serializers.ModelSerializer):
    room = serializers.IntegerField(source="chatroom_id", read_only=True)

    sender_username = serializers.CharField(source="sender.username", read_only=True)
    sender_email = serializers.CharField(source="sender.email", read_only=True)

    class Meta:
        model = Message
        fields = ["id", "room", "sender", "sender_username", "sender_email", "content", "is_read", "created_at"]
        read_only_fields = ["room", "sender", "created_at", "is_read"]


class ChatRoomListSerializer(serializers.ModelSerializer):
    """채팅방 목록용 (간단한 정보)"""

    book = BookListSerializer(read_only=True)
    other_user = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = ["id", "book", "other_user", "last_message", "unread_count", "created_at", "updated_at"]

    def get_other_user(self, obj):
        """상대방 정보"""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            other = obj.get_other_user(request.user)
            return {
                "id": other.id,
                "username": other.username,
                "email": other.email,
                "profile_image": safe_image_url(getattr(other, "profile_image", None)),
            }
        return None

    def get_last_message(self, obj):
        """마지막 메시지"""
        last_msg = obj.messages.last()
        if last_msg:
            return {
                "content": last_msg.content,
                "sender_username": last_msg.sender.username,
                "created_at": last_msg.created_at.isoformat(),
                "is_read": last_msg.is_read,
            }
        return None

    def get_unread_count(self, obj):
        """안 읽은 메시지 개수"""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.messages.filter(is_read=False).exclude(sender=request.user).count()
        return 0


class ChatRoomBookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ["id", "title"]


class ChatRoomDetailSerializer(serializers.ModelSerializer):
    """채팅방 상세 (메시지 포함)"""

    book = ChatRoomBookSerializer(read_only=True)
    buyer = serializers.SerializerMethodField()
    seller = serializers.SerializerMethodField()
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = ChatRoom
        fields = ["id", "book", "buyer", "seller", "messages", "created_at", "updated_at"]

    def get_buyer(self, obj):
        u = obj.buyer
        return {
            "id": obj.buyer.id,
            "username": obj.buyer.username,
            "email": obj.buyer.email,
            "profile_image": safe_image_url(getattr(u, "profile_image", None)),
        }

    def get_seller(self, obj):
        u = obj.seller
        return {
            "id": obj.seller.id,
            "username": obj.seller.username,
            "email": obj.seller.email,
            "profile_image": safe_image_url(getattr(u, "profile_image", None)),
        }
