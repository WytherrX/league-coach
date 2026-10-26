# League Coach

Application web auto-hébergée pour progresser en jungle sur League of Legends :

- **Comptes** : plusieurs utilisateurs, chacun avec ses comptes LoL (Riot ID, rang, objectif).
- **Parties** : import automatique depuis l'API Riot (voir plus bas), ou saisie manuelle après chaque partie (KDA, morts avant 15 min, participation, CS/min, control wards, objectifs cédés, rang).
- **Points faibles** : indicateurs calculés sur les 10, 20 ou 50 dernières parties et comparés à des cibles.
- **Objectif par partie** : l'appli choisit un exercice concret sur ton point faible n° 1 et suit si tu l'as tenu.
- **Pool** : pour chaque champion, ton aisance de 1 à 5. Le nombre de parties et ton bilan viennent directement des parties enregistrées. Le pool est trié par aisance puis par nombre de parties.
- **Counters** : face à un jungler adverse, l'appli classe tes champions avec un score égal à la moyenne de trois sources (op.gg, u.gg, lolalytics), ajustée par ton historique sur le matchup, plus un bonus de maîtrise : de −4 à +3 points selon l'aisance, de 0 à +1 point selon les parties enregistrées. Elle indique si les sources sont d'accord et propose des bans pondérés par ton aisance.

Stack : Python 3.12, FastAPI, SQLite, pages rendues côté serveur. Un seul conteneur, un seul volume.

## Installation sur le serveur

```bash
# 1. Depuis ton PC : envoyer l'archive (scp direct vers /root est souvent refusé)
scp league-coach.zip user@serveur:/tmp/

# 2. Sur le serveur, en root (sudo -i) : extraire et configurer
cd /root && unzip -o /tmp/league-coach.zip
cd /root/league-coach
cp .env.example .env
sed -i "s/^SECRET_KEY=$/SECRET_KEY=$(openssl rand -hex 32)/" .env

# 3. Lancer
docker compose up -d --build
docker compose logs -f   # attendre "Application startup complete"
```

L'appli écoute sur le port **8085** du serveur.

## Nginx Proxy Manager

1. Chez ton registrar, crée une entrée DNS `coach.wytherrbastion.fr` vers l'IP du serveur, comme pour tes autres sous-domaines.
2. Dans Nginx Proxy Manager, ajoute un **Proxy Host** :
   - Domain Names : `coach.wytherrbastion.fr`
   - Scheme : `http`
   - Forward Hostname / IP : l'IP du serveur sur le réseau Docker ou le LAN (par exemple `172.17.0.1` ou `192.168.x.x`)
   - Forward Port : `8085`
   - Coche **Block Common Exploits**
3. Dans l'onglet **SSL** : demande un certificat Let's Encrypt, puis coche **Force SSL** et **HTTP/2 Support**.
4. Ouvre tout de suite `https://coach.wytherrbastion.fr/register` et crée ton compte. **Le premier compte créé devient administrateur, et les inscriptions se ferment ensuite** (sauf avec `ALLOW_SIGNUP=true`).

Si Nginx Proxy Manager tourne lui-même dans Docker, tu peux aussi éviter d'ouvrir le port 8085. Dans `docker-compose.yml`, remplace le bloc `ports` par le réseau de NPM :

```yaml
    networks: [npm]
networks:
  npm:
    external: true
    name: <nom du réseau de NPM>   # docker network ls
```

Dans NPM, utilise alors `league-coach` comme Forward Hostname et `8000` comme port.

## Variables (.env)

| Variable | Rôle |
| --- | --- |
| `SECRET_KEY` | Clé de signature des sessions, 32 caractères minimum. L'appli refuse de démarrer sans elle. |
| `ALLOW_SIGNUP` | `false` : seul le premier compte peut s'inscrire. `true` : inscriptions ouvertes pour tes amis. |
| `COOKIE_SECURE` | `true` derrière HTTPS. `false` seulement pour un test en `http://IP:8085`. |

Après modification : `docker compose up -d`.

## Import automatique des parties (API Riot)

Avec `RIOT_API_KEY` dans `.env`, l'appli importe toute seule tes parties classées solo/duo jouées en jungle. Elle le fait toutes les `SYNC_MINUTES` minutes (10 par défaut), à l'ajout d'un compte (50 dernières parties classées) et avec le bouton **Synchroniser** des pages Parties et Comptes.

