from django.contrib import admin
from books.models import Book, Favorite

admin.site.register(Book)
admin.site.register(Favorite)
