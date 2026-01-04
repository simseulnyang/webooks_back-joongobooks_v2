from django.shortcuts import render
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.request import Request

from books.serializers import BookSerializer, BookListSerializer
from books.models import Book
from books.pagination import BookPagination
from books.permissions import IsOwnerOrReadOnly, IsOwner
from drf_spectacular.utils import extend_schema


class BookListView(APIView):
    permission_classes = [AllowAny]
    @extend_schema(
        tags=['Books_list'],
        summary='중고 책 전체 리스트',
        description='중고 책 전체 리스트를 반환합니다.',
        request=BookListSerializer,
        responses={
            200: BookListSerializer(many=True),
            400: None,
        },
    )
    def get(self, request: Request) -> Response:
        books = Book.objects.all().order_by('-created_at')
        
        paginator = BookPagination()
        paginated_books = paginator.paginate_queryset(books, request)
        serializer = BookListSerializer(paginated_books, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    
class BookDetailView(APIView):
    permission_classes = [IsOwnerOrReadOnly]
    @extend_schema(
        tags=['Books_detail'],
        summary='중고 책 상세 정보',
        description='중고 책의 상세 정보를 반환합니다.',
        responses={
            200: BookSerializer,
            404: None,
        },
    )
    def get(self, request: Request, book_id: int) -> Response:
        try:
            book = Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            return Response({'detail': 'Book not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        self.check_object_permissions(request, book)
        
        serializer = BookSerializer(book)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    
class BookCreateView(APIView):
    permission_classes = [IsAuthenticated]
    @extend_schema(
        tags=['Books_create'],
        summary='중고 책 등록',
        description='중고 책을 새로 등록합니다.',
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
        tags=['Books_update'],
        summary='중고 책 수정',
        description='중고 책의 정보를 수정합니다.',
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
            return Response({'detail': 'Book not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        self.check_object_permissions(request, book)
        
        serializer = BookSerializer(book, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
class BookDeleteView(APIView):
    permission_classes = [IsAuthenticated, IsOwner]
    @extend_schema(
        tags=['Books_delete'],
        summary='중고 책 삭제',
        description='중고 책을 삭제합니다.',
        responses={
            204: None,
            404: None,
        },
    )
    def delete(self, request: Request, book_id: int) -> Response:
        try:
            book = Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            return Response({'detail': 'Book not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        self.check_object_permissions(request, book)
        
        book.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)