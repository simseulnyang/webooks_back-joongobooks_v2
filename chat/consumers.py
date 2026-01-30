import json
import logging

from django.contrib.auth import get_user_model

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from chat.models import ChatRoom, Message

User = get_user_model()

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket Consumer - 실시간 채팅 처리

    동작 흐름:
    1. 클라이언트가 연결 요청 (connect)
    2. 권한 확인 후 그룹에 추가
    3. 메시지 수신 (receive)
    4. DB 저장 후 그룹 전체에 전송
    5. 연결 종료 (disconnect)
    """

    async def connect(self):
        """
        WebSocket 연결 시 호출
        - URL에서 chatroom_id 추출
        - 인증/권한 확인
        - 그룹에 추가
        - accept 후 입장 브로드캐스트
        """
        logger.warning(
            f"[WS CONNECT] path={self.scope.get('path')} user={self.scope.get('user')} headers={self.scope.get('headers')}"
        )

        self.chatroom_id = self.scope["url_route"]["kwargs"].get("chatroom_id")
        if self.chatroom_id is None:
            await self.close(code=4400)
            return

        self.room_group_name = f"chat_{self.chatroom_id}"

        self.user = self.scope.get("user")
        if not self.user or not getattr(self.user, "is_authenticated", False):
            await self.close(code=4401)
            return

        try:
            has_permission = await self.check_permission()
        except Exception as e:
            logger.exception("❌ [WS CONNECT] check_permission error", exc_info=e)
            await self.close(code=4500)
            return

        if not has_permission:
            await self.close(code=4403)  # Forbidden
            return

        has_permission = await self.check_permission()
        if not has_permission:
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept(subprotocol="Authorization")

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "user_join",
                "username": self.user.username,
                "user_id": self.user.id,
            },
        )

    async def disconnect(self, close_code):
        """
        WebSocket 연결 종료 시 호출
        - 그룹에서 제거
        """
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        """
        클라이언트로부터 메시지 수신
        - JSON 파싱
        - 타입별 처리 (message, read, typing)
        """

        if not text_data:
            logger.warning("[WS RECEIVE] empty text_data")
            return

        try:
            data = json.loads(text_data)
        except Exception as e:
            logger.exception(f"[WS RECEIVE] JSON parse error: {e}, raw={text_data}")
            return

        message_type = data.get("type", "message")

        logger.warning(
            f"[WS RECEIVE] room={getattr(self, 'chatroom_id', None)} "
            f"user={getattr(self, 'user', None)} type={message_type} data={data}"
        )

        if message_type == "message":
            content = (data.get("content") or data.get("message") or "").strip()
            if not content:
                return

            try:
                message = await self.save_message(content)
            except Exception as e:
                logger.exception(f"[WS SAVE_MESSAGE] failed: {e}")
                await self.send(
                    text_data=json.dumps(
                        {
                            "type": "error",
                            "error": "failed_to_save_message",
                        }
                    )
                )
                return

            payload = {
                "type": "chat_message",
                "message": {
                    "id": message.id,
                    "content": message.content,
                    # created_at 키 이름도 Flutter가 기대하는 createdAt/created_at 중 무엇인지에 따라 조정 필요
                    # 일단 snake_case 유지
                    "created_at": message.created_at.isoformat(),
                    "is_read": message.is_read,
                    "room": self.chatroom_id,  # ✅ Message.room이 int라면 필요
                    "sender": {
                        "id": message.sender.id,
                        "username": message.sender.username,
                        # Flutter User 모델에 email/profileImage 등이 required면 여기서도 넣어줘야 함
                        # 없으면 null/""로 내려야 파싱 에러가 안 남
                        "email": getattr(message.sender, "email", None),
                        "profile_image": getattr(message.sender, "profile_image", "") or "",
                    },
                },
            }

            await self.channel_layer.group_send(self.room_group_name, payload)
            logger.warning(f"[WS GROUP_SEND] room={self.chatroom_id} sent message_id={message.id}")

        elif message_type == "read":
            message_ids = data.get("message_ids") or []
            if not isinstance(message_ids, list):
                message_ids = []

            try:
                await self.mark_messages_as_read(message_ids)
            except Exception as e:
                logger.exception(f"[WS MARK_READ] failed: {e}")
                return

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "message": {
                        "id": message.id,
                        "room_id": self.chatroom_id,
                        "content": message.content,
                        "sender_id": message.sender.id,
                        "sender_name": message.sender.username,
                        "sender_image": getattr(message.sender, "profile_image", "") or "",
                        "created_at": message.created_at.isoformat(),
                        "is_read": message.is_read,
                    },
                },
            )

        elif message_type == "typing":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "message": {
                        "id": message.id,
                        "room_id": self.chatroom_id,
                        "content": message.content,
                        "sender_id": message.sender.id,
                        "sender_name": message.sender.username,
                        "sender_image": getattr(message.sender, "profile_image", "") or "",
                        "created_at": message.created_at.isoformat(),
                        "is_read": message.is_read,
                    },
                },
            )

        else:
            logger.warning(f"[WS RECEIVE] unknown type={message_type}")

    async def chat_message(self, event):
        """채팅 메시지를 클라이언트로 전송"""
        await self.send(text_data=json.dumps(event))

    async def messages_read(self, event):
        """메시지 읽음 상태를 클라이언트로 전송"""
        await self.send(text_data=json.dumps(event))

    async def user_typing(self, event):
        """타이핑 상태를 클라이언트로 전송"""
        # 자기 자신에게는 전송하지 않음
        sender_id = event.get("user_id")
        # 안전장치: user 없으면 그냥 보내지 않음
        if sender_id is None:
            return

        # 자기 자신에게는 전송하지 않음
        if getattr(self.user, "id", None) == sender_id:
            return

        await self.send(
            text_data=json.dumps(
                {
                    "type": "user_typing",  # ✅ 타입 일관성 유지
                    "user_id": sender_id,
                    "username": event.get("username"),
                    "is_typing": bool(event.get("is_typing", False)),
                    "room": getattr(self, "chatroom_id", None),  # 있으면 디버깅에 도움
                }
            )
        )

    async def user_join(self, event):
        """사용자 접속 알림"""
        if event["user_id"] != self.user.id:
            await self.send(text_data=json.dumps({"type": "user_join", "username": event["username"]}))

    # === Database 작업 (동기 → 비동기 변환) ===

    @database_sync_to_async
    def check_permission(self):
        """채팅방 접근 권한 확인"""
        try:
            chatroom = ChatRoom.objects.get(id=self.chatroom_id)
            return chatroom.is_participant(self.user)
        except ChatRoom.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, content):
        """메시지를 DB에 저장"""
        chatroom = ChatRoom.objects.get(id=self.chatroom_id)
        message = Message.objects.create(chatroom=chatroom, sender=self.user, content=content)
        # 채팅방 updated_at 갱신 (목록 정렬용)
        chatroom.save()
        return message

    @database_sync_to_async
    def mark_messages_as_read(self, message_ids):
        """메시지들을 읽음으로 표시"""
        Message.objects.filter(id__in=message_ids, chatroom_id=self.chatroom_id).exclude(
            sender=self.user  # 내가 보낸 메시지는 제외
        ).update(is_read=True)
