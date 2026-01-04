from django.urls import path
from books.views import BookListView, BookDetailView, BookCreateView, BookUpdateView, BookDeleteView

urlpatterns = [
    path(route="", view=BookListView.as_view(), name="book-list"),
    path(route="detail/<int:pk>/", view=BookDetailView.as_view(), name="book-detail"),
    path(route="create/", view=BookCreateView.as_view(), name="book-create"),
    path(route="update/<int:pk>/", view=BookUpdateView.as_view(), name="book-update"),
    path(route="delete/<int:pk>/", view=BookDeleteView.as_view(), name="book-delete"),
]
