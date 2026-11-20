# Lectio — Bible catholique

Lectio est une appli de lecture de la Bible catholique, à installer sur son téléphone :

- **la Bible en entier** (73 livres du canon catholique, deutérocanoniques compris) dans la traduction catholique d’Augustin Crampon (néo-Crampon Libre) ;
- pour chaque livre, une **présentation complète** : auteur et date, contexte, plan, grands thèmes, lecture chrétienne, passages clés, place dans la liturgie ;
- pour chaque chapitre, un lien vers la **traduction liturgique officielle** (AELF) ;
- un **fil de versets** à faire défiler et à aimer, et la page **Mes versets** ;
- le temps liturgique du jour (couleur, année A, B ou C, semaine du psautier).

## Installer l’appli

- **Android (Chrome)** : ouvrir le site, puis « Installer l’appli » (ou menu ⋮ › Installer l’application).
- **iPhone (Safari)** : ouvrir le site, puis Partager › Sur l’écran d’accueil. Utiliser ensuite Lectio depuis son icône.

L’appli fonctionne ensuite sans connexion.

## Vos versets et les mises à jour

Les versets aimés, l’endroit où l’on en est dans la Bible et dans le fil sont enregistrés **sur le téléphone uniquement** (rien n’est envoyé). Quand une nouvelle version est publiée ici, l’appli propose « Mettre à jour » : les versets et la progression sont conservés. Le code de sauvegarde (Mes versets › Sauvegarder ou transférer) permet de tout retrouver sur un autre appareil.

## Pour publier une nouvelle version

1. Modifier les fichiers, changer `BUILD` (dans `index.html` et `sw.js`, même valeur).
2. Publier sur la branche `main` : GitHub Pages met le site à jour, puis l’appli propose la mise à jour.

Règles à respecter pour ne jamais perdre les données des utilisateurs :

- ne jamais renommer ni vider la clé de stockage `lectio.state` (objet versionné, champ `v`) : une nouvelle version doit relire l’ancien format et le faire évoluer ;
- ne pas changer l’adresse du site (nom du dépôt) : le stockage est lié à l’adresse ;
- les fichiers de `data/` sont appelés avec une empreinte (`?v=…`) : en changer le contenu suffit, l’appli retélécharge seulement les fichiers modifiés.

## Sources et licences

- Texte biblique : **Sainte Bible néo-Crampon Libre**, traduction d’Augustin Crampon révisée, © 2022 Fraternité de Tibériade, licence [Creative Commons BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/deed.fr), texte obtenu sur eBible.org. Modifications : mise en page, séparation des intertitres, correction de quelques coquilles typographiques. Ces modifications n’engagent pas la Fraternité de Tibériade ; le texte biblique de l’appli reste sous licence CC BY-SA 4.0.
- Traduction liturgique officielle : [AELF](https://www.aelf.org) (non reproduite, liens uniquement).
- Les présentations des livres, les plans et les méditations ont été rédigés pour cette appli ; ce ne sont pas des documents officiels de l’Église.
