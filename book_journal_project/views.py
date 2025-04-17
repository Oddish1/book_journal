import requests
import threading
from urllib.parse import quote_plus
from django.shortcuts import render, redirect, HttpResponse
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from .forms import RegisterForm, BookSearchForm, NewJournalForm, ListDropDownForm, NewReviewForm
from django.conf import settings
from datetime import datetime
from library.models import Book, Genres, Authors, Covers, Journal, Tags, List, Reviews
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile, File
from django.core.exceptions import ValidationError
from django.template import loader
import logging
from django.db.models import Q, Case, When, IntegerField, Value, Sum

logger = logging.getLogger('book_journal')

API_KEY = settings.GOOGLE_BOOKS_API_KEY

# helper methods
def extract_isbn(volume_info):
    # extract isbn
    isbn_13 = None
    for identifier in volume_info.get('industryIdentifiers', []):
        if identifier['type'] == 'ISBN_13':
            isbn_13 = identifier['identifier']
            logger.debug(f'[ISBN]: Found isbn_13 {isbn_13}')
            break
    if not isbn_13:
        isbn_10 = None
        for identifier in volume_info.get('industryIdentifiers', []):
            if identifier['type'] == 'ISBN_10':
                isbn_10 = identifier['identifier']
                logger.debug(f'[ISBN]: Found isbn_10 {isbn_10}')
                break
        isbn_13 = isbn_10 # use isbn-10 if isbn-13 isn't found
    return isbn_13


def extract_genre(volume_info):
    try:
        genres = [g for g in volume_info['categories']]
        logger.info(f'[Extracting Genres]: Found genres {genres}')
    except Exception as e:
        logger.error(f'[Extracting Genres]: Error:\n{e}')
        genres = []
    return genres


def download_cover(url, book_title, isbn):
    try:
        img_response = requests.get(url, stream=True)
        if img_response.status_code == 200:
            logger.debug(f'[Image Download "{book_title}"]: Good URL response, attempting download.')
            cover = Covers(image_url=url)
            filename=f'{isbn}.png'
            cover.image.save(filename, ContentFile(img_response.content), save=True)
            cover_file = cover # set cover_image
            logger.info(f'[Image Download "{book_title}"]: Successfully saved to DB.')
            return cover_file
    except ValidationError as e:
        logger.error(f'[Image Download: "{book_title}"] Validation error: \n{e}')
    except Exception as e:
        logger.error(f'[Image Download: "{book_title}"] Image failed to download.')
        logger.debug(f'Image link: {cover_image_url}')
        logger.error(f'Error:\n{e}')


# Create your views here.

