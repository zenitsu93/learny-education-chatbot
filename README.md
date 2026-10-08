# Learny, répétiteur pour le BEPC

Learny aide les élèves de 3e au Burkina Faso à réviser le BEPC. L'élève choisit une matière, pose sa question (écrite ou dictée) et Learny répond étape par étape en s'appuyant sur les cours officiels, avec la page citée.

![Accueil](docs/captures/accueil.png)

<img src="docs/captures/discussion-mobile.png" alt="Discussion sur téléphone, thème sombre" width="320">

## V1 du MVP

- **3 matières** : mathématiques, physique-chimie et SVT, niveau 3e.
- **Réponses fondées sur les cours** : les PDF officiels sont découpés et vectorisés une seule fois (`import_cours`). À chaque question, Learny retrouve les passages proches et les cite.
- **Mode « Guide-moi »** : Learny pose des questions au lieu de donner la solution tout de suite.
- **Quota** de questions par jour et par élève (30 par défaut), remis à zéro à minuit, heure de Ouagadougou.
- **Connexion par numéro de téléphone**. Les anciens comptes créés avec un e-mail fonctionnent toujours.
- **Accessibilité** : design system « Tableau » (contraste AA, focus visible, navigation au clavier, lecteurs d'écran), taille du texte jusqu'à 200 %, police facile à lire, animations réduites, thème clair ou sombre, mode économie de données.
- **Téléphone et réseau faible** : application installable (PWA), page hors ligne, pas de framework JavaScript (htmx seul, environ 50 ko).

Le design system et l'audit d'accessibilité sont dans [docs/design-system-et-accessibilite](docs/design-system-et-accessibilite/).

## Architecture

```
chat/
  subjects.py        matières et consignes données à Gemini
  ai.py              appels Gemini (google-genai) : réponses et embeddings
  retrieval.py       découpage des cours et recherche par similarité (numpy)
  rendering.py       Markdown des réponses, nettoyé (pas de HTML injecté)
  forms.py           inscription, connexion, réglages
  views.py           pages, question (htmx), PWA
  models.py          profil, discussions, échanges, passages de cours
  management/commands/import_cours.py
  templates/
    cotton/          composants (bouton, champ, alerte, interrupteur, icône)
    chat/            pages
    partials/        fragments renvoyés à htmx
  static/learny/     css, js, polices, icônes, htmx
```

Django 5.2, PostgreSQL en production (SQLite en local), Gemini via `google-genai`. Les embeddings sont rangés en base et comparés en mémoire : ni base vectorielle, ni tâche de fond. Tout tient sur un hébergement mutualisé.

## Mise en route en local

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # puis renseigner GEMINI_API_KEY
python manage.py migrate
python manage.py import_cours "context/Cours de Maths 3ème Burkina Faso.pdf" --matiere maths --titre "Maths 3e"
python manage.py runserver
```

Sans `GEMINI_API_KEY`, l'application marche quand même : les réponses sont un message de démonstration.

`import_cours` accepte `--matiere maths|physique-chimie|svt`, `--titre` (le nom affiché dans les sources) et `--remplacer` pour réimporter un cours.

Tests : `DJANGO_DEBUG=1 python manage.py test chat`

## Variables d'environnement

| Variable | Rôle |
|---|---|
| `DJANGO_SECRET_KEY` | obligatoire en production |
| `DJANGO_DEBUG` | `1` en local seulement |
| `DJANGO_ALLOWED_HOSTS` | domaines séparés par des virgules |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | ex. `https://learny.exemple.bf` |
| `DATABASE_URL` | ex. `postgres://user:mdp@localhost:5432/learny` (SQLite si vide) |
| `GEMINI_API_KEY` | clé Google AI Studio |
| `GEMINI_MODEL` | `gemini-2.5-flash` par défaut |
| `LEARNY_QUOTA_JOUR` | questions par élève et par jour (30) |
| `LEARNY_DATE_BEPC` | date de l'examen (`AAAA-MM-JJ`) pour le compte à rebours |
| `LEARNY_AIDE_WHATSAPP` | numéro affiché pour l'aide |

## Déploiement sur o2switch

1. **cPanel → Bases de données PostgreSQL** : créer la base et l'utilisateur, puis renseigner `DATABASE_URL`.
2. **cPanel → Setup Python App** : Python 3.11, racine de l'application = ce dépôt, fichier de démarrage `passenger_wsgi.py` (fourni). Ajouter les variables ci-dessus dans l'interface.
3. Dans le terminal de l'application (environnement virtuel activé) :
   ```bash
   pip install -r requirements.txt
   python manage.py migrate
   python manage.py collectstatic --noinput
   python manage.py import_cours "context/Cours de Maths 3ème Burkina Faso.pdf" --matiere maths --titre "Maths 3e"
   python manage.py createsuperuser
   ```
4. Servir `staticfiles/` sous `/static/` (alias dans le `.htaccess` ou dossier `public_html/static`), puis redémarrer l'application.
