#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Outil batch de pseudonymisation (CSV / Parquet / XLSX)

Produit pour chaque exécution :
- un fichier pseudonymisé
- une table de correspondance (réversibilité)
- un manifeste JSON horodaté (<output>.manifeste.json)

Stratégie : HMAC-SHA256 déterministe
Secret     : variable d'environnement PSEUDONYMIZER_SECRET
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import hmac
import json
import os
import secrets
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

ALGO_NAME: str = "hmac_sha256"
ENV_SECRET: str = "PSEUDONYMIZER_SECRET"
SUPPORTED_FORMATS: frozenset[str] = frozenset({".csv", ".parquet", ".pq", ".xlsx"})
DEFAULT_TRUNCATE: int = 22
SECRET_MIN_LENGTH: int = 32
SIGNATURE_VERSION: str = "1"
FILE_READ_CHUNK: int = 8 * 1024 * 1024  # 8 MiB — lecture par blocs pour les grands fichiers


# ---------------------------------------------------------------------------
# Utilitaires temporels et identification
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    """Retourne l'horodatage courant au format ISO 8601 avec fuseau horaire."""
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def _run_id() -> str:
    """
    Génère un identifiant d'exécution horodaté et non prédictible.

    Utilise ``secrets.token_hex`` (CSPRNG) plutôt que ``uuid4``
    pour garantir la non-prédictibilité de la partie aléatoire.

    Format : <ISO8601>_<8 hex>
    Exemple : 2026-03-27T06:52:40+01:00_3fa19c2b
    """
    ts = dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")
    return f"{ts}_{secrets.token_hex(4)}"


# ---------------------------------------------------------------------------
# Gestion du secret
# ---------------------------------------------------------------------------


def _secret_from_env() -> str:
    """
    Lit le secret depuis la variable d'environnement PSEUDONYMIZER_SECRET.

    Raises
    ------
    RuntimeError
        Si la variable est absente ou vide.
    ValueError
        Si le secret est inférieur à SECRET_MIN_LENGTH caractères.
    """
    secret = os.environ.get(ENV_SECRET, "").strip()
    if not secret:
        raise RuntimeError(
            f"Secret absent — définir la variable d'environnement {ENV_SECRET}"
        )
    if len(secret) < SECRET_MIN_LENGTH:
        raise ValueError(
            f"Secret trop court ({len(secret)} car.) — minimum : {SECRET_MIN_LENGTH}"
        )
    return secret


def _secret_fingerprint(secret: str) -> str:
    """
    Retourne une empreinte courte et non réversible du secret.

    Permet de détecter un changement de clé entre deux exécutions
    sans divulguer la valeur du secret.

    Format : ``sha256:<16 premiers hex>``
    """
    digest = hashlib.sha256(secret.encode("utf-8")).hexdigest()
    return f"sha256:{digest[:16]}"


# ---------------------------------------------------------------------------
# Pseudonymisation
# ---------------------------------------------------------------------------


def _hmac_pseudonym(secret_bytes: bytes, value: str, truncate: int) -> str:
    """
    Calcule le pseudonyme HMAC-SHA256 d'une valeur textuelle.

    Parameters
    ----------
    secret_bytes:
        Clé HMAC pré-encodée en bytes (calculée une seule fois hors boucle).
    value:
        Valeur originale à pseudonymiser (normalisée par strip).
    truncate:
        Longueur du pseudonyme en sortie (0 = longueur complète).

    Returns
    -------
    str
        Pseudonyme base64 URL-safe sans padding ``=``.
    """
    msg = value.strip().encode("utf-8")
    digest = hmac.new(secret_bytes, msg=msg, digestmod=hashlib.sha256).digest()
    token = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return token[:truncate] if truncate > 0 else token


# ---------------------------------------------------------------------------
# Détection de format et I/O
# ---------------------------------------------------------------------------


def _detect_format(path: Path) -> str:
    """
    Détecte le format du fichier à partir de son extension.

    Raises
    ------
    ValueError
        Si l'extension n'est pas dans SUPPORTED_FORMATS.
    """
    ext = path.suffix.lower()
    mapping = {".csv": "csv", ".parquet": "parquet", ".pq": "parquet", ".xlsx": "xlsx"}
    if ext not in mapping:
        raise ValueError(
            f"Extension non supportée : '{ext}' "
            f"— formats acceptés : {', '.join(sorted(SUPPORTED_FORMATS))}"
        )
    return mapping[ext]