def home(request):
    form = BookSearchForm()
    stored_results = []
    results = []

    if request.method == "GET" and "query" in request.GET:
        form = BookSearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data["query"].strip()
            if query:
                # local db search and basic ranking
                results = Book.objects.filter(
                        Q(title__icontains=query) |
                        Q(authors__name__icontains=query) |
                        Q(isbn__iexact=query) |
                        Q(description__icontains=query)
                ).annotate(
                    relevance=Sum(Case(
                        When(title__icontains=query, then=Value(3)),
                        When(authors__name__icontains=query, then=Value(2)),
                        When(isbn__iexact=query, then=Value(5)),
                        When(description__icontains=query, then=Value(1)),
                        default=Value(0),
                        output_field=IntegerField()))).distinct().order_by("-relevance")
                # search API and create new Books to save to local db
                encoded_query = quote_plus(query)
                url = f'https://www.googleapis.com/books/v1/volumes?q={encoded_query}&maxResults=40&orderBy=relevance&printType=books&key={API_KEY}'
                response = requests.get(url)
                if response.status_code == 200:
                    data = response.json()
                    api_results = data.get("items", [])
                    # caches to prevent repeated db hits
                    genre_cache = {}
                    author_cache = {}
                    cover_cache = {}
                    new_books = []
                    book_author_links = [] # (book, authors) tuples for many to many relationsip
                    stored_results = []

                    for result in api_results:
                        volume_info = result['volumeInfo']
                        isbn = extract_isbn(volume_info)

                        try:
                            book_title = volume_info['title']
                        except:
                            book_title = "Unknown Title"

                        # genres
                        genre_names = extract_genre(volume_info)
                        for genre_name in genre_names:
                            genre = genre_cache.get(genre_name)
                            if not genre:
                                try:
                                    Genres.objects.filter(genre=genre_name).first()
                                except Genres.DoesNotExist:
                                    genre = Genres(genre=genre_name)
                                    genre_cache[genre_name] = genre # hold for later bulk_create

                        # authors
                        try:
                            authors_names = volume_info.get("authors") or ["Unkown Author"]
                            logger.debug(f'[Author Import]: found {authors_names}')
                            logger.debug(f'[Book Import "{book_title}"]: found authors ({authors_names})')
                            authors = []
                            for name in authors_names:
                                author = author_cache.get(name)
                                if not author:
                                    try:
                                        author = Authors.objects.get(name=name)
                                        logger.debug(f'[Author Import]: Author "{author}" exists in db')
                                    except Authors.DoesNotExist:
                                        logger.debug(f'[Author Import]: Author DNE, attempting to create.')
                                        author = Authors(name=name)
                                        author_cache[name] = author # hold for later bulk_create
                                authors.append(author)
                                logger.info(f'[Book Import "{book_title}"]: added authors {authors}')
                        except Exception as e:
                            logger.error(f'[Book Import: "{book_title}"] authors could not be added.')
                            logger.debug(f'volumeInfo:\n{volume_info}')
                            logger.debug(f'Error:\n{e}')

                        # set cover image
                        # ideally using PostgreSQL, would async image downloads, with sqlite this causes db locking errors.
                        # this is a current bottleneck, but don't have time to move to a different db right now.
                        try:
                            cover_image_url = volume_info['imageLinks']['thumbnail']
                            logger.debug(f'[Image Download "{book_title}"]: image URL ({cover_image_url})')
                            cover = cover_cache.get(cover_image_url) or Covers.objects.filter(image_url=cover_image_url).first()
                            if not cover:
                                cover = download_cover(cover_image_url, book_title, isbn)
                        except Exception as e:
                            logger.warning(f'[Book Import: "{book_title}"] thumbnail_cover could not be added. Setting to None.')
                            cover = None
                            logger.debug(f'volumeInfo:\n{volume_info}')
                            logger.error(f'Error:\n{e}')

                        # add title
                        try:
                            title = book_title
                            logger.debug(f'[Book Import "{book_title}"]: Added title {title}')
                        except Exception as e:
                            logger.warning(f'[Book Import: "{book_title}"] title could not be added. Setting to None.')
                            logger.debug(f'volumeInfo:\n{volume_info}')
                            logger.debug(f'Error:\n{e}')

                        # add page_count
                        try:
                            page_count = volume_info.get("pageCount")
                            logger.debug(f'[Book Import "{book_title}"]: Added page count {page_count}')
                        except Exception as e:
                            logger.warning(f'[Book Import: "{book_title}"] page_count could not be added. Setting to None.')
                            logger.debug(f'volumeInfo:\n{volume_info}')
                            logger.debug(f'Error:\n{e}')

                        # add publisher
                        try:
                            publisher = volume_info.get("publisher")
                            if isinstance(publisher, list):
                                try:
                                    publishers = [pub for pub in publisher]
                                    publisher = ", ".join(publishers)
                                except Exception as e:
                                    logger.error(f'[Adding Publishers: "{book_title}"] unable to join publishers into single string.')
                                    logger.debug(f'Error: {e}')
                            logger.debug(f'[Book Import "{book_title}"]: Added publisher "{publisher}"')
                        except Exception as e:
                            logger.warning(f'[Book Import: "{book_title}" publisher could not be added. Setting to None.')
                            logger.debug(f'volumeInfo:\n{volume_info}')
                            logger.debug(f'Error:\n{e}')
                            publisher = None

                        # add publisher date
                        try:
                            publisher_date = volume_info.get("publishedDate")
                            try:
                                date = datetime.strptime(publisher_date, "%Y-%m-%d")
                                date = datetime.strftime(date, "%Y-%m-%d")
                            except Exception as e:
                                logger.warning(f'[Date Conversion "{book_title}"]: date not in "Y-m-d" format. Trying different format.')
                                logger.debug(f'Error:\n{e}')
                                try:
                                    date = datetime.strptime(publisher_date, "%Y")
                                    date = datetime.strftime(date, "%Y-%m-%d")
                                    logger.info(f'[Date Conversion "{book_title}"]: date stored in "Y" format: {date}')
                                except Exception as e:
                                    logger.warning(f'[Date Conversion "{book_title}"]: date not in "Y" format. Trying different format.')
                                    logger.debug(f'Error:\n{e}')
                                    try:
                                        date = datetime.strptime(publisher_date, "%Y-%m")
                                        date = datetime.strftime(date, "%Y-%m-%d")
                                    except Exception as e:
                                        logger.warning(f'[Date Conversion "{book_title}"]: date not in "Y-M format. Attempting to set date from string value if possible.')
                                        try:
                                            if isinstance(publisher_date, str):
                                                date = publisher_date
                                        except Exception as e:
                                            logger.warning(f'[Date Conversion "{book_title}"] date not a string. Setting publisher_date to None.')
                                            logger.debug(f'Error:\n{e}')
                                            date = None
                        except Exception as e:
                            logger.error(f'[Book Import "{book_title}"] unable to set date.')
                            logger.debug(f'Error:\n{e}')

                        # add description
                        try:
                            description = volume_info.get("description")
                            logger.info(f'[Book Import "{book_title}"]: Added description')
                        except Exception as e:
                            logger.warning(f'[Book Import "{book_title}"] unable to set description. Setting to None.')
                            logger.debug(f'volumeInfo:\n{volume_info}')
                            logger.debug(f'Error:\n{e}')
                            description = None

                        # add print type
                        try:
                            print_type = volume_info.get("printType").lower()
                            logger.info(f'[Book Import "{book_title}"]: Added print type "{print_type}"')
                        except Exception as e:
                            logger.warning(f'[Book Import "{book_title}"] unable to set print_type. Setting to None.')
                            print_type = None
                            logger.debug(f'volumeInfo:\n{volume_info}')
                            logger.debug(f'Error:\n{e}')

                        # add language
                        try:
                            logger.debug("Trying to set language")
                            language = volume_info.get('language')
                            if isinstance(language, str):
                                logger.debug("language is str")
                            if isinstance(language, list):
                                logger.debug('language is list')
                                langauges = [lang for lang in language]
                                language = " ,".join(languages)
                            else:
                                logger.warning(f'[Book Import "{book_title}"] unable to set language. Setting to None.')
                                logger.debug(f'volumeInfo:\n{volume_info}')
                                language = None
                            logger.info(f'[Book Import "{book_title}"]: Added language "{language}"')
                        except Exception as e:
                            logger.error(f'[Book Import "{book_title}"] error while setting language.')
                            logger.debug(f'Error:\n{e}')

                        try:
                            new_book = Book(
                                main_genre = genre,
                                thumbnail_cover = cover,
                                title = title,
                                page_count = page_count,
                                publisher = publisher,
                                published_date = date,
                                description = description,
                                print_type = print_type,
                                language = language,
                                isbn = isbn)
                            new_books.append(new_book)
                            book_author_links.append((new_book, authors))
                        except ValidationError as e:
                            logger.error(f'Validation error for "{book_title}":\n{e}')
                        except Exception as e:
                            logger.error(f'Book import failed.')
                            logger.debug(f'volumeInfo:\n{volume_info}')
                            logger.error(f'Error:\n{e}')
                    # bulk save related models first
                    Genres.objects.bulk_create(genre_cache.values(), ignore_conflicts=True)
                    Authors.objects.bulk_create(author_cache.values(), ignore_conflicts=True)
                    # save books
                    Book.objects.bulk_create(new_books, ignore_conflicts=True)
                    # attatch many to many relationships
                    all_authors = set(a.name for _, authors in book_author_links for a in authors)
                    saved_authors = {a.name: a for a in Authors.objects.filter(name__in=all_authors)}
                    book_author_links = [(book, [saved_authors[a.name] for a in authors]) for book, authors in book_author_links]
                    for book, authors in book_author_links:
                        saved_book = Book.objects.filter(isbn=book.isbn).first()
                        if saved_book:
                            saved_book.authors.set(authors)
                            saved_book.save()
                            stored_results.append(saved_book)
                        else:
                            logger.warning(f'[Book Import]: Could not find saved_book for ISBN: {book.isbn}')

            else:
                # add extra search stuff here
                stored_results = results
    # Render the HTML template index.html
    if request.user.is_authenticated:
        currently_reading = Book.objects.filter(list=List.objects.get(user=request.user, name="Currently Reading"))
        context = {"form": form,
               "stored_results": stored_results,
               "page_title": "home",
               "currently_reading": currently_reading}
        return render(request, 'index.html', context)
        logger.debug(f'currently_reading({type(currently_reading)}): {currently_reading}')
    logger.debug(f'stored_results:\n{stored_results}')
    context = {"form": form,
               "stored_results": stored_results,
               "page_title": "home"}
    return render(request, 'index.html', context)

