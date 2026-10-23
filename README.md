# Simulateur de Play Boosters — Reality Fracture (FRA)

Page HTML locale qui simule l'ouverture de Play Boosters de l'édition
Reality Fracture et affiche les cartes en français.

## Utilisation

Ouvrez `index.html` dans un navigateur. Aucun serveur n'est nécessaire.
Les images viennent du CDN Scryfall, donc une connexion internet est requise.

La page affiche un seul booster. Chaque clic sur « Ouvrir un nouveau booster » le
remplace par un nouveau tirage.

Le booster a un bouton « Copier le lien » (voir ci-dessous) et un bouton
« Télécharger l'image » qui enregistre les 14 cartes
dans un fichier JPEG (7 cartes par ligne, 672 × 936 px par carte, sans aucune
autre information).

## Partager un booster

L'adresse de la page contient la graine du tirage après le `#`, par exemple
`index.html#k3j9x2a`. Le bouton « Copier le lien » copie cette adresse ; qui
l'ouvre voit le même booster. Toute chaîne peut servir de graine : taper
`index.html#noel` donne toujours le même booster.

Un lien reste valable tant que `cards.js` et la logique de tirage de `sim.js`
ne changent pas. Régénérer `cards.js` pour la même édition conserve l'ordre
des cartes (ordre de collection Scryfall) et donc les liens.

## Notes 17Lands (optionnel)

Le bouton « Notes 17Lands » affiche sur chaque carte son taux de victoire
« games in hand » (GIH), son rang dans l'édition et sa position moyenne de
prise (ATA). Il trie aussi les cartes par GIH décroissant ; les cartes sans
assez de parties passent en dernier. Les terrains de base n'ont pas de note et
restent en fin de booster : ils sont gratuits en limité. L'image téléchargée
suit le même ordre.
Ces chiffres viennent des jeux de données publics de 17Lands
(licence CC BY 4.0) : https://www.17lands.com/public_datasets

```
python3 -I fetch_ratings.py
```

Le script télécharge une seule fois les deux fichiers du bucket public S3
(`game_data` et `draft_data`, Premier Draft FRA) dans `data_17lands/`, calcule
les statistiques localement et écrit `ratings.js`. Il ne retélécharge qu'avec
`--refresh` et n'appelle jamais le site 17lands.com. La page lit seulement
`ratings.js` ; sans ce fichier, le bouton est désactivé.

La source est indiquée en tête de page avec un lien, comme le demande la
licence CC BY 4.0.

## Fichiers

| Fichier          | Rôle                                                        |
|------------------|-------------------------------------------------------------|
| `index.html`     | Interface (HTML, CSS, JavaScript sans dépendance)           |
| `sim.js`         | Logique de tirage des boosters et probabilités théoriques   |
| `cards.js`       | Données des cartes (généré, ne pas modifier à la main)      |
| `fetch_cards.py` | Script qui régénère `cards.js` depuis l'API Scryfall        |
| `fetch_ratings.py` | Script qui calcule `ratings.js` depuis les données 17Lands |
| `ratings.js`     | Statistiques 17Lands par carte (généré)                     |
| `data_17lands/`  | Cache des fichiers 17Lands téléchargés (ignoré par git)     |
| `LICENSE`        | Licence MIT du code                                         |

Pour régénérer les données (Python 3, aucune dépendance) :

```
python3 fetch_cards.py
```

Le script vérifie que les effectifs de chaque groupe de cartes correspondent
à la structure publiée par Wizards et signale tout écart.

## Sources

- Structure des boosters et probabilités :
  https://magic.wizards.com/en/news/feature/collecting-reality-fracture
- Liste des paires en écho : https://draftsim.com/mtg-reality-fracture-echoed-pairs/
- Données des cartes et images : https://scryfall.com (API publique)
- Statistiques de draft : 17Lands public datasets, CC BY 4.0,
  https://www.17lands.com/public_datasets

## Licences

- **Code** (`index.html`, `sim.js`, `fetch_cards.py`, `fetch_ratings.py`) :
  licence MIT, voir `LICENSE`.
- **Données des cartes** (`cards.js`) : les noms, numéros et liens d'images
  viennent de l'API Scryfall et appartiennent à Wizards of the Coast. Ce
  simulateur est un contenu de fans non officiel, autorisé par la
  [Fan Content Policy](https://company.wizards.com/en/legal/fancontentpolicy)
  de Wizards of the Coast. Il est gratuit et ne doit pas être vendu.
  Avis officiel : *This simulator is unofficial Fan Content permitted under
  the Fan Content Policy. Not approved/endorsed by Wizards. Portions of the
  materials used are property of Wizards of the Coast. © Wizards of the
  Coast LLC.*
- **Statistiques** (`ratings.js`) : dérivées des jeux de données publics de
  17Lands, licence [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
  L'attribution dans l'en-tête du fichier et sur la page doit être conservée.
- **Cache `data_17lands/`** : données brutes de 17Lands, non versionnées.

## Limites

- Le jeton ou la carte de compteurs du booster n'est pas simulé.
- Les taux donnés comme « moins de 1 % » par Wizards sont approximés.
- Deux cartes Braintwister (n° 362 et 371) n'ont pas d'image française sur
  Scryfall ; l'image anglaise est utilisée.
- La répartition des couleurs entre les communes d'un même booster n'est pas
  modélisée ; seule l'absence de doublon est garantie.
