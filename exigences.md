# Spécification – Exigences formelles
## Microservice de pseudonymisation

---

## 1. Exigences générales

### REQ‑GEN‑01 – Nature du composant

Le système SHALL être implémenté sous la forme d’un microservice conteneurisé, déployable via Docker.

---

### REQ‑GEN‑02 – Finalité du traitement

Le microservice SHALL réaliser un traitement de pseudonymisation au sens du RGPD, consistant en la substitution d’identifiants directs par des pseudonymes.

Le traitement SHALL être réversible sous conditions maîtrisées.

---

### REQ‑GEN‑03 – Caractère des données produites

Les données produites par le microservice SHALL rester des données à caractère personnel.

Le microservice MUST NOT être utilisé comme mécanisme d’anonymisation irréversible.

---

### REQ‑GEN‑04 – Langage d’implémentation

Le microservice SHALL être développé en Python.

---

## 2. Exigences de cas d’usage

### REQ‑USE‑01 – Pseudonymisation avant traitement

Le microservice SHALL permettre la pseudonymisation de données en vue de leur transmission pour traitement ultérieur.

Ce cas d’usage SHALL préserver les capacités de rapprochement, d’analyse et de production de statistiques.

---

### REQ‑USE‑02 – Pseudonymisation pour transmission sur réseau non sécurisé

Le microservice SHALL permettre une pseudonymisation destinée à réduire le risque en cas de transmission sur un canal non chiffré.

Dans ce cas
- La table de correspondance MUST NOT être transmise avec les données pseudonymisées
- Le destinataire SHALL être incapable de procéder à une ré‑identification

---

### REQ‑USE‑03 – Limites de sécurité

Le microservice MUST NOT être présenté comme un substitut à un mécanisme de chiffrement des communications.

---

## 3. Exigences d’entrée

### REQ‑IN‑01 – Formats de fichiers supportés

Le microservice SHALL accepter en entrée des fichiers structurés aux formats suivants
- CSV
- JSON
- XML
- Parquet

---

### REQ‑IN‑02 – Nature des données traitées

Le microservice SHALL traiter exclusivement des données structurées.

Le traitement de texte libre SHALL être considéré comme hors périmètre.

---

### REQ‑IN‑03 – Règles de pseudonymisation

Le microservice SHALL accepter un jeu de règles de pseudonymisation fourni
- Soit par configuration
- Soit à chaque appel

---

## 4. Exigences d’identification des champs

### REQ‑ID‑01 – Mode explicite

Le microservice SHALL permettre la désignation explicite des champs à pseudonymiser
- Par nom de colonne
- Par chemin de donnée (JSON / XML)

Ce mode SHALL être obligatoire et constituer le socle fonctionnel.

---

### REQ‑ID‑02 – Mode implicite assisté

Le microservice MAY proposer une fonctionnalité d’identification assistée des champs sensibles.

Cette fonctionnalité
- SHALL s’appuyer sur des règles simples (nom, type, longueur, régularités)
- SHALL être limitée aux données tabulaires

---

### REQ‑ID‑03 – Validation obligatoire

Le microservice MUST NOT pseudonymiser un champ sur la seule base d’une détection automatique.

Toute pseudonymisation SHALL nécessiter une validation explicite.

---

## 5. Exigences de sortie

### REQ‑OUT‑01 – Fichier pseudonymisé

Le microservice SHALL produire un fichier pseudonymisé dans le même format que le fichier source.

---

### REQ‑OUT‑02 – Table de correspondance

Le microservice SHALL pouvoir produire une table de correspondance permettant la ré‑identification.

La production de cette table SHALL être conditionnée à une autorisation explicite.

---

### REQ‑OUT‑03 – Séparation des données

La table de correspondance SHALL être séparée physiquement ou logiquement du fichier pseudonymisé.

---

## 6. Exigences de comportement