def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            # create default lists (currently reading, to be read)
            # TODO error handling on list creation
            currently_reading = List(user=user, name="Currently Reading", description="Currently reading")
            currently_reading.save()
            to_be_read = List(user=user, name="To Be Read", description="My TBR")
            to_be_read.save()
            finished = List(user=user, name="Finished", description="Finished reading")
            finished.save()
            # log user in and redirect home
            login(request, user)
            return redirect("home")
    else:
        form = RegisterForm()
        context = {"form": form,
                   "page_title": "register"}
    return render(request, "register.html", context)

def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("home")
        else:
            context = {"form": form,
                       "page_title": "login"}
    else:
        form = AuthenticationForm()
        context = {"form": form,
                   "page_title": "login"}
    return render(request, "login.html", context)

def logout_view(request):
    logout(request)
    return redirect("home")


def books(request, book_id):
    book = Book.objects.get(id=book_id)
    logger.debug(f'book: {book}')
    currently_reading = Book.objects.filter(list=List.objects.get(user=request.user, name="Currently Reading"))
    logger.debug(f'currently_reading: {currently_reading}')
    template = loader.get_template("books.html")
    if request.method == "POST":
        form = ListDropDownForm(request.POST, user=request.user)
        if form.is_valid():
            selected_lists = form.cleaned_data['lists']
            logger.debug(f'selected_lists: {selected_lists}')
            book.list.set(selected_lists)
            book.save()
            if selected_lists.filter(user=request.user, name="Finished").exists():
                book.list.remove(List.objects.get(user=request.user, name="Currently Reading"))
                book.save()
                return redirect('library')
            return redirect('books', book_id=book.id)
    else:
        form = ListDropDownForm(user=request.user, initial={
                                'lists': book.list.all()
        })
    context = {"book": book,
               "currently_reading": currently_reading,
               "page_title": book.title.lower(),
               "form": form}
    return HttpResponse(template.render(context, request))


