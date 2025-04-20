from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.conf import settings
from library.models import Tags, List, Book
from django.forms import ModelForm, TextInput, NumberInput
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]


class BookSearchForm(forms.Form):
    query = forms.CharField(label='', max_length=200, widget=forms.TextInput(attrs={
                                                    'placeholder': 'Search books...',
                                                    'class': 'search-input'
                                                    }))

class NewJournalForm(forms.Form):
    book = forms.ModelChoiceField(
        queryset=Book.objects.none(), # defualt empty
        required=True,
        label='',
        empty_label='Pick a Book'
    )
    title = forms.CharField(label='',
                            max_length=200,
                            required=False,
                            widget=TextInput(attrs={
                                'placeholder': 'Journal Title'
                            })
    )
    page = forms.IntegerField(label='',
                              widget=NumberInput(attrs={
                                'placeholder': 'Page Number'
                              })
    )
    tags = forms.CharField(label='',
                           max_length=200,
                           required=False,
                           widget=TextInput(attrs={
                                'placeholder': 'tags, with, commas'
                           })
    )
    journal_text = forms.CharField(
        label='',
        max_length=10000,
        required=False,
        widget=forms.Textarea(attrs={
                'rows': 8,
                'placeholder': 'Write your journal entry here...',
                'style': 'resize: vertical'
            })
    )
    is_public = forms.BooleanField(label='Make Public', required=False)
    is_finished = forms.BooleanField(label='Finished the Book?', required=False)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        currently_reading = List.objects.get(user=user, name="Currently Reading")
        super().__init__(*args, **kwargs)
        self.fields['book'].queryset = Book.objects.filter(list=currently_reading)



class ListDropDownForm(forms.Form):
    lists = forms.ModelMultipleChoiceField(
        queryset=List.objects.none(), # default empty,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="",
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['lists'].queryset = List.objects.filter(user=user)


class NewReviewForm(forms.Form):
    book = forms.ModelChoiceField(
        queryset=Book.objects.none(), # default empty
        required=True,
        label='',
        empty_label='Pick a Book'
    )
    rating = forms.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(5)
        ],
        required=True,
        label='',
        widget=NumberInput(attrs={
            'placeholder': 'Rating (0-5)'
        })
    )
    title = forms.CharField(label='',
                            max_length=200,
                            required=False,
                            widget=TextInput(attrs={
                                'placeholder': 'Review Title'
                            })
    )
    review = forms.CharField(label='',
                             max_length=5000,
                             required=False,
                             widget=forms.Textarea(attrs={
                                'rows': 8,
                                'placeholder': 'Write your review here...',
                                'style': 'resize: vertical'
                             })
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        finished = List.objects.get(user=user, name="Finished")
        super().__init__(*args, **kwargs)
        self.fields['book'].queryset = Book.objects.filter(list=finished)
