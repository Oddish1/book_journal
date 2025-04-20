"""
URL configuration for book_journal_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from .views import home, register, login_view, logout_view, books, journal, new_journal, library, new_review, generate_recommendations, book_reviews_aggregate, book_review, book_journal, about
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("", home, name="home"),
    path("register/", register, name="register"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("library/", library, name="library"),
    path('admin/', admin.site.urls),
    path('about/', about, name="about"),
    path("books/<int:book_id>/", books, name="books"),
    path("journal/", journal, name="journal"),
    path("journal/<int:journal_id>", book_journal, name="book_journal"),
    path("journal/new-journal", new_journal, name="new_journal"),
    path("journal/new-journal/<int:book_id>", new_journal, name="new_journal_with_book"),
    path("recommendations", generate_recommendations, name="generate_recommendations"),
    path("reviews/new-review/<int:book_id>", new_review, name="new_review"),
    path("reviews/book/<int:book_id>", book_reviews_aggregate, name="book_reviews_aggregate"),
    path("reviews/<int:review_id>", book_review, name="book_review"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
