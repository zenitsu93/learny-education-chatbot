<p align="center">
  <img src="docs/assets/cover-a-ardoise.svg" alt="Learny, le répétiteur du BEPC dans la poche des élèves de 3e : maths, physique-chimie et SVT." width="100%">
</p>

<p align="center">
  <a href="#demarrer"><img alt="Python 3.11+" src="https://img.shields.io/badge/Python-3.11%2B-146B43?style=flat-square&logo=python&logoColor=white"></a>
  <a href="https://www.djangoproject.com/"><img alt="Django 5.2" src="https://img.shields.io/badge/Django-5.2-146B43?style=flat-square&logo=django&logoColor=white"></a>
  <a href="https://htmx.org/"><img alt="htmx 2.0" src="https://img.shields.io/badge/htmx-2.0-146B43?style=flat-square&logo=htmx&logoColor=white"></a>
  <a href="https://ai.google.dev/"><img alt="Gemini 2.5 Flash" src="https://img.shields.io/badge/Gemini-2.5%20Flash-146B43?style=flat-square&logo=googlegemini&logoColor=white"></a>
  <a href="#deployer"><img alt="PostgreSQL" src="https://img.shields.io/badge/PostgreSQL-prod-146B43?style=flat-square&logo=postgresql&logoColor=white"></a>
  <br>
  <img alt="PWA installable" src="https://img.shields.io/badge/PWA-installable-F2C14E?style=flat-square&logo=pwa&logoColor=12241A&labelColor=F2C14E">
  <a href="docs/design-system-et-accessibilite/"><img alt="Accessibilité WCAG 2.2 AA" src="https://img.shields.io/badge/WCAG_2.2-AA-F2C14E?style=flat-square&labelColor=F2C14E"></a>
  <img alt="Statut : MVP en test" src="https://img.shields.io/badge/statut-MVP_en_test-F2C14E?style=flat-square&labelColor=F2C14E">
</p>

<p align="center">
  <b>Learny</b> aide les élèves de 3e au Burkina Faso à réviser le <b>BEPC</b>.<br>
  L'élève choisit une matière, pose sa question (écrite ou dictée) et Learny répond étape par étape<br>
  en s'appuyant sur les cours officiels, avec la page citée.
</p>

<p align="center">
  <a href="#fonctionnalites">Fonctionnalités</a> ·
  <a href="#accessibilite">Accessibilité</a> ·
  <a href="#architecture">Architecture</a> ·
  <a href="#demarrer">Démarrer</a> ·
  <a href="#deployer">Déployer</a> ·
  <a href="#feuille-de-route">Feuille de route</a>
</p>

<table>
  <tr>
    <td width="72%" valign="top"><img src="docs/captures/accueil.png" alt="Page d'accueil de Learny sur ordinateur, thème clair"></td>
    <td width="28%" valign="top"><img src="docs/captures/discussion-mobile.png" alt="Discussion sur téléphone, thème sombre"></td>
  </tr>
  <tr>
    <td align="center"><sub>Accueil sur ordinateur, thème clair</sub></td>
    <td align="center"><sub>Discussion sur téléphone, thème sombre</sub></td>
  </tr>
</table>

<br>

<h2 id="fonctionnalites"><img src="docs/assets/section-fonctionnalites.svg" alt="01 · Fonctionnalités" width="100%"></h2>

| Fonctionnalité | Ce que ça change pour l'élève |
|---|---|
| 📚 **Trois matières du BEPC** | Mathématiques, physique-chimie et SVT, sur le programme officiel burkinabè de 3e. |
| 🔎 **Réponses fondées sur les cours** | Les PDF officiels sont découpés et vectorisés une seule fois. À chaque question, Learny retrouve les passages proches et cite la page. |
| 🧭 **Mode « Guide-moi »** | Sur un exercice, Learny pose une question à la fois au lieu de donner la solution tout de suite. |
| 🎙️ **Question écrite ou dictée** | La reconnaissance vocale du navigateur évite de taper les formules sur un petit clavier. |
| ⏳ **Quota quotidien** | 30 questions par élève et par jour par défaut, remises à zéro à minuit, heure de Ouagadougou. |
| 📱 **Connexion par numéro de téléphone** | Inscription en trois champs. Les anciens comptes créés avec un e-mail fonctionnent toujours. |
| 📶 **Pensé pour la 2G** | Application installable (PWA), page hors ligne, mode économie de données, aucun framework JavaScript lourd (htmx seul, environ 50 ko). |

> [!NOTE]
> Sans clé Gemini, l'application fonctionne quand même : les réponses sont remplacées par un message de démonstration. Pratique pour tester l'interface.

<h2 id="accessibilite"><img src="docs/assets/section-accessibilite.svg" alt="02 · Accessibilité" width="100%"></h2>

L'interface suit le design system **Tableau** : vert ardoise `#146B43`, craie jaune `#F2C14E` et la police **Atkinson Hyperlegible**, conçue pour les lecteurs malvoyants.

- Contrastes AA vérifiés en thème clair et en thème sombre.
- Focus toujours visible, navigation complète au clavier, libellés pour les lecteurs d'écran.
- Réglages pour l'élève : taille du texte jusqu'à 200 %, police facile à lire, animations réduites, thème clair ou sombre, économie de données.
- Le Markdown des réponses est nettoyé avec `nh3` : aucun HTML venant du modèle n'est injecté dans la page.

