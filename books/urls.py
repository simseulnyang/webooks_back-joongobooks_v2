from django.urls import path
from books.views import BookListView, BookDetailView, BookCreateView, BookUpdateView, BookDeleteView, FavoriteToggleView, FavoriteListView

urlpatterns = [
    path(route="", view=BookListView.as_view(), name="book-list"),
    path(route="detail/<int:book_id>/", view=BookDetailView.as_view(), name="book-detail"),
    path(route="create/", view=BookCreateView.as_view(), name="book-create"),
    path(route="update/<int:book_id>/", view=BookUpdateView.as_view(), name="book-update"),
    path(route="delete/<int:book_id>/", view=BookDeleteView.as_view(), name="book-delete"),
    
    path(route='<int:book_id>/favorite/', view=FavoriteToggleView.as_view(), name='favorite-toggle'),
    path(route='favorites/', view=FavoriteListView.as_view(), name='favorite-list'),
]
