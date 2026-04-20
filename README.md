# Microservice de pseudonymisation

> Microservice conteneurisé (Docker) de pseudonymisation de données structurées, conforme RGPD, avec interface Web et API.  
> Développé en **Python**.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)]()
[![Licence Apache 2.0](https://img.shields.io/badge/licence-Apache%202.0-green.svg)]()

---

## Positionnement réglementaire

Ce microservice met en œuvre un traitement de **pseudonymisation** au sens du RGPD : les identifiants directs sont remplacés par des pseudonymes, sans que les données puissent être rattachées à une personne physique sans accès à une information séparée.

- Les données produites restent des **données à caractère personnel**
- Le traitement est **réversible sous conditions maîtrisées**
- La pseudonymisation **ne se substitue pas** à un mécanisme de chiffrement des communications

---

## Cas d'usage

### Cas 1 – Pseudonymisation avant traitement

Pseudonymisation de données avant transmission pour exploitation (analyse, tests, reprises de données). Ce cas d'usage préserve les capacités de **rapprochement, d'analyse et de production de statistiques**. La table de correspondance est conservée par l'émetteur ; la ré-identification peut constituer un besoin métier légitime.

### Cas 2 – Pseudonymisation pour transmission sur réseau non sécurisé

Réduction du risque en cas d'interception sur un canal non chiffré. La table de correspondance n'est jamais transmise ; le destinataire ne dispose d'aucun moyen de ré-identification.

---

## Fonctionnement général

Pour chaque exécution, le microservice produit quatre artefacts :

| Artefact | Nom | Description |
|---|---|---|
| Fichier pseudonymisé | `<sortie>` | Données sources avec les colonnes désignées remplacées par des pseudonymes HMAC-SHA256 |
| Table de correspondance | `<mapping>` | Fichier de réversibilité, généré uniquement si la réversibilité est autorisée |
| Manifeste JSON | `<sortie>.manifeste.json` | Rapport d'exécution horodaté : colonnes traitées, taux de couverture, chemins de sortie |
| Fichier de signature | `<sortie>.signature.json` | Empreintes HMAC-SHA256 du fichier source, du fichier pseudonymisé, de la table de correspondance et du manifeste |

Le manifeste et la signature sont générés **systématiquement**, y compris en cas de succès partiel.

---

## Formats supportés

| Format | Lecture | Écriture | Remarques |
|---|---|---|---|
| CSV | ✓ | ✓ | UTF-8 recommandé |
| JSON | ✓ | ✓ | Chemin de champ configurable |
| XML | ✓ | ✓ | Chemin de champ configurable |
| Parquet | ✓ | ✓ | Types natifs conservés |
| Excel (XLSX) | ✓ | ✓ | Première feuille par défaut |

Seules les données structurées sont traitées. Le texte libre est hors périmètre.

---

## Identification des champs à pseudonymiser

### Mode explicite (obligatoire)

Les champs sont désignés explicitement par nom de colonne ou par chemin (JSON / XML). Ce mode constitue le socle fonctionnel et garantit déterminisme, absence d'ambiguïté réglementaire et simplicité d'audit.

### Mode implicite assisté (optionnel)

Le microservice peut proposer une identification automatique de champs sensibles, fondée sur le schéma du fichier et des règles sémantiques simples (nom, type, longueur, régularités de valeurs). Ce mode est limité aux données tabulaires.

> **Aucun champ ne peut être pseudonymisé sur la seule base d'une détection automatique. Une validation explicite est obligatoire avant toute exécution.**

---

## Installation

```bash
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -U pip
pip install -e .
```

**Dépendances principales :** `pandas`, `pyarrow`, `openpyxl`, `typer`, `streamlit`

### Via Docker

```bash
docker build -t pseudodata .
docker run --rm \
  -e PSEUDONYMIZER_SECRET="votre_clé_secrète" \
  -v $(pwd)/données:/data \
  pseudodata
```

---

## Configuration

La clé de pseudonymisation est fournie via variable d'environnement :

```bash
export PSEUDONYMIZER_SECRET="votre_clé_secrète"   # minimum 32 caractères
```

> ⚠️ Ne jamais stocker cette clé dans le dépôt ou les journaux d'exécution. Elle est également requise pour la dépseudonymisation et la vérification de signature.

---

## Interface Web (Streamlit)

```bash
streamlit run app.py
```

L'interface permet :
- la sélection du fichier à traiter
- la configuration des règles de pseudonymisation
- le déclenchement du traitement
- le téléchargement du fichier pseudonymisé et des artefacts associés

---

## API

Le microservice expose une API REST permettant :
- la soumission d'un fichier
- la fourniture des règles de pseudonymisation
- la récupération du fichier pseudonymisé

Voir la documentation OpenAPI disponible à `/docs` une fois le service démarré.

---

## Pseudonymisation (CLI)

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
| `--input` | ✓ | — | Fichier source (CSV, JSON, XML, Parquet, XLSX) |
| `--output` | ✓ | — | Fichier pseudonymisé en sortie |
| `--mapping` | ✓ | — | Table de correspondance pour la réversibilité |
| `--columns` | ✓ | — | Colonnes à pseudonymiser, séparées par des virgules |
| `--truncate` | | `22` | Longueur des pseudonymes (`0` = sans limite) |
| `--sheet` | | — | Nom de feuille XLSX (optionnel) |
| `--sep` | | `,` | Séparateur CSV |
| `--encoding` | | `utf-8` | Encodage CSV |

### Codes de retour

| Code | Signification |
|---|---|
| `0` | Succès complet |
| `2` | Succès partiel (colonnes absentes ou aucune cellule éligible) |
| `1` | Erreur fatale |

---

## Dépseudonymisation (CLI)

```bash
python depseudonymize.py \
  --input     données/sortie_pseudonymisee.csv \
  --mapping   données/table_correspondance.parquet \
  --signature données/sortie_pseudonymisee.csv.signature.json \
  --output    données/restaure.csv
```

La vérification d'intégrité via le fichier de signature est **obligatoire**. Le traitement est bloqué si la signature est invalide ou si les fichiers ont été modifiés depuis la pseudonymisation. Les noms de colonnes du fichier à dépseudonymiser doivent être identiques à ceux utilisés lors de la pseudonymisation.

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

Un rapport `<sortie>.rapport_depseudo.json` est généré à côté du fichier restauré, sans aucune valeur originale ni pseudonyme.

---

## Manifeste de pseudonymisation

Généré automatiquement sous le nom `<sortie>.manifeste.json`.

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

- `taux` — proportion de valeurs non nulles effectivement pseudonymisées
- `taux_global` — couverture sur l'ensemble des cellules éligibles
- `colonnes_absentes` — écart entre la configuration demandée et le schéma réel ; le traitement se poursuit et le résultat est qualifié de succès partiel
- `empreinte_secret` — empreinte non réversible de la clé, permettant de détecter un changement entre deux exécutions

> Un `taux_global` de 1.0 atteste une couverture technique complète. Il ne constitue pas une garantie d'anonymisation au sens du RGPD.

---

## Algorithme

**HMAC-SHA256 déterministe** : une même valeur source produit toujours le même pseudonyme, à clé identique, entre plusieurs exécutions. Cette propriété permet les jointures entre jeux de données pseudonymisés avec la même clé.

La réversibilité est assurée **exclusivement** par la table de correspondance — l'algorithme seul ne permet pas la ré-identification.

---

## Sécurité

- **Minimisation** — seules les données strictement nécessaires à l'opération sont traitées ; aucune donnée superflue n'est conservée ni exposée
- **Séparation des secrets et des données** — la table de correspondance, les clés et secrets sont séparés logiquement et/ou physiquement des données pseudonymisées ; ils ne sont jamais stockés au même emplacement par défaut
- **Gestion des secrets** — les clés et sels ne doivent jamais être codés en dur ni versionnés dans Git ; les fournir via variables d'environnement ou un gestionnaire de secrets externe
- **Isolation du conteneur** — le microservice fonctionne sans privilèges élevés (non-root), conformément aux bonnes pratiques Docker
- **Exposition réseau minimale** — seuls les ports de l'API et de l'interface Web sont exposés ; tout autre port est fermé
- **Stateless par défaut** — toute persistance doit être explicitement configurée
- **Journalisation sécurisée** — les journaux ne contiennent ni données pseudonymisées exploitables, ni table de correspondance, ni secrets ; ils restent exploitables à des fins d'audit
- **Protection contre les usages abusifs** — des mécanismes de limitation sont prévus pour éviter les appels excessifs et les traitements massifs non autorisés
- **Défense en profondeur** — la sécurité repose sur plusieurs niveaux complémentaires (isolation, séparation des données et secrets, traçabilité) ; aucun mécanisme pris isolément n'est considéré comme suffisant

---

## Points d'attention

- Les données pseudonymisées restent des **données à caractère personnel** (RGPD applicable)
- Pour les CSV volumineux (> 10 M lignes), envisager un traitement par lots
- Les valeurs nulles ne sont pas éligibles au calcul du taux de couverture
- Une troncature agressive des pseudonymes (`--truncate` faible) augmente le risque de collision

---

## Hors périmètre

- Anonymisation irréversible
- Chiffrement de bout en bout
- Traitement de texte libre
- Analyse sémantique avancée
- Décisions automatiques non validées concernant la sensibilité des champs

---

## Tests

```bash
pytest test_pseudonymize.py -v
```

---

## Licence

Ce projet est distribué sous licence Apache 2.0.  
La propriété intellectuelle du code demeure celle de ses auteurs.
