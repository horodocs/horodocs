from django import forms
from django.utils.translation import gettext_lazy as _


class HorodatageForm(forms.Form):
    # ATTENTION : l'input qui sert à upload le fichier est dans le fichier document-hash.html, cela permet de ne pas avoir à envoyer l'image au serveur.
    # filename_value = forms.CharField(required=True, widget=forms.HiddenInput(attrs={'class' : 'form-control horoform',  'autocomplete':'off'}))
    md5_value = forms.CharField(
        required=True,
        widget=forms.HiddenInput(
            attrs={"class": "form-control horoform", "autocomplete": "off"}
        ),
    )
    sha256_value = forms.CharField(
        required=True,
        widget=forms.HiddenInput(
            attrs={"class": "form-control horoform", "autocomplete": "off"}
        ),
    )
    case_number = forms.CharField(
        label=_("Numéro du cas"),
        max_length=100,
        required=True,
        widget=forms.TextInput(
            attrs={"class": "form-control horoform", "autocomplete": "off"}
        ),
    )
    file_id = forms.CharField(
        label=_("Identifiant du fichier"),
        max_length=100,
        required=True,
        widget=forms.TextInput(
            attrs={"class": "form-control horoform", "autocomplete": "off"}
        ),
    )
    investigator = forms.CharField(
        label=_("Enquêteur"),
        max_length=100,
        required=True,
        widget=forms.TextInput(
            attrs={"class": "form-control horoform", "autocomplete": "off"}
        ),
    )
    email_user = forms.EmailField(
        required=True,
        label=_("Email de l'enquêteur"),
        max_length=100,
        widget=forms.EmailInput(
            attrs={"class": "form-control horoform", "autocomplete": "off"}
        ),
    )
    comments = forms.CharField(
        label=_("Texte libre"),
        max_length=500,
        required=False,
        widget=forms.Textarea(
            attrs={"class": "form-control horoform", "autocomplete": "off"}
        ),
    )
    want_ancrage_informations = forms.BooleanField(
        label=_("Recevoir la confirmation de l'ancrage dans la blockchain par mail"),
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "horoform"}),
    )
