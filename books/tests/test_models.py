from django.db import IntegrityError
from django.test import TestCase

from accounts.factories import UserFactory
from books.factories import BookFactory, FavoriteFactory
from books.models import Book, Favorite


class BookModelTest(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.book = BookFactory(writer=self.user)

    def test_book_creation(self):
        """책 생성 테스트"""
        self.assertIsNotNone(self.book.id)
        self.assertEqual(self.book.writer, self.user)
        self.assertIn("테스트 책", self.book.title)

    def test_like_count_zero(self):
        """초기 좋아요 개수 : 0"""
        self.assertEqual(self.book.like_count(), 0)

    def test_like_count_increment(self):
        """좋아요 추가 시 개수 증가"""
        FavoriteFactory(user=self.user, book=self.book)
        self.assertEqual(self.book.like_count(), 1)

        user2 = UserFactory()
        FavoriteFactory(user=user2, book=self.book)
        self.assertEqual(self.book.like_count(), 2)

    def test_is_liked_by_authenticated_user(self):
        """인증된 유저가 좋아요를 눌렀는지 확인"""
        self.assertFalse(self.book.is_liked_by(self.user))

        FavoriteFactory(user=self.user, book=self.book)
        self.assertTrue(self.book.is_liked_by(self.user))

    def test_is_liked_by_other_user(self):
        """다른 유저가 좋아요를 눌렀고, 현재 로그인한 유저와는 상관이 없음"""
        user2 = UserFactory()
        FavoriteFactory(user=user2, book=self.book)

        self.assertFalse(self.book.is_liked_by(self.user))

    def test_book_category_choices(self):
        book = BookFactory(category=Book.Category.FANTASY)
        self.assertEqual(book.category, Book.Category.FANTASY)


class FavoriteModelTest(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.book = BookFactory(writer=self.user)

    def test_favorite_creation(self):
        """좋아요 생성 테스트"""
        favorite = FavoriteFactory(user=self.user, book=self.book)

        self.assertIsNotNone(favorite.id)
        self.assertEqual(favorite.user, self.user)
        self.assertEqual(favorite.book, self.book)
        self.assertIsNotNone(favorite.created_at)

    def test_favorite_unique_constraint(self):
        """중복 좋아요 방지 테스트"""
        FavoriteFactory(user=self.user, book=self.book)

        with self.assertRaises(IntegrityError):
            Favorite.objects.create(user=self.user, book=self.book)

    def test_favorite_different_users(self):
        """다른 유저는 같은 책에 좋아요 가능"""
        user2 = UserFactory()

        favorite1 = FavoriteFactory(user=self.user, book=self.book)
        favorite2 = FavoriteFactory(user=user2, book=self.book)

        self.assertEqual(Favorite.objects.filter(book=self.book).count(), 2)

    def test_favorite_cascade_delete_user(self):
        """유저 삭제 시 좋아요도 함께 삭제"""
        favorite = FavoriteFactory(user=self.user, book=self.book)
        favorite_id = favorite.id

        self.user.delete()

        self.assertFalse(Favorite.objects.filter(id=favorite_id).exists())

    def test_favorite_cascade_delete_book(self):
        """책 삭제 시 좋아요도 함께 삭제"""
        favorite = FavoriteFactory(user=self.user, book=self.book)
        favorite_id = favorite.id

        self.book.delete()

        self.assertFalse(Favorite.objects.filter(id=favorite_id).exists())