# regular journal "home" page
def journal(request):
    if not request.user.is_authenticated:
        return redirect("home")
    else:
        # if finished books with no review, prompt user to review books
        journals = Journal.objects.filter(user=request.user).order_by("-created_at")
        template = loader.get_template("journal/index.html")
        context = {"journals": journals,
                   "page_title": "journal"}
        return HttpResponse(template.render(context, request))


def new_journal(request, book_id=None):
    logger.debug(f'Book ID: {book_id}')
    if book_id:
        book = Book.objects.get(id=book_id)
        logger.debug(f'[New Journal From book_id]: book is {book}')
    if request.method == "POST":
        logger.debug("[New Journal]: POST request")
        # TODO get currently reading book list to choose from in form
        new_journal_form = NewJournalForm(request.POST, user=request.user)
        if new_journal_form.is_valid():
            logger.debug("[New Journal]: Journal form is valid")
            # parse and create tags if dont exist
            tags = new_journal_form.cleaned_data["tags"]
            logger.debug(f'[New Journal]: Unprocessed Tags:\n{tags}')
            if tags:
                tag_objects = []
                tags = tags.strip()
                tags = tags.split(",")
                for tag in tags:
                    tag = tag.strip().lower()
                    if not Tags.objects.filter(tag=tag).exists():
                        logger.debug(f'[New Journal]: Tag "{tag}" not found, attempting to create new tag.')
                        t = Tags(tag=tag)
                        t.save()
                        logger.info(f'[Tag]: New tag "{t.tag}" saved.')
                        tag_objects.append(t)
                    else:
                        logger.debug(f'[New Journal]: Tag "{tag}" exists in DB, adding to to journal.')
                        t = Tags.objects.filter(tag=tag).first()
                        tag_objects.append(t)
                new_journal_form.cleaned_data["tags"] = tag_objects
                logger.debug(f'[New Journal]: Cleaned Data:\n{new_journal_form.cleaned_data}')
            if new_journal_form.is_valid():
                clean_data = new_journal_form.cleaned_data
                new_journal = Journal(
                        user = request.user,
                        book = clean_data['book'],
                        title = clean_data['title'],
                        page = clean_data['page'],
                        journal_text = clean_data['journal_text'],
                        is_public = clean_data['is_public'],
                        is_finished = clean_data['is_finished'],
                )
                new_journal.save()
                new_journal.tags.set(clean_data['tags'])
                new_journal.save()
                if new_journal.is_finished:
                    # remove from currently reading and add to finished list
                    new_journal.book.list.remove(List.objects.get(user=request.user, name="Currently Reading"))
                    new_journal.book.list.add(List.objects.get(user=request.user, name="Finished"))
                logger.info(f'[New Journal]: Saved successfully!')
                return redirect("journal")
    else:
        initial_data = {'book': book} if book else None
        new_journal_form = NewJournalForm(user=request.user, initial=initial_data)
        logger.debug(f'[New Journal From book_id]: initial book data is\n{new_journal_form.initial['book']}')
    template = loader.get_template("journal/new_journal.html")
    context = {"page_title": "new journal",
               "form": new_journal_form}
    return HttpResponse(template.render(context, request))


