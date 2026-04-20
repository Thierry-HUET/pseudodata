# Spécification – Exigences formelles
## Microservice de pseudonymisation

---

## 1. Exigences générales

### REQ‑GEN‑01 – Nature du composant

Le système SHALL être implémenté sous la forme d'un microservice conteneurisé, déployable via Docker.

---

### REQ‑GEN‑02 – Finalité du traitement

Le microservice SHALL réaliser deux opérations complémentaires :
- La pseudonymisation : substitution d'identifiants directs par des pseudonymes
- La dépseudonymisation : restauration des valeurs originales à partir de la table de correspondance

Le traitement SHALL être réversible sous conditions maîtrisées.

---

### REQ‑GEN‑03 – Caractère des données produites

Les données produites par le microservice SHALL rester des données à caractère personnel.

Le microservice MUST NOT être utilisé comme mécanisme d'anonymisation irréversible.

---

### REQ‑GEN‑04 – Langage d'implémentation

Le microservice SHALL être développé en Python.

---

## 2. Exigences de cas d'usage

### REQ‑USE‑01 – Pseudonymisation avant traitement avec dépseudonymisation

Le microservice SHALL permettre la pseudonymisation de données en vue de leur transmission pour traitement ultérieur.

Ce cas d'usage SHALL préserver les capacités de rapprochement, d'analyse et de production de statistiques.

La ré‑identification (dépseudonymisation) SHALL être possible pour l'émetteur disposant de la table de correspondance.

---

### REQ‑USE‑02 – Pseudonymisation pour transmission sur réseau non sécurisé

Le microservice SHALL permettre une pseudonymisation destinée à réduire le risque en cas de transmission sur un canal non chiffré.

Dans ce cas
- La table de correspondance MUST NOT être transmise avec les données pseudonymisées
- Le destinataire SHALL être incapable de procéder à une ré‑identification
- La dépseudonymisation MUST NOT être proposée dans ce cas d'usage

---

### REQ‑USE‑03 – Limites de sécurité

Le microservice MUST NOT être présenté comme un substitut à un mécanisme de chiffrement des communications.

---

## 3. Exigences d'entrée

### REQ‑IN‑01 – Formats de fichiers supportés

Le microservice SHALL accepter en entrée des fichiers structurés aux formats suivants, pour la pseudonymisation comme pour la dépseudonymisation
- CSV
- JSON
- XML
- Parquet
- Excel (XLSX)

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

### REQ‑IN‑04 – Entrées requises pour la dépseudonymisation

Toute opération de dépseudonymisation SHALL nécessiter la fourniture simultanée de
- Le fichier pseudonymisé à restaurer
- La table de correspondance produite lors de la pseudonymisation
- Le fichier de signature associé

---

## 4. Exigences d'identification des champs

### REQ‑ID‑01 – Mode explicite

Le microservice SHALL permettre la désignation explicite des champs à pseudonymiser
- Par nom de colonne
- Par chemin de donnée (JSON / XML)

Ce mode SHALL être obligatoire et constituer le socle fonctionnel.

---

### REQ‑ID‑02 – Mode implicite assisté

Le microservice MAY proposer une fonctionnalité d'identification assistée des champs sensibles.

Cette fonctionnalité
- SHALL s'appuyer sur des règles simples (nom, type, longueur, régularités)
- SHALL être limitée aux données tabulaires

---

### REQ‑ID‑03 – Validation obligatoire

Le microservice MUST NOT pseudonymiser un champ sur la seule base d'une détection automatique.

Toute pseudonymisation SHALL nécessiter une validation explicite.

---

### REQ‑ID‑04 – Cohérence des colonnes pour la dépseudonymisation

Les noms de colonnes du fichier soumis à la dépseudonymisation SHALL être identiques à ceux utilisés lors de la pseudonymisation.

Tout écart SHALL être signalé et bloquer le traitement.

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

### REQ‑OUT‑04 – Artefacts de sortie obligatoires (pseudonymisation)

À chaque exécution de pseudonymisation, le microservice SHALL produire les artefacts suivants :
- Le fichier pseudonymisé
- Une table de correspondance permettant la ré‑identification contrôlée
- Un manifeste d'exécution au format JSON
- Un fichier de signature garantissant l'intégrité des artefacts

Ces artefacts SHALL être produits systématiquement, y compris en cas de succès partiel.

---

### REQ‑OUT‑05 – Fichier restauré (dépseudonymisation)

Le microservice SHALL produire un fichier restauré dans le même format que le fichier pseudonymisé soumis en entrée.

---

### REQ‑OUT‑06 – Rapport de dépseudonymisation

Le microservice SHALL produire un rapport de dépseudonymisation au format JSON.

Ce rapport SHALL contenir au minimum :
- Un identifiant d'exécution unique
- Un horodatage
- Les colonnes traitées
- Les compteurs de valeurs restaurées et d'orphelins (pseudonymes absents de la table)

