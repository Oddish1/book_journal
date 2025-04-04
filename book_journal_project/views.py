import requests
from urllib.parse import quote_plus
from django.shortcuts import render, redirect, HttpResponse
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from .forms import RegisterForm, BookSearchForm
from django.conf import settings

API_KEY = settings.GOOGLE_BOOKS_API_KEY


# Create your views here.

def home(request):
    form = BookSearchForm()
    results = []

    if request.method == "GET" and "query" in request.GET:
        form = BookSearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data["query"]
            encoded_query = quote_plus(query)
            url = f'https://www.googleapis.com/books/v1/volumes?q={encoded_query}&orderBy=relevance&printType=books&key={API_KEY}'
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                results = data.get("items", [])

    # Render the HTML template index.html
    return render(request, 'index.html', {
                  "form": form,
                  "results": results,
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
