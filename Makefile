# ==============================================================================
# Makefile – pseudodata
# ==============================================================================
# Usage :
#   make release                 → commit, tag et push avec la version du fichier VERSION
#   make commit                  → commit simple (sans changement de version ni tag)
#   make push                    → push branche courante + tags
#   make status                  → affiche l'état git
#   make version                 → affiche la version courante
#   make run                     → lance l'interface Streamlit (port : STREAMLIT_PORT, défaut 8501)
#
# Pour changer de version : éditer le fichier VERSION, puis lancer make release
# Pour changer le port    : STREAMLIT_PORT=8502 make run
# ==============================================================================

.DEFAULT_GOAL := help

# Horodatage ISO 8601 local
DATE := $(shell date '+%Y-%m-%d %H:%M:%S')

# Version lue depuis le fichier VERSION (trim des espaces et sauts de ligne)
VERSION := $(shell cat VERSION | tr -d '[:space:]')

# Branche courante
BRANCH := $(shell git rev-parse --abbrev-ref HEAD)

# Port Streamlit — surchargeable via variable d'environnement
STREAMLIT_PORT ?= 8501

# Répertoire et nom du fichier SBOM
SBOM_DIR      ?= docs/cra
SBOM_FILE     ?= $(SBOM_DIR)/sbom.json

# ------------------------------------------------------------------------------
.PHONY: help
help:
	@echo ""
	@echo "  make release    Commit, tag v$(VERSION) et push  (version lue depuis VERSION)"
	@echo "  make commit     Commit de tous les fichiers modifiés (sans tag)"
	@echo "  make push       Push branche courante + tags vers origin"
	@echo "  make status     État du dépôt git"
	@echo "  make version    Affiche la version courante"
	@echo "  make run        Lance l'interface Streamlit (STREAMLIT_PORT=$(STREAMLIT_PORT))"
	@echo "  make sbom       Génère le SBOM CycloneDX JSON dans $(SBOM_FILE)"
	@echo ""
	@echo "  → Pour changer de version : éditer le fichier VERSION puis make release"
	@echo "  → Pour changer le port    : STREAMLIT_PORT=8502 make run"
	@echo "  → Pour changer le répertoire SBOM : SBOM_DIR=. make sbom"
	@echo ""

# ------------------------------------------------------------------------------
.PHONY: version
version:
	@echo "Version courante : $(VERSION)"

# ------------------------------------------------------------------------------
.PHONY: status
status:
	@git status

# ------------------------------------------------------------------------------
.PHONY: run
run:
	@echo "→ Démarrage Streamlit sur le port $(STREAMLIT_PORT)..."
	STREAMLIT_PORT=$(STREAMLIT_PORT) streamlit run app.py --server.port $(STREAMLIT_PORT)

# ------------------------------------------------------------------------------
.PHONY: commit
commit:
	@echo "→ Ajout de tous les fichiers modifiés..."
	@git add -A
	@git diff --cached --quiet \
		&& echo "  Rien à committer." \
		|| git commit -m "[$(DATE)] mise à jour"
	@echo "  Branche : $(BRANCH)"

# ------------------------------------------------------------------------------
.PHONY: push
push:
	@echo "→ Push vers origin/$(BRANCH) (avec tags)..."
	@git push origin $(BRANCH) --tags
	@echo "  Push terminé."

# ------------------------------------------------------------------------------
.PHONY: sbom
sbom:
	@echo "→ Génération du SBOM CycloneDX ($(SBOM_FILE))..."
	@command -v cyclonedx-py >/dev/null 2>&1 \
		|| { echo "  ✗ cyclonedx-py absent — installation : pip install cyclonedx-bom"; exit 1; }
	@mkdir -p $(SBOM_DIR)
	@cyclonedx-py requirements requirements.txt \
		--of JSON \
		--sv 1.6 \
		-o $(SBOM_FILE)
	@echo "  ✓ SBOM généré : $(SBOM_FILE)"
	@python3 -c "import json; d=json.load(open('$(SBOM_FILE)')); print('  Composants :', len(d.get('components', [])), 'dépendances indexées')"

# ------------------------------------------------------------------------------
.PHONY: release
release:
	@echo "→ Version : $(VERSION)"
	@# Synchronisation de pyproject.toml avec le fichier VERSION
	@CURRENT=$$(grep '^version' pyproject.toml | sed 's/version = "\(.*\)"/\1/'); \
	 sed -i.bak "s/^version = \"$$CURRENT\"/version = \"$(VERSION)\"/" pyproject.toml \
	 && rm -f pyproject.toml.bak
	@echo "  pyproject.toml synchronisé."
	@# Vérification qu'il y a quelque chose à committer
	@git add -A
	@git diff --cached --quiet \
		&& echo "  Rien à committer." \
		|| git commit -m "[$(DATE)] release $(VERSION)"
	@# Tag annoté (échoue proprement si le tag existe déjà)
	@if git rev-parse "v$(VERSION)" >/dev/null 2>&1; then \
		echo "  ⚠ Tag v$(VERSION) déjà existant — skippé."; \
	else \
		git tag -a "v$(VERSION)" -m "[$(DATE)] release $(VERSION)"; \
		echo "  Tag v$(VERSION) créé."; \
	fi
	@# Push
	@git push origin $(BRANCH) --tags
	@echo ""
	@echo "  ✓ Release $(VERSION) publiée sur $(BRANCH)."
