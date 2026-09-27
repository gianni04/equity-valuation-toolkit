# Equity Valuation Toolkit

Valorisation d'actions en Python : DCF (WACC par CAPM, valeur terminale de Gordon), comparables EV/EBITDA et grille de sensibilité, appliqués à un panier de 10 grandes capitalisations US.

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![Data](https://img.shields.io/badge/data-Yahoo%20Finance-purple) ![License](https://img.shields.io/badge/License-MIT-green)

## Ce que fait le projet

Reproduit en version simplifiée les deux méthodes de valorisation d'un analyste sell-side, puis classe le panier par potentiel de hausse/baisse.

- **DCF** : projection du free cash flow sur 5 ans, actualisation au WACC (coût des fonds propres par CAPM, coût de la dette après impôt), valeur terminale de Gordon (g = 2,5 %).
- **Comparables** : application du multiple EV/EBITDA médian du panier à l'EBITDA de chaque société.
- **Sensibilité** : grille de valeur DCF selon le WACC et le taux de croissance terminal, pour la plus grosse capitalisation du panier.

Univers : AAPL, MSFT, GOOGL, JPM, XOM, JNJ, PG, KO, NVDA, UNH.

## Quickstart

```bash
pip install -r requirements.txt
python equity_valuation.py
```

Les résultats sont écrits dans `output/`.

## Résultats

![Screening de valorisation](output/valuation_screen.png)

| Ticker | Cours | WACC | Valeur DCF | Potentiel DCF | Valeur comps | Potentiel comps |
|---|---:|---:|---:|---:|---:|---:|
| XOM | 153,04 | 4,8 % | 320,69 | +109,5 % | 310,01 | +102,6 % |
| UNH | 407,08 | 6,6 % | 545,97 | +34,1 % | 471,69 | +15,9 % |
| PG | 145,79 | 5,7 % | 167,40 | +14,8 % | 195,25 | +33,9 % |
| JNJ | 259,24 | 5,1 % | 296,25 | +14,3 % | 268,73 | +3,7 % |
| AAPL | 313,33 | 9,3 % | 148,66 | −52,6 % | 221,55 | −29,3 % |
| NVDA | 223,96 | 15,0 % | 24,12 | −89,2 % | 134,11 | −40,1 % |

Grille de sensibilité NVDA (valeur par action, `output/sensitivity_NVDA.csv`) : de **19,9 $** (WACC 17 %, g 1,5 %) à **31,0 $** (WACC 13 %, g 3,5 %).

## Lecture critique

Les écarts extrêmes sont instructifs plus que prescriptifs :

- **Valeurs de croissance** (NVDA, MSFT, AAPL) : un DCF à 5 ans avec croissance terminale de 2,5 % ne capture pas une croissance attendue à deux chiffres, d'où des valeurs très inférieures au cours. Le marché intègre des hypothèses de croissance bien plus élevées.
- **WACC bas** (XOM ~4,8 %) : un beta faible fait mécaniquement exploser la valeur terminale ; en pratique on appliquerait un plancher de prime de risque.
- **JPM sans valeur** : Yahoo Finance ne fournit ni free cash flow ni EBITDA exploitables pour une banque. Surtout, le DCF sur free cash flow et l'EV/EBITDA ne s'appliquent pas aux banques (la dette est une matière première, pas un financement). Une banque se valorise en P/B, P/E ou par dividend discount model.
- Données Yahoo Finance réelles mais non normalisées (pas de consensus analystes, pas de retraitement des éléments exceptionnels).

## Stack

`Python` · `NumPy` · `pandas` · `SciPy` · `Matplotlib` · `yfinance`

## Licence

MIT — voir [LICENSE](LICENSE).
