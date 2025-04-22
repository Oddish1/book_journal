from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, SetPasswordForm
from django.contrib.auth import get_user_model
from django.conf import settings
from library.models import Tags, List, Book
from django.forms import ModelForm, TextInput, NumberInput, PasswordInput
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError

User = get_user_model()

class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'Email'
        })
    )
    username = forms.CharField(
            widget=TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Username'
            })
    )
    password1 = forms.CharField(
            widget=PasswordInput(attrs={
                'class': 'form-input',
                'placeholder': 'Password'
            })
    )
    password2 = forms.CharField(
            widget=PasswordInput(attrs={
                'class': 'form-input',
                'placeholder': 'Confirm Password'
            })
    )

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]


class LoginForm(AuthenticationForm):
    username = forms.CharField(
            widget=TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Username'
            })
    )
    password = forms.CharField(
            widget=PasswordInput(attrs={
                'class': 'form-input',
                'placeholder': 'Password'
            })
    )

    class Meta:
        model = User
        fields = ["username", "password"]

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
                                'placeholder': 'Journal Title',
                                'class': 'form-input'
                            })
    )
    page = forms.IntegerField(label='',
                              widget=NumberInput(attrs={
                                'placeholder': 'Page Number',
                                'class': 'form-input'
                              })
    )
    tags = forms.CharField(label='',
                           max_length=200,
                           required=False,
                           widget=TextInput(attrs={
                                'placeholder': 'tags, with, commas',
                                'class': 'form-input'
                           })
    )
    journal_text = forms.CharField(
        label='',
        max_length=10000,
        required=False,
        widget=forms.Textarea(attrs={
                'rows': 8,
                'placeholder': 'Write your journal entry here...',
                'style': 'resize: vertical',
                'class': 'form-input'
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
            'placeholder': 'Rating (0-5)',
            'class': 'form-input'
        })
    )
    title = forms.CharField(label='',
                            max_length=200,
                            required=False,
                            widget=TextInput(attrs={
                                'placeholder': 'Review Title',
                                'class': 'form-input'
                            })
    )
    review = forms.CharField(label='',
                             max_length=5000,
                             required=False,
                             widget=forms.Textarea(attrs={
                                'rows': 8,
                                'placeholder': 'Write your review here...',
                                'style': 'resize: vertical',
                                'class': 'form-input'
                             })
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        finished = List.objects.get(user=user, name="Finished")
        super().__init__(*args, **kwargs)
        self.fields['book'].queryset = Book.objects.filter(list=finished)


class PasswordResetForm(forms.Form):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'Email'
        })
    )


class PasswordResetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(
            widget=PasswordInput(attrs={
                'class': 'form-input',
                'placeholder': 'New Password'
            })
    )
    new_password2 = forms.CharField(
            widget=PasswordInput(attrs={
                'class': 'form-input',
                'placeholder': 'Confirm Password'
            })
    )


class UserProfileForm(ModelForm):
    is_public = forms.BooleanField(
            required=False,
            label="Make profile public",
            widget=forms.CheckboxInput(attrs={'class': 'form-input'})
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'profile_picture', 'bio', 'is_public']
        widgets = {
                'first_name': forms.TextInput(attrs={
                    'class': 'form-input',
                    'placeholder': 'First Name'
                }),
                'last_name': forms.TextInput(attrs={
                    'class': 'form-input',
                    'placeholder': 'Last Name'
                }),
                'email': forms.EmailInput(attrs={
                    'class': 'form-input',
                    'placeholder': 'Email'
                }),
                'bio': forms.Textarea(attrs={
                    'class': 'form-input',
                    'placeholder': 'Tell us about yourself'
                }),
                'profile_picture': forms.FileInput(attrs={
                    'class': 'form-input'
                }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in self.fields:
            if field_name != 'email':
                self.fields[field_name].required = False
