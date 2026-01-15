import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from PIL import Image
from rest_framework import status
from rest_framework.test import APIRequestFactory

from accounts.factories import UserFactory
from books.factories import BookFactory, FavoriteFactory
from books.models import Book
from books.serializers import BookSerializer, FavoriteSerializer


class BookSerializerTest(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.book = BookFactory(writer=self.user)
        self.factory = APIRequestFactory()

    def test_book_serializer_create(self):
        """모든 필수 필드 포함 시 유효한 데이터를 사용하여 BookSerializer로 책 생성 테스트"""

        # 가짜 이미지 생성
        image = Image.new("RGB", (100, 100), color="green")
        image_file = io.BytesIO()
        image.save(image_file, format="JPEG")
        image_file.seek(0)

        uploaded_file = SimpleUploadedFile(name="test_image.jpg", content=image_file.read(), content_type="image/jpeg")

        data = {
            "title": "새로운 책",
            "author": "새로운 작가",
            "publisher": "새로운 출판사",
            "condition": "최상",
            "original_price": 20000,
            "selling_price": 15000,
            "book_image": uploaded_file,
            "detail_info": "새로운 책의 상세 정보 내용",
            "category": Book.Category.NOVEL,
        }

        serializer = BookSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        # save 시 writer 전달
        book = serializer.save(writer=self.user)
        self.assertEqual(book.writer, self.user)

    def test_serializer_create_without_book_image(self):
        """book_image 없이도 책 생성이 가능한지 테스트"""

        data = {
            "title": "이미지 없는 책",
            "author": "작가",
            "publisher": "출판사",
            "condition": "양호",
            "original_price": 15000,
            "selling_price": 12000,
            # 'book_image' 필드 누락
            "detail_info": "이미지 없는 책의 상세 정보 내용",
            "category": Book.Category.FANTASY,
        }

        serializer = BookSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        book = serializer.save(writer=self.user)
        self.assertEqual(book.book_image, "")

    def test_book_serializer_invalid_data(self):
        """필수 필드 누락으로 유효하지 않은 데이터를 사용하여 BookSerializer 검증 테스트"""
        data = {
            "title": "",  # 제목 누락
            "author": "작가",
            "publisher": "출판사",
            "condition": "좋음",
            "original_price": 1000,
            "selling_price": 5000,
            "detail_info": "상세 정보",
            "category": "InvalidCategory",  # 유효하지 않음
            # book_image 필드는 blank=True 이므로 누락되어도 상관없음
        }

        serializer = BookSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("title", serializer.errors)
        self.assertIn("category", serializer.errors)

    def test_like_count_in_serializer(self):
        """좋아요 개수가 Serializer에 올바르게 포함되는지 테스트"""
        FavoriteFactory.create_batch(3, book=self.book)

        serializer = BookSerializer(self.book)
        self.assertEqual(serializer.data["like_count"], 3)

    def test_is_liked_with_authenticated_user(self):
        """인증된 유저의 좋아요 여부"""
        FavoriteFactory(user=self.user, book=self.book)

        request = self.factory.get("/")
        request.user = self.user

        serializer = BookSerializer(self.book, context={"request": request})
        self.assertTrue(serializer.data["is_liked"])

    def test_is_liked_without_favorite(self):
        """좋아요를 하지 않은 경우"""
        request = self.factory.get("/")
        request.user = self.user

        serializer = BookSerializer(self.book, context={"request": request})
        self.assertFalse(serializer.data["is_liked"])


class FavoriteSerializerTest(TestCase):
    def setUp(self):
        self.book = BookFactory()
        self.user = UserFactory()
        self.favorite = FavoriteFactory(user=self.user, book=self.book)

    def test_nested_book_data(self):
        """FavoriteSerializer에서 중첩된 Book 데이터 테스트"""
        serializer = FavoriteSerializer(self.favorite)
        book_data = serializer.data["book"]

        self.assertIn("id", book_data)
        self.assertIn("title", book_data)
        self.assertEqual(book_data["id"], self.book.id)
