# League Coach

Application web auto-hébergée pour progresser sur League of Legends, **dans tous les rôles** : top, jungle, mid, ADC et support. Elle importe tes parties classées depuis l'API Riot, repère tes points faibles, te fixe un objectif concret pour la partie suivante et t'aide à choisir le bon counter en draft selon ton propre champion pool.

Interface en français, multi-utilisateur, un seul conteneur Docker.

## Fonctionnalités

- **Tous les rôles, sur un seul compte.** Chaque partie est rangée dans le rôle réellement joué, d'après le poste attribué par Riot : un autofill en top est compté, analysé et noté comme une partie de top. Chaque rôle a ses indicateurs, ses cibles, ses exercices, son champion pool et ses counters.
- **Tableau de bord par rôle** : un onglet « Tous » (LP, bilan, répartition des rôles, objectif de chaque rôle) et un onglet par rôle joué.
- **Import automatique des parties** via l'API officielle de Riot : KDA, participation aux kills, CS/min, control wards, morts avant 15 minutes, rang et LP gagnés ou perdus. En jungle, les objectifs perdus sans combat. En top, mid et ADC, le CS à 10 minutes, l'écart d'or à 15 minutes face à l'adversaire direct et la part des dégâts de l'équipe. En support, le score de vision par minute. La saisie manuelle reste possible sans clé API.
- **Points faibles** : indicateurs calculés sur les 10, 20 ou 50 dernières parties et comparés à des cibles de niveau Diamant.
- **Objectif par partie, un par rôle** : un exercice concret sur ton point faible principal dans ce rôle. Après la partie, tu notes si tu l'as tenu et une leçon ; le formulaire propose les exercices du rôle joué.
- **Évolution des LP** : courbe sur les dernières parties, avec les divisions en fond et le détail de chaque partie au survol.
- **Un champion pool par rôle** : ton aisance de 1 à 5 sur chaque champion. Le nombre de parties et le bilan viennent de tes parties dans ce rôle.
- **Counters** : face à ton adversaire direct, tes champions sont classés par un score combinant le winrate du matchup (moyenne d'op.gg, u.gg et lolalytics), ton bilan personnel sur ce matchup et ton aisance. L'aisance pèse peu (de −1,3 à +1 point) : elle départage les matchups proches sans faire oublier un mauvais matchup. Bans conseillés et meilleurs counters hors de ton pool.
- **Plusieurs comptes LoL par utilisateur**, plusieurs utilisateurs par instance. Le premier inscrit devient administrateur.

Stack : Python 3.12, FastAPI, Jinja2, SQLite. Pages rendues côté serveur, sans framework JavaScript.

## Prérequis

- Docker avec le plugin Compose.
- Facultatif, une clé API Riot pour l'import automatique (voir plus bas).
- Pour un accès depuis Internet, un reverse proxy en HTTPS : Nginx Proxy Manager, Caddy, Traefik ou équivalent.

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
| `SECRET_KEY` | *(obligatoire)* | Clé de signature des sessions, 32 caractères minimum. L'appli refuse de démarrer sans elle. |
| `ALLOW_SIGNUP` | `false` | `false` : seul le premier compte peut s'inscrire. `true` : inscriptions ouvertes. |
| `COOKIE_SECURE` | `true` | Cookie de session réservé au HTTPS. `false` uniquement pour un test en HTTP. |
| `BIND_IP` | `127.0.0.1` dans `.env.example` | Adresse de l'hôte sur laquelle le port est publié : `127.0.0.1` si le reverse proxy tourne sur l'hôte, l'IP du serveur s'il tourne dans Docker ou sur une autre machine. `0.0.0.0` (toutes les interfaces) est la valeur appliquée si la variable est absente. |
| `PORT` | `8085` | Port exposé sur l'hôte. |
| `FORWARDED_ALLOW_IPS` | réseaux privés | Proxys autorisés à transmettre l'IP réelle du visiteur (`X-Forwarded-For`). Mets l'IP de ton reverse proxy pour être strict. |
| `RIOT_API_KEY` | *(vide)* | Active l'import automatique des parties. Vide : saisie manuelle uniquement. |
| `SYNC_MINUTES` | `10` | Intervalle de synchronisation avec Riot, 5 minutes minimum. |
| `TZ` | `Europe/Paris` | Fuseau horaire utilisé pour dater les parties. |

Après une modification : `docker compose up -d`.

## Derrière un reverse proxy

L'appli lit les en-têtes `X-Forwarded-*` : elle fonctionne derrière n'importe quel reverse proxy qui termine le HTTPS.

Exemple avec **Nginx Proxy Manager** :

1. Crée une entrée DNS pour ton sous-domaine, par exemple `coach.example.com`, vers ton serveur.
2. Ajoute un **Proxy Host** : le domaine, le scheme `http`, l'IP de l'hôte Docker et le port `8085`. Si NPM tourne dans Docker, mets cette même IP dans `BIND_IP` : NPM ne peut pas joindre le `127.0.0.1` de l'hôte.
3. Dans l'onglet **SSL**, demande un certificat Let's Encrypt, puis coche **Force SSL** et **HTTP/2 Support**.

Si le reverse proxy tourne lui-même dans Docker, tu peux ne pas exposer de port. Remplace le bloc `ports` de `docker-compose.yml` par le réseau du proxy, puis cible `league-coach:8000` :

```yaml
    networks: [proxy]
networks:
  proxy:
    external: true
    name: <réseau du reverse proxy>   # docker network ls
```

## Import automatique (API Riot)

Demande une clé sur [developer.riotgames.com](https://developer.riotgames.com). Une **Personal API Key** convient à un usage personnel. Une clé de développement fonctionne aussi, mais expire toutes les 24 heures : la page Parties affiche alors « Clé API Riot refusée ».

Pour vérifier la clé, remplace `<pseudo>` et `<tag>` par ton Riot ID. Si ton compte est en Amérique ou en Asie, remplace aussi `europe` par `americas` ou `asia` :

```bash
source .env && curl -s -H "X-Riot-Token: $RIOT_API_KEY" "https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/<pseudo>/<tag>"
```

Une réponse contenant `"puuid"` confirme que la clé fonctionne.

L'appli synchronise chaque compte toutes les `SYNC_MINUTES` minutes et à l'ajout d'un compte, où elle importe les 50 dernières parties classées. Le bouton **Synchroniser** des pages Parties et Comptes lance aussi une synchronisation. Toutes les parties **classées solo/duo** sont importées, quel que soit le rôle : le poste attribué par Riot (`TOP`, `JUNGLE`, `MIDDLE`, `BOTTOM`, `UTILITY`) décide du rôle de la partie, et l'adversaire direct est le joueur du même poste en face. Les remakes sont ignorés.

| Donnée | Calcul |
| --- | --- |
| Champion, adversaire du même poste, résultat, K/D/A | Résultat de la partie (Match-V5) |
| Participation aux kills, CS/min, control wards | Statistiques de fin de partie |
| Morts avant 15 min | Chronologie de la partie |
| Objectifs perdus sans combat | Dragon, vague de larves, héraut, Baron ou Atakhan pris par l'adversaire, sans kill à moins de 3 000 unités du pit entre 30 s avant et 15 s après, et sans allié près du pit aux relevés de positions qui encadrent la prise (Riot en fournit un par minute). C'est une estimation. |
| CS à 10 min (top, mid, ADC) | Relevé de la chronologie à 10:00 : sbires et monstres tués |
| Écart d'or à 15 min (top, mid, ADC) | Relevé de la chronologie à 15:00 : ton or total moins celui de l'adversaire du même poste |
| Part des dégâts (mid, ADC) | `teamDamagePercentage` de Riot, ou tes dégâts aux champions divisés par ceux de ton équipe |
| Vision par minute (support) | `visionScore` de fin de partie divisé par la durée |
| Rang et LP | League-V4, relevé à chaque synchronisation |
| LP gagnés ou perdus | Écart entre deux relevés, attribué à une partie seulement si une seule partie classée a été jouée entre les deux. Promotions et rétrogradations comprises. |

Riot ne fournit pas l'historique des LP : les LP par partie et la courbe se remplissent à partir de l'installation.

Une partie déjà saisie à la main n'est pas dupliquée : l'import la complète et conserve l'objectif et la leçon. Une partie importée puis supprimée n'est pas réimportée. Les requêtes respectent les limites de débit d'une clé personnelle, soit 20 par seconde et 100 toutes les 2 minutes.

## Indicateurs et cibles par rôle

| Indicateur | Top | Jungle | Mid | ADC | Support |
| --- | --- | --- | --- | --- | --- |
| CS par minute | ≥ 7,5 | ≥ 6,5 | ≥ 7,5 | ≥ 8 | — |
| CS à 10 min | ≥ 75 | — | ≥ 75 | ≥ 80 | — |
| Écart d'or à 15 min | ≥ 0 | — | ≥ 0 | ≥ 0 | — |
| Morts par partie | ≤ 4,5 | ≤ 4,5 | ≤ 4,5 | ≤ 4 | ≤ 5 |
| Morts avant 15 min | ≤ 1 | ≤ 1,5 | ≤ 1 | ≤ 1 | ≤ 1,5 |
| Participation aux kills | ≥ 45 % | ≥ 60 % | ≥ 55 % | ≥ 50 % | ≥ 60 % |
| Part des dégâts de l'équipe | — | — | ≥ 25 % | ≥ 27 % | — |
| Score de vision par minute | — | — | — | — | ≥ 2,2 |
| Control wards | ≥ 1,5 | ≥ 2 | ≥ 1,5 | ≥ 1,5 | ≥ 3 |
| Objectifs perdus sans combat | — | ≤ 1 | — | — | — |
| Parties sur ton pool | ≥ 80 % | ≥ 80 % | ≥ 80 % | ≥ 80 % | ≥ 80 % |

Les cibles, les exercices et les plans de jeu sont dans [`app/analysis.py`](app/analysis.py) (`TOP`, `JUNGLE`, `MID`, `ADC`, `SUPPORT`).

## Données de counters

Les winrates de matchups sont dans `app/data`, un fichier par rôle, collectés sur trois sources pour les rangs Émeraude et plus, patch 26.21.

| Fichier | Champions | op.gg | u.gg | lolalytics |
| --- | --- | --- | --- | --- |
| [`matchups-top.json`](app/data/matchups-top.json) (top, toplaner contre toplaner) | 52 | 2 476 | 2 552 | 2 576 |
| [`matchups.json`](app/data/matchups.json) (jungle, jungler contre jungler) | 59 | 3 242 | 3 422 | 2 837 |
| [`matchups-mid.json`](app/data/matchups-mid.json) (mid, midlaner contre midlaner) | 42 | 1 688 | 1 708 | 1 716 |
| [`matchups-adc.json`](app/data/matchups-adc.json) (ADC, ADC contre ADC en bot) | 28 | 756 | 756 | 754 |
| [`matchups-support.json`](app/data/matchups-support.json) (support, support contre support) | 42 | 1 594 | 1 652 | 1 672 |

op.gg et u.gg donnent des parties et des victoires brutes. lolalytics masque les matchups sous 100 parties, et ses winrates surestiment d'environ 1,7 point le champion de la page, dans tous les rôles : la moyenne des deux sens de lecture corrige ce biais. Les ADC retenus sont ceux qu'u.gg compte au moins 800 fois face à Jinx en bot, ce qui inclut les picks bot hors ADC classiques (Ziggs, Veigar, Yasuo…). En top, mid et support, ce sont les champions joués au moins 10 000 fois dans le rôle sur u.gg. Une fois réunies, les trois sources sont très proches : corrélation de 0,91 à 0,96 entre elles, écart moyen de 0,6 à 1 point par matchup.

Pour chaque matchup, l'appli fait la moyenne des sources qui ont au moins 100 parties. Elle indique « sources d'accord » quand l'écart entre elles reste sous 3 points.

Pour un nouveau patch, un administrateur importe un fichier depuis la page **Admin**, en choisissant le rôle. Le fichier est conservé dans le volume de données et remplace celui du dépôt pour ce rôle. Format attendu :

```json
{
  "patch": "26.22", "tier": "Émeraude+", "collected": "2026-11-05", "ddragon": "16.22.1",
  "champions": { "viego": { "img": "Viego", "name": "Viego" } },
  "sources": {
    "opgg": { "label": "op.gg", "url": "https://op.gg", "matchups": { "viego": { "leesin": [3835, 1968] } } },
    "ugg":  { "label": "u.gg",  "url": "https://u.gg",  "matchups": { "viego": { "leesin": [4834, 2495] } } }
  }
}
```

`matchups[A][B] = [parties, victoires de A contre B]`. Les clés des champions sont le `championName` de Riot en minuscules : `monkeyking` pour Wukong, `khazix`, `belveth`…

## Sécurité

- **Mots de passe** hachés avec scrypt et un sel aléatoire, entre 10 et 128 caractères. Changement de mot de passe dans **Comptes**.
- **Connexion** bloquée 15 minutes après 10 échecs sur un identifiant ou 30 échecs depuis une même adresse IP. Les échecs sont journalisés (`docker compose logs | grep Échec`).
- **Sessions** dans un cookie signé `HttpOnly`, `Secure` et `SameSite=Lax`, valable 30 jours. Changer son mot de passe, ou cliquer sur **Déconnecter mes autres appareils**, invalide toutes les autres sessions. Changer `SECRET_KEY` déconnecte tout le monde.
- **CSRF** : tout envoi de formulaire dont l'en-tête `Origin` ou `Referer` désigne un autre site, y compris un autre sous-domaine, est refusé.
- **En-têtes** `Content-Security-Policy`, `X-Frame-Options: DENY`, `X-Content-Type-Options` et `Referrer-Policy` sur toutes les réponses.
- **Données** : requêtes SQL paramétrées, affichage échappé, saisies bornées. Chaque compte et chaque partie sont rattachés à leur propriétaire.
- **Conteneur** sans les droits root. La clé Riot ne quitte jamais le serveur.

Pour signaler une faille, ouvre une issue sur GitHub sans détails exploitables et demande un contact privé.

## Mise à jour

```bash
cd league-coach && git pull && docker compose up -d --build
```

Le schéma de la base est migré automatiquement au démarrage. Une base d'une version qui suivait un seul rôle par compte est convertie : les comptes ajoutés deux fois pour deux rôles sont fusionnés (parties, pools, objectifs), et la synchronisation suivante importe les parties jouées sur les autres rôles parmi les 50 dernières, sans réimporter celles que tu avais supprimées. `.env` et la base ne sont pas versionnés : une mise à jour ne les touche jamais. Pour revenir à une version précédente : `git log --oneline`, puis `git checkout <commit>` et `docker compose up -d --build`.

## Sauvegarde

Les données (base SQLite, matchups importés et icônes en cache) sont dans le volume Docker `league-coach_league-coach-data`.

```bash
docker compose exec league-coach python -c "import sqlite3; sqlite3.connect('/data/league-coach.db').backup(sqlite3.connect('/data/backup.db'))"
docker compose cp league-coach:/data/backup.db ./league-coach-$(date +%F).db
```

## Développement

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cd app
SECRET_KEY=$(openssl rand -hex 32) COOKIE_SECURE=false DB_PATH=./dev.db uvicorn main:app --reload
```

| Fichier | Rôle |
| --- | --- |
| `app/main.py` | Routes, sessions, rendu des pages |
| `app/db.py` | Schéma SQLite, migrations, mots de passe (scrypt) |
| `app/analysis.py` | Rôles (indicateurs, cibles, exercices, plans de jeu), counters, graphiques SVG |
| `app/riot.py` | Client de l'API Riot et extraction des données d'une partie |
| `app/sync.py` | Synchronisation en tâche de fond |
| `app/templates/`, `app/static/` | Pages Jinja2 et feuille de style |

## Licence

Code distribué sous licence [MIT](LICENSE) : tu peux l'utiliser, le modifier et le redistribuer librement, à condition de conserver la mention de copyright.

## Mentions

League Coach n'est ni approuvé ni soutenu par Riot Games et ne reflète pas les opinions de Riot Games ni de quiconque officiellement impliqué dans la production ou la gestion des propriétés de Riot Games. Riot Games et toutes les propriétés associées sont des marques commerciales ou des marques déposées de Riot Games, Inc.

Les winrates de matchups proviennent d'op.gg, u.gg et lolalytics. Les icônes de champions viennent du Data Dragon de Riot : le serveur les télécharge une fois (environ 4 Mo) et les sert lui-même, ce qui les affiche aussi derrière un proxy d'entreprise qui bloque les sites de jeux.
