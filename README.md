# MarketDesk — offres publiques

Site statique consacré aux stages, VIE et programmes graduate en finance de marché.
GitHub Pages sert uniquement les fichiers HTML/CSS/JS, logos PNG et offres publiques.
La collecte Python s'exécute toutes les deux heures de 6 h 07 à 2 h 07 le lendemain,
en Europe/Paris (6, 8, 10, 12, 14, 16, 18, 20, 22, 0 et 2 h 07).
Elle couvre les journées parisienne et américaine, indépendamment du PC.
Les horaires peuvent subir des retards.

## Sécurité

- Aucun compte, CV, contact, suivi de candidature, outil IA ou clé IA dans ce dépôt.
- Aucun fichier `.env`, historique Git du projet principal ou base utilisateur transféré.
- Aucune clé IA. Les seuls paramètres privés nécessaires sont les paramètres SMTP
  et les adresses, chiffrés dans l'environnement GitHub `email-alerts`, limité à
  la branche `main`. Ils ne sont fournis qu'à l'étape d'envoi, après publication.
- Le collecteur, le site public et les artefacts de publication ne reçoivent pas
  ces secrets. Les jetons temporaires GitHub sont gérés par la plateforme.
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
Le bouton « Recharger » ouvre la page du workflow GitHub. Le propriétaire se
connecte à GitHub et confirme « Run workflow ». Ce passage est nécessaire :
aucun jeton d'écriture n'est intégré au site public. Le site lit ensuite les
métadonnées publiques de l'exécution, une fois par minute pendant 30 minutes au
maximum, et recharge les offres après une publication réussie. Une erreur de
suivi n'interrompt pas la collecte GitHub. Les données affichées restent disponibles.
Une collecte manuelle contourne les caches des sources ; les collectes planifiées
conservent leurs délais de cache pour éviter de surcharger les sites carrières.
Certaines sources peuvent refuser les IP des centres de données : l'état affiché
signale les indisponibilités et le cache conserve les offres précédentes.
Une collecte sans aucune offre bloque la publication et conserve l'ancien site.

## Alertes email

Après chaque publication réussie (planifiée ou manuelle), une étape séparée compare
les offres à l'historique des alertes. Elle envoie un seul récapitulatif s'il y a
de nouvelles offres employeurs et aucun mail sinon. Les liens issus uniquement
du sitemap JobTeaser, dont l'ouverture n'est pas confirmée, ne déclenchent pas
d'alerte. Le même poste retrouvé chez une autre source n'est pas renvoyé.

L'historique durable est conservé sur la branche `notification-state`. Il contient
uniquement des empreintes SHA-256 d'offres publiques et une date, jamais d'adresse,
de mot de passe ou de profil. Cette branche ne déclenche pas de collecte. En cas
de réinitialisation de cet historique, la première exécution établit une référence
silencieuse pour éviter l'envoi massif d'anciennes offres.

L'envoi utilise SMTP avec TLS vérifié. Une erreur de mail reste visible dans le
job `notify`, mais ne retire pas le site publié. Les offres ne sont enregistrées
comme notifiées qu'après acceptation du message par le serveur SMTP ; un refus
d'envoi peut donc être retenté à la mise à jour suivante. Une interruption entre
l'acceptation SMTP et l'enregistrement peut exceptionnellement causer un doublon.

Le lancement manuel peut cocher « Envoyer un mail de test » pour vérifier la
configuration sans marquer d'offre comme notifiée.

L'envoi reste désactivé tant que la variable GitHub `EMAIL_ALERTS_ENABLED` n'est
pas définie à `true`. Ne l'activer qu'après avoir configuré les sept secrets SMTP
dans l'environnement `email-alerts`, limité à `main`, et initialisé la branche
`notification-state`. Les valeurs doivent être chiffrées avec la clé publique
GitHub avant leur transfert. Ne jamais les placer dans le code ou les artefacts.

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

La barre de tri sous les filtres propose Pertinence et Publication récente.
Les deux choix sont exclusifs et accessibles au clavier. Les fichiers CSS et JS
portent une version calculée sur leur contenu pour éviter les mélanges de versions
dans le cache du navigateur.
