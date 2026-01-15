from django.test import TestCase
from django.db import IntegrityError

from accounts.factories import UserFactory
from books.factories import BookFactory
from chat.factories import ChatRoomFactory, MessageFactory

from chat.models import ChatRoom, Message


class ChatRoomModelTest(TestCase):
    def setUp(self):
        self.buyer = UserFactory()
        self.seller = UserFactory()
        self.book = BookFactory(writer=self.seller)
        self.chatroom = ChatRoomFactory(
            book=self.book,
            buyer=self.buyer,
            seller=self.seller
        )
    
    def test_chatroom_creation(self):
        """채팅방 생성 테스트"""
        self.assertIsNotNone(self.chatroom.id)
        self.assertEqual(self.chatroom.buyer, self.buyer)
        self.assertEqual(self.chatroom.seller, self.seller)
        self.assertEqual(self.chatroom.book, self.book)
    
    def test_room_group_name(self):
        """채팅방 그룹 이름 생성 테스트"""
        expected = f"chat_{self.chatroom.id}"
        self.assertEqual(self.chatroom.room_group_name, expected)
    
    def test_is_participant_buyer(self):
        """구매자가 참여자인지 확인"""
        self.assertTrue(self.chatroom.is_participant(self.buyer))
    
    def test_is_participant_seller(self):
        """판매자가 참여자인지 확인"""
        self.assertTrue(self.chatroom.is_participant(self.seller))
    
    def test_is_participant_other_user(self):
        """다른 유저는 참여자가 아님"""
        other_user = UserFactory()
        self.assertFalse(self.chatroom.is_participant(other_user))
    
    def test_get_other_user_for_buyer(self):
        """구매자 입장에서 상대방(판매자) 가져오기"""
        other = self.chatroom.get_other_user(self.buyer)
        self.assertEqual(other, self.seller)
    
    def test_get_other_user_for_seller(self):
        """판매자 입장에서 상대방(구매자) 가져오기"""
        other = self.chatroom.get_other_user(self.seller)
        self.assertEqual(other, self.buyer)
    
    def test_unique_together_constraint(self):
        """같은 책과 구매자로 중복 채팅방 생성 불가"""
        with self.assertRaises(IntegrityError):
            ChatRoom.objects.create(
                book=self.book,
                buyer=self.buyer,
                seller=self.seller
            )
    
    def test_different_buyer_can_create_chatroom(self):
        """다른 구매자는 같은 책에 대해 채팅방 생성 가능"""
        another_buyer = UserFactory()
        chatroom2 = ChatRoomFactory(
            book=self.book,
            buyer=another_buyer,
            seller=self.seller
        )
        
        self.assertIsNotNone(chatroom2.id)
        self.assertEqual(ChatRoom.objects.filter(book=self.book).count(), 2)


class MessageModelTest(TestCase):
    def setUp(self):
        self.chatroom = ChatRoomFactory()
        self.sender = self.chatroom.buyer
        self.message = MessageFactory(
            chatroom=self.chatroom,
            sender=self.sender
        )
    
    def test_message_creation(self):
        """메시지 생성 테스트"""
        self.assertIsNotNone(self.message.id)
        self.assertEqual(self.message.chatroom, self.chatroom)
        self.assertEqual(self.message.sender, self.sender)
        self.assertIsNotNone(self.message.content)
        self.assertFalse(self.message.is_read)
    
    def test_message_str(self):
        """메시지 문자열 표현 테스트"""
        content_preview = self.message.content[:30]
        expected = f'{self.sender.username}: {content_preview}'
        self.assertEqual(str(self.message), expected)
    
    def test_message_default_is_read_false(self):
        """메시지 기본 읽음 상태는 False"""
        new_message = MessageFactory(chatroom=self.chatroom, sender=self.sender)
        self.assertFalse(new_message.is_read)
    
    def test_message_ordering(self):
        """메시지 정렬 테스트 (생성일시 오름차순)"""
        message2 = MessageFactory(chatroom=self.chatroom, sender=self.sender)
        message3 = MessageFactory(chatroom=self.chatroom, sender=self.sender)
        
        messages = Message.objects.filter(chatroom=self.chatroom)
        self.assertEqual(messages[0], self.message)
        self.assertEqual(messages[1], message2)
        self.assertEqual(messages[2], message3)
    
    def test_message_cascade_delete_chatroom(self):
        """채팅방 삭제 시 메시지도 함께 삭제"""
        message_id = self.message.id
        self.chatroom.delete()
        
        self.assertFalse(Message.objects.filter(id=message_id).exists())
    
    def test_message_cascade_delete_sender(self):
        """발신자 삭제 시 메시지도 함께 삭제"""
        message_id = self.message.id
        self.sender.delete()
        
        self.assertFalse(Message.objects.filter(id=message_id).exists())
    
    def test_multiple_messages_in_chatroom(self):
        """한 채팅방에 여러 메시지 존재 가능"""
        MessageFactory.create_batch(5, chatroom=self.chatroom, sender=self.sender)
        
        self.assertEqual(self.chatroom.messages.count(), 6)  # setUp의 1개 + 5개