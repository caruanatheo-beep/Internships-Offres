# MarketDesk — offres publiques

Site statique consacré aux stages, VIE et programmes graduate en finance de marché.
GitHub Pages sert uniquement les fichiers HTML/CSS/JS, logos PNG et offres publiques.
La collecte Python s'exécute dans GitHub Actions à 8 h 07, 13 h 07 et 18 h 07
Europe/Paris. Elle reste indépendante du PC. Les horaires peuvent subir des retards.

## Sécurité

- Aucun compte, CV, contact, suivi de candidature, outil IA ou clé IA dans ce dépôt.
- Aucun fichier `.env`, historique Git du projet principal ou base utilisateur transféré.
- Aucun secret à ajouter dans GitHub Actions : le jeton temporaire GitHub de
  publication est géré par la plateforme, dans un job distinct de la collecte.
- Actions officielles épinglées par SHA ; aucun workflow de pull request privilégié.
- Le job de collecte n'a pas de droit d'écriture sur le dépôt et ne conserve pas
  les identifiants Git dans sa copie de travail.
- Publication limitée au répertoire `_site` construit depuis une liste explicite.
- Contrôle des motifs de clés et des variables secrètes avant l'export, validation
  des liens HTTPS, affichage des textes via `textContent`, politique CSP restrictive.
- Les descriptions, erreurs brutes et diagnostics internes ne sont pas publiés.
- Les données des offres sont publiques. Aucun faux écran de connexion ne protège
  ce site : les données personnelles restent dans l'application locale.

## Mise en service

Dans Settings → Pages, choisir « GitHub Actions ». Activer HTTPS. Le workflow
« Collect and publish public offers » peut être lancé manuellement depuis Actions.
Il n'utilise que des endpoints publics et un navigateur sans interface.
Certaines sources peuvent refuser les IP des centres de données : l'état affiché
signale les indisponibilités et le cache conserve les offres précédentes.
Une collecte sans aucune offre bloque la publication et conserve l'ancien site.

GitHub peut désactiver les horaires après 60 jours sans activité sur un dépôt
public. Vérifier périodiquement l'onglet Actions et réactiver le workflow au besoin.
Les caches GitHub peuvent être évincés ; `public_seed.json` constitue une base
initiale publique, pas une garantie de fraîcheur. La date affichée fait foi.

## Développement

`python scripts/build_internships_pages.py --collect --output _site`

Le répertoire de sortie doit être vide. Pour une prévisualisation hors ligne,
préparer un cache d'offres publiques puis omettre `--collect`.
Les critères géographiques et les dates de début sont calculés par le collecteur
existant. La pertinence suit son classement ; recherche et filtres s'appliquent
instantanément dans le navigateur. Aucun appel réseau n'est requis pour filtrer.
