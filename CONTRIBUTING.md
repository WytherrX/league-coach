# Contribuer à League Coach

Merci de ton intérêt ! Les contributions les plus utiles :

- **Exercices et plans de lane** : plus concrets, mieux adaptés à un rôle ou à un elo.
- **Cibles** mieux calibrées, avec une source (statistiques par rang, par rôle).
- **Matchups d'un nouveau patch** au [format attendu](docs/coaching.md#importer-les-matchups-dun-nouveau-patch).
- **Corrections** de bugs, d'accessibilité ou d'affichage mobile.

Pour une fonctionnalité importante, ouvre d'abord une issue pour en discuter.

## Lancer l'appli en local

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cd app
SECRET_KEY=$(openssl rand -hex 32) COOKIE_SECURE=false DB_PATH=./dev.db uvicorn main:app --reload
```

Le code d'installation du premier compte s'affiche dans le terminal. Ajoute `RIOT_API_KEY=…` devant la commande pour tester l'import.

## Où se trouve chaque chose

| Fichier | Rôle |
| --- | --- |
| `app/main.py` | Routes, sessions, rendu des pages, icônes |
| `app/db.py` | Schéma SQLite, migrations, mots de passe (scrypt) |
| `app/analysis.py` | Rôles (indicateurs, cibles, exercices, plans de jeu), choix de l'objectif, counters, graphiques |
| `app/riot.py` | Client de l'API Riot et extraction des données d'une partie |
| `app/sync.py` | Synchronisation en tâche de fond |
| `app/data/` | Matchups par rôle et liste des champions |
| `app/templates/`, `app/static/` | Pages Jinja2 et feuille de style |

## Conventions

- **Simple d'abord** : Python standard, pages rendues côté serveur, pas de framework JavaScript ni de dépendance sans bonne raison.
- **Interface en français**, textes courts et concrets.
- **Migrations** dans `db.init()` : elles doivent être idempotentes et ne jamais perdre de données d'une base existante.
- **Sécurité** : requêtes SQL paramétrées, aucune donnée de l'utilisateur ni de Riot insérée sans échappement, formulaires en POST.

## Proposer une modification

1. Crée une branche depuis `main`.
2. Vérifie l'appli en local, sur ordinateur et sur mobile.
3. Ouvre une pull request qui explique le problème réglé et comment tu l'as vérifié.