L'audit WCAG 2.2 AA et le design system complet sont dans [`docs/design-system-et-accessibilite`](docs/design-system-et-accessibilite/). Les personas et le choix de la stack sont dans [`docs/conception-personas-et-stack`](docs/conception-personas-et-stack/).

<h2 id="architecture"><img src="docs/assets/section-architecture.svg" alt="03 · Architecture" width="100%"></h2>

```mermaid
flowchart LR
    E["📱 Élève<br/>navigateur ou PWA"] -- "question (htmx)" --> V["Django<br/>views.py"]
    V --> Q{"Quota<br/>du jour"}
    Q -- ok --> R["retrieval.py<br/>similarité cosinus (numpy)"]
    R <--> DB[("PostgreSQL<br/>passages + embeddings")]
    R --> A["ai.py<br/>Gemini via google-genai"]
    A --> M["rendering.py<br/>Markdown nettoyé (nh3)"]
    M -- "fragment HTML" --> E
    P["📄 PDF officiels"] -. "import_cours (une fois)" .-> DB
```

Les embeddings sont rangés en base et comparés en mémoire : ni base vectorielle, ni tâche de fond. Chaque question coûte un appel d'embedding et un appel de génération, et tout tient sur un hébergement mutualisé.

<details>
<summary><b>Arborescence du code</b></summary>

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
docs/                conception, design system, captures, bannières
passenger_wsgi.py    point d'entrée cPanel
```

</details>

| Couche | Choix |
|---|---|
| Serveur | Django 5.2, gabarits + [django-cotton](https://django-cotton.com/) |
| Interactions | [htmx](https://htmx.org/) 2.0, auto-hébergé |
| IA | Gemini 2.5 Flash et `gemini-embedding-001` via `google-genai` |
| Recherche | embeddings en base, similarité cosinus avec numpy |
| Données | PostgreSQL en production, SQLite en local |
| Hébergement | o2switch, cPanel « Setup Python App » (Passenger) |

<h2 id="demarrer"><img src="docs/assets/section-demarrer.svg" alt="04 · Démarrer en local" width="100%"></h2>

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # puis renseigner GEMINI_API_KEY
python manage.py migrate
python manage.py import_cours "context/Cours de Maths 3ème Burkina Faso.pdf" --matiere maths --titre "Maths 3e"
python manage.py runserver
```

Puis ouvrir <http://127.0.0.1:8000>.

`import_cours` accepte `--matiere maths|physique-chimie|svt`, `--titre` (le nom affiché dans les sources) et `--remplacer` pour réimporter un cours.

**Tests** : `DJANGO_DEBUG=1 python manage.py test chat`

<details>
<summary><b>Variables d'environnement</b></summary>

| Variable | Rôle |
|---|---|
| `DJANGO_SECRET_KEY` | obligatoire en production |
| `DJANGO_DEBUG` | `1` en local seulement |
| `DJANGO_ALLOWED_HOSTS` | domaines séparés par des virgules |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | ex. `https://learny.exemple.bf` |
| `DATABASE_URL` | ex. `postgres://user:mdp@localhost:5432/learny` (SQLite si vide) |
| `GEMINI_API_KEY` | clé Google AI Studio |
| `GEMINI_MODEL` | `gemini-2.5-flash` par défaut |
| `GEMINI_EMBED_MODEL` | `gemini-embedding-001` par défaut |
| `LEARNY_QUOTA_JOUR` | questions par élève et par jour (30) |
| `LEARNY_DATE_BEPC` | date de l'examen (`AAAA-MM-JJ`) pour le compte à rebours |
| `LEARNY_AIDE_WHATSAPP` | numéro affiché pour l'aide |

</details>

<h2 id="deployer"><img src="docs/assets/section-deployer.svg" alt="05 · Déployer sur o2switch" width="100%"></h2>

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

> [!IMPORTANT]
> Les PDF de physique-chimie et de SVT restent à importer : seul le cours de maths est fourni dans `context/`.

<h2 id="feuille-de-route">🗺️ Feuille de route</h2>

- [x] **Étape 1 · BEPC prêt** : tuteur fiable en 3e sur le vrai programme, sources citées, mode « Guide-moi », connexion par téléphone, page légère *(V1 du MVP, en test)*
- [ ] **Étape 2 · Partout, même sans réseau** : packs hors ligne, quiz de 5 minutes avec répétition espacée, Learny sur WhatsApp, ouverture à la Terminale et au BAC
- [ ] **Étape 3 · Toute la communauté** : explications audio en mooré, dioula et fulfuldé, espace enseignant, suivi des parents, groupes de révision

Le détail de chaque étape et ses critères de succès sont dans [`docs/conception-personas-et-stack`](docs/conception-personas-et-stack/).

<h2 id="credits">🙏 Crédits</h2>

- Polices **Atkinson Hyperlegible** (© Braille Institute of America) et **Bricolage Grotesque**, sous licence [SIL Open Font License 1.1](https://openfontlicense.org).
- Covers et bandeaux générés par [`docs/assets/generer_bannieres.py`](docs/assets/generer_bannieres.py) ; deux autres covers sont disponibles dans [`docs/assets`](docs/assets/).

<p align="center">
  <img src="chat/static/learny/img/icone.svg" alt="" width="48"><br>
  <sub>Pensé pour les élèves du Burkina Faso, sur les téléphones et les réseaux qu'ils ont vraiment.</sub>
</p>
