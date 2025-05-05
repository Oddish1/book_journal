# 📚 BookJournal

**BookJournal** is a full-stack Django web app that allows users to search for books, save them to a personal collection, and write journal entries. It integrates with the Google Books API and provides a clean interface for managing and exploring a personal reading history.

## Screenshots

**Homepage (not logged in)**
![Unauthenticated Homepage Screenshot](./screenshots/homepage_noauth.png)

**Register**
![Register Page Screenshot](./screenshots/register.png)

**Login**
![Login Page Screenshot](./screenshots/login.png)

**Homepage (logged in)**
![Authenticated Homepage Screenshot](./screenshots/homepage_auth.png)

**Search Results**
![Search Results Screenshot](./screenshots/search_results.png)

**Book Details**
![Book Details Screenshot](./screenshots/book_details.png)

**Book Reviews**
![Book Reviews Screenshot](./screenshots/book_reviews.png)

**Review**
![Review Screenshot](./screenshots/review.png)

**New Review**
![New Review Screenshot](./screenshots/new_review.png)

**Library**
![Library Screenshot](./screenshots/library.png)

**Journal Home Page**
![Journal Homepage Screenshot](./screenshots/journal.png)

**New Journal**
![New Journal Screenshot](./screenshots/new_journal.png)

**Your Profile**
![Your Profile Screenshot](./screenshots/profile.png)

**Other User Profile**
![Other User Profile Screenshot](./screenshots/user_profile.png)

**

## Features

- Search books using the Google Books API
- Add to your library with persistent storage in PostgreSQL
- Follow your friends
- View detailed book pages including cover, metadata, journal entries, and reviews
- Journal your reading with timestamped entries
- Content-based recommendations based on books you have rated
- Custom password reset flow using Django's Auth system
- Responsive UI built with Bootsrap

## Tech Stack

- **Backend:** Django, Python, PostgreSQL
- **Frontend:** HTML, Bootstrap
- **APIs:** Google Books API

## Future Improvements

- Add user-to-user sharing
- Implement auto-tagging of books, reviews, and journals
- Implement Celery for background processing and scalability
- Dockerize for production deployment
