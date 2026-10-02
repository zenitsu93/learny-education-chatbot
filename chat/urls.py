from django.urls import path

from . import views

urlpatterns = [
    path("", views.racine, name="racine"),
    path("connexion/", views.connexion, name="connexion"),
    path("inscription/", views.inscription, name="inscription"),
    path("deconnexion/", views.deconnexion, name="deconnexion"),
    path("accueil/", views.accueil, name="accueil"),
    path("reglages/", views.reglages, name="reglages"),
    path("matiere/<slug:slug>/", views.matiere, name="matiere"),
    path("matiere/<slug:slug>/nouvelle/", views.nouvelle_discussion, name="nouvelle_discussion"),
    path("matiere/<slug:slug>/tout-supprimer/", views.supprimer_tout, name="supprimer_tout"),
    path("discussion/<uuid:pk>/", views.discussion, name="discussion"),
    path("discussion/<uuid:pk>/question/", views.question, name="question"),
    path("discussion/<uuid:pk>/supprimer/", views.supprimer_discussion, name="supprimer_discussion"),
    path("hors-ligne/", views.hors_ligne, name="hors_ligne"),
    path("sw.js", views.service_worker, name="service_worker"),
    path("manifest.webmanifest", views.manifeste, name="manifeste"),
]
