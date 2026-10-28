# Sécurité

## Signaler une faille

Ouvre une [issue](https://github.com/WytherrX/league-coach/issues) **sans détails exploitables** et demande un contact privé, ou utilise le signalement privé de GitHub (onglet **Security**, puis **Report a vulnerability**) s'il est disponible.

Seule la dernière version de la branche `main` reçoit des correctifs.

## Protections en place

- **Mots de passe** hachés avec scrypt et un sel aléatoire, entre 10 et 128 caractères. Changement de mot de passe dans **Comptes**.
- **Premier compte** protégé par un code d'installation affiché dans les journaux du conteneur : personne ne peut prendre une instance mise en ligne avant ton inscription.
- **Connexion** bloquée 15 minutes après 10 échecs sur un identifiant ou 30 échecs depuis une même adresse IP. Les échecs sont journalisés (`docker compose logs | grep Échec`).
- **Sessions** dans un cookie signé `HttpOnly`, `Secure` et `SameSite=Lax`, valable 30 jours. Changer son mot de passe, ou cliquer sur **Déconnecter mes autres appareils**, invalide toutes les autres sessions. Changer `SECRET_KEY` déconnecte tout le monde.
- **CSRF** : tout envoi de formulaire dont l'en-tête `Origin` ou `Referer` désigne un autre site, y compris un autre sous-domaine, est refusé.
- **En-têtes** `Content-Security-Policy` (aucune ressource externe hors polices), `X-Frame-Options: DENY`, `X-Content-Type-Options` et `Referrer-Policy` sur toutes les réponses.
- **Données** : requêtes SQL paramétrées, affichage échappé, saisies bornées. Chaque compte et chaque partie sont rattachés à leur propriétaire.
- **Icônes** : le serveur ne télécharge que les icônes des champions connus, dans la version des données, et rejette tout ce qui n'est pas une image PNG. Il ne sert pas de proxy ouvert.
- **Conteneur** sans les droits root. La clé Riot ne quitte jamais le serveur.
