# pseudonymize-batch

Outil Python en ligne de commande pour pseudonymiser des fichiers tabulaires (CSV, Parquet, XLSX) avec traçabilité complète du traitement.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Licence MIT](https://img.shields.io/badge/licence-MIT-green.svg)]()

---

## Fonctionnement

Pour chaque exécution, l'outil produit quatre artefacts :

| Artefact | Nom | Description |
|---|---|---|
| Fichier pseudonymisé | `<sortie>` | Données sources avec les colonnes désignées remplacées par des pseudonymes HMAC-SHA256 |
| Table de correspondance | `<mapping>` | Fichier de réversibilité permettant la ré-identification contrôlée |
| Manifeste JSON | `<sortie>.manifeste.json` | Rapport d'exécution horodaté : colonnes traitées, taux de couverture, chemins de sortie |
| Fichier de signature | `<sortie>.signature.json` | Empreintes HMAC-SHA256 de tous les artefacts et du fichier source, permettant de détecter toute modification ultérieure |

Le manifeste et la signature sont générés **systématiquement**, indépendamment du succès ou des erreurs partielles.

---

## Installation

```bash
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -U pip
pip install -e .
```

**Dépendances principales :** `pandas`, `pyarrow`, `openpyxl`, `typer`

---

## Configuration

La clé de pseudonymisation est fournie via variable d'environnement :

```bash
export PSEUDONYMIZER_SECRET="votre_clé_secrète"   # minimum 32 caractères
```

> ⚠️ Ne jamais stocker cette clé dans le dépôt ou les journaux d'exécution. Elle est également requise pour la dépseudonymisation et la vérification de signature.

---

## Pseudonymisation

```bash
python pseudonymize.py \
  --input     données/entree.csv \
  --output    données/sortie_pseudonymisee.csv \
  --mapping   données/table_correspondance.parquet \
  --columns   email,telephone,identifiant_client
```

### Paramètres

| Paramètre | Obligatoire | Défaut | Description |
|---|---|---|---|
| `--input` | ✓ | — | Fichier source (CSV, Parquet, XLSX) |
| `--output` | ✓ | — | Fichier pseudonymisé en sortie |
| `--mapping` | ✓ | — | Table de correspondance pour la réversibilité |
| `--columns` | ✓ | — | Colonnes à pseudonymiser, séparées par des virgules |
| `--truncate` | | `22` | Longueur des pseudonymes (`0` = sans limite) |
| `--sheet` | | — | Nom de feuille XLSX (optionnel) |
| `--sep` | | `,` | Séparateur CSV |
| `--encoding` | | `utf-8` | Encodage CSV |

Les colonnes non listées ne sont **pas modifiées**. Toute colonne absente du schéma réel est signalée dans le manifeste sans interruption du traitement.

### Codes de retour

| Code | Signification |
|---|---|
| `0` | Succès complet |
| `2` | Succès partiel (colonnes absentes ou aucune cellule éligible) |
| `1` | Erreur fatale |

---

## Dépseudonymisation

```bash
python depseudonymize.py \
  --input     données/sortie_pseudonymisee.csv \
  --mapping   données/table_correspondance.parquet \
  --signature données/sortie_pseudonymisee.csv.signature.json \
  --output    données/restaure.csv
```

La vérification d'intégrité via le fichier de signature est **obligatoire**. Le traitement est bloqué si la signature est invalide ou si les fichiers ont été modifiés depuis la pseudonymisation.

### Paramètres

| Paramètre | Obligatoire | Description |
|---|---|---|
| `--input` | ✓ | Fichier pseudonymisé à restaurer |
| `--mapping` | ✓ | Table de correspondance produite lors de la pseudonymisation |
| `--signature` | ✓ | Fichier de signature `.signature.json` |
| `--output` | ✓ | Fichier restauré en sortie |
| `--sheet` | | Nom de feuille XLSX (optionnel) |
| `--sep` | | Séparateur CSV (défaut : `,`) |
| `--encoding` | | Encodage CSV (défaut : `utf-8`) |

Un rapport `<sortie>.rapport_depseudo.json` est généré à côté du fichier restauré. Il contient les métadonnées opérationnelles (colonnes traitées, compteurs d'orphelins) sans aucune valeur originale ni pseudonyme.

---

## Formats supportés

| Format | Lecture | Écriture | Remarques |
|---|---|---|---|
| CSV | ✓ | ✓ | UTF-8 recommandé |
| Parquet | ✓ | ✓ | Types natifs conservés |
| XLSX | ✓ | ✓ | Première feuille uniquement — attention aux conversions implicites de types |

---

## Manifeste de pseudonymisation

Généré automatiquement à côté du fichier de sortie sous le nom `<sortie>.manifeste.json`.

```json
{
  "id_execution": "2026-03-27T06:52:40+01:00_7c2f8b1a",
  "horodatage_creation": "2026-03-27T06:52:40+01:00",
  "entree": {
    "chemin": "données/entree.csv",
    "format": "csv",
    "lignes": 125000,
    "colonnes": 12
  },
  "colonnes_demandees": ["email", "telephone", "identifiant_client"],
  "colonnes_effectives": ["email", "telephone", "identifiant_client"],
  "colonnes_absentes": [],
  "pseudonymisation": {
    "algorithme": "hmac_sha256",
    "empreinte_secret": "sha256:3f1a9c2b44d7e081",
    "troncature": 22,
    "statistiques_par_colonne": {
      "email":              { "non_nul": 124532, "transformees": 124532, "taux": 0.9963 },
      "telephone":          { "non_nul": 118900, "transformees": 118900, "taux": 0.9512 },
      "identifiant_client": { "non_nul": 125000, "transformees": 125000, "taux": 1.0000 }
    },
    "taux_global": 1.0
  },
  "sorties": {
    "pseudonymise":   { "chemin": "données/sortie_pseudonymisee.csv", "format": "csv" },
    "correspondance": { "chemin": "données/table_correspondance.parquet", "format": "parquet", "lignes": 368432 },
    "manifeste":      { "chemin": "données/sortie_pseudonymisee.csv.manifeste.json", "format": "json" }
  }
}
```

**Lecture des indicateurs**

- `taux` (par colonne) — proportion de valeurs non nulles effectivement pseudonymisées
- `taux_global` — couverture sur l'ensemble des cellules éligibles
- `colonnes_absentes` — écart entre la configuration demandée et le schéma réel du fichier
- `empreinte_secret` — empreinte non réversible de la clé (permet de détecter un changement de clé entre deux exécutions)

> Un `taux_global` de 1.0 atteste une couverture technique complète. Il ne constitue pas une garantie d'anonymisation au sens du RGPD.

---

## Algorithme

**HMAC-SHA256 déterministe** : une même valeur source produit toujours le même pseudonyme, ce qui permet les jointures entre jeux de données pseudonymisés avec la même clé.

La réversibilité est assurée exclusivement par la table de correspondance — l'algorithme seul ne permet pas la ré-identification.

---

## Points d'attention

- Stocker la table de correspondance **séparément** des données pseudonymisées
- Les données pseudonymisées restent des **données à caractère personnel** (RGPD applicable)
- Pour les CSV volumineux (> 10M lignes), envisager un traitement par lots
- Les valeurs nulles ne sont pas considérées comme éligibles au calcul du taux
- Une troncature agressive des pseudonymes (`--truncate` faible) augmente le risque de collision

---

## Tests

```bash
pytest test_pseudonymize.py -v
```

---

## Licence

MIT