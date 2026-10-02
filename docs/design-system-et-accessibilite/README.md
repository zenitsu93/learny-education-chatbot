# Design system et accessibilité

Audit d'accessibilité du front actuel et trois directions complètes pour la refonte de Learny.

**Décision du 2 octobre 2026 : le concept A « Tableau » est retenu.**

Ouvrir [`index.html`](index.html) dans un navigateur. La page contient :

- l'audit WCAG 2.2 AA du code actuel : 19 problèmes, dont 5 critiques, avec fichier, ligne et correction, et les contrastes mesurés ;
- la recherche utilisateurs sous l'angle de l'accessibilité : contraintes de contexte, personas, parcours, plan d'étude et guide d'entretien ;
- trois concepts de design system interactifs, chacun en clair et en sombre : A « Tableau » (recommandé), B « Faso », C « Clair » ;
- pour chaque concept : couleurs avec contrastes calculés en direct, typographie, espacements, rayons, élévation, 21 animations et leur version réduite, plus de 40 composants dans tous leurs états, six écrans et la UX copy dans sa voix ;
- un inventaire « zéro comportement par défaut » de 32 éléments natifs du navigateur ;
- la comparaison des trois concepts ;
- la stack front, alignée sur [`../conception-personas-et-stack`](../conception-personas-et-stack) : Django, htmx, Alpine.js et django-cotton sur o2switch.

Les personas et le parcours sont des hypothèses à valider ; les constats d'audit et les contrastes viennent du code.
