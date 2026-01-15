from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from accounts.factories import UserFactory
from books.factories import BookFactory
from chat.factories import ChatRoomFactory, MessageFactory
from chat.models import ChatRoom


class ChatRoomCreateOrGetViewTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.buyer = UserFactory()
        self.seller = UserFactory()
        self.book = BookFactory(writer=self.seller)
        self.url = "/api/chat/rooms/create/"

    def test_create_chatroom_success(self):
        """채팅방 생성 성공"""
        self.client.force_authenticate(user=self.buyer)

        data = {"book_id": self.book.id}
        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["buyer"]["id"], self.buyer.id)
        self.assertEqual(response.data["seller"]["id"], self.seller.id)
        self.assertEqual(response.data["book"]["id"], self.book.id)

    def test_get_existing_chatroom(self):
        """이미 존재하는 채팅방 반환"""
        self.client.force_authenticate(user=self.buyer)

        # 먼저 채팅방 생성
        existing_chatroom = ChatRoomFactory(book=self.book, buyer=self.buyer, seller=self.seller)

        data = {"book_id": self.book.id}
        response = self.client.post(self.url, data, format="json")

        # 200 OK (새로 생성되지 않음)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], existing_chatroom.id)

    def test_create_chatroom_without_authentication(self):
        """인증 없이 채팅방 생성 시도"""
        data = {"book_id": self.book.id}
        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_chatroom_without_book_id(self):
        """book_id 없이 요청"""
        self.client.force_authenticate(user=self.buyer)

        response = self.client.post(self.url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_create_chatroom_with_invalid_book_id(self):
        """존재하지 않는 book_id로 요청"""
        self.client.force_authenticate(user=self.buyer)

        data = {"book_id": 99999}
        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_chatroom_with_own_book(self):
        """자신의 책에 채팅방 생성 시도 (불가)"""
        self.client.force_authenticate(user=self.seller)

        data = {"book_id": self.book.id}
        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertIn("본인의 책", response.data["error"])


class ChatRoomListViewTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.url = "/api/chat/rooms/"

    def test_get_chatroom_list_success(self):
        """채팅방 목록 조회 성공"""
        self.client.force_authenticate(user=self.user)

        # 내가 구매자인 채팅방
        ChatRoomFactory.create_batch(3, buyer=self.user)
        # 내가 판매자인 채팅방
        ChatRoomFactory.create_batch(2, seller=self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 5)

    def test_get_chatroom_list_empty(self):
        """채팅방이 없을 때"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_get_chatroom_list_without_authentication(self):
        """인증 없이 목록 조회"""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_chatroom_list_only_shows_my_chatrooms(self):
        """내 채팅방만 보임"""
        self.client.force_authenticate(user=self.user)

        # 내 채팅방
        ChatRoomFactory.create_batch(2, buyer=self.user)

        # 다른 사람 채팅방
        other_user = UserFactory()
        ChatRoomFactory.create_batch(3, buyer=other_user)

        response = self.client.get(self.url)

        self.assertEqual(len(response.data), 2)

    def test_chatroom_list_includes_other_user_info(self):
        """채팅방 목록에 상대방 정보 포함"""
        self.client.force_authenticate(user=self.user)

        seller = UserFactory()
        book = BookFactory(writer=seller)
        ChatRoomFactory(book=book, buyer=self.user, seller=seller)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("other_user", response.data[0])
        self.assertEqual(response.data[0]["other_user"]["id"], seller.id)

    def test_chatroom_list_ordering(self):
        """채팅방 정렬 (최근 업데이트순)"""
        self.client.force_authenticate(user=self.user)

        chatroom1 = ChatRoomFactory(buyer=self.user)
        chatroom2 = ChatRoomFactory(buyer=self.user)
        chatroom3 = ChatRoomFactory(buyer=self.user)

        response = self.client.get(self.url)

        # 최근 것이 먼저
        self.assertEqual(response.data[0]["id"], chatroom3.id)
        self.assertEqual(response.data[1]["id"], chatroom2.id)
        self.assertEqual(response.data[2]["id"], chatroom1.id)


class ChatRoomDetailViewTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.buyer = UserFactory()
        self.seller = UserFactory()
        self.book = BookFactory(writer=self.seller)
        self.chatroom = ChatRoomFactory(book=self.book, buyer=self.buyer, seller=self.seller)
        self.url = f"/api/chat/rooms/{self.chatroom.id}/"

    def test_get_chatroom_detail_as_buyer(self):
        """구매자로서 채팅방 상세 조회"""
        self.client.force_authenticate(user=self.buyer)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.chatroom.id)
        self.assertIn("messages", response.data)

    def test_get_chatroom_detail_as_seller(self):
        """판매자로서 채팅방 상세 조회"""
        self.client.force_authenticate(user=self.seller)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.chatroom.id)

    def test_get_chatroom_detail_without_authentication(self):
        """인증 없이 조회"""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_chatroom_detail_without_permission(self):
        """권한 없는 유저가 조회 시도"""
        other_user = UserFactory()
        self.client.force_authenticate(user=other_user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("error", response.data)

    def test_get_nonexistent_chatroom(self):
        """존재하지 않는 채팅방 조회"""
        self.client.force_authenticate(user=self.buyer)

        url = "/api/chat/rooms/99999/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_chatroom_detail_has_messages_field(self):
        """채팅방 상세에 messages 필드가 있는지 확인"""
        self.client.force_authenticate(user=self.buyer)

        response = self.client.get(self.url)

        self.assertIn("messages", response.data)
        self.assertIsInstance(response.data["messages"], list)


class UnreadCountViewTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.url = "/api/chat/unread-count/"

    def test_get_unread_count_zero(self):
        """안 읽은 메시지가 없을 때"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["unread_count"], 0)

    def test_get_unread_count_with_unread_messages(self):
        """안 읽은 메시지가 있을 때"""
        self.client.force_authenticate(user=self.user)

        # 내가 구매자인 채팅방
        chatroom1 = ChatRoomFactory(buyer=self.user)
        MessageFactory.create_batch(3, chatroom=chatroom1, sender=chatroom1.seller, is_read=False)

        # 내가 판매자인 채팅방
        chatroom2 = ChatRoomFactory(seller=self.user)
        MessageFactory.create_batch(2, chatroom=chatroom2, sender=chatroom2.buyer, is_read=False)

        response = self.client.get(self.url)

        self.assertEqual(response.data["unread_count"], 5)

    def test_unread_count_excludes_own_messages(self):
        """자신이 보낸 메시지는 제외"""
        self.client.force_authenticate(user=self.user)

        chatroom = ChatRoomFactory(buyer=self.user)

        # 내가 보낸 메시지
        MessageFactory.create_batch(4, chatroom=chatroom, sender=self.user, is_read=False)

        response = self.client.get(self.url)

        self.assertEqual(response.data["unread_count"], 0)

    def test_unread_count_excludes_read_messages(self):
        """읽은 메시지는 제외"""
        self.client.force_authenticate(user=self.user)

        chatroom = ChatRoomFactory(buyer=self.user)

        # 읽지 않은 메시지
        MessageFactory.create_batch(2, chatroom=chatroom, sender=chatroom.seller, is_read=False)

        # 읽은 메시지
        MessageFactory.create_batch(3, chatroom=chatroom, sender=chatroom.seller, is_read=True)

        response = self.client.get(self.url)

        self.assertEqual(response.data["unread_count"], 2)

    def test_get_unread_count_without_authentication(self):
        """인증 없이 조회"""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