Ce rapport MUST NOT contenir de valeurs originales ni de pseudonymes.

---

## 6. Exigences de comportement

### REQ‑BEH‑01 – Déterminisme

Le traitement SHALL être déterministe.

Une même valeur source SHALL produire le même pseudonyme dans un contexte donné.

---

### REQ‑BEH‑02 – Réversibilité contrôlée

La ré‑identification SHALL être possible uniquement par l'accès à la table de correspondance.

La dépseudonymisation SHALL être réservée au seul cas d'usage REQ‑USE‑01.

---

### REQ‑BEH‑03 – Traçabilité

Le microservice SHALL produire une journalisation minimale pour chaque opération (pseudonymisation et dépseudonymisation) comprenant
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
- Dépseudonymisation dans le cadre du cas d'usage REQ‑USE‑02

---

## 8. Exigences d'interfaces et de pilotage

### REQ‑INT‑01 – Pilotage par API

Le microservice SHALL exposer une API permettant
- La soumission d'un fichier pour pseudonymisation
- La fourniture des règles de pseudonymisation
- La récupération du fichier pseudonymisé et des artefacts associés
- La soumission d'un fichier pour dépseudonymisation, avec sa table de correspondance et son fichier de signature
- La récupération du fichier restauré et du rapport de dépseudonymisation

---

### REQ‑INT‑02 – Pilotage par interface Web

Le microservice SHALL proposer une interface Web développée avec Streamlit.

L'interface SHALL comporter trois pages distinctes
- **Page 1** – Pseudonymisation et dépseudonymisation (REQ‑USE‑01)
- **Page 2** – Pseudonymisation pour transmission sur réseau non sécurisé (REQ‑USE‑02)
- **Page 3** – Documentation et à propos

L'affichage SHALL être conforme aux conventions Bootstrap (mise en page, typographie, composants).

---

### REQ‑INT‑03 – Page 1 : pseudonymisation et dépseudonymisation (REQ‑USE‑01)

Cette page SHALL proposer deux onglets ou sections distincts : **Pseudonymiser** et **Dépseudonymiser**.

**Section Pseudonymiser**

Inputs obligatoires
- Fichier source (upload) — formats acceptés : CSV, JSON, XML, Parquet, XLSX
- Sélection des colonnes à pseudonymiser
  - Mode explicite : saisie ou sélection des noms de colonnes
  - Mode assisté : suggestion automatique soumise à validation explicite de l'utilisateur
- Longueur de troncature des pseudonymes (défaut : 22 ; 0 = sans limite)

Inputs optionnels
- Séparateur CSV (défaut : `,`)
- Encodage CSV (défaut : `utf-8`)
- Nom de feuille XLSX

