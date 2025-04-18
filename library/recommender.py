from library.models import Book, Reviews, UserRecommendations
import numpy as np
import pandas as pd
import string, re
from nltk.corpus import stopwords
from nltk.stem.wordnet import WordNetLemmatizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
from scipy.sparse import csr_matrix
from difflib import SequenceMatcher
import logging
# import matplotlib.pyplot as plt
# import seaborn as sns

logger = logging.getLogger('book_journal')

def clean_text(sentence):
    text = [word for word in sentence.split() if word not in stopwords.words('english')]
    lemmatizer = WordNetLemmatizer()
    text = [lemmatizer.lemmatize(word) for word in text]
    return ' '.join(text).strip().lower()

def build_dataset():
    all_user_reviews = Reviews.objects.all()
    all_books = Book.objects.all()
    # build the ratings DataFrame
    ratings_cols = ["user_id", "book_id", "rating", "timestamp"]
    ratings_lst = []
    for review in all_user_reviews:
        ratings_lst.append([review.user.id, review.book.id, review.rating, review.created_at])
    ratings = pd.DataFrame(ratings_lst, columns=ratings_cols)
    # build the books DataFrame
    book_cols = ["book_id", "title", "author", "genre_text", "description", "combined_text"]
    book_lst = []

    for book in all_books:
        book_id = book.id
        title = book.title
        authors = [author.name for author in book.authors.all()]
        author = " ".join(authors)
        description = book.description if book.description else ""
        genres = [genre.genre for genre in book.genres.all()]
        genre_text = " ".join(genres)
        combined_text = f'{title} {author} {genre_text} {description}'
        combined_text = clean_text(combined_text)
        book_lst.append([book_id, title, author, genre_text, description, combined_text])
    books = pd.DataFrame(book_lst, columns=book_cols)
    books = books.reset_index(drop=True)
    return ratings, books

def vectorize_books(books_df):
    tfidf = TfidfVectorizer(stop_words='english')
    tfidf_matrix = tfidf.fit_transform(books_df['combined_text'])
    return tfidf_matrix, tfidf

def get_recommendations(title, books_df, tfidf_matrix, top_n=5):
    idxs = pd.Series(books_df.index, index=books_df['title']).drop_duplicates()
    if title not in idxs:
        return []
    idx = books_df[books_df['title'] == title].index[0]
    cosine_similarities = linear_kernel(tfidf_matrix[idx], tfidf_matrix).flatten()
    similar_indices = [i for i in cosine_similarities.argsort()[::-1] if i != idx][:top_n]
    logger.debug(f'similar_indices:{similar_indices}')
    logger.debug(f'books_df.shape: {books_df.shape})')
    top_books = books_df.iloc[similar_indices]
    return top_books[['title']], cosine_similarities[similar_indices]

def is_similar(title1, title2, threshold=0.8):
    return SequenceMatcher(None, title1.lower(), title2.lower()).ratio() >= threshold

def content_based_recommendations(user):
    ratings_df, books_df = build_dataset()
    tfidf_matrix, tfidf = vectorize_books(books_df)

    # filter ratings by this user
    user_ratings = ratings_df[ratings_df['user_id'] == user.id]
    if user_ratings.empty:
        return pd.DataFrame(), []

    # filter books already read
    rated_books = user_ratings['book_id'].values
    rated_indices = books_df[books_df['book_id'].isin(rated_books)].index
    rated_book_ids = set(user_ratings['book_id'].values)
    rated_books_info = books_df[books_df['book_id'].isin(rated_book_ids)][['book_id', 'title']]
    logger.debug(f'Rated books by user:\n{rated_books_info}')
    rated_titles = books_df[books_df['book_id'].isin(rated_book_ids)]['title'].tolist()

    # get user tfidf vectors for those books
    user_tfidfs = tfidf_matrix[rated_indices]

    # weight them by users rating
    book_ids_in_order = books_df.loc[rated_indices, 'book_id'].values
    ratings_dict = user_ratings.set_index('book_id')['rating'].to_dict()
    ratings = np.array([ratings_dict.get(book_id, 0) for book_id in book_ids_in_order], dtype=float)
    logger.debug(f'user_tfidfs shape: {user_tfidfs.shape}')
    logger.debug(f'ratings shape: {ratings.shape}')
    user_profile = np.average(user_tfidfs.toarray(), axis=0, weights=ratings)

    # compute similarity with all books
    cosine_similarities = linear_kernel([user_profile], tfidf_matrix).flatten()

    # exclude books user has already rated
    exclude_mask = books_df['book_id'].isin(rated_book_ids)
    cosine_similarities[np.where(exclude_mask)[0]] = -1

    # get top N
    top_indices = cosine_similarities.argsort()[::-1][:20]
    book_recs = books_df.iloc[top_indices]
    logger.debug(f'Top recommendations before deduplication:\n{book_recs[['book_id', 'title']]}')
    # apply similarity filter to filter books by title further
    book_recs = book_recs[~book_recs['title'].apply(
        lambda rec_title: any(is_similar(rec_title, rated_title, 0.5) for rated_title in rated_titles)
    )]
    logger.debug(f'book_recs:{book_recs}')
    return book_recs[['title']], cosine_similarities[top_indices]


def collaborative_recommendatiions(user):
    return None
