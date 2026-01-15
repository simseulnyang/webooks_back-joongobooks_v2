from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from accounts.factories import UserFactory
from books.factories import BookFactory
from books.models import Book


class BookListViewTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.url = "/api/books/"

    def test_get_book_list_success(self):
        BookFactory.create_batch(5, writer=self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 5)
        self.assertEqual(len(response.data["results"]), 5)
        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)

    def test_book_list_pagination(self):
        """페이지네이션 테스트"""
        BookFactory.create_batch(40)

        response = self.client.get(self.url)

        self.assertEqual(len(response.data["results"]), 10)
        self.assertIsNotNone(response.data["next"])

    def test_search_by_title(self):
        """제목으로 검색"""
        BookFactory(title="해리포터와 마법사의 돌")
        BookFactory(title="반지의 제왕")

        response = self.client.get(self.url, {"search": "해리포터"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertIn("해리포터", response.data["results"][0]["title"])

    def test_search_by_author(self):
        """저자로 검색"""
        BookFactory(author="J.K. 롤링")

        response = self.client.get(self.url, {"search": "롤링"})

        self.assertEqual(response.data["count"], 1)

    def test_filter_by_category(self):
        """카테고리 필터"""
        BookFactory.create_batch(3, category=Book.Category.NOVEL)
        BookFactory.create_batch(2, category=Book.Category.FANTASY)

        response = self.client.get(self.url, {"category": Book.Category.NOVEL})

        self.assertEqual(response.data["count"], 3)


class BookDetailViewTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.book = BookFactory(writer=self.user)
        self.url = f"/api/books/detail/{self.book.id}/"

    def test_get_book_detail_success(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.book.id)
        self.assertEqual(response.data["title"], self.book.title)
        self.assertIn("like_count", response.data)
        self.assertIn("is_liked", response.data)

    def test_get_nonexistent_book(self):
        """존재하지 않는 책 조회"""

        url = "/api/books/detail/99999/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_book_detail_with_authenticated_user(self):
        """로그인한 유저의 상세 조회"""

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class BookCreateViewTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.url = "/api/books/create/"
        self.valid_data = {
            "title": "새로운 책",
            "author": "새 저자",
            "publisher": "새 출판사",
            "condition": "최상",
            "original_price": 20000,
            "selling_price": 15000,
            "detail_info": "상세 정보",
            "category": Book.Category.NOVEL,
        }

    def test_create_book_success(self):
        """로그인한 유저가 책 생성 성공"""
        # Given
        self.client.force_authenticate(user=self.user)
        initial_count = Book.objects.count()

        # When
        response = self.client.post(self.url, self.valid_data, format="json")

        # Then
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], "새로운 책")
        self.assertEqual(response.data["writer"], self.user.id)
        self.assertEqual(Book.objects.count(), initial_count + 1)

    def test_create_book_without_authentication(self):
        """인증 없이 책 생성 시도 - 실패"""
        response = self.client.post(self.url, self.valid_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_book_with_invalid_data(self):
        """유효하지 않은 데이터로 생성"""
        self.client.force_authenticate(user=self.user)

        invalid_data = self.valid_data.copy()
        invalid_data["title"] = ""  # 빈 제목

        response = self.client.post(self.url, invalid_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("title", response.data)

    def test_create_book_missing_required_field(self):
        """필수 필드 누락"""
        self.client.force_authenticate(user=self.user)

        incomplete_data = {
            "title": "제목만 있는 책",
        }

        response = self.client.post(self.url, incomplete_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class BookUpdateViewTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.other_user = UserFactory()
        self.book = BookFactory(writer=self.user)
        self.url = f"/api/books/update/{self.book.id}/"

    def test_update_book_success(self):
        """작성자가 책 수정 성공"""
        # Given
        self.client.force_authenticate(user=self.user)

        update_data = {
            "title": "수정된 제목",
            "selling_price": 10000,
        }

        response = self.client.patch(self.url, update_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "수정된 제목")
        self.assertEqual(response.data["selling_price"], 10000)

        # DB 확인
        self.book.refresh_from_db()
        self.assertEqual(self.book.title, "수정된 제목")

    def test_update_book_partial(self):
        """일부 필드만 수정 (partial=True 테스트)"""
        self.client.force_authenticate(user=self.user)

        update_data = {"selling_price": 12000}

        response = self.client.patch(self.url, update_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["selling_price"], 12000)

        # 다른 필드는 그대로
        self.assertEqual(response.data["title"], self.book.title)

    def test_update_book_without_authentication(self):
        update_data = {"title": "수정 시도"}
        response = self.client.patch(self.url, update_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_book_without_permission(self):
        """다른 유저가 수정 시도"""

        self.client.force_authenticate(user=self.other_user)
        update_data = {"title": "다른 사람이 수정"}
        response = self.client.patch(self.url, update_data, format="json")

        # Permission에 따라 403 또는 404
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    def test_update_nonexistent_book(self):
        """존재하지 않는 책 수정"""
        self.client.force_authenticate(user=self.user)

        url = "/api/books/update/99999/"
        response = self.client.patch(url, {"title": "수정"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class BookDeleteViewTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.other_user = UserFactory()
        self.book = BookFactory(writer=self.user)
        self.url = f"/api/books/delete/{self.book.id}/"

    def test_delete_book_success(self):
        """작성자가 책 삭제 성공"""
        self.client.force_authenticate(user=self.user)
        book_id = self.book.id

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Book.objects.filter(id=book_id).exists())

    def test_delete_book_without_authentication(self):
        """인증 없이 삭제 시도"""
        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertTrue(Book.objects.filter(id=self.book.id).exists())

    def test_delete_book_without_permission(self):
        """다른 유저가 삭제 시도"""
        self.client.force_authenticate(user=self.other_user)

        response = self.client.delete(self.url)

        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])
        self.assertTrue(Book.objects.filter(id=self.book.id).exists())

    def test_delete_nonexistent_book(self):
        """존재하지 않는 책 삭제"""
        self.client.force_authenticate(user=self.user)

        url = "/api/books/delete/99999/"
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
