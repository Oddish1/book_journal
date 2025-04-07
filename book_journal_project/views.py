import requests
from urllib.parse import quote_plus
from django.shortcuts import render, redirect, HttpResponse
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from .forms import RegisterForm, BookSearchForm
from django.conf import settings
from datetime import datetime
from library.models import Book, Genres, Authors, Covers
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile, File
from django.core.exceptions import ValidationError
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

                            # add average rating
                            try:
                                average_rating = float(volume_info['averageRating'])
                                logger.debug(f'[Book Import "{title}"]: Added average rating {average_rating}')
                            except Exception as e:
                                logger.warning(f'[Book Import: "{book_title}"] average_rating could not be added. Setting to None.')
                                logger.debug(f'volumeInfo:\n{volume_info}')
                                logger.debug(f'Error:\n{e}')
                            
                            # add ratings count
                            try:
                                ratings_count = int(volume_info['ratingsCount'])
                                logger.debug(f'[Book Import "{title}"]: Added ratings count {ratings_count}')
                            except Exception as e:
                                logger.warning(f'[Book Import: "{book_title}"] ratings_count could not be added. Setting to None.')
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
                                    average_rating = average_rating,
                                    ratings_count = ratings_count,
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
                                logger.info(f'Error:\n{e}')
                        else:
                            logger.info(f'[Book Import: "{query}"] Book already exists in the database.')
            else:
                # add extra search stuff here
                stored_results = results
                logger.debug(f'DB FETCH:\n{results}')
    # Render the HTML template index.html
    logger.debug(f'stored_results:\n{stored_results}')
    return render(request, 'index.html', {
                  "form": form,
                  "stored_results": stored_results,
                  })

def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("home")
    else:
        form = RegisterForm()
    return render(request, "register.html", {"form": form})

def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("home")
    else:
        form = AuthenticationForm()
    return render(request, "login.html", {"form": form})

def logout_view(request):
    logout(request)
    return redirect("home")


def book(request, book_id):
    return HttpResponse(f"You're looking at book {book_id}")
