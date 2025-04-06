import requests
from urllib.parse import quote_plus
from django.shortcuts import render, redirect, HttpResponse
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from .forms import RegisterForm, BookSearchForm
from django.conf import settings
from datetime import datetime
from library.models import Book, Genres, Authors
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
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
                                break
                        if not isbn_13:
                            isbn_10 = None
                            for identifier in volume_info.get('industryIdentifiers', []):
                                if identifier['type'] == 'ISBN_10':
                                    isbn_10 = identifier['identifier']
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
                            logger.info(f'[Book Import: "{book_title}"] No existing book found, attempting to import.')
                            
                            try:
                                main_genre = Genres(genre=results[i]['volumeInfo']['mainCategory'])
                            except Exception as e:
                                logger.warning(f'[Book Import: "{book_title}"] mainCategory could not be found or does not exist. Setting to None.')
                                logger.debug(f'volumeInfo:\n{volume_info}')
                                logger.debug(f'Error:\n{e}')
                                main_genre = None
                            
                            try:
                                genres = [genre for genre in results[i]['volumeInfo']['categories']]
                                genre_objects = [Genres(genre=genre) for genre in genres]
                            except Exception as e:
                                logger.warning(f'[Book Import: "{book_title}"] genres could not be added. Setting to None.')
                                logger.debug(f'volumeInfo:\n{volume_info}')
                                logger.debug(f'Error:\n{e}')
                                genre_objects = None
                            
                            try:
                                image_url = results[i]['volumeInfo']['imageLinks']['thumbnail']
                                try:
                                    img_response = requests.get(image_url)
                                    if img_response.status_code == 200:
                                        image = Image.open(BytesIO(img_response.content))
                                        image_io = BytesIO()
                                        image.save(image_io, format='PNG')
                                        cover_file = ContentFile(image_io.getvalue(), name=f"{isbn_13}.png")
                                except Exception as e:
                                    logger.error(f'[Image Download: "{book_title}"] Image failed to download.')
                                    logger.debug(f'Image link: {image_url}')
                                    logger.debug(f'Error:\n{e}')
                            except Exception as e:
                                logger.warning(f'[Book Import: "{book_title}"] thumbnail_cover could not be added. Setting to None.')
                                logger.debug(f'volumeInfo:\n{volume_info}')
                                logger.debug(f'Error:\n{e}')

                            try:
                                name = results[i]['volumeInfo']['authors'][0],
                                main_author = Authors(name=name)
                            except Exception as e:
                                logger.warning(f'[Book Import: "{book_title}"] author could not be added. Setting to None.')
                                logger.debug(f'volumeInfo:\n{volume_info}')
                                logger.debug(f'Error:\n{e}')
                                main_author = None

                            try:
                                authors_list = volume_info['authors']
                                authors = [author for author in authors_list]
                            except Exception as e:
                                logger.warning(f'[Book Import: "{book_title}"] authors could not be added. Setting to None.')
                                logger.debug(f'volumeInfo:\n{volume_info}')
                                logger.debug(f'Error:\n{e}')
                                authors = None

                            try:
                                title = results[i]['volumeInfo']['title']
                            except Exception as e:
                                logger.warning(f'[Book Import: "{book_title}"] title could not be added. Setting to None.')
                                logger.debug(f'volumeInfo:\n{volume_info}')
                                logger.debug(f'Error:\n{e}')

                            try:
                                page_count = results[i]['volumeInfo']['pageCount']
                            except Exception as e:
                                logger.warning(f'[Book Import: "{book_title}"] page_count could not be added. Setting to None.')
                                logger.debug(f'volumeInfo:\n{volume_info}')
                                logger.debug(f'Error:\n{e}')

                            try:
                                average_rating = results[i]['volumeInfo']['averageRating']
                            except Exception as e:
                                logger.warning(f'[Book Import: "{book_title}"] average_rating could not be added. Setting to None.')
                                logger.debug(f'volumeInfo:\n{volume_info}')
                                logger.debug(f'Error:\n{e}')
                            
                            try:
                                ratings_count = results[i]['volumeInfo']['ratingsCount']
                            except Exception as e:
                                logger.warning(f'[Book Import: "{book_title}"] ratings_count could not be added. Setting to None.')
                                logger.debug(f'volumeInfo:\n{volume_info}')
                                logger.debug(f'Error:\n{e}')
                            

                            try:
                                publisher = results[i]['volumeInfo']['publisher']
                                if isinstance(publisher, list):
                                    try:
                                        publishers = [pub for pub in publisher]
                                        publisher = ", ".join(publishers)
                                    except Exception as e:
                                        logger.error(f'[Adding Publishers: "{book_title}"] unable to join publishers into single string.')
                                        logger.debug(f'Error: {e}')
                            except Exception as e:
                                logger.warning(f'[Book Import: "{book_title}" publisher could not be added. Setting to None.')
                                logger.debug(f'volumeInfo:\n{volume_info}')
                                logger.debug(f'Error:\n{e}')
                                publisher = None

                            try:
                                publisher_date = volume_info['publishedDate']
                                try:
                                    date = datetime.strptime(publisher_date, "%Y-%m-%d")
                                    date = datetime.strftime(date, "%B %d, %Y")
                                except Exception as e:
                                    logger.warning(f'[Date Conversion "{book_title}"]: date not in "Y-m-d" format. Trying different format.')
                                    logger.debug(f'Error:\n{e}')
                                    try:
                                        date = datetime.strptime(publisher_date, "%Y")
                                        date = datetime.strftime(date, "%Y")
                                        logger.info(f'[Date Conversion "{book_title}"]: date stored in "Y" format: {date}')
                                    except Exception as e:
                                        logger.warning(f'[Date Conversion "{book_title}"]: date not in "Y" format. Attempting to set date from string value if possible.')
                                        logger.debug(f'Error:\n{e}')
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
                                
                            try:
                                description = results[i]['volumeInfo']['description']
                            except Exception as e:
                                logger.warning(f'[Book Import "{book_title}"] unable to set description. Setting to None.')
                                logger.debug(f'volumeInfo:\n{volume_info}')
                                logger.debug(f'Error:\n{e}')
                                description = None

                            try:
                                print_type = results[i]['volumeInfo']['printType'].lower()
                            except Exception as e:
                                logger.warning(f'[Book Import "{book_title}"] unable to set print_type. Setting to None.')
                                logger.debug(f'volumeInfo:\n{volume_info}')
                                logger.debug(f'Error:\n{e}')

                            try:
                                language = results[i]['volumeInfo']['language']
                                if isinstance(language, str):
                                    continue
                                if isinstance(language, list):
                                    langauges = [lang for lang in language]
                                    language = " ,".join(languages)
                                else:
                                    logger.warning(f'[Book Import "{book_title}"] unable to set language. Setting to None.')
                                    logger.debug(f'volumeInfo:\n{volume_info}')
                                    language = None
                            except Exception as e:
                                logger.error(f'[Book Import "{book_title}"] error while setting language.')
                                logger.debug(f'Error:\n{e}')

                            try:
                                isbn = isbn_13 
                            except Exception as e:
                                logger.error(f'[Book Import "{book_title}"] unable to set isbn.')
                                logger.debug(f'Error:\n{e}')

                            try:
                                logger.debug(f'[Book Import "{book_title}"] Attempting to save book.')
                                new_book = Book(
                                    main_genre = main_genre,
                                    genres = genre_objects,
                                    thumbnail_cover = cover_file,
                                    covers = Covers(image=None),
                                    main_author = main_author,
                                    authors = authors,
                                    title = title,
                                    page_count = page_count,
                                    average_rating = average_rating,
                                    ratings_count = ratings_count,
                                    publisher = publisher,
                                    published_date = published_date,
                                    description = description,
                                    print_type = print_type,
                                    language = language,
                                    isbn = isbn_13)
                                new_book.full_clean() # trigger validation errors before saving
                                new_book.save()
                                stored_results.append(new_book)
                                logger.info(f'[Book Import "{book_title}"] Successfully imported.')
                            except ValidationError as e:
                                logger.error(f'Validation error for"{book_title}":\n{e}')
                            except Exception as e:
                                logger.error(f'Book import failed.')
                                logger.debug(f'volumeInfo:\n{volume_info}')
                                logger.info(f'Error:\n{e}')
                        else:
                            logger.info(f'[Book Import: "{query}"] Book already exists in the database.')

    # Render the HTML template index.html
    return render(request, 'index.html', {
                  "form": form,
                  "results": stored_results,
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
