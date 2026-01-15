from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from accounts.factories import UserFactory
from books.factories import BookFactory, FavoriteFactory
from books.models import Favorite


class FavoriteToggleViewTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.book = BookFactory()
        self.url = f"/api/books/{self.book.id}/favorite/"

    def test_add_favorite_success(self):
        self.client.force_authenticate(user=self.user)
        initial_count = Favorite.objects.count()

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["is_liked"])
        self.assertEqual(response.data["like_count"], 1)
        self.assertEqual(Favorite.objects.count(), initial_count + 1)

    def test_remove_favorite_success(self):
        """좋아요 취소 성공"""
        self.client.force_authenticate(user=self.user)
        FavoriteFactory(user=self.user, book=self.book)
        initial_count = Favorite.objects.count()

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["is_liked"])
        self.assertEqual(response.data["like_count"], 0)
        self.assertEqual(Favorite.objects.count(), initial_count - 1)

    def test_toggle_favorite_multiple_times(self):
        """좋아요 여러 번 클릭하기"""
        self.client.force_authenticate(user=self.user)

        # 첫 번째: 추가
        response1 = self.client.post(self.url)
        self.assertTrue(response1.data["is_liked"])

        # 두 번째: 취소
        response2 = self.client.post(self.url)
        self.assertFalse(response2.data["is_liked"])

        # 세 번째: 다시 추가
        response3 = self.client.post(self.url)
        self.assertTrue(response3.data["is_liked"])

    def test_favorite_without_authentication(self):
        """인증 없이 좋아요 시도"""
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_favorite_nonexistent_book(self):
        """존재하지 않는 책에 좋아요"""
        self.client.force_authenticate(user=self.user)

        url = "/api/books/99999/favorite/"
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_favorite_count_with_multiple_users(self):
        """여러 유저가 좋아요"""
        self.client.force_authenticate(user=self.user)

        # 첫 번째 유저 좋아요
        response1 = self.client.post(self.url)
        self.assertEqual(response1.data["like_count"], 1)

        # 두 번째 유저 좋아요
        user2 = UserFactory()
        FavoriteFactory(user=user2, book=self.book)

        # 좋아요 개수 확인
        response2 = self.client.post(self.url)  # 토글 (취소)
        self.assertEqual(response2.data["like_count"], 1)  # user2만 남음

    def test_favorite_message_text(self):
        """응답 메시지 확인"""
        self.client.force_authenticate(user=self.user)

        # 추가 시
        response_add = self.client.post(self.url)
        self.assertIn("message", response_add.data)
        self.assertIn("좋아요", response_add.data["message"])

        # 취소 시
        response_remove = self.client.post(self.url)
        self.assertIn("message", response_remove.data)
        self.assertIn("취소", response_remove.data["message"])


class FavoriteListViewTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.url = "/api/books/favorites/"

    def test_get_favorite_list_success(self):
        """좋아요 목록 조회 성공"""
        self.client.force_authenticate(user=self.user)
        FavoriteFactory.create_batch(3, user=self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(len(response.data["results"]), 3)

    def test_favorite_list_empty(self):
        """좋아요 없을 때"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    def test_favorite_list_without_authentication(self):
        """인증 없이 목록 조회"""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_favorite_list_only_shows_my_favorites(self):
        """내 좋아요만 보임"""
        self.client.force_authenticate(user=self.user)
        other_user = UserFactory()

        FavoriteFactory.create_batch(2, user=self.user)
        FavoriteFactory.create_batch(3, user=other_user)

        response = self.client.get(self.url)

        self.assertEqual(response.data["count"], 2)

    def test_favorite_list_pagination(self):
        """페이지네이션 테스트"""
        self.client.force_authenticate(user=self.user)

        FavoriteFactory.create_batch(15, user=self.user)

        response = self.client.get(self.url)

        self.assertEqual(len(response.data["results"]), 10)
        self.assertIsNotNone(response.data["next"])

    def test_favorite_list_includes_book_info(self):
        """책 정보가 포함되는지"""
        self.client.force_authenticate(user=self.user)

        favorite = FavoriteFactory(user=self.user)

        response = self.client.get(self.url)

        book_data = response.data["results"][0]["book"]
        self.assertIn("id", book_data)
        self.assertIn("title", book_data)
        self.assertEqual(book_data["id"], favorite.book.id)
