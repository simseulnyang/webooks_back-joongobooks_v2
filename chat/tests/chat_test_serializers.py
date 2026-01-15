from django.test import TestCase
from rest_framework.test import APIRequestFactory

from accounts.factories import UserFactory
from books.factories import BookFactory
from chat.factories import ChatRoomFactory, MessageFactory

from chat.serializers import (
    MessageSerializer,
    ChatRoomListSerializer,
    ChatRoomDetailSerializer
)


class MessageSerializerTest(TestCase):
    def setUp(self):
        self.chatroom = ChatRoomFactory()
        self.sender = self.chatroom.buyer
        self.message = MessageFactory(
            chatroom=self.chatroom,
            sender=self.sender,
            content="테스트 메시지입니다."
        )
    
    def test_message_serializer_fields(self):
        """메시지 시리얼라이저 필드 확인"""
        serializer = MessageSerializer(self.message)
        data = serializer.data
        
        self.assertIn('id', data)
        self.assertIn('sender', data)
        self.assertIn('sender_username', data)
        self.assertIn('sender_email', data)
        self.assertIn('content', data)
        self.assertIn('is_read', data)
        self.assertIn('created_at', data)
    
    def test_message_serializer_sender_info(self):
        """발신자 정보가 올바르게 포함되는지 확인"""
        serializer = MessageSerializer(self.message)
        data = serializer.data
        
        self.assertEqual(data['sender'], self.sender.id)
        self.assertEqual(data['sender_username'], self.sender.username)
        self.assertEqual(data['sender_email'], self.sender.email)
    
    def test_message_serializer_content(self):
        """메시지 내용 확인"""
        serializer = MessageSerializer(self.message)
        self.assertEqual(serializer.data['content'], "테스트 메시지입니다.")


class ChatRoomListSerializerTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.buyer = UserFactory()
        self.seller = UserFactory()
        self.book = BookFactory(writer=self.seller)
        self.chatroom = ChatRoomFactory(
            book=self.book,
            buyer=self.buyer,
            seller=self.seller
        )
    
    def test_chatroom_list_serializer_fields(self):
        """채팅방 목록 시리얼라이저 필드 확인"""
        request = self.factory.get('/')
        request.user = self.buyer
        
        serializer = ChatRoomListSerializer(
            self.chatroom,
            context={'request': request}
        )
        data = serializer.data
        
        self.assertIn('id', data)
        self.assertIn('book', data)
        self.assertIn('other_user', data)
        self.assertIn('last_message', data)
        self.assertIn('unread_count', data)
        self.assertIn('created_at', data)
        self.assertIn('updated_at', data)
    
    def test_other_user_for_buyer(self):
        """구매자 입장에서 상대방(판매자) 정보 확인"""
        request = self.factory.get('/')
        request.user = self.buyer
        
        serializer = ChatRoomListSerializer(
            self.chatroom,
            context={'request': request}
        )
        data = serializer.data
        
        self.assertEqual(data['other_user']['id'], self.seller.id)
        self.assertEqual(data['other_user']['username'], self.seller.username)
        self.assertEqual(data['other_user']['email'], self.seller.email)
    
    def test_other_user_for_seller(self):
        """판매자 입장에서 상대방(구매자) 정보 확인"""
        request = self.factory.get('/')
        request.user = self.seller
        
        serializer = ChatRoomListSerializer(
            self.chatroom,
            context={'request': request}
        )
        data = serializer.data
        
        self.assertEqual(data['other_user']['id'], self.buyer.id)
        self.assertEqual(data['other_user']['username'], self.buyer.username)
    
    def test_last_message_none(self):
        """메시지가 없을 때 last_message는 None"""
        request = self.factory.get('/')
        request.user = self.buyer
        
        serializer = ChatRoomListSerializer(
            self.chatroom,
            context={'request': request}
        )
        
        self.assertIsNone(serializer.data['last_message'])
    
    def test_last_message_exists(self):
        """마지막 메시지 정보 확인"""
        message = MessageFactory(
            chatroom=self.chatroom,
            sender=self.seller,
            content="안녕하세요"
        )
        
        request = self.factory.get('/')
        request.user = self.buyer
        
        serializer = ChatRoomListSerializer(
            self.chatroom,
            context={'request': request}
        )
        data = serializer.data
        
        self.assertIsNotNone(data['last_message'])
        self.assertEqual(data['last_message']['content'], "안녕하세요")
        self.assertEqual(data['last_message']['sender_username'], self.seller.username)
    
    def test_unread_count_zero(self):
        """안 읽은 메시지가 없을 때"""
        request = self.factory.get('/')
        request.user = self.buyer
        
        serializer = ChatRoomListSerializer(
            self.chatroom,
            context={'request': request}
        )
        
        self.assertEqual(serializer.data['unread_count'], 0)
    
    def test_unread_count_excludes_own_messages(self):
        """자신이 보낸 메시지는 안 읽은 개수에서 제외"""
        MessageFactory.create_batch(
            3,
            chatroom=self.chatroom,
            sender=self.buyer,
            is_read=False
        )
        
        request = self.factory.get('/')
        request.user = self.buyer
        
        serializer = ChatRoomListSerializer(
            self.chatroom,
            context={'request': request}
        )
        
        self.assertEqual(serializer.data['unread_count'], 0)
    
    def test_unread_count_includes_other_messages(self):
        """상대방이 보낸 안 읽은 메시지 개수"""
        MessageFactory.create_batch(
            5,
            chatroom=self.chatroom,
            sender=self.seller,
            is_read=False
        )
        
        request = self.factory.get('/')
        request.user = self.buyer
        
        serializer = ChatRoomListSerializer(
            self.chatroom,
            context={'request': request}
        )
        
        self.assertEqual(serializer.data['unread_count'], 5)


class ChatRoomDetailSerializerTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.buyer = UserFactory()
        self.seller = UserFactory()
        self.book = BookFactory(writer=self.seller)
        self.chatroom = ChatRoomFactory(
            book=self.book,
            buyer=self.buyer,
            seller=self.seller
        )
    
    def test_chatroom_detail_serializer_fields(self):
        """채팅방 상세 시리얼라이저 필드 확인"""
        serializer = ChatRoomDetailSerializer(self.chatroom)
        data = serializer.data
        
        self.assertIn('id', data)
        self.assertIn('book', data)
        self.assertIn('buyer', data)
        self.assertIn('seller', data)
        self.assertIn('messages', data)
        self.assertIn('created_at', data)
        self.assertIn('updated_at', data)
    
    def test_buyer_seller_info(self):
        """구매자와 판매자 정보 확인"""
        serializer = ChatRoomDetailSerializer(self.chatroom)
        data = serializer.data
        
        self.assertEqual(data['buyer']['id'], self.buyer.id)
        self.assertEqual(data['buyer']['username'], self.buyer.username)
        self.assertEqual(data['seller']['id'], self.seller.id)
        self.assertEqual(data['seller']['username'], self.seller.username)
    
    def test_messages_included(self):
        """메시지 목록이 포함되는지 확인"""
        MessageFactory.create_batch(
            3,
            chatroom=self.chatroom,
            sender=self.buyer
        )
        
        serializer = ChatRoomDetailSerializer(self.chatroom)
        data = serializer.data
        
        self.assertEqual(len(data['messages']), 3)
        self.assertIn('content', data['messages'][0])
        self.assertIn('sender_username', data['messages'][0])