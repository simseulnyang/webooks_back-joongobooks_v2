from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Book(models.Model):
    class Category(models.TextChoices):
        SOCIAL_POLITIC = "Social Politic", "사회 정치"
        LITERARY_FICTION = "Literary Fiction", "인문"
        CHILD = "Child", "아동"
        TRAVEL = "Travel", "여행"
        HISTORY = "History", "역사"
        ART = "Art", "예술"
        NOVEL = "Novel", "소설"
        POEM = "Poem", "시"
        SCIENCE = "Science", "과학"
        FANTASY = "Fantasy", "판타지"
        MAGAZINE = "Magazine", "잡지"

    class SALE_CONDITION_CHOICES(models.TextChoices):
        FOR_SALE = "For Sale", "판매 중"
        RESERVED = "Reserved", "예약 중"
        SOLD_OUT = "Sold Out", "판매 완료"

    writer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="books")
    category = models.CharField(
        max_length=50, choices=Category.choices, default=Category.NOVEL, verbose_name="카테고리"
    )
    sale_condition = models.CharField(
        max_length=20,
        choices=SALE_CONDITION_CHOICES.choices,
        default=SALE_CONDITION_CHOICES.FOR_SALE,
        verbose_name="판매 상태",
    )
    title = models.CharField(max_length=255, verbose_name="책 제목")
    author = models.CharField(max_length=255, verbose_name="책 저자")
    publisher = models.CharField(max_length=255, verbose_name="출판사")
    condition = models.CharField(max_length=100, verbose_name="책 상태")
    original_price = models.IntegerField(verbose_name="원가")
    selling_price = models.IntegerField(verbose_name="판매가")
    detail_info = models.TextField(verbose_name="상세 정보")
    book_image = models.ImageField(upload_to="book_images/", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"책 제목 : {self.title} / 책 저자 : {self.author} / 책 상태 : {self.condition} / 판매자: {self.writer} / 판매가격 {self.selling_price}"

    def like_count(self):
        """좋아요 개수 반환"""
        return self.favorites.count()

    def is_liked_by(self, user):
        """특정 사용자가 좋아요를 눌렀는지 여부 반환"""
        if user.is_authenticated:
            return self.favorites.filter(user=user).exists()
        return False


class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favorites", verbose_name="사용자")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="favorites", verbose_name="책")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "book")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user}님이 좋아하는 책: {self.book.title}"
