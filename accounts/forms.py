"""
accounts/forms.py - Formularze aplikacji accounts.

Zawiera:
- RegisterForm: Rejestracja nowego użytkownika (username, email, hasło x2)
- LoginForm: Logowanie (email + hasło), rozszerza AuthenticationForm
- ProfileForm: Edycja profilu (username)
- ChangePasswordForm: Zmiana hasła (stare + nowe x2)
- ChangeEmailForm: Zmiana adresu email
"""

from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from .models import User


class RegisterForm(forms.ModelForm):
    """Formularz rejestracji nowego użytkownika.

    Pola: username, email, password1, password2.
    Waliduje unikalność emaila i zgodność haseł.
    """

    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Create a password',
        }),
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm your password',
        }),
    )

    class Meta:
        model = User
        fields = ['username', 'email']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Choose a username',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your email',
            }),
        }

    def clean_password2(self):
        """Walidacja zgodności obu haseł."""
        p1 = self.cleaned_data.get('password1')
        p2 = self.cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Passwords do not match.')
        return p2

    def save(self, commit=True):
        """Tworzy użytkownika z zahashowanym hasłem."""
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    """Formularz logowania z email i hasłem.

    Rozszerza wbudowany AuthenticationForm Django,
    dodając klasy CSS Bootstrap do pól.
    """

    username = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email',
            'autofocus': True,
        }),
    )
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password',
        }),
    )


class ProfileForm(forms.ModelForm):
    """Formularz edycji profilu - zmiana nazwy użytkownika."""

    class Meta:
        model = User
        fields = ['username']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
            }),
        }


class ChangePasswordForm(PasswordChangeForm):
    """Formularz zmiany hasła z klasami CSS Bootstrap."""

    old_password = forms.CharField(
        label='Current Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter current password',
        }),
    )
    new_password1 = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password',
        }),
    )
    new_password2 = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password',
        }),
    )


class ChangeEmailForm(forms.Form):
    """Formularz zmiany adresu email z walidacją hasła."""

    new_email = forms.EmailField(
        label='New Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new email address',
        }),
    )
    password = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password to confirm',
        }),
    )

    def clean_new_email(self):
        """Walidacja unikalności nowego adresu email."""
        email = self.cleaned_data['new_email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email address is already in use.')
        return email
