import uuid

from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    THEMES = [("auto", "Comme le téléphone"), ("clair", "Clair"), ("sombre", "Sombre")]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    telephone = models.CharField(max_length=20, blank=True)
    date_naissance = models.DateField(null=True, blank=True)
    genre = models.CharField(max_length=10, blank=True, choices=[("M", "Masculin"), ("F", "Féminin")])
    niveau = models.CharField(
        max_length=10,
        default="3eme",
        choices=[("6eme", "6e"), ("5eme", "5e"), ("4eme", "4e"), ("3eme", "3e")],
    )
    ville = models.CharField(max_length=100, blank=True)

    # Réglages de lecture et de confort
    taille_texte = models.PositiveSmallIntegerField(default=100)
    police_lecture = models.BooleanField(default=False)
    reduire_animations = models.BooleanField(default=False)
    economie_donnees = models.BooleanField(default=False)
    theme = models.CharField(max_length=10, choices=THEMES, default="auto")

    def __str__(self):
        return f"Profil de {self.user.username}"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)


class Session(models.Model):
    """Une discussion de l'élève dans une matière."""

    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    title = models.CharField(max_length=80)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="session")
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    cours_name = models.CharField(max_length=40, default="maths")
    guide = models.BooleanField(default=True, help_text="Mode « Guide-moi » : Learny pose des questions au lieu de donner la solution.")

    class Meta:
        ordering = ["-updated"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("discussion", kwargs={"pk": self.pk})


class Chat(models.Model):
    """Un échange : la question de l'élève et la réponse de Learny."""

    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    created = models.DateTimeField(auto_now_add=True)
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="chats", blank=True, null=True)
    message = models.TextField()
    response = models.TextField()
    sources = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["created"]

    def __str__(self):
        return self.message[:60]


class CourseChunk(models.Model):
    """Un passage d'un cours officiel, avec son embedding précalculé."""

    matiere = models.CharField(max_length=40, db_index=True)
    source = models.CharField(max_length=200)
    page = models.PositiveIntegerField(null=True, blank=True)
    texte = models.TextField()
    embedding = models.JSONField(default=list)

    class Meta:
        indexes = [models.Index(fields=["matiere", "source"])]

    def __str__(self):
        return f"{self.source} p. {self.page}"
