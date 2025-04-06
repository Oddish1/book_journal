from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, List, Covers, Genres, Authors, Book, Journal, UserFollow, UserRecommendations, Tags, Reviews, BooksOwned

# Register your models here.

admin.site.register(User, UserAdmin)
admin.site.register(List)
admin.site.register(Covers)
admin.site.register(Genres)
admin.site.register(Authors)
admin.site.register(Book)
admin.site.register(Journal)
admin.site.register(UserFollow)
admin.site.register(UserRecommendations)
admin.site.register(Tags)
admin.site.register(Reviews)
admin.site.register(BooksOwned)

