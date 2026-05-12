# Conformité Cyber Resilience Act (CRA)

> Règlement (UE) 2024/2847 du Parlement européen et du Conseil  
> Applicable à partir du **11 octobre 2027**

---

## Table des matières

- [1. Qualification du produit](#1-qualification-du-produit)
- [2. Classement et périmètre](#2-classement-et-périmètre)
- [3. Exigences essentielles applicables](#3-exigences-essentielles-applicables)
- [4. État de conformité actuel](#4-état-de-conformité-actuel)
- [5. Actions restantes](#5-actions-restantes)
- [6. Obligations post-mise sur le marché](#6-obligations-post-mise-sur-le-marché)
- [7. Documentation technique requise](#7-documentation-technique-requise)
- [8. Références réglementaires](#8-références-réglementaires)

---

## 1. Qualification du produit

| Attribut | Valeur |
|---|---|
| Nom du produit | Microservice de pseudonymisation |
| Nature | Logiciel conteneurisé (Docker) |
| Langage | Python 3.10+ |
| Interfaces exposées | API REST, interface Web (Streamlit), CLI |
| Licence | Apache 2.0 |
| Mode de distribution | Open source — dépôt Git public |

### Applicabilité du CRA

Le CRA s'applique aux **produits comportant des éléments numériques** (PEN) mis sur le marché de l'Union européenne, y compris les logiciels distribués séparément.

**Critères déclencheurs retenus :**
- Logiciel exposant une API REST à destination d'autres systèmes
- Traitant des données à caractère personnel dans des contextes professionnels
- Susceptible d'être intégré dans des chaînes de traitement automatisées
- Distribué publiquement avec intention d'usage professionnel

**Exemption open source :** l'exemption prévue à l'article 3(2)(f) du CRA pour les logiciels libres ne s'applique que lorsque le logiciel est distribué sans intention commerciale directe et hors de tout flux de revenus. Si ce microservice est intégré dans une offre commerciale ou un service payant, l'exemption ne s'applique pas.

---

## 2. Classement et périmètre

### Classe applicable

**Classe I — Produit important (Annexe III, catégorie 1)**

Justification : le microservice met en œuvre des **fonctions de sécurité** au sens de l'Annexe III du CRA, notamment :
- pseudonymisation de données personnelles (fonction cryptographique appliquée à la protection des données)
- vérification d'intégrité par signature HMAC-SHA256
- contrôle d'accès aux données via séparation table de correspondance / données pseudonymisées

### Conséquences du classement Classe I

- Évaluation de conformité par **tierce partie** (organisme notifié) **ou** auto-évaluation si le produit est développé selon des normes harmonisées publiées au JOUE
- Déclaration de conformité UE obligatoire
- Marquage CE obligatoire avant mise sur le marché

---

## 3. Exigences essentielles applicables

### 3.1 Sécurité dès la conception (Annexe I, Partie I)

| Réf. | Exigence | Applicable |
|---|---|---|
| 1(a) | Pas de vulnérabilités connues exploitables au moment de la mise sur le marché | Oui |
| 1(b) | Configuration sécurisée par défaut | Oui |
| 1(c) | Protection contre les accès non autorisés | Oui |
| 1(d) | Protection de la confidentialité des données traitées | Oui |
| 1(e) | Protection de l'intégrité des données et des commandes | Oui |
| 1(f) | Minimisation de la surface d'attaque | Oui |
| 1(g) | Résilience aux attaques par déni de service | Partiel |
| 1(h) | Minimisation de l'impact des incidents | Oui |
| 1(i) | Journalisation des événements de sécurité | Oui |

### 3.2 Gestion des vulnérabilités (Annexe I, Partie II)

| Réf. | Exigence | Applicable |
|---|---|---|
| 2(a) | Identification et documentation des composants (SBOM) | Oui |
| 2(b) | Traitement rapide des vulnérabilités découvertes | Oui |
| 2(c) | Tests de sécurité réguliers | Oui |
| 2(d) | Divulgation coordonnée des vulnérabilités (CVD) | Oui |
| 2(e) | Mises à jour de sécurité disponibles gratuitement | Oui |
| 2(f) | Politique de fin de support | Oui |
| 2(g) | Durée minimale de support de 5 ans | Oui |

---

## 4. État de conformité actuel

### Conforme ou en bonne voie

| Domaine | Exigence CRA | Couverture dans le projet | Référence |
|---|---|---|---|
| Sécurité dès la conception | Configuration sécurisée par défaut | Conteneur non-root, ports minimaux | REQ-SEC-04, REQ-SEC-05 |
| Minimisation des données | Traitement minimal | Seules les colonnes désignées sont traitées | REQ-SEC-01 |
| Séparation des secrets | Clés hors données | Variables d'environnement, pas de stockage en dur | REQ-SEC-02, REQ-SEC-03 |
| Intégrité | Signature des artefacts | HMAC-SHA256 sur tous les artefacts | REQ-INTG-01, REQ-INTG-02 |
| Journalisation | Logs d'audit | Logs sans données ni secrets | REQ-SEC-06 |
| Confidentialité | Protection des données en traitement | Isolation conteneur, stateless par défaut | REQ-SEC-04, REQ-BEH-04 |
| Traçabilité | Enregistrement des opérations | Manifeste JSON horodaté par exécution | REQ-TRA-01, REQ-TRA-03 |

### Non conforme — actions requises

| Domaine | Exigence CRA | Gap identifié |
|---|---|---|
| SBOM | Inventaire des composants (art. 13 + Annexe I, 2a) | Absent — aucun fichier SBOM généré |
| Gestion des vulnérabilités | Politique documentée et processus de traitement | Absente |
| Notification d'incidents | Procédure de signalement à l'ENISA sous 24h | Absente |
| Durée de support | Politique de support 5 ans minimum | Non définie |
| Déclaration de conformité | Déclaration UE de conformité (art. 13) | Absente |
| Marquage CE | Apposition du marquage CE | Absent |
| Documentation technique | Dossier technique complet (Annexe VII) | Partiel |
| Point de contact | Adresse de signalement de vulnérabilités publiée | Absent |

---

## 5. Actions restantes

### Priorité haute (bloquantes pour la mise sur le marché)

**5.1 Générer et maintenir un SBOM**

Produire un Software Bill of Materials au format CycloneDX ou SPDX couvrant toutes les dépendances directes et transitives.

```bash
# Exemple avec cyclonedx-bom
pip install cyclonedx-bom
cyclonedx-py requirements requirements.txt -o sbom.json --format json
```

Dépendances directes actuelles à inventorier : `pandas`, `pyarrow`, `openpyxl`, `typer`, `streamlit`, `duckdb`, `numpy`, `python-dateutil`.

---

**5.2 Rédiger une politique de gestion des vulnérabilités**

Créer un fichier `SECURITY.md` contenant :
- périmètre couvert
- canal de signalement des vulnérabilités (adresse email dédiée ou issue tracker privé)
- délai de traitement et de réponse
- processus de divulgation coordonnée (CVD)
- politique de publication des correctifs

---

**5.3 Définir la politique de support**

Documenter :
- version(s) maintenue(s)
- durée minimale de support (5 ans imposés par le CRA)
- procédure de fin de vie

---

**5.4 Préparer la déclaration de conformité UE**

La déclaration doit couvrir (art. 13 + Annexe IV) :
- identification du fabricant
- identification du produit (nom, version, numéro de modèle)
- déclaration de responsabilité
- liste des normes harmonisées appliquées ou référence à l'organisme notifié
- date et signature

---

**5.5 Constituer la documentation technique (Annexe VII)**

Éléments requis :
- description générale du produit et de ses fonctions
- conception et architecture (schémas)
- liste des normes appliquées
- résultats des tests et évaluations de sécurité
- SBOM
- déclaration de conformité
- politique de gestion des vulnérabilités

---

### Priorité normale

**5.6 Mettre en place une procédure de notification d'incidents**

Le CRA impose la notification à l'ENISA (via l'autorité nationale compétente) dans les délais suivants :
- **24h** : alerte initiale dès connaissance d'un incident actif
- **72h** : rapport intermédiaire
- **1 mois** : rapport final

Préparer un modèle de notification et désigner un responsable.

---

**5.7 Publier un point de contact pour les signalements de sécurité**

Ajouter dans le README et sur la page de dépôt une adresse ou un canal de signalement des vulnérabilités, conformément à l'article 13(6) du CRA.

---

**5.8 Renforcer les tests de sécurité**

Compléter la suite de tests existante (`pytest`) avec :
- tests de régression de sécurité sur les fonctions cryptographiques
- tests de robustesse sur les entrées malformées
- vérification systématique des codes de retour en cas d'erreur d'intégrité

---

## 6. Obligations post-mise sur le marché

| Obligation | Fréquence / Déclencheur | Responsable |
|---|---|---|
| Surveillance active des vulnérabilités dans les dépendances | Continue | Mainteneur |
| Publication de mises à jour de sécurité | Dès détection d'une vulnérabilité exploitable | Mainteneur |
| Notification ENISA (alerte initiale) | Dans les 24h suivant la connaissance d'un incident actif | Mainteneur |
| Notification ENISA (rapport intermédiaire) | 72h après l'alerte initiale | Mainteneur |
| Notification ENISA (rapport final) | 1 mois après l'alerte initiale | Mainteneur |
| Mise à jour du SBOM | À chaque mise à jour des dépendances | Mainteneur |
| Révision de la déclaration de conformité | À chaque modification substantielle du produit | Mainteneur |
| Maintien du support de sécurité | Minimum 5 ans à compter de la mise sur le marché | Mainteneur |

---

## 7. Documentation technique requise

Structure recommandée du dossier technique (Annexe VII du CRA) :

```
docs/
├── cra/
│   ├── declaration-conformite.pdf     # Déclaration UE de conformité (Annexe IV)
│   ├── evaluation-securite.md         # Résultats des tests et analyses de risques
│   ├── architecture.md                # Conception et architecture du produit
│   └── normes-appliquees.md           # Normes harmonisées ou spécifications communes
├── sbom.json                          # SBOM au format CycloneDX ou SPDX
└── SECURITY.md                        # Politique de gestion des vulnérabilités
```

---

## 8. Références réglementaires

| Document | Référence |
|---|---|
| Texte du règlement | [Règlement (UE) 2024/2847 — JOUE L, 20 novembre 2024](https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=OJ:L_202402847) |
| Guide ENISA CRA | [ENISA — Cyber Resilience Act](https://www.enisa.europa.eu/topics/cyber-resilience-act) |
| Normes harmonisées (en cours de publication) | JOUE — séries EN IEC 62443, EN ISO/IEC 27001 |
| Déclaration de conformité (modèle) | Annexe IV du Règlement (UE) 2024/2847 |
| Documentation technique (contenu requis) | Annexe VII du Règlement (UE) 2024/2847 |
| Catégories de produits importants | Annexe III du Règlement (UE) 2024/2847 |

---

*Document maintenu par les auteurs du projet — à réviser lors de toute modification substantielle du produit ou de publication de normes harmonisées applicables.*
