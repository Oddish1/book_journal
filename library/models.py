from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.files.storage import default_storage


def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_profile_pictures/user_<user.id>/avatar
    return f'user_profile_pictures/user_{instance.id}/avatar'


def optimize_image(image, max_width=1200, quality=85):
    """
    crop, resize, and compress the image to make it web-optimized.

    parameters:
    - image: the image file to process
    - max_width: the maximum width for the image, teh height is adjusted to maintain the aspect ratio
    - quality: the quality level for compression (1-100), where 100 is the best quality.

    returns:
    - an InMemoryUploadedFile containing the optimized image
    """
    img = Image.open(image)
    img = img.convert("RGB")
    img = img.crop(img.getbbox())
    img_width, img_height = img.size

    if img_width > max_width:
        aspect_ratio = img_height / float(img_width)
        new_width = max_width
        new_height = int(new_width * aspect_ratio)
        img = img.resize((new_width, new_height), Image.ANTIALIAS)

    img_io = BytesIO()
    img.save(img_io, format='JPEG', quality=quality, optimize=True)
    img_io.seek(0)

    image_file = InMemoryUploadedFile(img_io, None, image.name, 'image/jpeg', img_io.tell(), None)
    return image_file


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
    is_public = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        try:
            old = User.objects.get(pk=self.pk)
        except User.DoesNotExist:
            old = None

        if old and old.profile_picture and old.profile_picture != self.profile_picture:
            if default_storage.exists(old.profile_picture.path):
                default_storage.delete(old.profile_picture.path)

        if self.profile_picture:
            self.profile_picture = optimize_image(self.profile_picture)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.username


# data model for book lists (currently reading, read, etc.)
class List(models.Model):
    # a forein key linking to the User.id (auto-generated primary key by Django)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    # a disply name for the list
    name = models.CharField(max_length=200, default='My List')
    # a boolean representing if the list visible to the public or not (default
    # false)
    is_public = models.BooleanField(default=False)
    # a text field representing a list description
    description = models.TextField(max_length=2000, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Covers(models.Model):
    # represents the cover image
    image = models.ImageField(upload_to='book_covers/', null=True)
    # represents the url of original image (used to verify if in db or not)
    image_url = models.URLField(null=True)


class Genres(models.Model):
    # represents the genre (sci-fi, history, historical fiction)
    genre = models.CharField(max_length=200)

    def __str__(self):
        return self.genre


class Authors(models.Model):
    # represents the author's name
    name = models.CharField(max_length=200)
    # datetime.date object representing the date the author was born
    birth_date = models.DateField(null=True, blank=True)
    # datetime.date object representing the date the author died
    death_date = models.DateField(null=True, blank=True)
    # text field representing the author's biography
    biography = models.TextField(max_length=2000, null=True, blank=True)

    def __str__(self):
        return self.name


class Book(models.Model):
    # foreign key linking to Genres.id representing the main genre of the book
    main_genre = models.ForeignKey(Genres, on_delete=models.CASCADE, null=True, blank=True)
    genres = models.ManyToManyField(Genres, related_name="genres")
    # foreign key linking to Covers.id representing the thumbnail cover
    thumbnail_cover = models.ForeignKey(Covers, on_delete=models.CASCADE, default=None, null=True, blank=True)
    cover_image_url = models.URLField(null=True)
    covers = models.ManyToManyField(Covers, related_name="covers", default=None)
    authors = models.ManyToManyField(Authors, related_name="authors", default=None)
    # foreign key linking to List.id representing the list the book is in
    list = models.ManyToManyField(List, related_name="list", default=None)
    # represents the book title, max length of 500 characters
    title = models.CharField(max_length=500)
    # integer representing the number of pages in the book
    page_count = models.IntegerField(null=True, blank=True)
    # float representing the average rating given by users
    average_rating = models.FloatField(null=True, blank=True)
    # integer representing the number of ratings given by users
    ratings_count = models.IntegerField(default=0)
    # represents the book publisher
    publisher = models.CharField(max_length=500, null=True, blank=True)
    # represents the date published
    published_date = models.DateField(null=True, blank=True)
    # represents a summary/description of the book
    description = models.TextField(max_length=1000, null=True, blank=True)
    # represents the print type of the book (Hardcover, EBook, Mass Market Paperback)
    print_type = models.CharField(max_length=200, null=True, blank=True)
    # represents the language the book is published in
    language = models.CharField(max_length=200, null=True, blank=True)
    # represents the isbn of the book
    isbn = models.CharField(max_length=50, null=True)

    def __str__(self):
        return self.title


# data model for a user created journal entry
class Journal(models.Model):
    # a foreign key linking the User.id
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    # a foreign key linking the Book.id
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    # a title for the journal entry
    title = models.CharField(max_length=200, null=True, blank=True)
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
    # a boolean representing if the user finished the book
    is_finished = models.BooleanField(default=False)
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
    # score from the recommendation model
    score = models.FloatField(null=True)
    # auto-generated datetime object for when the recommendation is being made
    created_at = models.DateTimeField(auto_now_add=True)


class Tags(models.Model):
    # represents the tag text
    tag = models.CharField(max_length=200)

    def __str__(self):
        return self.tag


class Reviews(models.Model):
    # foreign key linking to Book.id
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    # foreign key linking to User.id
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    # represents a float rating given by the user
    rating = models.FloatField(null=True,
                               validators=[MinValueValidator(0), MaxValueValidator(5)])
    # represents a title for the review
    title = models.CharField(max_length=200, null=True, blank=True)
    # represents the text of the review
    review = models.TextField(max_length=5000, null=True, blank=True)
    # a datetime object representing the timestamp the review was created at
    created_at = models.DateTimeField(auto_now_add=True)
    # a datetime object representing the timestamp the review was last edited
    updated_at = models.DateTimeField(auto_now=True)
    # a boolean representing if the review is approved (used for moderation)
    is_approved = models.BooleanField(default=True)
    tags = models.ManyToManyField("Tags", related_name="reviews", blank=True)


class BooksOwned(models.Model):
    # foreign key linking to User.id
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    # foreign key linking to Book.id
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
