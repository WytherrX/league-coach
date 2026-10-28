# Import Riot

[← Retour au README](../README.md)

League Coach lit tes parties classées solo/duo avec l'API officielle de Riot (Account-V1, Match-V5 et League-V4). Sans clé, l'appli fonctionne en saisie manuelle.

## Obtenir et vérifier une clé

Demande une clé sur [developer.riotgames.com](https://developer.riotgames.com). Une **Personal API Key** convient à un usage personnel. Une clé de développement fonctionne aussi, mais expire toutes les 24 heures : la page Parties affiche alors « Clé API Riot refusée ».

Mets-la dans `.env` (`RIOT_API_KEY=RGAPI-…`), puis `docker compose up -d`. Elle ne quitte jamais le serveur.

Pour la vérifier, remplace `<pseudo>` et `<tag>` par ton Riot ID. Si ton compte est en Amérique ou en Asie, remplace aussi `europe` par `americas` ou `asia` :

```bash
source .env && curl -s -H "X-Riot-Token: $RIOT_API_KEY" "https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/<pseudo>/<tag>"
```

Une réponse contenant `"puuid"` confirme que la clé fonctionne.

## Synchronisation

- À l'ajout d'un compte, l'appli importe les **50 dernières parties classées**, puis vérifie les nouvelles toutes les `SYNC_MINUTES` minutes (10 par défaut).
- Le bouton **Synchroniser** des pages Parties et Comptes lance une synchronisation immédiate.
- **Tous les rôles sont importés.** Le poste attribué par Riot (`TOP`, `JUNGLE`, `MIDDLE`, `BOTTOM`, `UTILITY`) décide du rôle de la partie, et l'adversaire direct est le joueur du même poste en face.
- Les remakes sont ignorés. Une partie importée puis supprimée n'est pas réimportée.
- Une partie déjà saisie à la main n'est pas dupliquée : l'import la complète et conserve ton objectif et ta leçon.
- Les requêtes respectent les limites d'une clé personnelle : 20 par seconde et 100 toutes les 2 minutes. Une première synchronisation de 50 parties prend environ 2 minutes.

## Données importées

| Donnée | Calcul |
| --- | --- |
| Champion, adversaire du même poste, résultat, K/D/A | Résultat de la partie (Match-V5) |
| Participation aux kills, CS/min, control wards | Statistiques de fin de partie |
| Morts avant 15 min | Chronologie de la partie |
| Objectifs perdus sans combat (jungle) | Dragon, vague de larves, héraut, Baron ou Atakhan pris par l'adversaire, sans kill à moins de 3 000 unités du pit entre 30 s avant et 15 s après, et sans allié près du pit aux relevés de positions qui encadrent la prise (Riot en fournit un par minute). C'est une estimation. |
| CS à 10 min (top, mid, ADC) | Relevé de la chronologie à 10:00 : sbires et monstres tués |
| Écart d'or à 15 min (top, mid, ADC) | Relevé de la chronologie à 15:00 : ton or total moins celui de l'adversaire du même poste |
| Part des dégâts (mid, ADC) | `teamDamagePercentage` de Riot, ou tes dégâts aux champions divisés par ceux de ton équipe |
| Vision par minute (support) | `visionScore` de fin de partie divisé par la durée |
| Rang et LP | League-V4, relevé à chaque synchronisation |

## LP par partie

Riot ne fournit pas l'historique des LP : l'appli relève ton rang à chaque synchronisation et attribue l'écart à une partie **seulement si une seule partie classée a été jouée entre deux relevés**. Promotions et rétrogradations sont comprises.

Le classement (League-V4) et l'historique (Match-V5) ne se mettent pas à jour au même moment : l'appli n'avance son relevé que lorsque les deux montrent la même nouvelle partie. La courbe des LP se remplit donc à partir de l'installation.