| Champ | Calcul |
| --- | --- |
| Champion, jungler adverse, résultat, K/D/A | Résultat de la partie (Match-V5) |
| Participation aux kills, CS/min, control wards | Statistiques de fin de partie |
| Morts avant 15 min | Chronologie : tes morts avant 15:00 |
| Objectifs perdus sans combat | Chronologie : dragon, vague de larves, héraut, Baron ou Atakhan pris par l'adversaire, sans kill à moins de 3 000 unités du pit entre 30 s avant et 15 s après, et sans allié près du pit aux relevés de positions qui encadrent la prise (Riot en donne un par minute). Reste une estimation. |
| Rang et LP | League-V4, relevé à chaque synchronisation et reporté sur la dernière partie |
| LP gagnés ou perdus | Écart entre deux relevés, attribué à la partie seulement si une seule partie classée a été jouée entre les deux (compteur victoires + défaites de League-V4). Promotions et rétrogradations comprises. |

Le tableau de bord affiche l'évolution des LP sur les 60 dernières parties qui ont un rang, avec les divisions en fond et le détail de chaque partie au survol.

Les remakes et les parties hors jungle sont ignorés. Une partie déjà saisie à la main n'est pas dupliquée : la synchronisation la complète et garde ton objectif et ta leçon. Il te reste à indiquer pour chaque nouvelle partie si tu as tenu ton objectif, et une leçon (badge « À compléter »). Une partie importée que tu supprimes n'est pas réimportée.

La clé se demande sur developer.riotgames.com (Personal API Key). Une clé de développement fonctionne aussi, mais expire toutes les 24 heures : la page Parties affiche alors « Clé API Riot refusée ». Après un changement de clé : `docker compose up -d`.

Vérifier la clé depuis le serveur :

```bash
source .env && curl -s -H "X-Riot-Token: $RIOT_API_KEY" "https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/KingX/8992"
```

Une réponse contenant `"puuid"` signifie que la clé fonctionne.

## Mettre à jour les counters à chaque patch

Les winrates de matchups sont dans `app/data/matchups.json` : 59 junglers, Émeraude+, patch 26.21, collectés le 26/10/2026 sur trois sources.

| Source | Matchups | Remarque |
| --- | --- | --- |
| op.gg | 3 242 | Parties et victoires brutes |
| u.gg | 3 422 | Parties et victoires brutes |
| lolalytics | 2 837 | Masque les matchups sous 100 parties. Ses winrates surestiment d'environ 1,7 point le champion de la page : la moyenne des deux sens de lecture corrige ce biais. |

Pour chaque matchup, l'appli fait la moyenne des sources qui ont au moins 100 parties. Elle affiche « sources d'accord » quand l'écart entre elles reste sous 3 points.

Pour un nouveau patch, importe un nouveau fichier depuis la page **Admin**. Il est conservé dans le volume et prioritaire sur celui de l'image.

Format attendu :

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

`matchups[A][B] = [parties, victoires de A contre B]`. L'ancien format à une seule source (`"matchups"` à la racine) est toujours accepté.

## Reprise d'une installation « jungle-coach »

Docker nomme le volume d'après le dossier : `jungle-coach_jungle-coach-data` devient `league-coach_league-coach-data`. Pour garder tes comptes et tes parties :

```bash
cp /opt/jungle-coach/.env /root/league-coach/.env
cd /opt/jungle-coach && docker compose down
docker volume create league-coach_league-coach-data
docker run --rm -v jungle-coach_jungle-coach-data:/from -v league-coach_league-coach-data:/to alpine cp -a /from/. /to/
cd /root/league-coach && docker compose up -d --build
```

Au démarrage, l'appli renomme `jungle-coach.db` en `league-coach.db`. Il faudra te reconnecter une fois (cookie renommé). Une fois vérifié : `docker volume rm jungle-coach_jungle-coach-data` et `rm -r /opt/jungle-coach`.

## Mise à jour depuis une version précédente

Au démarrage, l'appli convertit automatiquement l'ancien pool : main → 5/5, secondaire → 3/5, situationnel → 2/5. Ajuste ensuite les niveaux d'aisance dans la page **Pool**.

## Sauvegarde

```bash
docker compose exec league-coach python -c "import sqlite3; sqlite3.connect('/data/league-coach.db').backup(sqlite3.connect('/data/backup.db'))"
docker compose cp league-coach:/data/backup.db ./league-coach-$(date +%F).db
```

## Mise à jour du code

Le code est sur GitHub. Sur le serveur :

```bash
cd /root/league-coach && git pull && docker compose up -d --build
```

`.env` et la base de données ne sont pas versionnés (`.gitignore`) : une mise à jour ne les touche jamais. Pour revenir à la version précédente : `git log --oneline` puis `git checkout <commit>` et `docker compose up -d --build`.
