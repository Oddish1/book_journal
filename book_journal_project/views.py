import requests
from urllib.parse import quote_plus
from django.shortcuts import render, redirect, HttpResponse
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from .forms import RegisterForm, BookSearchForm, NewJournalForm, ListDropDownForm
from django.conf import settings
from datetime import datetime
from library.models import Book, Genres, Authors, Covers, Journal, Tags, List
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile, File
from django.core.exceptions import ValidationError
from django.template import loader
import logging

logger = logging.getLogger('book_journal')

API_KEY = settings.GOOGLE_BOOKS_API_KEY


# Create your views here.

def home(request):
    form = BookSearchForm()
    stored_results = []
    results = []

    if request.method == "GET" and "query" in request.GET:
        form = BookSearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data["query"]
            # add database search first then search google API and add results to db
            results = list(Book.objects.filter(title__icontains=query))
            if not results:
                encoded_query = quote_plus(query)
                url = f'https://www.googleapis.com/books/v1/volumes?q={encoded_query}&orderBy=relevance&printType=books&key={API_KEY}'
                response = requests.get(url)
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("items", [])
                    for i in range(0, len(results)):
                        volume_info = results[i]['volumeInfo']

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

                        # check if in db already
                        existing_book = Book.objects.filter(isbn=isbn_13).first()

                                                    # create & save the book in the db
                        try:
                            book_title = volume_info['title']
                        except:
                            book_title = "Unknown Title"

                        if not existing_book:
                            logger.info(f'[Book Import "{book_title}"]: No existing book found, attempting to import.')

                            # set genres
                            try:
                                genres = [g for g in volume_info['categories']]
                                if isinstance(genres, list):
                                    for g in genres:
                                        if isinstance(g, str):
                                            # check for genre in db if exists, set
                                            if not Genres.objects.filter(genre=g).exists():
                                                # create and set genre
                                                g = Genres(genre=g)
                                                try:
                                                    logger.debug(f'[Database]: attempting to save genre: "{g.genre}"')
                                                    g.full_clean() # check for validation errors
                                                    g.save() # save genre to db
                                                    logger.info(f'[Database]: genre save success: "{g.genre}"')
                                                    main_genre = g # set genre
                                                    logger.debug(f'[Book Import "{book_title}"]: Genre set to "{main_genre.genre}"')
                                                except Exception as e:
                                                    logger.error(f'[Database]: save failed, genre: "{g.genre}" -- Error\n{e}')
                                                except ValidationError as e:
                                                    logger.error(f'[Database]: save failed, validation error:\n{e}')
                                            else:
                                                # if genre in db, set genre
                                                main_genre = Genres.objects.get(genre=g)
                                                logger.info(f'[Book Import "{book_title}"]: Genre in DB, setting genre to "{main_genre.genre}"')
                                        else:
                                            logger.error(f'[Book Import "{book_title}"]: Genre {g} is not type str, but type {type(g)}')
                            except Exception as e:
                                logger.warning(f'[Book Import: "{book_title}"] genres could not be added. Setting to None.')
                                logger.debug(f'volumeInfo:\n{volume_info}')
                                logger.debug(f'Error:\n{e}')
                                genre_objects = None

                            # set cover image
                            try:
                                cover_image_url = volume_info['imageLinks']['thumbnail']
                                logger.debug(f'[Image Download "{book_title}"]: image URL ({cover_image_url})')
                                # check if in db already
                                if not Covers.objects.filter(image_url=cover_image_url).exists():
                                    # download and create Cover then set cover_image
                                    logger.debug(f'[Book Import: "{book_title}"]: Cover not in DB, attempting to download.')
                                    try:
                                        img_response = requests.get(cover_image_url, stream=True)
                                        if img_response.status_code == 200:
                                            logger.debug(f'[Image Download "{book_title}"]: Good URL response, attempting download.')
                                            cover = Covers(image_url=cover_image_url)
                                            filename=f'{isbn_13}.png'
                                            cover.image.save(filename, ContentFile(img_response.content), save=True)
                                            cover_file = cover # set cover_image
                                            logger.info(f'[Image Download "{book_title}"]: Successfully saved to DB.')
                                    except ValidationError as e:
                                        logger.error(f'[Image Download: "{book_title}"] Validation error: \n{e}')
                                    except Exception as e:
                                        logger.error(f'[Image Download: "{book_title}"] Image failed to download.')
                                        logger.debug(f'Image link: {cover_image_url}')
                                        logger.error(f'Error:\n{e}')
                                else:
                                    logger.info(f'[Book Import "{book_title}"]: Cover in DB, setting image.')
                                    cover_file = Covers.objects.get(image_url=cover_image_url)
                            except Exception as e:
                                logger.warning(f'[Book Import: "{book_title}"] thumbnail_cover could not be added. Setting to None.')
                                logger.debug(f'volumeInfo:\n{volume_info}')
                                logger.error(f'Error:\n{e}')

                            # add authors
                            try:
                                authors_list = volume_info['authors']
                                logger.debug(f'[Book Import "{book_title}"]: found authors ({authors_list})')
                                authors = []
                                for author in authors_list:
                                    # check if exists in db
                                    if not Authors.objects.filter(name=author).exists():
                                        # create author
                                        logger.debug(f'[Database]: Author not found, attempting to save to database.')
                                        a = Authors(name=author)
                                        a.full_clean() # check for validation errors
                                        a.save() # save to db
                                        logger.info(f'[Database]: Author {a.name} successfully saved.')
                                        authors.append(a)
                                    else:
                                        authors.append(Authors.objects.get(name=author))
                                        logger.info(f'[Book Import: "{book_title}"]: Author in DB. Adding to authors list.')
                            except Exception as e:
                                logger.warning(f'[Book Import: "{book_title}"] authors could not be added. Setting to None.')
                                logger.debug(f'volumeInfo:\n{volume_info}')
                                logger.debug(f'Error:\n{e}')
                                authors = None
                            except ValidationError as e:
                                logger.error(f'Validation Error when adding author! Error:\n{e}')

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
                                page_count = volume_info['pageCount']
                                logger.debug(f'[Book Import "{book_title}"]: Added page count {page_count}')
                            except Exception as e:
                                logger.warning(f'[Book Import: "{book_title}"] page_count could not be added. Setting to None.')
                                logger.debug(f'volumeInfo:\n{volume_info}')
                                logger.debug(f'Error:\n{e}')

                            # add publisher
                            try:
                                publisher = volume_info['publisher']
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
                                publisher_date = volume_info['publishedDate']
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
                                description = results[i]['volumeInfo']['description']
                                logger.info(f'[Book Import "{book_title}"]: Added description')
                            except Exception as e:
                                logger.warning(f'[Book Import "{book_title}"] unable to set description. Setting to None.')
                                logger.debug(f'volumeInfo:\n{volume_info}')
                                logger.debug(f'Error:\n{e}')
                                description = None

                            # add print type
                            try:
                                print_type = results[i]['volumeInfo']['printType'].lower()
                                logger.info(f'[Book Import "{book_title}"]: Added print type "{print_type}"')
                            except Exception as e:
                                logger.warning(f'[Book Import "{book_title}"] unable to set print_type. Setting to None.')
                                print_type = None
                                logger.debug(f'volumeInfo:\n{volume_info}')
                                logger.debug(f'Error:\n{e}')

                            # add language
                            try:
                                logger.debug("Trying to set language")
                                language = results[i]['volumeInfo']['language']
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

                            logger.debug(f'checkpoint!')
                            try:
                                logger.debug(f'[Book Import "{book_title}"] Attempting to save book.')
                                new_book = Book(
                                    main_genre = main_genre,
                                    thumbnail_cover = cover_file,
                                    title = title,
                                    page_count = page_count,
                                    publisher = publisher,
                                    published_date = date,
                                    description = description,
                                    print_type = print_type,
                                    language = language,
                                    isbn = isbn_13)
                                new_book.full_clean() # trigger validation errors before saving
                                new_book.save()
                                logger.debug('checkpoint2')
                                new_book.authors.set(authors)
                                stored_results.append(new_book)
                                logger.info(f'[Book Import "{book_title}"] Successfully imported.')
                            except ValidationError as e:
                                logger.error(f'Validation error for "{book_title}":\n{e}')
                            except Exception as e:
                                logger.error(f'Book import failed.')
                                logger.debug(f'volumeInfo:\n{volume_info}')
                                logger.error(f'Error:\n{e}')
                        else:
                            logger.info(f'[Book Import: "{query}"] Book already exists in the database.')
            else:
                # add extra search stuff here
                stored_results = results
                logger.debug(f'DB FETCH:\n{results}')
    # Render the HTML template index.html
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
            book.list.set(selected_lists)
            book.save()
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
        journals = Journal.objects.filter(user=request.user).order_by("-created_at")
        template = loader.get_template("journal/index.html")
        context = {"journals": journals,
                   "page_title": "journal"}
        return HttpResponse(template.render(context, request))


def new_journal(request, book_id=None):
    if book_id:
        book = Book.objects.filter(id=book_id.first())
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
                )
                new_journal.save()
                new_journal.tags.set(clean_data['tags'])
                new_journal.save()
                logger.info(f'[New Journal]: Saved successfully!')
                return redirect("journal")
        else:
            initial_data = {}
            if book:
                initial_data['book'] = book
            new_journal_form = NewJournalForm(user=request.user, initial=initial_data)
    else:
        new_journal_form = NewJournalForm(user=request.user)
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
        # latest_journals a list of 10 most recent Journal Objects
        latest_journals = Journal.objects.filter(user=request.user).order_by("-created_at")[:10]
        logger.debug(f'latest_journals: {latest_journals}')
        user = request.user
        logger.debug(f'user: {user.username}')
        template = loader.get_template("library.html")
        context = {"page_title": "library",
                   "currently_reading": currently_reading,
                   "lists": lists,
                   "latest_journals": latest_journals,
                   "user": user,
        }
        return HttpResponse(template.render(context, request))
