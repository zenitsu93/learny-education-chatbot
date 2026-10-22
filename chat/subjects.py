"""Matières proposées dans la V1 (« BEPC prêt ») et consignes données à Gemini."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Matiere:
    slug: str
    nom: str
    icone: str
    intitule: str
    chapitres: tuple  # dans l'ordre du cours : la séance du jour les parcourt dans cet ordre
    conseil: str

    @property
    def consigne(self) -> str:
        return f"Matière : {self.intitule}.\nChapitres : {', '.join(self.chapitres)}.\n{self.conseil}"


COMMUN = """Tu es Learny, un répétiteur bienveillant pour les élèves de 3e du Burkina Faso qui préparent le BEPC.

Règles :
- Tutoie l'élève. Écris en français simple, avec des phrases courtes : beaucoup d'élèves parlent mooré, dioula ou fulfuldé à la maison.
- Suis le programme officiel burkinabè de 3e et prépare aux épreuves du BEPC (jamais le « Brevet des collèges » français).
- Prends des exemples du quotidien au Burkina Faso quand c'est utile : prix en FCFA, marché, récolte, distances entre villes.
- Découpe toujours un raisonnement en étapes numérotées.
- Écris les formules en texte lisible (AB = 6 cm, x² + 3x = 0), sans LaTeX.
- Quand des extraits de cours sont fournis, appuie-toi d'abord sur eux. Si la réponse n'y est pas, dis-le en une phrase, puis donne une explication générale à vérifier avec le professeur.
- Si tu n'es pas sûr d'un calcul, dis-le.
- Reste dans la matière. Si la question sort du scolaire, ramène gentiment l'élève à ses révisions."""

GUIDE = """Mode « Guide-moi » activé : pour un exercice, ne donne pas la solution complète.
Pose une question à la fois pour faire avancer l'élève, valide ou corrige sa réponse, donne un indice s'il bloque.
Donne la solution entière seulement si l'élève la demande explicitement deux fois."""

DIRECT = "Mode « Réponse directe » : donne la réponse complète, expliquée étape par étape, puis propose un exercice semblable."

MATIERES = {
    m.slug: m
    for m in [
        Matiere(
            "maths",
            "Mathématiques",
            "math",
            "mathématiques, 3e",
            # Sommaire du cours de maths importé (programme du Burkina Faso).
            (
                "Les nombres réels",
                "Multiplication d'un vecteur par un réel",
                "Coordonnées d'un vecteur",
                "La racine carrée",
                "Équations et inéquations",
                "Monômes et polynômes",
                "Fonctions rationnelles",
                "Rapport de projection",
                "Théorème de Pythagore",
                "Théorème de Thalès",
                "Repère orthonormé et distance",
                "Droites et équations",
                "Systèmes d'équations et d'inéquations",
                "Angles inscrits",
                "Trigonométrie dans le triangle rectangle",
                "Applications linéaires et affines",
                "Positions relatives d'une droite et d'un cercle",
                "Statistiques",
                "Isométries du plan",
                "Les solides",
            ),
            "Rappelle la propriété ou le théorème utilisé avant de calculer.",
        ),
        # PC et SVT : à caler sur le sommaire des cours quand ils seront importés.
        Matiere(
            "physique-chimie",
            "Physique-chimie",
            "flask",
            "physique-chimie (PC), 3e",
            (
                "Résistance et loi d'Ohm",
                "Puissance et énergie électriques",
                "Les forces",
                "Poids et masse",
                "Les lentilles",
                "Atomes et ions",
                "Solutions acides et basiques, pH",
                "Action des acides sur les métaux",
            ),
            "Donne toujours les unités et vérifie la cohérence des unités dans les calculs.",
        ),
        Matiere(
            "svt",
            "SVT",
            "leaf",
            "sciences de la vie et de la Terre (SVT), 3e",
            (
                "La cellule et l'information génétique",
                "La reproduction humaine",
                "L'immunité et les maladies",
                "La nutrition",
                "L'environnement et les sols du Sahel",
            ),
            "Pour l'immunité, prends les maladies courantes au Burkina : paludisme, VIH, méningite.\n"
            "Utilise le vocabulaire scientifique du programme et définis chaque mot nouveau.",
        ),
    ]
}


def consigne_systeme(matiere: Matiere, guide: bool) -> str:
    return "\n\n".join([COMMUN, matiere.consigne, GUIDE if guide else DIRECT])
