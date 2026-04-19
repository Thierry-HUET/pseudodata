## 1. Contexte et objectif

### 1.1 Contexte général

Dans le cadre de traitements impliquant des données à caractère personnel, il est nécessaire de mettre en œuvre des mécanismes permettant de **réduire les risques liés à l’exposition de données sensibles**, tout en conservant leur exploitabilité fonctionnelle.

La **pseudonymisation**, au sens du RGPD, est un traitement de données personnelles consistant à remplacer les identifiants directs par des pseudonymes, de telle sorte que les données ne puissent plus être attribuées à une personne physique sans information supplémentaire conservée séparément.  
Ce traitement est **réversible** et ne constitue pas une anonymisation.

---

### 1.2 Objectif du microservice

L’objectif est de concevoir un **microservice conteneurisé (Docker)** dont la fonction principale est de **pseudonymiser des fichiers contenant des données sensibles**, de manière :

- Déterministe
- Réversible sous conditions maîtrisées
- Traçable
- Conforme aux principes du RGPD relatifs à la protection des données dès la conception

Ce microservice est destiné à être intégré dans des chaînes de traitement automatisées ou utilisé comme composant transverse de sécurisation des échanges de données.

---

### 1.3 Cas d’usage couverts

Le microservice doit couvrir **deux cas d’usage distincts**, aux objectifs et contraintes différents.

#### Cas d’usage 1 – Pseudonymisation avant traitement

- Pseudonymisation de données avant transmission à un tiers ou à une autre brique du système d’information
- Objectifs
  - Limiter l’exposition de données directement identifiantes
  - Conserver les capacités d’analyse, de rapprochement et de statistiques
- Exemples d’utilisation
  - Analyse de données
  - Recette et tests
  - Reprises ou migrations de données
- Hypothèse
  - La table de correspondance est conservée par l’entité émettrice
  - La ré‑identification peut constituer un besoin métier légitime

---

#### Cas d’usage 2 – Pseudonymisation pour transmission sur réseau non sécurisé

- Utilisation de la pseudonymisation comme **mesure de réduction du risque** lors d’une transmission sur un canal non chiffré
- Objectif
  - Limiter l’impact d’une interception accidentelle ou malveillante
- Hypothèses
  - La table de correspondance n’est jamais transmise avec le fichier pseudonymisé
  - Le destinataire ne dispose d’aucun moyen de ré‑identification

⚠️ Remarque importante  
La pseudonymisation ne se substitue pas à un mécanisme de chiffrement des communications.  
Dans ce cas d’usage, elle constitue une **mesure complémentaire de sécurité**, et non une garantie de confidentialité équivalente à un canal sécurisé.

---

### 1.4 Positionnement réglementaire

- Le microservice met en œuvre un **traitement de pseudonymisation**, tel que défini par le RGPD
- Les données produites restent des données personnelles
- Le traitement doit être
  - Documenté
  - Justifié
  - Inscrit dans le registre des traitements le cas échéant
- L’anonymisation irréversible est explicitement hors périmètre

## 2. Périmètre fonctionnel

### 2.1 Entrées

- Un fichier structuré contenant des données à caractère personnel  
- Formats supportés
  - CSV
  - JSON
  - XML
  - Parquet
- Un jeu de règles de pseudonymisation
  - Déclaratif
  - Paramétrable par appel ou par configuration

---

### 2.2 Identification des champs à pseudonymiser

Le microservice doit être capable d’identifier les champs à pseudonymiser selon deux modes complémentaires.

#### Mode explicite (déclaratif)

- Les champs à pseudonymiser sont fournis explicitement
  - Par nom de colonne
  - Par chemin (JSON / XML)
- Ce mode est obligatoire et constitue le socle fonctionnel

Avantages
- Déterminisme total
- Absence d’ambiguïté réglementaire
- Simplicité d’audit

---

#### Mode implicite (assisté)

- Le microservice peut proposer une identification automatique des champs sensibles
- Cette identification repose sur
  - Le schéma du fichier lorsqu’il est disponible
  - Des règles sémantiques simples
    - Nom du champ
    - Type logique
    - Longueur
    - Régularités de valeurs

Statut
- Fonction d’aide à la configuration
- Ne constitue pas une décision automatique

Hypothèses
- Une validation humaine ou applicative est requise avant exécution
- Aucun champ ne doit être pseudonymisé sans validation explicite

Limites connues
- Pertinent pour données tabulaires
- Non fiable pour texte libre ou champs multi‑sémantiques

---

### 2.3 Sorties

- Le fichier pseudonymisé
  - Même format que le fichier d’entrée
- Optionnel
  - Table de correspondance
    - Identifiant original ↔ pseudonyme
    - Générée uniquement si la réversibilité est autorisée
    - Séparée physiquement ou logiquement du fichier pseudonymisé

---

### 2.4 Propriétés attendues du traitement

- Déterminisme
  - Une même valeur source produit toujours le même pseudonyme
- Réversibilité contrôlée
  - Restreinte à l’accès à la table de correspondance
- Traçabilité
  - Journalisation minimale
    - Type de traitement
    - Date
    - Jeu de règles appliqué
- Isolation
  - Microservice stateless par défaut
  - Toute persistance doit être explicitement configurée

---

### 2.5 Hors périmètre explicite

- Anonymisation irréversible
- Chiffrement de bout en bout
- Analyse sémantique avancée de texte libre
- Décisions automatiques sans validation sur la sensibilité des champs
