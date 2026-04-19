# Microservice de pseudonymisation

## Table des matières

- [1. Contexte et objectif](#1-contexte-et-objectif)
  - [1.1 Contexte général](#11-contexte-général)
  - [1.2 Objectif du microservice](#12-objectif-du-microservice)
  - [1.3 Cas d’usage couverts](#13-cas-dusage-couverts)
  - [1.4 Positionnement réglementaire](#14-positionnement-réglementaire)
- [2. Périmètre fonctionnel](#2-périmètre-fonctionnel)
  - [2.1 Entrées](#21-entrées)
  - [2.2 Identification des champs à pseudonymiser](#22-identification-des-champs-à-pseudonymiser)
  - [2.3 Sorties](#23-sorties)
  - [2.4 Propriétés attendues du traitement](#24-propriétés-attendues-du-traitement)
  - [2.5 Hors périmètre explicite](#25-hors-périmètre-explicite)

---

## 1. Contexte et objectif

### 1.1 Contexte général

Dans le cadre de traitements impliquant des données à caractère personnel, il est nécessaire de mettre en œuvre des mécanismes permettant de réduire les risques liés à l’exposition de données sensibles, tout en conservant leur exploitabilité fonctionnelle.

La pseudonymisation, au sens du RGPD, est un traitement de données personnelles consistant à remplacer les identifiants directs par des pseudonymes, de telle sorte que les données ne puissent plus être attribuées à une personne physique sans information supplémentaire conservée séparément.

Ce traitement est réversible et ne constitue pas une anonymisation.

---

### 1.2 Objectif du microservice

L’objectif est de concevoir un microservice conteneurisé (Docker) dont la fonction principale est de pseudonymiser des fichiers contenant des données sensibles, de manière :

- Déterministe
- Réversible sous conditions maîtrisées
- Traçable
- Conforme aux principes de protection des données dès la conception

Ce microservice est destiné à être intégré dans des chaînes de traitement automatisées ou utilisé comme composant transverse de sécurisation des échanges de données.

---

### 1.3 Cas d’usage couverts

Le microservice doit couvrir deux cas d’usage distincts.

#### Cas d’usage 1 – Pseudonymisation avant traitement

- Pseudonymisation de données avant transmission pour exploitation
- Objectifs
  - Limiter l’exposition de données directement identifiantes
  - Conserver les capacités d’analyse et de rapprochement
- Exemples
  - Analyse de données
  - Tests
  - Reprises de données
- Hypothèse
  - La table de correspondance est conservée par l’émetteur
  - La ré‑identification peut constituer un besoin métier légitime

---

#### Cas d’usage 2 – Pseudonymisation pour transmission sur réseau non sécurisé

- Utilisation de la pseudonymisation comme mesure de réduction du risque
- Objectif
  - Limiter l’impact d’une interception lors d’une transmission sur un canal non chiffré
- Hypothèses
  - La table de correspondance n’est jamais transmise
  - Le destinataire ne dispose d’aucun moyen de ré‑identification

> **Remarque importante**  
> La pseudonymisation ne se substitue pas à un mécanisme de chiffrement.  
> Elle constitue une mesure complémentaire de sécurité.

---

### 1.4 Positionnement réglementaire

- Le microservice met en œuvre un traitement de pseudonymisation
- Les données produites restent des données personnelles
