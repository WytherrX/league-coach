# Installation et configuration

[← Retour au README](../README.md)

- [Prérequis](#prérequis)
- [Installation](#installation)
- [Configuration (`.env`)](#configuration-env)
- [Derrière un reverse proxy](#derrière-un-reverse-proxy)
- [Mise à jour](#mise-à-jour)
- [Sauvegarde](#sauvegarde)

## Prérequis

- Docker avec le plugin Compose.
- Facultatif mais recommandé : une clé API Riot pour l'import automatique ([Import Riot](import-riot.md)).
- Pour un accès depuis Internet : un reverse proxy en HTTPS (Nginx Proxy Manager, Caddy, Traefik ou équivalent).

Ressources : un seul conteneur Python, moins de 100 Mo de mémoire. La base SQLite et le cache d'icônes tiennent en quelques Mo.

## Installation

```bash
git clone https://github.com/WytherrX/league-coach.git
cd league-coach
cp .env.example .env
sed -i "s/^SECRET_KEY=$/SECRET_KEY=$(openssl rand -hex 32)/" .env
nano .env    # ajouter RIOT_API_KEY, ajuster BIND_IP, PORT, TZ…
docker compose up -d --build
docker compose logs | grep installation
```

La dernière commande affiche un **code d'installation**. Ouvre `/register` et crée ton compte avec ce code : **le premier compte devient administrateur, et les inscriptions se ferment ensuite**, sauf avec `ALLOW_SIGNUP=true`. Le code empêche quelqu'un d'autre de prendre l'instance si elle est en ligne avant que tu aies créé ton compte. Il change à chaque redémarrage tant qu'aucun compte n'existe.

Par défaut, l'appli n'écoute que sur `127.0.0.1:8085` (voir `BIND_IP` et `PORT`). Pour un premier essai en HTTP depuis une autre machine, mets `BIND_IP=0.0.0.0` et `COOKIE_SECURE=false`, sinon la connexion ne tiendra pas.

## Configuration (`.env`)

| Variable | Défaut | Rôle |
| --- | --- | --- |
| `SECRET_KEY` | *(obligatoire)* | Clé de signature des sessions, 32 caractères minimum. L'appli refuse de démarrer sans elle. La changer déconnecte tout le monde. |
| `ALLOW_SIGNUP` | `false` | `false` : seul le premier compte peut s'inscrire. `true` : inscriptions ouvertes. |
| `COOKIE_SECURE` | `true` | Cookie de session réservé au HTTPS. `false` uniquement pour un test en HTTP. |
| `BIND_IP` | `127.0.0.1` dans `.env.example` | Adresse de l'hôte sur laquelle le port est publié : `127.0.0.1` si le reverse proxy tourne sur l'hôte, l'IP du serveur s'il tourne dans Docker ou sur une autre machine. `0.0.0.0` (toutes les interfaces) est la valeur appliquée si la variable est absente. |
| `PORT` | `8085` | Port exposé sur l'hôte. |
| `FORWARDED_ALLOW_IPS` | réseaux privés | Proxys autorisés à transmettre l'IP réelle du visiteur (`X-Forwarded-For`). Mets l'IP de ton reverse proxy pour être strict. |
| `RIOT_API_KEY` | *(vide)* | Active l'import automatique des parties. Vide : saisie manuelle uniquement. |
| `SYNC_MINUTES` | `10` | Intervalle de synchronisation avec Riot, 5 minutes minimum. |
| `TZ` | `Europe/Paris` | Fuseau horaire utilisé pour dater les parties. |

Après une modification : `docker compose up -d`.

Le serveur doit pouvoir joindre `*.api.riotgames.com` (import des parties) et `ddragon.leagueoflegends.com` (icônes des champions). Les navigateurs, eux, ne contactent que League Coach : les icônes s'affichent même derrière un proxy d'entreprise qui bloque les sites de jeux.

## Derrière un reverse proxy

L'appli lit les en-têtes `X-Forwarded-*` : elle fonctionne derrière n'importe quel reverse proxy qui termine le HTTPS.

Exemple avec **Nginx Proxy Manager** :

1. Crée une entrée DNS pour ton sous-domaine, par exemple `coach.example.com`, vers ton serveur.
2. Ajoute un **Proxy Host** : le domaine, le scheme `http`, l'IP de l'hôte Docker et le port `8085`. Si NPM tourne dans Docker, mets cette même IP dans `BIND_IP` : NPM ne peut pas joindre le `127.0.0.1` de l'hôte.
3. Dans l'onglet **SSL**, demande un certificat Let's Encrypt, puis coche **Force SSL** et **HTTP/2 Support**.

Avec **Caddy** :

```caddy
coach.example.com {
    reverse_proxy 127.0.0.1:8085
}
```

Si le reverse proxy tourne lui-même dans Docker, tu peux ne pas exposer de port. Remplace le bloc `ports` de `docker-compose.yml` par le réseau du proxy, puis cible `league-coach:8000` :

```yaml
    networks: [proxy]
networks:
  proxy:
    external: true
    name: <réseau du reverse proxy>   # docker network ls
```

## Mise à jour

```bash
cd league-coach && git pull && docker compose up -d --build
```

Le schéma de la base est migré automatiquement au démarrage. `.env` et la base ne sont pas versionnés : une mise à jour ne les touche jamais.

Une base d'une ancienne version, qui suivait un seul rôle par compte, est convertie : les comptes ajoutés deux fois pour deux rôles sont fusionnés (parties, pools, objectifs), et la synchronisation suivante importe les parties jouées sur les autres rôles parmi les 50 dernières, sans réimporter celles que tu avais supprimées.

Pour revenir à une version précédente : `git log --oneline`, puis `git checkout <commit>` et `docker compose up -d --build`.

## Sauvegarde

Les données (base SQLite, matchups importés et icônes en cache) sont dans le volume Docker `league-coach_league-coach-data`.

```bash
docker compose exec league-coach python -c "import sqlite3; sqlite3.connect('/data/league-coach.db').backup(sqlite3.connect('/data/backup.db'))"
docker compose cp league-coach:/data/backup.db ./league-coach-$(date +%F).db
```
