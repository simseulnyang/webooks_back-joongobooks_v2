from rest_framework import serializers
from books.models import Book


class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = [
            'id',
            'writer',
            'category',
            'sale_condition',
            'title',
            'author',
            'publisher',
            'condition',
            'original_price',
            'selling_price',
            'detail_info',
            'book_image',
            'created_at',
            'updated_at',
        ]
        
        
class BookListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = [
            'id',
            'title',
            'author',
            'original_price',
            'selling_price',
            'book_image',
            'sale_condition',
            'updated_at',
        ]