# chat/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Q
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from .models import ChatRoom, Message
from .serializers import (
    ChatRoomListSerializer,
    ChatRoomDetailSerializer,
    MessageSerializer
)
from books.models import Book


class ChatRoomCreateOrGetView(APIView):
    """
    채팅방 생성 또는 기존 생성된 방 불러오기
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Chat - ChatROOM'],
        summary='채팅방 생성 또는 불러오기',
        description='''
        특정 책에 대한 채팅방을 생성하거나 기존 생성되었던 채팅방을 불러옵니다.
        - 이미 해당 책에 대한 채팅방이 존재하면 기존 채팅방 반환 (200)
        - 새로 생성되었다면 201 상태 코드 반환
        - 본인 책에 대해서는 채팅방 생성 불가능 (판매자가 판매하고 있는 본인 책의 채팅방 생성 불가능)
        ''',
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'book_id': {
                        'type': 'integer',
                        'description': '채팅하려는 책의 ID'
                    }
                },
                'required': ['book_id']
            }
        },
        responses={
            201: ChatRoomDetailSerializer,
            200: ChatRoomDetailSerializer,
            400: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'}
                }
            },
            404: {
                'type': 'object',
                'properties': {
                    'detail': {'type': 'string'}
                }
            }
        },
        examples=[
            OpenApiExample(
                '채팅방 생성 요청',
                value={'book_id': 1},
                request_only=True,
            ),
            OpenApiExample(
                '새 채팅방 생성 성공 (201)',
                value={
                    'id': 1,
                    'book': {
                        'id': 1,
                        'title': '해리포터와 마법사의 돌',
                        'author': 'J.K. 롤링',
                        'selling_price': 15000,
                    },
                    'buyer': {
                        'id': 2,
                        'username': '구매자',
                        'email': 'buyer@example.com'
                    },
                    'seller': {
                        'id': 1,
                        'username': '판매자',
                        'email': 'seller@example.com'
                    },
                    'messages': [],
                    'created_at': '2025-01-15T10:00:00Z',
                    'updated_at': '2025-01-15T10:00:00Z'
                },
                response_only=True,
                status_codes=['201']
            ),
            OpenApiExample(
                '기존 채팅방 반환 (200)',
                value={
                    'id': 1,
                    'book': {
                        'id': 1,
                        'title': '해리포터와 마법사의 돌',
                    },
                    'buyer': {'id': 2, 'username': '구매자', 'email': 'buyer@example.com'},
                    'seller': {'id': 1, 'username': '판매자', 'email': 'seller@example.com'},
                    'messages': [
                        {
                            'id': 1,
                            'content': '안녕하세요',
                            'sender': 2,
                            'sender_username': '구매자',
                            'created_at': '2025-01-15T10:05:00Z'
                        }
                    ],
                    'created_at': '2025-01-15T10:00:00Z',
                    'updated_at': '2025-01-15T10:05:00Z'
                },
                response_only=True,
                status_codes=['200']
            ),
        ],
    )
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
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Chat - ChatRoomLIST'],
        summary='내 채팅방 목록 조회',
        description='''
        현재 로그인한 사용자가 참여 중인 모든 채팅방 목록을 반환합니다.
        - 내가 구매자인 채팅방
        - 내가 판매자인 채팅방
        - 최근 업데이트 순으로 정렬
        - 각 채팅방의 상대방 정보, 마지막 메시지, 안 읽은 메시지 개수 포함
        ''',
        responses={
            200: ChatRoomListSerializer(many=True),
        },
        examples=[
            OpenApiExample(
                '채팅방 목록 조회 성공',
                value=[
                    {
                        'id': 2,
                        'book': {
                            'id': 2,
                            'title': '반지의 제왕',
                            'author': 'J.R.R. 톨킨',
                            'selling_price': 20000,
                            'book_image': None,
                            'sale_condition': 'For Sale',
                            'updated_at': '2025년 01월 15일',
                            'like_count': 5
                        },
                        'other_user': {
                            'id': 3,
                            'username': '판매자2',
                            'email': 'seller2@example.com',
                            'profile_image': ''
                        },
                        'last_message': {
                            'content': '네, 가능합니다!',
                            'sender_username': '판매자2',
                            'created_at': '2025-01-15T14:30:00Z',
                            'is_read': True
                        },
                        'unread_count': 0,
                        'created_at': '2025-01-15T10:00:00Z',
                        'updated_at': '2025-01-15T14:30:00Z'
                    },
                    {
                        'id': 1,
                        'book': {
                            'id': 1,
                            'title': '해리포터와 마법사의 돌',
                            'author': 'J.K. 롤링',
                            'selling_price': 15000,
                        },
                        'other_user': {
                            'id': 1,
                            'username': '판매자1',
                            'email': 'seller1@example.com',
                            'profile_image': ''
                        },
                        'last_message': {
                            'content': '가격 협상 가능할까요?',
                            'sender_username': '구매자',
                            'created_at': '2025-01-15T11:00:00Z',
                            'is_read': False
                        },
                        'unread_count': 2,
                        'created_at': '2025-01-14T10:00:00Z',
                        'updated_at': '2025-01-15T11:00:00Z'
                    }
                ],
                response_only=True,
            ),
        ],
    )
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
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Chat - Room'],
        summary='채팅방 상세 조회',
        description='''
        특정 채팅방의 상세 정보를 조회합니다.
        - 채팅방의 기본 정보 (책, 구매자, 판매자)
        - 모든 메시지 내역 포함
        - 채팅방 참여자만 조회 가능
        ''',
        parameters=[
            OpenApiParameter(
                name='chatroom_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='조회할 채팅방 ID'
            ),
        ],
        responses={
            200: ChatRoomDetailSerializer,
            403: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'}
                }
            },
            404: {
                'type': 'object',
                'properties': {
                    'detail': {'type': 'string'}
                }
            },
        },
        examples=[
            OpenApiExample(
                '채팅방 상세 조회 성공',
                value={
                    'id': 1,
                    'book': {
                        'id': 1,
                        'title': '해리포터와 마법사의 돌',
                        'author': 'J.K. 롤링',
                        'selling_price': 15000,
                        'book_image': None,
                        'sale_condition': 'For Sale',
                        'updated_at': '2025년 01월 15일',
                        'like_count': 10
                    },
                    'buyer': {
                        'id': 2,
                        'username': '구매자',
                        'email': 'buyer@example.com'
                    },
                    'seller': {
                        'id': 1,
                        'username': '판매자',
                        'email': 'seller@example.com'
                    },
                    'messages': [
                        {
                            'id': 1,
                            'sender': 2,
                            'sender_username': '구매자',
                            'sender_email': 'buyer@example.com',
                            'content': '안녕하세요, 책 상태가 어떤가요?',
                            'is_read': True,
                            'created_at': '2025-01-15T10:00:00Z'
                        },
                        {
                            'id': 2,
                            'sender': 1,
                            'sender_username': '판매자',
                            'sender_email': 'seller@example.com',
                            'content': '상태 아주 좋습니다!',
                            'is_read': True,
                            'created_at': '2025-01-15T10:05:00Z'
                        }
                    ],
                    'created_at': '2025-01-15T09:00:00Z',
                    'updated_at': '2025-01-15T10:05:00Z'
                },
                response_only=True,
            ),
        ],
    )
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
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Chat - Message'],
        summary='채팅방 메시지 목록 조회',
        description='''
        특정 채팅방의 모든 메시지를 조회합니다.
        - 메시지는 생성 시간 순으로 정렬 (오래된 것부터)
        - 조회 시 상대방이 보낸 안 읽은 메시지는 자동으로 읽음 처리
        - 채팅방 참여자만 조회 가능
        ''',
        parameters=[
            OpenApiParameter(
                name='chatroom_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='메시지를 조회할 채팅방 ID'
            ),
        ],
        responses={
            200: MessageSerializer(many=True),
            403: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'}
                }
            },
            404: {
                'type': 'object',
                'properties': {
                    'detail': {'type': 'string'}
                }
            },
        },
        examples=[
            OpenApiExample(
                '메시지 목록 조회 성공',
                value=[
                    {
                        'id': 1,
                        'sender': 2,
                        'sender_username': '구매자',
                        'sender_email': 'buyer@example.com',
                        'content': '책 상태가 궁금합니다',
                        'is_read': True,
                        'created_at': '2025-01-15T10:00:00Z'
                    },
                    {
                        'id': 2,
                        'sender': 1,
                        'sender_username': '판매자',
                        'sender_email': 'seller@example.com',
                        'content': '거의 새 책입니다!',
                        'is_read': True,
                        'created_at': '2025-01-15T10:05:00Z'
                    },
                    {
                        'id': 3,
                        'sender': 2,
                        'sender_username': '구매자',
                        'sender_email': 'buyer@example.com',
                        'content': '가격 협상 가능할까요?',
                        'is_read': True,
                        'created_at': '2025-01-15T10:10:00Z'
                    }
                ],
                response_only=True,
            ),
        ],
    )
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
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Chat - Message'],
        summary='안 읽은 메시지 개수 조회',
        description='''
        현재 로그인한 사용자의 전체 안 읽은 메시지 개수를 반환합니다.
        - 내가 참여한 모든 채팅방의 안 읽은 메시지 합계
        - 자신이 보낸 메시지는 제외
        - 알림 배지 등에 활용 가능
        ''',
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'unread_count': {
                        'type': 'integer',
                        'description': '안 읽은 메시지 개수'
                    }
                }
            },
        },
        examples=[
            OpenApiExample(
                '안 읽은 메시지 5개',
                value={'unread_count': 5},
                response_only=True,
            ),
            OpenApiExample(
                '안 읽은 메시지 없음',
                value={'unread_count': 0},
                response_only=True,
            ),
        ],
    )
    def get(self, request):
        # 내가 참여한 채팅방들의 안 읽은 메시지
        unread_count = Message.objects.filter(
            Q(chatroom__buyer=request.user) | Q(chatroom__seller=request.user),
            is_read=False
        ).exclude(
            sender=request.user
        ).count()
        
        return Response({'unread_count': unread_count})