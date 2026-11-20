# Lectio — Bible catholique

**Ouvrir l’appli : https://nthfv.github.io/lectio/**

Propriétaire : **nthfv** (© 2026) — voir [LICENSE.md](LICENSE.md).

Lectio est une appli de lecture de la Bible catholique, à installer sur son téléphone :

- **la Bible en entier** (73 livres du canon catholique, deutérocanoniques compris) dans la traduction catholique d’Augustin Crampon (néo-Crampon Libre) ;
- pour chaque livre, une **présentation complète** : auteur et date, contexte, plan, grands thèmes, lecture chrétienne, passages clés, place dans la liturgie ;
- pour chaque chapitre, un lien vers la **traduction liturgique officielle** (AELF) ;
- un **fil de versets** à faire défiler et à aimer, et la page **Mes versets** ;
- la **messe du jour** : lectures (dans la Bible Crampon, avec le lien vers le texte officiel AELF), fêtes et mémoires des saints du calendrier pour la France ;
- le temps liturgique du jour (couleur, année A, B ou C, semaine du psautier) ;
- des **comptes** (nom d’utilisateur ou e-mail + mot de passe) pour retrouver ses versets et sa progression sur un autre téléphone.

## Installer l’appli

- **Android (Chrome)** : ouvrir le site, puis « Installer l’appli » (ou menu ⋮ › Installer l’application).
- **iPhone (Safari)** : ouvrir le site, puis Partager › Sur l’écran d’accueil. Utiliser ensuite Lectio depuis son icône.

L’appli fonctionne ensuite sans connexion.

## Vos versets et les mises à jour

Les versets aimés, l’endroit où l’on en est dans la Bible et dans le fil sont enregistrés **sur le téléphone**. Sans compte, rien n’est envoyé. Avec un compte (Mon compte, en haut à droite), une copie est gardée en ligne et synchronisée : on la retrouve en se connectant sur un autre téléphone. Quand une nouvelle version est publiée ici, l’appli propose « Mettre à jour » : les versets et la progression sont conservés. Le code de sauvegarde (Mes versets › Sauvegarder ou transférer) permet de tout retrouver sur un autre appareil.

## Pour publier une nouvelle version

1. Récupérer d’abord la dernière version du dépôt (`git pull`) : chaque semaine, GitHub y ajoute seul les nouvelles lectures de la messe.
2. Modifier les fichiers (l’appli tient dans `index.html` ; les textes sont dans `data/`).
3. Lancer `python3 outils/nouvelle-version.py` : nouveau numéro de version dans `index.html` et `sw.js`, et nouvelles empreintes des fichiers de `data/`.
4. Publier sur la branche `main` : GitHub Pages met le site à jour en une minute environ, puis l’appli installée propose « Mettre à jour ».

Règles à respecter pour ne jamais perdre les données des utilisateurs :

- ne jamais renommer ni vider la clé de stockage `lectio.state` (objet versionné, champ `v`) : une nouvelle version doit relire l’ancien format et le faire évoluer ;
- ne pas changer l’adresse du site (nom du dépôt) : le stockage est lié à l’adresse ;
- toujours lancer `outils/nouvelle-version.py` avant de publier : sans nouvelle empreinte, un fichier de `data/` modifié ne serait pas retéléchargé par les téléphones.

## Comptes (Firebase)

- Projet Firebase **lectio-72d94** (compte Google nthfv4141), base Firestore à Paris (europe-west9), connexion par e-mail ou nom d’utilisateur + mot de passe.
- Un nom d’utilisateur devient une adresse interne `nom@nthfv.github.io` (jamais utilisée pour écrire) ; seuls les comptes par e-mail peuvent réinitialiser leur mot de passe.
- Chaque compte a un seul document `comptes/{uid}` : `etat` (versets aimés et retirés, endroit de lecture, position dans le fil). Règles de sécurité : chacun ne lit et n’écrit que le sien. La fusion garde, pour chaque verset, la décision la plus récente.
- La clé web Firebase présente dans `index.html` est publique par nature ; la protection vient des règles de sécurité.

## Lectures de la messe (mises à jour automatiques)

Chaque lundi, `.github/workflows/lectionnaire.yml` lance `outils/lectionnaire.py`, qui ajoute à `data/lectionnaire.json` les jours que l’AELF vient de publier (calendrier pour la France) : références des lectures et noms des célébrations uniquement, chacune reliée au texte Crampon et vérifiée. L’appli reçoit ces nouvelles dates sans mise à jour à installer. Pour revérifier le fichier sans réseau : `python3 outils/lectionnaire.py --verifier`.

Pour contrôler que chaque lecture affichée correspond bien au passage lu à la messe : onglet **Actions › Vérification des lectures › Run workflow** (`outils/verifier-lectures.py` compare chaque passage Crampon au texte officiel de l’AELF, sans le recopier, et signale les décalages de numérotation). Les correspondances de numérotation déjà contrôlées (Siracide, Tobie, Judith, Esther) sont dans `VMAP`, au début de `outils/lectionnaire.py` ; `outils/correspondances.py` aide à en établir de nouvelles.

## Sources et licences

- Texte biblique : **Sainte Bible néo-Crampon Libre**, traduction d’Augustin Crampon révisée, © 2022 Fraternité de Tibériade, licence [Creative Commons BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/deed.fr), texte obtenu sur eBible.org. Modifications : mise en page, séparation des intertitres, correction de quelques coquilles typographiques, remarques de l’éditeur imprimées dans le corps du texte (Dn 3, 23 et 90 ; Dn 12, 13 ; 2 S 13, 21 ; 1 Ch 11, 46) placées dans les notes. Ces modifications n’engagent pas la Fraternité de Tibériade ; le texte biblique de l’appli reste sous licence CC BY-SA 4.0.
- Traduction liturgique officielle : [AELF](https://www.aelf.org) (non reproduite, liens uniquement).
- Les présentations des livres, les plans et les méditations ont été rédigés pour cette appli ; ce ne sont pas des documents officiels de l’Église.
