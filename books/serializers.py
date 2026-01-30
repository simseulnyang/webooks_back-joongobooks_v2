from rest_framework import serializers

from books.models import Book, Favorite


class BookSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y년 %m월 %d일 %H:%M", read_only=True)
    updated_at = serializers.DateTimeField(format="%Y년 %m월 %d일 %H:%M", read_only=True)
    like_count = serializers.IntegerField(source="favorites.count", read_only=True)
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = [
            "id",
            "writer",
            "category",
            "sale_condition",
            "title",
            "author",
            "publisher",
            "condition",
            "original_price",
            "selling_price",
            "detail_info",
            "book_image",
            "created_at",
            "updated_at",
            "like_count",
            "is_liked",
        ]
        read_only_fields = ["writer"]

    def get_is_liked(self, obj):
        """현재 사용자가 좋아요 했는지 여부"""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.favorites.filter(user=request.user).exists()
        return False


class BookListSerializer(serializers.ModelSerializer):
    updated_at = serializers.DateTimeField(format="%Y년 %m월 %d일", read_only=True)
    like_count = serializers.IntegerField(source="favorites.count", read_only=True)

    class Meta:
        model = Book
        fields = [
            "id",
            "title",
            "author",
            "selling_price",
            "book_image",
            "sale_condition",
            "updated_at",
            "like_count",
        ]


class FavoriteSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source="book.title", read_only=True)
    author = serializers.CharField(source="book.author", read_only=True)
    selling_price = serializers.IntegerField(source="book.selling_price", read_only=True)
    book_image = serializers.ImageField(source="book.book_image", read_only=True)
    sale_condition = serializers.CharField(source="book.sale_condition", read_only=True)

    updated_at = serializers.DateTimeField(
        source="book.updated_at",
        format="%Y년 %m월 %d일",
        read_only=True,
    )
    like_count = serializers.IntegerField(source="book.favorites.count", read_only=True)

    class Meta:
        model = Favorite
        fields = [
            "id",
            "title",
            "author",
            "selling_price",
            "book_image",
            "sale_condition",
            "updated_at",
            "like_count",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["id"] = instance.book_id
        return data
