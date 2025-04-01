from django.db import models

def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return "user_{0}/{1}".format(instance.user.id, filename)

# data model for the user
class User(models.Model):
    # a user-defined email
    email = models.EmailField()
    # a user-defined username
    username = models.CharField(max_length=200)
    # the hashed version of a user-defined password
    password_hashed = models.CharField(max_length=200)
    # date-time object representing the time the account was created
    created_at = models.DateTimeField(auto_now=True)
    # a date-time object representing the last time the account password was
    # reset
    last_password_reset = models.DateTimeField(auto_now=True)
    # the user's first name; optional
    first_name = models.CharField(max_length=200, blank=True)
    # the user's last name; optional
    last_name = models.CharField(max_length=200, blank=True)
    # a user-uploaded profile picture; optional
    profile_picture = models.ImageField(upload_to=user_directory_path,
                                        blank=True)
    # a user-defined bio; optional
    bio = models.TextField(max_length=5000, blank=True)
    # define preference choices
    #
    # the user's preferences
    preferences = 
    # a boolean to depict wether the user is currently active or not
    is_active = models.BooleanField()
    # a date-time object representing the last time the user logged in
    last_login = models.DateTimeField(auto_now=True)
    # define account type choices
    ADMIN = "ad"
    STANDARD_USER = "us"
    ACCOUNT_TYPE_CHOICES = {
            ADMIN: "Administrator",
            STANDARD_USER: "Standard User",
            }
    # the type of account; defaults to standard user
    account_type = models.CharField(max_length=2, choices=ACCOUNT_TYPE_CHOICES,
                                    default=STANDARD_USER)

# data model for book lists (currently reading, read, etc.)
class List(models.Model):
    # a forein key linking to the User.id (auto-generated primary key by Django)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    # a disply name for the list
    list_name =models.CharField(max_length=200)
    # a boolean representing if the list visible to the public or not (default
    # false)
    is_public = models.BooleanField(default=False)


# data model for a user created journal entry
class Journal(models.Model):
    # a foreign key linking the User.id
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    # a foreign key linking the Book.id
    book_id = models.ForeignKey(Book, on_delete=models.CASCADE)
    # a title for the journal entry
    title = models.CharField(max_length=200, blank=True)
    # a page number representing the page they are on
    page = models.IntegerField()
    # text space for the user to make a journal entry
    journal_text = models.TextField(max_length=10000, blank=True)
    # a datetime object representing when the journal entry was created
    created_at = models.DateTimeField(auto_now=True)
    # a datetime object representing when the journal entry was last edited
    edited_at = models.DateTimeField(auto_now=True)
    # a boolean representing if the journal entry is visible to the public or
    # not
    is_public = models.BooleanField(default=False)
    # a boolean representing if the journal entry able to be viewed by the
    # public or not, for moderation purposes
    is_approved = models.BooleanField(default=False)


class JournalTags(models.Model):



class UserFollow(models.Model):



class UserRecommendations(models.Model):



class Book(models.Model):



class ReviewTags(models.Model):



class Tags(models.Model):



class Covers(models.Model):



class BookCovers(models.Model):



class Genres(models.Model):



class BookGeneres(models.Model):



class Authors(models.Model):



class BookAuthors(models.Model):



class Reviews(models.Model):