Sorties disponibles au téléchargement
- Fichier pseudonymisé
- Table de correspondance (conditionnée à une autorisation explicite de l'utilisateur)
- Manifeste JSON
- Fichier de signature

**Section Dépseudonymiser**

Inputs obligatoires
- Fichier pseudonymisé (upload) — formats acceptés : CSV, JSON, XML, Parquet, XLSX
- Table de correspondance (upload)
- Fichier de signature (upload)

Inputs optionnels
- Séparateur CSV (défaut : `,`)
- Encodage CSV (défaut : `utf-8`)
- Nom de feuille XLSX

Sorties disponibles au téléchargement
- Fichier restauré
- Rapport de dépseudonymisation JSON

Contraintes spécifiques
- Le traitement SHALL être bloqué et un message d'erreur explicite SHALL être affiché si la vérification d'intégrité échoue

---

### REQ‑INT‑04 – Page 2 : pseudonymisation pour transmission sur réseau non sécurisé (REQ‑USE‑02)

Cette page SHALL permettre la pseudonymisation sans réversibilité côté destinataire.

Inputs obligatoires
- Fichier source (upload) — formats acceptés : CSV, JSON, XML, Parquet, XLSX
- Sélection des colonnes à pseudonymiser
  - Mode explicite : saisie ou sélection des noms de colonnes
  - Mode assisté : suggestion automatique soumise à validation explicite de l'utilisateur
- Longueur de troncature des pseudonymes (défaut : 22 ; 0 = sans limite)

Inputs optionnels
- Séparateur CSV (défaut : `,`)
- Encodage CSV (défaut : `utf-8`)
- Nom de feuille XLSX

Contraintes spécifiques
- La table de correspondance MUST NOT être proposée au téléchargement sur cette page
- La dépseudonymisation MUST NOT être accessible depuis cette page
- Un avertissement SHALL être affiché rappelant que la pseudonymisation ne se substitue pas au chiffrement

Sorties disponibles au téléchargement
- Fichier pseudonymisé
- Manifeste JSON
- Fichier de signature

---

### REQ‑INT‑05 – Page 3 : documentation et à propos

Cette page SHALL présenter
- La description fonctionnelle du microservice
- Les deux cas d'usage et leurs différences, y compris les conditions d'accès à la dépseudonymisation
- Le positionnement réglementaire (RGPD, nature des données produites)
- Les formats supportés
- Les limites et points d'attention
- Les informations de version et de licence

---

## 9. Exigences de sécurité

### REQ‑SEC‑01 – Principe de minimisation des données

Le microservice SHALL traiter uniquement les données strictement nécessaires à l'opération en cours (pseudonymisation ou dépseudonymisation).

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
- Variables d'environnement
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

Les journaux SHALL être exploitables à des fins d'audit et d'investigation.

---

### REQ‑SEC‑07 – Protection contre les usages abusifs

Le microservice SHOULD inclure des mécanismes de limitation permettant d'éviter
- Les appels excessifs
- Les traitements involontaires ou massifs non autorisés

---

### REQ‑SEC‑08 – Principe de défense en profondeur

La sécurité du microservice SHALL reposer sur plusieurs niveaux complémentaires
- Isolation du conteneur
- Séparation des données et des secrets
- Traçabilité

Aucun mécanisme de sécurité unique SHALL être considéré comme suffisant.

---

## 10. Exigences de traçabilité

### REQ‑TRA‑01 – Manifeste d'exécution (pseudonymisation)

Le microservice SHALL générer un manifeste d'exécution au format JSON pour chaque opération de pseudonymisation.

Le manifeste SHALL contenir au minimum :
- Un identifiant d'exécution unique
- Un horodatage
- Le schéma d'entrée observé
- Les colonnes demandées, effectives et absentes
- Les statistiques de couverture par colonne
- Les chemins et formats des artefacts générés

---

### REQ‑TRA‑02 – Tolérance aux écarts de schéma (pseudonymisation)

Si certaines colonnes demandées sont absentes du fichier réel :
- Le traitement SHALL se poursuivre
- Les écarts SHALL être consignés dans le manifeste
- Le résultat SHALL être qualifié de succès partiel

---

### REQ‑TRA‑03 – Rapport d'exécution (dépseudonymisation)

Le microservice SHALL générer un rapport au format JSON pour chaque opération de dépseudonymisation.

Ce rapport SHALL contenir au minimum :
- Un identifiant d'exécution unique
- Un horodatage
- Les colonnes traitées
- Les compteurs de valeurs restaurées et d'orphelins

Ce rapport MUST NOT contenir de valeurs originales ni de pseudonymes.

---

## 11. Exigences cryptographiques

### REQ‑CRY‑01 – Algorithme de pseudonymisation

La pseudonymisation SHALL reposer sur un mécanisme déterministe.

Un algorithme de type HMAC basé sur une fonction de hachage cryptographique SHOULD être utilisé.

---

### REQ‑CRY‑02 – Déterminisme inter‑exécutions

À clé identique, une même valeur source SHALL produire le même pseudonyme entre plusieurs exécutions, afin de permettre des jointures entre jeux de données pseudonymisés.

---

### REQ‑CRY‑03 – Réversibilité exclusivement externe

Le mécanisme cryptographique seul MUST NOT permettre la ré‑identification.

La réversibilité SHALL être assurée exclusivement par la table de correspondance.

---

## 12. Exigences d'intégrité

### REQ‑INTG‑01 – Signature des artefacts

Le microservice SHALL produire un fichier de signature couvrant :
- Le fichier source
- Le fichier pseudonymisé
- La table de correspondance
- Le manifeste

---

### REQ‑INTG‑02 – Vérification préalable à la dépseudonymisation

Toute opération de dépseudonymisation MUST inclure une vérification d'intégrité des fichiers fournis (fichier pseudonymisé, table de correspondance) par rapport au fichier de signature.

Le traitement SHALL être bloqué si une modification est détectée.

Un message d'erreur explicite SHALL être produit en cas d'échec de la vérification.

---

## 13. Exigences d'interface en ligne de commande

### REQ‑CLI‑01 – Interface CLI de pseudonymisation

Le microservice SHALL pouvoir être piloté via une interface en ligne de commande pour la pseudonymisation.

Cette interface SHALL permettre :
- La spécification du fichier d'entrée
- La désignation explicite des colonnes à pseudonymiser
- La localisation des artefacts de sortie (fichier pseudonymisé, table de correspondance, manifeste, signature)

---

### REQ‑CLI‑02 – Interface CLI de dépseudonymisation

Le microservice SHALL pouvoir être piloté via une interface en ligne de commande pour la dépseudonymisation.

Cette interface SHALL permettre :
- La spécification du fichier pseudonymisé à restaurer
- La fourniture de la table de correspondance
- La fourniture du fichier de signature
- La localisation du fichier restauré en sortie

---

### REQ‑CLI‑03 – Codes de retour normalisés

L'interface CLI SHALL retourner des codes distincts pour :
- Succès complet
- Succès partiel
- Erreur bloquante

Ces codes SHALL s'appliquer à la pseudonymisation comme à la dépseudonymisation.

---
