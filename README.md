# Learny — assistant de révision

Un chatbot éducatif en Django : l'élève dépose ses documents de cours, pose ses questions, et obtient des réponses tirées de ses propres supports plutôt que des connaissances générales du modèle.

![Accueil](<Accueil (1).png>)

![Session de mathématiques](<Maths (1).png>)

## Ce qu'il fait

**Les réponses viennent des cours déposés.** Les PDF téléversés sont découpés, vectorisés et rangés dans une base Chroma. À chaque question, les passages pertinents sont retrouvés et transmis au modèle. Un élève qui demande une définition obtient celle de son manuel, pas une paraphrase générique.

**Les conversations sont rangées par cours.** Chaque session est rattachée à une matière, ce qui évite de mélanger un contexte de mathématiques avec une question d'histoire.

**On peut parler au lieu d'écrire.** La reconnaissance vocale du navigateur transcrit la question — utile sur mobile, et pour les formules qu'on énonce plus vite qu'on ne les tape.

**Les réponses sont rendues en Markdown**, ce qui compte dès qu'il y a des listes, du code ou une mise en forme.

Chaque utilisateur a son compte, son profil et son historique.

## Architecture

```
chat/
  models.py          utilisateurs, sessions, messages, cours
  views.py           vues Django et points d'entrée du chat
  migrations/        évolution du schéma
  static/js/         chat, téléversement, reconnaissance vocale, chargement
  static/css/        une feuille par écran
  templates/         les pages
```

Le modèle est Google Gemini, appelé via LangChain. Le stockage vectoriel est Chroma, l'extraction PDF passe par PyPDF.

## Mise en route

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

La clé Gemini se place dans un fichier `.env` :

```
GOOGLE_API_KEY=votre_clé
```

## Limites

Le découpage des documents est uniforme, sans tenir compte de leur structure. Sur un cours bien découpé en chapitres, un découpage guidé par les titres donnerait des passages plus cohérents et donc de meilleures réponses.

La reconnaissance vocale s'appuie sur l'API du navigateur : elle fonctionne bien sur Chrome, moins ailleurs, et demande une connexion.
