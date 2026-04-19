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

### REQ‑BEH‑01 – Déterminisme

Le traitement SHALL être déterministe.

Une même valeur source SHALL produire le même pseudonyme dans un contexte donné.

---

### REQ‑BEH‑02 – Réversibilité contrôlée

La ré‑identification SHALL être possible uniquement par l’accès à la table de correspondance.

---

### REQ‑BEH‑03 – Traçabilité

Le microservice SHALL produire une journalisation minimale comprenant
- La date du traitement
- Le type de traitement
- Le jeu de règles appliqué

---

### REQ‑BEH‑04 – Stateless par défaut

Le microservice SHALL être stateless par défaut.

Toute persistance SHALL être explicitement configurée.

---

## 7. Exigences hors périmètre

### REQ‑OOS‑01 – Traitements exclus

Sont explicitement hors périmètre
- Anonymisation irréversible
- Chiffrement de bout en bout
- Analyse sémantique avancée de texte libre
- Décisions automatiques non validées concernant la sensibilité des champs

---

## 8. Exigences d’interfaces et de pilotage

### REQ‑INT‑01 – Pilotage par API

Le microservice SHALL exposer une API permettant
- La soumission d’un fichier
- La fourniture des règles de pseudonymisation
- La récupération du fichier pseudonymisé

---

### REQ‑INT‑02 – Pilotage par interface Web

Le microservice SHALL proposer une interface Web permettant
- La sélection du fichier à traiter
- La configuration des règles de pseudonymisation
- Le déclenchement du traitement
- Le téléchargement du résultat

---

### REQ‑INT‑03 – Technologie de l’interface Web

L’interface Web SHALL être développée avec Streamlit.

## 9. Exigences de sécurité

### REQ‑SEC‑01 – Principe de minimisation des données

Le microservice SHALL traiter uniquement les données strictement nécessaires à l’opération de pseudonymisation.

Aucune donnée inutile au traitement MUST NOT être conservée ou exposée.

---

### REQ‑SEC‑02 – Séparation des secrets et des données

Les éléments permettant la ré‑identification (tables de correspondance, clés, secrets) SHALL être séparés
- Logiquement
- Et/ou physiquement

Ils MUST NOT être stockés dans le même emplacement que les données pseudonymisées par défaut.

---

### REQ‑SEC‑03 – Gestion des secrets

Les secrets utilisés par le microservice (clés, sels, identifiants, accès) MUST NOT être
- Codés en dur
- Versionnés dans le dépôt Git

Ils SHALL être fournis via
- Variables d’environnement
- Ou un mécanisme externe de gestion de secrets

---

### REQ‑SEC‑04 – Isolation du service

Le microservice SHALL être isolé du système hôte conformément aux bonnes pratiques Docker.

Il MUST NOT nécessiter de privilèges élevés (root) pour fonctionner.

---

### REQ‑SEC‑05 – Exposition réseau

Le microservice SHALL exposer uniquement les ports strictement nécessaires
- API
- Interface Web

Tout autre port MUST NOT être exposé.

---

### REQ‑SEC‑06 – Journalisation sécurisée

Les journaux produits par le microservice
- MUST NOT contenir de données pseudonymisées exploitables
- MUST NOT contenir la table de correspondance ou des secrets

Les journaux SHALL être exploitables à des fins d’audit et d’investigation.

---

### REQ‑SEC‑07 – Protection contre les usages abusifs

Le microservice SHOULD inclure des mécanismes de limitation permettant d’éviter
- Les appels excessifs
- Les traitements involontaires ou massifs non autorisés

---

### REQ‑SEC‑08 – Principe de défense en profondeur

La sécurité du microservice SHALL reposer sur plusieurs niveaux complémentaires
- Isolation du conteneur
- Séparation des données et des secrets
- Traçabilité

Aucun mécanisme de sécurité unique SHALL être considéré comme suffisant.
