import re

from django import forms
from django.contrib.auth import authenticate, password_validation
from django.contrib.auth.models import User

from .models import UserProfile


def normaliser_telephone(valeur: str) -> str:
    """« 70 12 34 56 », « 0022670123456 », « +226 70123456 » → « +22670123456 »."""
    chiffres = re.sub(r"\D", "", valeur or "")
    if chiffres.startswith("00226"):
        chiffres = chiffres[5:]
    elif chiffres.startswith("226") and len(chiffres) == 11:
        chiffres = chiffres[3:]
    if len(chiffres) != 8:
        raise forms.ValidationError(
            "Le numéro doit avoir 8 chiffres, par exemple 70 12 34 56.", code="telephone"
        )
    return "+226" + chiffres


class InscriptionForm(forms.Form):
    prenom = forms.CharField(label="Ton prénom", max_length=50)
    telephone = forms.CharField(
        label="Numéro de téléphone",
        max_length=20,
        help_text="Il te servira à te connecter. Pas besoin d'adresse e-mail.",
    )
    password = forms.CharField(label="Mot de passe", widget=forms.PasswordInput, min_length=8)

    def clean_prenom(self):
        return " ".join(self.cleaned_data["prenom"].split()).title()

    def clean_telephone(self):
        tel = normaliser_telephone(self.cleaned_data["telephone"])
        if User.objects.filter(username=tel).exists():
            raise forms.ValidationError(
                "Ce numéro a déjà un compte. Connecte-toi, ou demande de l'aide sur WhatsApp.", code="pris"
            )
        return tel

    def clean_password(self):
        mdp = self.cleaned_data["password"]
        password_validation.validate_password(mdp)
        return mdp

    def save(self):
        d = self.cleaned_data
        user = User.objects.create_user(username=d["telephone"], password=d["password"], first_name=d["prenom"])
        UserProfile.objects.filter(user=user).update(telephone=d["telephone"], niveau="3eme")
        return user


class ConnexionForm(forms.Form):
    identifiant = forms.CharField(label="Numéro de téléphone", max_length=120)
    password = forms.CharField(label="Mot de passe", widget=forms.PasswordInput)

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user = None
        super().__init__(*args, **kwargs)

    def clean(self):
        d = super().clean()
        ident, mdp = d.get("identifiant", ""), d.get("password", "")
        if not ident or not mdp:
            return d
        candidats = [ident.strip()]
        try:
            candidats.insert(0, normaliser_telephone(ident))
        except forms.ValidationError:
            pass  # anciens comptes : identifiant = e-mail
        for c in candidats:
            self.user = authenticate(self.request, username=c, password=mdp)
            if self.user:
                return d
        raise forms.ValidationError(
            "Numéro ou mot de passe incorrect. Vérifie les deux, ou demande de l'aide sur WhatsApp.",
            code="invalide",
        )


class ReglagesForm(forms.ModelForm):
    taille_texte = forms.TypedChoiceField(
        label="Taille du texte",
        coerce=int,
        choices=[(v, f"{v} %") for v in (100, 115, 130, 150, 175, 200)],
    )

    class Meta:
        model = UserProfile
        fields = ["taille_texte", "police_lecture", "reduire_animations", "economie_donnees", "theme"]
        labels = {
            "police_lecture": "Police facile à lire",
            "reduire_animations": "Réduire les animations",
            "economie_donnees": "Économiser les données",
            "theme": "Apparence",
        }
        help_texts = {
            "police_lecture": "Lettres plus espacées, interligne plus grand.",
            "reduire_animations": "Les éléments apparaissent sans bouger.",
            "economie_donnees": "Polices du téléphone, aucune image téléchargée.",
        }
        widgets = {"theme": forms.RadioSelect}
