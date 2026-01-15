from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from accounts.factories import UserFactory
from books.factories import BookFactory
from chat.factories import ChatRoomFactory, MessageFactory
from chat.models import Message


class MessageListViewTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.buyer = UserFactory()
        self.seller = UserFactory()
        self.book = BookFactory(writer=self.seller)
        self.chatroom = ChatRoomFactory(
            book=self.book,
            buyer=self.buyer,
            seller=self.seller
        )
        self.url = f'/api/chat/rooms/{self.chatroom.id}/messages/'
    
    def test_get_message_list_success(self):
        """메시지 목록 조회 성공"""
        self.client.force_authenticate(user=self.buyer)
        
        MessageFactory.create_batch(
            5,
            chatroom=self.chatroom,
            sender=self.seller
        )
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 5)
    
    def test_get_message_list_empty(self):
        """메시지가 없을 때"""
        self.client.force_authenticate(user=self.buyer)
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)
    
    def test_get_message_list_without_authentication(self):
        """인증 없이 조회"""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_get_message_list_without_permission(self):
        """권한 없는 유저가 조회 시도"""
        other_user = UserFactory()
        self.client.force_authenticate(user=other_user)
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_get_message_list_nonexistent_chatroom(self):
        """존재하지 않는 채팅방의 메시지 조회"""
        self.client.force_authenticate(user=self.buyer)
        
        url = '/api/chat/rooms/99999/messages/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_message_list_ordering(self):
        """메시지 정렬 (오래된 순)"""
        self.client.force_authenticate(user=self.buyer)
        
        msg1 = MessageFactory(chatroom=self.chatroom, sender=self.buyer, content="첫번째")
        msg2 = MessageFactory(chatroom=self.chatroom, sender=self.seller, content="두번째")
        msg3 = MessageFactory(chatroom=self.chatroom, sender=self.buyer, content="세번째")
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.data[0]['content'], "첫번째")
        self.assertEqual(response.data[1]['content'], "두번째")
        self.assertEqual(response.data[2]['content'], "세번째")
    
    def test_auto_mark_as_read_when_viewing_messages(self):
        """메시지 조회 시 자동으로 읽음 처리"""
        self.client.force_authenticate(user=self.buyer)
        
        # 판매자가 보낸 안 읽은 메시지들
        messages = MessageFactory.create_batch(
            3,
            chatroom=self.chatroom,
            sender=self.seller,
            is_read=False
        )
        
        # 조회 전 확인
        for msg in messages:
            self.assertFalse(msg.is_read)
        
        # 메시지 조회
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 조회 후 메시지들이 읽음 처리되었는지 확인
        for msg in messages:
            msg.refresh_from_db()
            self.assertTrue(msg.is_read)
    
    def test_does_not_mark_own_messages_as_read(self):
        """자신이 보낸 메시지는 읽음 처리하지 않음"""
        self.client.force_authenticate(user=self.buyer)
        
        # 내가 보낸 메시지 (is_read=False)
        my_message = MessageFactory(
            chatroom=self.chatroom,
            sender=self.buyer,
            is_read=False
        )
        
        response = self.client.get(self.url)
        
        # 내 메시지는 읽음 처리되지 않음
        my_message.refresh_from_db()
        self.assertFalse(my_message.is_read)
    
    def test_message_list_includes_sender_info(self):
        """메시지에 발신자 정보 포함"""
        self.client.force_authenticate(user=self.buyer)
        
        MessageFactory(
            chatroom=self.chatroom,
            sender=self.seller,
            content="테스트 메시지"
        )
        
        response = self.client.get(self.url)
        
        message_data = response.data[0]
        self.assertIn('sender', message_data)
        self.assertIn('sender_username', message_data)
        self.assertIn('sender_email', message_data)
        self.assertEqual(message_data['sender'], self.seller.id)
        self.assertEqual(message_data['sender_username'], self.seller.username)
    
    def test_as_seller_can_view_messages(self):
        """판매자도 메시지 조회 가능"""
        self.client.force_authenticate(user=self.seller)
        
        MessageFactory.create_batch(
            3,
            chatroom=self.chatroom,
            sender=self.buyer
        )
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
    
    def test_mark_read_only_other_user_messages(self):
        """상대방의 메시지만 읽음 처리"""
        self.client.force_authenticate(user=self.buyer)
        
        # 판매자가 보낸 메시지
        seller_msg = MessageFactory(
            chatroom=self.chatroom,
            sender=self.seller,
            is_read=False
        )
        
        # 내가 보낸 메시지
        my_msg = MessageFactory(
            chatroom=self.chatroom,
            sender=self.buyer,
            is_read=False
        )
        
        response = self.client.get(self.url)
        
        # 판매자 메시지는 읽음 처리
        seller_msg.refresh_from_db()
        self.assertTrue(seller_msg.is_read)
        
        # 내 메시지는 그대로
        my_msg.refresh_from_db()
        self.assertFalse(my_msg.is_read)