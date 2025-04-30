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
from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("library/", views.library, name="library"),
    path('admin/', admin.site.urls),
    path('about/', views.about, name="about"),
    path("books/<int:book_id>/", views.books, name="books"),
    path("journal/", views.journal, name="journal"),
    path("journal/<int:journal_id>", views.book_journal, name="book_journal"),
    path("journal/new-journal", views.new_journal, name="new_journal"),
    path("journal/new-journal/<int:book_id>", views.new_journal, name="new_journal_with_book"),
    path("recommendations", views.generate_recommendations, name="generate_recommendations"),
    path("reviews/new-review/<int:book_id>", views.new_review, name="new_review"),
    path("reviews/book/<int:book_id>", views.book_reviews_aggregate, name="book_reviews_aggregate"),
    path("reviews/<int:review_id>", views.book_review, name="book_review"),
    path('verify/<uidb64>/<token>/', views.verify_email, name='verify_email'),
    path('register/verify', views.register_landing_page, name='register_landing_page'),
    path('password-reset', views.password_reset, name='password_reset'),
    path('password-reset/success', views.password_reset_success, name='password_reset_success'),
    path('password-reset/fail', views.password_reset_fail, name='password_reset_fail'),
    path('password-reset/<uidb64>/<token>/', views.password_reset_confirm, name='password_reset_confirm'),
    path('password-reset/complete', views.password_reset_complete, name='password_reset_complete'),
    path('profile/edit-profile', views.edit_profile, name='edit_profile'),
    path('profile/@', views.profile, name='profile'),
    path('profile/@<username>/', views.public_profile, name='public_profile'),
    path('profile/@<username>/not-public', views.profile_not_public, name='profile_not_public'),
    path('profile/@<username>/does-not-exist', views.profile_dne, name='profile_dne'),
    path('profile/@<username>/follow-user', views.user_follow, name='user_follow'),
    path('journals/book/<int:book_id>/', views.book_journals_aggregate, name='book_journals_aggregate'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
