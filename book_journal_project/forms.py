from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.conf import settings
from library.models import Tags, List
from django.forms import ModelForm

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

    # TODO select form for currently reading books
    book = forms.CharField(label='Select Your Book', max_length=200)
    page = forms.IntegerField(label='Page Number')
    journal_text = forms.CharField(label='Journal Entry', max_length=10000)
    is_public = forms.BooleanField(label='Public', required=False)
    tags = forms.CharField(label='Tags', max_length=200)


class ListDropDownForm(forms.Form):
    lists = forms.ModelMultipleChoiceField(
        queryset=List.objects.none(), # default empty,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Add to Lists",
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['lists'].queryset = List.objects.filter(user=user)
