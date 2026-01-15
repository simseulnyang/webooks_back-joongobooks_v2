from django.db import models
from django.shortcuts import render

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from books.models import Book, Favorite
from books.pagination import BookPagination
from books.permissions import IsOwner, IsOwnerOrReadOnly
from books.serializers import BookListSerializer, BookSerializer, FavoriteSerializer


class BookListView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Books_list"],
        summary="중고 책 전체 리스트",
        description="""
        중고 책의 전체 리스트를 반환합니다.
        다양한 필터링 옵션(카테고리, 판매 상태, 가격 범위)과 검색 기능(제목, 저자, 출판사)을 제공합니다.
        - search: 제목, 저자, 출판사 검색
        - category: 카테고리 필터
        - sale_condition: 판매 상태 필터
        - min_price, max_price: 가격 범위 필터
        """,
        request=BookListSerializer,
        responses={
            200: BookListSerializer(many=True),
            400: None,
        },
    )
    def get(self, request: Request) -> Response:
        books = Book.objects.all()

        # 검색 기능
        search = request.query_params.get("search")
        if search:
            books = books.filter(
                models.Q(title__icontains=search)
                | models.Q(author__icontains=search)
                | models.Q(publisher__icontains=search)
            )

        # 1. 카테고리 필터
        category = request.query_params.get("category")
        if category:
            books = books.filter(category=category)

        # 2. 판매 상태 필터
        sale_condition = request.query_params.get("sale_condition")
        if sale_condition:
            books = books.filter(sale_condition=sale_condition)

        # 3. 가격 범위 필터
        min_price = request.query_params.get("min_price")
        if min_price:
            books = books.filter(selling_price__gte=min_price)

        max_price = request.query_params.get("max_price")
        if max_price:
            books = books.filter(selling_price__lte=max_price)

        ordering = request.query_params.get("ordering", "-created_at")
        books = books.order_by(ordering)

        paginator = BookPagination()
        paginated_books = paginator.paginate_queryset(books, request)
        serializer = BookListSerializer(paginated_books, many=True)
        return paginator.get_paginated_response(serializer.data)


class BookDetailView(APIView):
    permission_classes = [IsOwnerOrReadOnly]

    @extend_schema(
        tags=["Books_detail"],
        summary="중고 책 상세 정보",
        description="중고 책의 상세 정보를 반환합니다.",
        responses={
            200: BookSerializer,
            404: None,
        },
    )
    def get(self, request: Request, book_id: int) -> Response:
        try:
            book = Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            return Response({"message": "Book not found."}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, book)

        serializer = BookSerializer(book)
        return Response(serializer.data, status=status.HTTP_200_OK)


class BookCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Books_create"],
        summary="중고 책 등록",
        description="중고 책을 새로 등록합니다.",
        request=BookSerializer,
        responses={
            201: BookSerializer,
            400: None,
        },
    )
    def post(self, request: Request) -> Response:
        serializer = BookSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(writer=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BookUpdateView(APIView):
    permission_classes = [IsOwnerOrReadOnly]

    @extend_schema(
        tags=["Books_update"],
        summary="중고 책 수정",
        description="중고 책의 정보를 수정합니다.",
        request=BookSerializer,
        responses={
            200: BookSerializer,
            400: None,
            404: None,
        },
    )
    def patch(self, request: Request, book_id: int) -> Response:
        try:
            book = Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            return Response({"message": "Book not found."}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, book)

        serializer = BookSerializer(book, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BookDeleteView(APIView):
    permission_classes = [IsAuthenticated, IsOwner]

    @extend_schema(
        tags=["Books_delete"],
        summary="중고 책 삭제",
        description="중고 책을 삭제합니다.",
        responses={
            204: None,
            404: None,
        },
    )
    def delete(self, request: Request, book_id: int) -> Response:
        try:
            book = Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            return Response({"message": "Book not found."}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, book)

        book.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FavoriteToggleView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Favorite_toggle"],
        summary="좋아요 토글",
        description="좋아요를 추가하거나 제거합니다.",
        responses={
            200: {"message": '"좋아요"를 취소했습니다.'},
            201: {"message": '"좋아요"를 클릭했습니다.'},
            404: {"message": "책을 찾을 수 없습니다."},
        },
    )
    def post(self, request: Request, book_id: int) -> Response:
        try:
            book = Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            return Response({"message": "책을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        favorite = Favorite.objects.filter(user=request.user, book=book).first()

        if favorite:
            favorite.delete()
            return Response(
                {
                    "message": '"좋아요"를 취소했습니다.',
                    "is_liked": False,
                    "like_count": book.favorites.count(),
                },
                status=status.HTTP_200_OK,
            )
        else:
            Favorite.objects.create(user=request.user, book=book)
            return Response(
                {
                    "message": '"좋아요"를 클릭했습니다.',
                    "is_liked": True,
                    "like_count": book.favorites.count(),
                },
                status=status.HTTP_201_CREATED,
            )


class FavoriteListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Favorite_list"],
        summary="내가 좋아요한 책 목록",
        description="현재 로그인한 사용자가 좋아요한 책 목록을 반환합니다.",
        responses={
            200: FavoriteSerializer(many=True),
        },
    )
    def get(self, request: Request) -> Response:
        favorite = Favorite.objects.filter(user=request.user).prefetch_related("book")

        pagination = BookPagination()
        paginated_favorites = pagination.paginate_queryset(favorite, request)

        serializer = FavoriteSerializer(paginated_favorites, many=True)
        return pagination.get_paginated_response(serializer.data)
