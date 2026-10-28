# Coaching et counters

[← Retour au README](../README.md)

- [Indicateurs et cibles par rôle](#indicateurs-et-cibles-par-rôle)
- [Choix de l'objectif](#choix-de-lobjectif)
- [Calcul des counters](#calcul-des-counters)
- [Données de matchups](#données-de-matchups)
- [Importer les matchups d'un nouveau patch](#importer-les-matchups-dun-nouveau-patch)

## Indicateurs et cibles par rôle

Les indicateurs sont calculés sur les 10, 20 ou 50 dernières parties du rôle et comparés à des cibles de niveau Diamant.

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

Chaque indicateur a aussi un seuil d'alerte : au-delà de la cible, il est « OK », entre la cible et le seuil « Proche », en dessous « À travailler ».

Les cibles, les seuils, les exercices et les plans de lane sont dans [`app/analysis.py`](../app/analysis.py) (`TOP`, `JUNGLE`, `MID`, `ADC`, `SUPPORT`).

## Choix de l'objectif

1. Les indicateurs du rôle sont triés : « À travailler » d'abord, puis « Proche », chacun par écart relatif à la cible.
2. Le premier donne la catégorie d'exercices. Si tout est dans les cibles, l'appli propose de travailler la fin de partie.
3. Dans cette catégorie, l'appli choisit un exercice **pas encore maîtrisé** (tenu dans au moins 70 % d'au moins 3 parties), puis le moins travaillé.

Après chaque partie, tu indiques si tu as tenu l'objectif. Le tableau **Suivi des objectifs** montre ton taux de réussite par exercice.

## Calcul des counters

Face à ton adversaire direct, chaque champion de ton pool reçoit un score :

```
score = winrate du matchup, corrigé par ton bilan + bonus d'aisance
```

**Winrate du matchup.** Moyenne des sources qui ont au moins 100 parties sur ce matchup. L'appli indique « sources d'accord » quand l'écart entre elles reste sous 3 points.

**Correction par ton bilan.** Tes parties sur ce matchup comptent face à l'équivalent de 15 parties au winrate des sites :

```
(tes victoires + winrate × 15) / (tes parties + 15)
```

**Bonus d'aisance.** Volontairement petit : face à un même adversaire, deux champions du même rôle n'ont en général que 2 à 3 points d'écart de matchup. L'aisance départage les matchups proches sans faire oublier un mauvais matchup.

| Aisance | 5/5 Main | 4/5 Très à l'aise | 3/5 À l'aise | 2/5 Correct | 1/5 En apprentissage |
| --- | :---: | :---: | :---: | :---: | :---: |
| Bonus | +1 pt | +0,5 pt | 0 | −0,7 pt | −1,3 pt |

Le premier du classement est conseillé, les suivants sont « Jouable » à partir d'un score de 49, « Évite » en dessous.

**Bans conseillés.** Les trois adversaires contre lesquels ton pool fait le pire winrate moyen, pondéré par ton aisance sur chaque champion (matchups d'au moins 150 parties).

**Meilleurs counters hors de ton pool.** Au moins 2 sources et 200 parties, classés sur la source la plus pessimiste : utile pour choisir un futur champion situationnel.

## Données de matchups

Un fichier par rôle dans [`app/data`](../app/data), collecté sur op.gg, u.gg et lolalytics pour les rangs Émeraude et plus, patch 26.21. Les chiffres comptent les matchups disponibles dans chaque source.

| Fichier | Champions | op.gg | u.gg | lolalytics |
| --- | ---: | ---: | ---: | ---: |
| [`matchups-top.json`](../app/data/matchups-top.json) | 52 | 2 476 | 2 552 | 2 576 |
| [`matchups.json`](../app/data/matchups.json) (jungle) | 59 | 3 242 | 3 422 | 2 837 |
| [`matchups-mid.json`](../app/data/matchups-mid.json) | 42 | 1 688 | 1 708 | 1 716 |
| [`matchups-adc.json`](../app/data/matchups-adc.json) | 28 | 756 | 756 | 754 |
| [`matchups-support.json`](../app/data/matchups-support.json) | 42 | 1 594 | 1 652 | 1 672 |

- **Champions retenus** : en top, mid et support, ceux joués au moins 10 000 fois dans le rôle sur u.gg. En ADC, ceux qu'u.gg compte au moins 800 fois face à Jinx en bot, ce qui inclut les picks hors ADC classiques (Ziggs, Veigar, Yasuo…).
- **Biais de lolalytics** : ses winrates surestiment d'environ 1,7 point le champion de la page, dans tous les rôles. La moyenne des deux sens de lecture corrige ce biais.
- **Fiabilité** : une fois réunies, les trois sources sont très proches, avec une corrélation de 0,91 à 0,96 entre elles et un écart moyen de 0,6 à 1 point par matchup.

## Importer les matchups d'un nouveau patch

Un administrateur importe un fichier depuis la page **Admin** en choisissant le rôle. Le fichier est conservé dans le volume de données et remplace celui du dépôt pour ce rôle (5 Mo maximum).

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