def _read_input(
    path: Path,
    sheet: Optional[str],
    sep: str,
    encoding: str,
) -> Tuple[pd.DataFrame, str]:
    """
    Lit le fichier source et retourne (DataFrame, format détecté).

    Notes
    -----
    - CSV / XLSX : ``dtype=str`` pour préserver les zéros initiaux
      et les identifiants textuels.
    - Parquet : types natifs conservés (pas de coercition str).
    """
    fmt = _detect_format(path)

    if fmt == "csv":
        df = pd.read_csv(path, sep=sep, encoding=encoding, dtype=str, keep_default_na=True)
    elif fmt == "parquet":
        df = pd.read_parquet(path)
    else:  # xlsx
        df = pd.read_excel(path, sheet_name=sheet or 0, dtype=str)

    return df, fmt


def _write_output(
    df: pd.DataFrame,
    path: Path,
    sheet: Optional[str],
    sep: str,
    encoding: str,
) -> str:
    """Écrit le DataFrame pseudonymisé ; crée les répertoires parents si nécessaire."""
    fmt = _detect_format(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "csv":
        df.to_csv(path, index=False, sep=sep, encoding=encoding)
    elif fmt == "parquet":
        df.to_parquet(path, index=False)
    else:
        df.to_excel(path, index=False, sheet_name=sheet or "Sheet1")
    return fmt


def _write_mapping(
    mapping_df: pd.DataFrame,
    path: Path,
    sep: str,
    encoding: str,
) -> str:
    """Écrit la table de correspondance ; crée les répertoires parents si nécessaire."""
    fmt = _detect_format(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "csv":
        mapping_df.to_csv(path, index=False, sep=sep, encoding=encoding)
    elif fmt == "parquet":
        mapping_df.to_parquet(path, index=False)
    else:
        mapping_df.to_excel(path, index=False, sheet_name="Correspondance")
    return fmt


# ---------------------------------------------------------------------------
# Transformation principale
# ---------------------------------------------------------------------------


def _build_mapping_and_transform(
    df: pd.DataFrame,
    columns: List[str],
    secret: str,
    truncate: int,
    run_id: str,
    created_at: str,
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Dict[str, float]]]:
    """
    Pseudonymise les colonnes désignées et construit la table de correspondance.

    Optimisation performance
    ------------------------
    Le secret est encodé en bytes **une seule fois** avant la boucle.
    Le calcul HMAC est effectué sur les **valeurs uniques** uniquement,
    puis réappliqué par ``Series.map`` — complexité O(unique) vs O(n).

    Parameters
    ----------
    df:
        DataFrame source (non modifié en place).
    columns:
        Colonnes effectives à traiter (présentes dans df).
    secret:
        Clé HMAC en clair.
    truncate:
        Longueur de troncature (0 = sans limite).
    run_id:
        Identifiant d'exécution pour traçabilité.
    created_at:
        Horodatage ISO 8601 de l'exécution.

    Returns
    -------
    df_pseudo : pd.DataFrame
        Copie du DataFrame avec les colonnes pseudonymisées.
    mapping_df : pd.DataFrame
        Table de correspondance en format long (une ligne par valeur unique).
    stats : dict
        Statistiques par colonne : non_nul, transformees, taux.
    """
    secret_bytes: bytes = secret.encode("utf-8")
    df_pseudo = df.copy()
    mapping_rows: List[dict] = []
    stats: Dict[str, Dict[str, float]] = {}

    for col in columns:
        series = df_pseudo[col]
        non_null_mask = series.notna()
        non_null_count = int(non_null_mask.sum())

        if non_null_count == 0:
            stats[col] = {"non_nul": 0.0, "transformees": 0.0, "taux": 0.0}
            continue

        s_str = series[non_null_mask].astype(str)
        unique_vals: list[str] = s_str.unique().tolist()

        # Calcul HMAC sur valeurs uniques uniquement
        pseudo_map: Dict[str, str] = {
            v: _hmac_pseudonym(secret_bytes, v, truncate) for v in unique_vals
        }

        # Application vectorisée
        df_pseudo.loc[non_null_mask, col] = s_str.map(pseudo_map)

        # Alimentation de la table de correspondance
        for orig, pseudo in pseudo_map.items():
            mapping_rows.append({
                "id_execution":       run_id,
                "colonne":            col,
                "valeur_originale":   orig,
                "valeur_pseudonymisee": pseudo,
                "algorithme":         ALGO_NAME,
                "horodatage_creation": created_at,
            })

        stats[col] = {
            "non_nul":      float(non_null_count),
            "transformees": float(non_null_count),
            "taux":         1.0,
        }

    _MAPPING_COLS = [
        "id_execution", "colonne", "valeur_originale",
        "valeur_pseudonymisee", "algorithme", "horodatage_creation",
    ]
    mapping_df = (
        pd.DataFrame(mapping_rows)
        if mapping_rows
        else pd.DataFrame(columns=_MAPPING_COLS)
    )
    return df_pseudo, mapping_df, stats


# ---------------------------------------------------------------------------
# Manifeste
# ---------------------------------------------------------------------------


def _manifest_path(output_path: Path) -> Path:
    """Retourne le chemin du manifeste JSON associé au fichier de sortie."""
    return output_path.with_name(output_path.name + ".manifeste.json")


def _build_manifest(
    *,
    run_id: str,
    created_at: str,
    input_path: Path,
    input_fmt: str,
    df_in: pd.DataFrame,
    requested_columns: List[str],
    effective_columns: List[str],
    missing_columns: List[str],
    stats: Dict[str, Dict[str, float]],
    truncate: int,
    secret_fingerprint: str,
    output_path: Path,
    output_fmt: str,
    mapping_path: Path,
    mapping_fmt: str,
    mapping_rows: int,
) -> dict:
    """
    Construit le dictionnaire du manifeste JSON.

    Tous les paramètres sont nommés (keyword-only) pour éviter
    les erreurs de position sur une signature longue.
    """
    eligible   = sum(int(s["non_nul"])      for s in stats.values())
    transformed = sum(int(s["transformees"]) for s in stats.values())
    taux_global = float(transformed / eligible) if eligible else 0.0

    return {
        "id_execution":       run_id,
        "horodatage_creation": created_at,
        "entree": {
            "chemin":   str(input_path),
            "format":   input_fmt,
            "lignes":   int(df_in.shape[0]),
            "colonnes": int(df_in.shape[1]),
        },
        "colonnes_demandees":  requested_columns,
        "colonnes_effectives": effective_columns,
        "colonnes_absentes":   missing_columns,
        "pseudonymisation": {
            "algorithme":              ALGO_NAME,
            "empreinte_secret":        secret_fingerprint,
            "troncature":              truncate,
            "statistiques_par_colonne": stats,
            "taux_global":             taux_global,
        },
        "sorties": {
            "pseudonymise":  {"chemin": str(output_path),  "format": output_fmt},
            "correspondance": {
                "chemin": str(mapping_path),
                "format": mapping_fmt,
                "lignes": mapping_rows,
            },
            "manifeste": {
                "chemin": str(_manifest_path(output_path)),
                "format": "json",
            },
        },
    }


# ---------------------------------------------------------------------------
# Signature d'intégrité
# ---------------------------------------------------------------------------


def _sha256_file(path: Path) -> str:
    """
    Calcule le SHA-256 d'un fichier par lecture en blocs (compatible grands volumes).

    Parameters
    ----------
    path:
        Chemin du fichier à empreindre.

    Returns
    -------
    str
        Empreinte hexadécimale SHA-256 (64 caractères).
    """
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while chunk := fh.read(FILE_READ_CHUNK):
            h.update(chunk)
    return h.hexdigest()


def _sign_files(
    *,
    secret: str,
    run_id: str,
    created_at: str,
    files: Dict[str, Path],
) -> dict:
    """
    Construit le document de signature HMAC-SHA256 pour un ensemble de fichiers.

    Protocole
    ---------
    Pour chaque fichier :
      1. Calcul de l'empreinte SHA-256 du contenu binaire (``sha256_contenu``).
      2. Calcul d'un HMAC-SHA256 sur la concaténation canonique :
         ``<role>|<chemin_absolu>|<sha256_contenu>|<run_id>``
         La liaison au ``run_id`` lie la signature à l'exécution précise
         et empêche le rejeu d'une signature valide sur un autre run.

    Le document de signature est lui-même signé (``hmac_document``) sur
    la sérialisation JSON triée de l'ensemble des entrées, ce qui garantit
    l'intégrité de la structure complète du fichier.

    Parameters
    ----------
    secret:
        Clé HMAC en clair.
    run_id:
        Identifiant d'exécution (liant la signature au run).
    created_at:
        Horodatage ISO 8601 de l'exécution.
    files:
        Dictionnaire ``{role: Path}`` — les rôles sont des labels sémantiques
        (``source``, ``pseudonymise``, ``correspondance``, ``manifeste``).

    Returns
    -------
    dict
        Document de signature complet, prêt à sérialiser en JSON.
    """
    secret_bytes = secret.encode("utf-8")

    entries: Dict[str, dict] = {}
    for role, path in sorted(files.items()):
        sha = _sha256_file(path)
        canonical = f"{role}|{path.resolve()}|{sha}|{run_id}"
        sig = hmac.new(
            secret_bytes,
            msg=canonical.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()
        entries[role] = {
            "chemin":        str(path),
            "sha256_contenu": sha,
            "hmac_fichier":  sig,
        }

    # Signature globale du document (garantit qu'aucune entrée n'a été ajoutée/supprimée)
    doc_payload = json.dumps(entries, sort_keys=True, ensure_ascii=False)
    hmac_doc = hmac.new(
        secret_bytes,
        msg=doc_payload.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    return {
        "version":          SIGNATURE_VERSION,
        "id_execution":     run_id,
        "horodatage":       created_at,
        "algorithme":       "hmac_sha256",
        "empreinte_secret": _secret_fingerprint(secret),
        "fichiers":         entries,
        "hmac_document":    hmac_doc,
    }


def _signature_path(output_path: Path) -> Path:
    """Retourne le chemin du fichier de signature associé au fichier de sortie."""
    return output_path.with_name(output_path.name + ".signature.json")


def verify_signature(signature_path: Path, secret: str) -> Dict[str, bool]:
    """
    Vérifie l'intégrité d'un ensemble de fichiers à partir d'un fichier de signature.

    Utilisable en ligne de commande ou depuis un pipeline externe.

    Parameters
    ----------
    signature_path:
        Chemin du fichier ``.signature.json`` produit lors du traitement.
    secret:
        Clé HMAC utilisée lors de la signature initiale.

    Returns
    -------
    dict
        ``{role: True|False}`` pour chaque fichier + ``"document"`` pour la
        signature globale. ``True`` = intégrité confirmée, ``False`` = altération
        détectée ou fichier absent.

    Example
    -------
    >>> results = verify_signature(Path("sortie.csv.signature.json"), secret)
    >>> assert all(results.values()), f"Fichiers altérés : {results}"
    """
    with open(signature_path, encoding="utf-8") as f:
        doc = json.load(f)

    secret_bytes = secret.encode("utf-8")
    run_id = doc["id_execution"]
    results: Dict[str, bool] = {}

    for role, entry in doc["fichiers"].items():
        path = Path(entry["chemin"])
        try:
            sha = _sha256_file(path)
        except FileNotFoundError:
            results[role] = False
            continue

        canonical = f"{role}|{path.resolve()}|{sha}|{run_id}"
        expected = hmac.new(
            secret_bytes,
            msg=canonical.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()
        results[role] = hmac.compare_digest(expected, entry["hmac_fichier"])

    # Vérification de la signature globale du document
    doc_payload = json.dumps(doc["fichiers"], sort_keys=True, ensure_ascii=False)
    expected_doc = hmac.new(
        secret_bytes,
        msg=doc_payload.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
    results["document"] = hmac.compare_digest(expected_doc, doc["hmac_document"])

    return results


# ---------------------------------------------------------------------------
# Point d'entrée CLI
# ---------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    """
    Point d'entrée principal.

    Codes de retour
    ---------------
    0 : succès complet
    2 : succès partiel (colonnes absentes ou aucune cellule éligible)
    1 : erreur fatale (capturée dans le bloc __main__)
    """
    parser = argparse.ArgumentParser(
        description="Pseudonymise un fichier CSV/Parquet/XLSX et produit un manifeste JSON"
    )
    parser.add_argument("--input",    required=True,               help="Fichier source")
    parser.add_argument("--output",   required=True,               help="Fichier pseudonymisé")
    parser.add_argument("--mapping",  required=True,               help="Table de correspondance")
    parser.add_argument("--columns",  required=True,               help="Colonnes à pseudonymiser (virgule)")
    parser.add_argument("--truncate", type=int, default=DEFAULT_TRUNCATE,
                        help=f"Longueur des pseudonymes (0 = sans limite, défaut : {DEFAULT_TRUNCATE})")
    parser.add_argument("--sheet",    default=None,                help="Feuille XLSX (optionnel)")
    parser.add_argument("--sep",      default=",",                 help="Séparateur CSV (défaut : ',')")
    parser.add_argument("--encoding", default="utf-8",             help="Encodage CSV (défaut : utf-8)")

    args = parser.parse_args(argv)

    input_path   = Path(args.input)
    output_path  = Path(args.output)
    mapping_path = Path(args.mapping)

    requested_columns = [c.strip() for c in args.columns.split(",") if c.strip()]
    if not requested_columns:
        raise ValueError("--columns est vide après parsing")

    secret     = _secret_from_env()
    fp         = _secret_fingerprint(secret)
    run_id     = _run_id()
    created_at = _now_iso()

    df_in, input_fmt = _read_input(
        input_path, sheet=args.sheet, sep=args.sep, encoding=args.encoding
    )

    missing_columns   = [c for c in requested_columns if c not in df_in.columns]
    effective_columns = [c for c in requested_columns if c in df_in.columns]

    df_pseudo, mapping_df, stats = _build_mapping_and_transform(
        df=df_in,
        columns=effective_columns,
        secret=secret,
        truncate=int(args.truncate),
        run_id=run_id,
        created_at=created_at,
    )

    output_fmt  = _write_output(df_pseudo, output_path,  sheet=args.sheet, sep=args.sep, encoding=args.encoding)
    mapping_fmt = _write_mapping(mapping_df, mapping_path, sep=args.sep, encoding=args.encoding)

    manifest = _build_manifest(
        run_id=run_id,
        created_at=created_at,
        input_path=input_path,
        input_fmt=input_fmt,
        df_in=df_in,
        requested_columns=requested_columns,
        effective_columns=effective_columns,
        missing_columns=missing_columns,
        stats=stats,
        truncate=int(args.truncate),
        secret_fingerprint=fp,
        output_path=output_path,
        output_fmt=output_fmt,
        mapping_path=mapping_path,
        mapping_fmt=mapping_fmt,
        mapping_rows=int(mapping_df.shape[0]),
    )

    manifest_path = _manifest_path(output_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # Signature d'intégrité — couvre source + tous les artefacts générés
    sig_doc = _sign_files(
        secret=secret,
        run_id=run_id,
        created_at=created_at,
        files={
            "source":        input_path,
            "pseudonymise":  output_path,
            "correspondance": mapping_path,
            "manifeste":     manifest_path,
        },
    )
    sig_path = _signature_path(output_path)
    with open(sig_path, "w", encoding="utf-8") as f:
        json.dump(sig_doc, f, ensure_ascii=False, indent=2)

    # Résumé console — le manifeste est la preuve principale
    eligible_cells = sum(int(s["non_nul"]) for s in stats.values())
    print(json.dumps({
        "id_execution":        run_id,
        "colonnes_effectives": effective_columns,
        "colonnes_absentes":   missing_columns,
        "taux_global":         manifest["pseudonymisation"]["taux_global"],
        "manifeste":           str(manifest_path),
        "signature":           str(sig_path),
    }, ensure_ascii=False))

    if missing_columns or eligible_cells == 0:
        return 2
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        # Aucune donnée sensible dans le message d'erreur
        print(f"Erreur : {type(exc).__name__} : {exc}", file=sys.stderr)
        sys.exit(1)