def library(request):
    if not request.user.is_authenticated:
        return redirect("home")
    else:
                # lists a dictionary of { "name": [BookObjects] }
        lists = {}
        user_lists = List.objects.filter(user=request.user)
        for lst in user_lists:
            books = Book.objects.filter(list=lst)
            lists[lst.name] = books
        logger.debug(f'lists with books: {lists}')
        # currently_reading a list of Book objects
        currently_reading = lists['Currently Reading']
        logger.debug(f'currently_reading: {currently_reading}')
        # latest_journals a list of 5 most recent Journal Objects
        latest_journals = Journal.objects.filter(user=request.user).order_by("-created_at")[:5]
        logger.debug(f'latest_journals: {latest_journals}')
        user = request.user
        logger.debug(f'user: {user.username}')
        # all of a user's reviewed books
        reviews = Reviews.objects.filter(user=request.user)
        logger.debug(f'reviews: {reviews}')
        # books the user hasn't reviewed yet
        reviewed_book_ids = reviews.values_list('book_id', flat=True)
        need_reviews = lists['Finished'].exclude(id__in=reviewed_book_ids)

        logger.debug(f'need_reviews: {need_reviews}')
        template = loader.get_template("library.html")
        context = {"page_title": "library",
                   "currently_reading": currently_reading,
                   "lists": lists,
                   "reviews": reviews,
                   "need_reviews": need_reviews,
                   "latest_journals": latest_journals,
                   "user": user,
        }
        return HttpResponse(template.render(context, request))


def new_review(request, book_id=None):
    if not request.user.is_authenticated:
        return redirect("home")
    else:
        if book_id:
            book = Book.objects.get(id=book_id)
        if request.method == "POST":
            form = NewReviewForm(request.POST, user=request.user)
            if form.is_valid():
                clean_data = form.cleaned_data
                new_review = Reviews(
                    book = book,
                    user = request.user,
                    rating = clean_data['rating'],
                    title = clean_data['title'],
                    review = clean_data['review']
                )
                new_review.save()
                return redirect("library")
        else:
            initial_data = {'book': book} if book else None
            form = NewReviewForm(user=request.user, initial=initial_data)
        template = loader.get_template('new_review.html')
        context = {
            "page_title": "new review",
            "form": form
        }
        return HttpResponse(template.render(context, request))
