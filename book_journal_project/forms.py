from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.conf import settings
from library.models import Tags, List, Book
from django.forms import ModelForm
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

# TODO create save method
class NewJournalForm(forms.Form):
    book = forms.ModelChoiceField(
        queryset=Book.objects.none(), # defualt empty
        required=True,
        label='Book')
    is_finished = forms.BooleanField(label='Finish', required=False)
    title = forms.CharField(label='Journal Title', max_length=200, required=False)
    page = forms.IntegerField(label='Page Number')
    journal_text = forms.CharField(label='Journal Entry', max_length=10000, required=False)
    is_public = forms.BooleanField(label='Public', required=False)
    tags = forms.CharField(label='Tags', max_length=200, required=False)

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
        label='Book')
    rating = forms.FloatField(
        validators=[MinValueValidator(0),
            MaxValueValidator(5)],
        required=True,
        label='Rating (0-5)')
    title = forms.CharField(label='Review Title', max_length=200, required=False)
    review = forms.CharField(label='Review', max_length=5000, required=False)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        finished = List.objects.get(user=user, name="Finished")
        super().__init__(*args, **kwargs)
        self.fields['book'].queryset = Book.objects.filter(list=finished)
