import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

from chat.models import ChatRoom, Message

User = get_user_model()


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
        - 권한 확인
        - 그룹에 추가
        """
        self.chatroom_id = self.scope['url_route']['kwargs']['chatroom_id']
        self.room_group_name = f'chat_{self.chatroom_id}'

        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return
        
        has_permission = await self.check_permission()
        if not has_permission:
            await self.close()
            return
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_join',
                'username': self.user.username,
                'user_id': self.user.id
            }
        )
        
    async def disconnect(self, close_code):
        """
        WebSocket 연결 종료 시 호출
        - 그룹에서 제거
        """
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
    async def receive(self, text_data):
        """
        클라이언트로부터 메시지 수신
        - JSON 파싱
        - 타입별 처리 (message, read 등)
        """
        data = json.loads(text_data)
        message_type = data.get('type', 'message')

        if message_type == 'message':
            content = data.get('content', '').strip()
            
            if not content:
                return
            
            message = await self.save_message(content)

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': {
                        'id': message.id,
                        'content': message.content,
                        'sender_id': message.sender.id,
                        'sender_username': message.sender.username,
                        'created_at': message.created_at.isoformat(),
                        'is_read': message.is_read,
                    }
                }
            )
        
        elif message_type == 'read':
            message_ids = data.get('message_ids', [])
            await self.mark_messages_as_read(message_ids)

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'message_read',
                    'message_ids': message_ids,
                    'user_id': self.user.id
                    
                }
            )
            
        elif message_type == 'typing':
            is_typing = data.get('is_typing', False)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_typing',
                    'user_id': self.user.id,
                    'username': self.user.username,
                    'is_typing': is_typing
                }
            )
            
    
    async def chat_message(self, event):
        """채팅 메시지를 클라이언트로 전송"""
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message']
        }))
    
    async def messages_read(self, event):
        """메시지 읽음 상태를 클라이언트로 전송"""
        await self.send(text_data=json.dumps({
            'type': 'read',
            'message_ids': event['message_ids'],
            'user_id': event['user_id']
        }))
    
    async def user_typing(self, event):
        """타이핑 상태를 클라이언트로 전송"""
        # 자기 자신에게는 전송하지 않음
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'username': event['username'],
                'is_typing': event['is_typing']
            }))
    
    async def user_join(self, event):
        """사용자 접속 알림"""
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'user_join',
                'username': event['username']
            }))
    
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
        message = Message.objects.create(
            chatroom=chatroom,
            sender=self.user,
            content=content
        )
        # 채팅방 updated_at 갱신 (목록 정렬용)
        chatroom.save()
        return message
    
    @database_sync_to_async
    def mark_messages_as_read(self, message_ids):
        """메시지들을 읽음으로 표시"""
        Message.objects.filter(
            id__in=message_ids,
            chatroom_id=self.chatroom_id
        ).exclude(
            sender=self.user  # 내가 보낸 메시지는 제외
        ).update(is_read=True)
        