from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return f'user_{instance.id}/{filename}'

# data model for the user
class User(AbstractUser):
    # a user-uploaded profile picture; optional
    profile_picture = models.ImageField(upload_to=user_directory_path,
                                        null=True)
    # a user-defined bio; optional
    bio = models.TextField(max_length=5000, null=True)
    # a date-time object representing the last time the account password was
    # reset
    last_password_reset = models.DateTimeField(auto_now_add=True)
    # the type of account; defaults to standard user
    account_type = models.CharField(max_length=2,
                                    choices=[("ad", "Administrator"), ("us", "Standard User")],
                                    default="us")

    def __str__(self):
        return self.username

# data model for book lists (currently reading, read, etc.)
class List(models.Model):
    # a forein key linking to the User.id (auto-generated primary key by Django)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    # a disply name for the list
    name =models.CharField(max_length=200, default='My List')
    # a boolean representing if the list visible to the public or not (default
    # false)
    is_public = models.BooleanField(default=False)
    # a text field representing a list description
    description = models.TextField(max_length=2000, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Covers(models.Model):
    # represents the cover image
    image = models.ImageField(upload_to='book_covers/', null=True)
    # represents the url of original image (used to verify if in db or not)
    image_url = models.URLField(null=True)


class Genres(models.Model):
    # represents the genre (sci-fi, history, historical fiction)
    genre = models.CharField(max_length=200)


class Authors(models.Model):
    # represents the author's name
    name = models.CharField(max_length=200)
    # datetime.date object representing the date the author was born
    birth_date = models.DateField()
    # datetime.date object representing the date the author died
    death_date = models.DateField(null=True)
    # text field representing the author's biography
    biography = models.TextField(max_length=2000, null=True)


class Book(models.Model):
    # foreign key linking to Genres.id representing the main genre of the book
    main_genre = models.ForeignKey(Genres, on_delete=models.CASCADE, null=True)
    genres = models.ManyToManyField(Genres, related_name="books")
    # foreign key linking to Covers.id representing the thumbnail cover
    thumbnail_cover = models.ForeignKey(Covers, on_delete=models.CASCADE, default=None)
    covers = models.ManyToManyField(Covers, related_name="covers", default=None)
    # foreign key linking to Authors.id representing the main author
    main_author = models.ForeignKey(Authors, on_delete=models.CASCADE, null=True)
    authors = models.ManyToManyField(Authors, related_name="authors", default=None)
    # foreign key linking to List.id representing the list the book is in
    list = models.ForeignKey(List, on_delete=models.CASCADE, null=True)
    # represents the book title, max length of 500 characters
    title = models.CharField(max_length=500)
    # represents the book subtitle, max length of 500 characters
    subtitle = models.CharField(max_length=500, null=True)
    # integer representing the number of pages in the book
    page_count = models.IntegerField(null=True)
    # float representing the average rating given by users
    average_rating = models.FloatField(null=True)
    # integer representing the number of ratings given by users
    ratings_count = models.IntegerField(default=0)
    # represents the book publisher
    publisher = models.CharField(max_length=500, null=True)
    # represents the date published
    published_date = models.DateField(null=True)
    # represents a summary/description of the book
    description = models.TextField(max_length=1000, null=True)
    # represents the print type of the book (Hardcover, EBook, Mass Market Paperback)
    print_type = models.CharField(max_length=200, null=True)
    # represents the language the book is published in
    language = models.CharField(max_length=200, null=True)
    # represents the isbn of the book
    isbn = models.CharField(max_length=50, null=True)


# data model for a user created journal entry
class Journal(models.Model):
    # a foreign key linking the User.id
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    # a foreign key linking the Book.id
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    # a title for the journal entry
    title = models.CharField(max_length=200, null=True)
    # a page number representing the page they are on
    page = models.IntegerField()
    # text space for the user to make a journal entry
    journal_text = models.TextField(max_length=10000, null=True)
    # a datetime object representing when the journal entry was created
    created_at = models.DateTimeField(auto_now_add=True)
    # a datetime object representing when the journal entry was last edited
    edited_at = models.DateTimeField(auto_now=True)
    # a boolean representing if the journal entry is visible to the public or
    # not
    is_public = models.BooleanField(default=False)
    # a boolean representing if the journal entry able to be viewed by the
    # public or not, for moderation purposes
    is_approved = models.BooleanField(default=False)
    tags = models.ManyToManyField("Tags", related_name="journals")


class UserFollow(models.Model):
    # foreign key linking to User.id representing the user following
    follower = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="followers")
    # foreign key linking to User.id representing the user that has been
    # followed
    followed = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="following")
    # auto-generated datetime object for when the follow event occurs
    created_at = models.DateTimeField(auto_now_add=True)


class UserRecommendations(models.Model):
    # foreign key linking to User.id representing the user the recommendation is
    # for
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    # foreign key linking to Book.id representing the book being recommended
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    # auto-generated datetime object for when the recommendation is being made
    created_at = models.DateTimeField(auto_now_add=True)



class Tags(models.Model):
    # represents the tag text
    tag = models.CharField(max_length=200)



class Reviews(models.Model):
    # foreign key linking to Book.id
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    # foreign key linking to User.id
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    # represents a float rating given by the user
    rating = models.FloatField(null=True,
                               validators=[MinValueValidator(0), MaxValueValidator(5)])
    # represents a title for the review
    title = models.CharField(max_length=200, null=True)
    # represents the text of the review
    review = models.TextField(max_length=5000, null=True)
    # a datetime object representing the timestamp the review was created at
    created_at = models.DateTimeField(auto_now_add=True)
    # a datetime object representing the timestamp the review was last edited
    updated_at = models.DateTimeField(auto_now=True)
    # a boolean representing if the review is approved (used for moderation)
    is_approved = models.BooleanField(default=False)
    tags = models.ManyToManyField("Tags", related_name="reviews")


class BooksOwned(models.Model):
    # foreign key linking to User.id
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    # foreign key linking to Book.id
    book = models.ForeignKey(Book, on_delete=models.CASCADE)

