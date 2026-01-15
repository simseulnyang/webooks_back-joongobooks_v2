# chat/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import ChatRoom, Message
from .serializers import (
    ChatRoomListSerializer,
    ChatRoomDetailSerializer,
    MessageSerializer
)
from books.models import Book


class ChatRoomCreateOrGetView(APIView):
    """
    채팅방 생성 또는 기존 방 가져오기
    POST /api/chat/rooms/create/
    Body: { "book_id": 1 }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        book_id = request.data.get('book_id')
        
        if not book_id:
            return Response(
                {'error': 'book_id가 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        book = get_object_or_404(Book, id=book_id)
        
        # 자기 자신의 책에는 채팅 불가
        if book.writer == request.user:
            return Response(
                {'error': '본인의 책에는 채팅할 수 없습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 기존 채팅방 확인 또는 생성
        chatroom, created = ChatRoom.objects.get_or_create(
            book=book,
            buyer=request.user,
            defaults={'seller': book.writer}
        )
        
        serializer = ChatRoomDetailSerializer(
            chatroom,
            context={'request': request}
        )
        
        response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        
        return Response(serializer.data, status=response_status)


class ChatRoomListView(APIView):
    """
    내 채팅방 목록
    GET /api/chat/rooms/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # 내가 구매자이거나 판매자인 채팅방
        chatrooms = ChatRoom.objects.filter(
            Q(buyer=request.user) | Q(seller=request.user)
        ).select_related(
            'book', 'buyer', 'seller'
        ).prefetch_related(
            'messages'
        ).order_by('-updated_at')
        
        serializer = ChatRoomListSerializer(
            chatrooms,
            many=True,
            context={'request': request}
        )
        
        return Response(serializer.data)


class ChatRoomDetailView(APIView):
    """
    채팅방 상세 (메시지 포함)
    GET /api/chat/rooms/{chatroom_id}/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, chatroom_id):
        chatroom = get_object_or_404(ChatRoom, id=chatroom_id)
        
        # 권한 확인
        if not chatroom.is_participant(request.user):
            return Response(
                {'error': '접근 권한이 없습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ChatRoomDetailSerializer(
            chatroom,
            context={'request': request}
        )
        
        return Response(serializer.data)


class MessageListView(APIView):
    """
    채팅방의 메시지 목록 (페이지네이션)
    GET /api/chat/rooms/{chatroom_id}/messages/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, chatroom_id):
        chatroom = get_object_or_404(ChatRoom, id=chatroom_id)
        
        # 권한 확인
        if not chatroom.is_participant(request.user):
            return Response(
                {'error': '접근 권한이 없습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 메시지 조회
        messages = chatroom.messages.select_related('sender').all()
        
        # 내가 받은 메시지 읽음 처리
        chatroom.messages.filter(
            is_read=False
        ).exclude(
            sender=request.user
        ).update(is_read=True)
        
        serializer = MessageSerializer(messages, many=True)
        
        return Response(serializer.data)


class UnreadCountView(APIView):
    """
    전체 안 읽은 메시지 개수
    GET /api/chat/unread-count/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # 내가 참여한 채팅방들의 안 읽은 메시지
        unread_count = Message.objects.filter(
            Q(chatroom__buyer=request.user) | Q(chatroom__seller=request.user),
            is_read=False
        ).exclude(
            sender=request.user
        ).count()
        
        return Response({'unread_count': unread_count})