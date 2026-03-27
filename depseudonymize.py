#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Outil de dépseudonymisation (CSV / Parquet / XLSX)

Restaure les valeurs originales d'un fichier pseudonymisé à partir
de la table de correspondance produite lors de la pseudonymisation.

Prérequis
---------
- Fichier pseudonymisé    : --input
- Table de correspondance : --mapping
- Fichier de signature    : --signature

La vérification d'intégrité via le fichier de signature est obligatoire.
Le traitement est bloqué si la signature est invalide ou absente.

Codes de retour
---------------
0 : succès complet
2 : succès partiel (pseudonymes sans correspondance dans le mapping)
1 : erreur fatale (signature invalide, fichier absent, erreur I/O)

Secret : variable d'environnement PSEUDONYMIZER_SECRET
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

# Réutilisation des utilitaires du module de pseudonymisation
from pseudonymize import (
    _detect_format,
    _now_iso,
    _run_id,
    _secret_fingerprint,
    _secret_from_env,
    _signature_path,
    verify_signature,
)


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

MAPPING_COLS_REQUIRED = frozenset({
    "colonne",
    "valeur_originale",
    "valeur_pseudonymisee",
})


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------


def _read_pseudonymized(
    path: Path,
    sheet: Optional[str],
    sep: str,
    encoding: str,
) -> Tuple[pd.DataFrame, str]:
    """
    Lit le fichier pseudonymisé et retourne (DataFrame, format).

    Notes
    -----
    Lecture systématique en ``dtype=str`` pour préserver la cohérence
    avec les valeurs pseudonymisées stockées dans la table de correspondance.
    """
    fmt = _detect_format(path)

    if fmt == "csv":
        df = pd.read_csv(path, sep=sep, encoding=encoding, dtype=str, keep_default_na=True)
    elif fmt == "parquet":
        df = pd.read_parquet(path).astype(str)
    else:  # xlsx
        df = pd.read_excel(path, sheet_name=sheet or 0, dtype=str)

    return df, fmt


def _read_mapping(
    path: Path,
    sep: str,
    encoding: str,
) -> pd.DataFrame:
    """
    Lit la table de correspondance et valide son schéma minimal.

    Raises
    ------
    ValueError
        Si les colonnes obligatoires sont absentes.
    """
    fmt = _detect_format(path)

    if fmt == "csv":
        mapping = pd.read_csv(path, sep=sep, encoding=encoding, dtype=str)
    elif fmt == "parquet":
        mapping = pd.read_parquet(path).astype(str)
    else:
        mapping = pd.read_excel(path, dtype=str)

    missing = MAPPING_COLS_REQUIRED - set(mapping.columns)
    if missing:
        raise ValueError(
            f"Table de correspondance invalide — colonnes manquantes : {sorted(missing)}"
        )

    return mapping


def _write_restored(
    df: pd.DataFrame,
    path: Path,
    sheet: Optional[str],
    sep: str,
    encoding: str,
) -> str:
    """Écrit le DataFrame restauré ; crée les répertoires parents si nécessaire."""
    fmt = _detect_format(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "csv":
        df.to_csv(path, index=False, sep=sep, encoding=encoding)
    elif fmt == "parquet":
        df.to_parquet(path, index=False)
    else:
        df.to_excel(path, index=False, sheet_name=sheet or "Sheet1")

    return fmt


# ---------------------------------------------------------------------------
# Vérification de signature
# ---------------------------------------------------------------------------


def _check_signature(
    signature_path: Path,
    secret: str,
    input_path: Path,
    mapping_path: Path,
) -> None:
    """
    Vérifie l'intégrité des fichiers via le fichier de signature.

    Contrôles effectués
    -------------------
    - Intégrité du document de signature lui-même (``hmac_document``)
    - Intégrité du fichier pseudonymisé (rôle ``pseudonymise``)
    - Intégrité de la table de correspondance (rôle ``correspondance``)

    Le fichier source original et le manifeste sont également vérifiés
    s'ils sont présents dans la signature.

    Raises
    ------
    SystemExit(1)
        Si la signature est invalide, absente, ou si un fichier est altéré.

    Notes
    -----
    Les chemins dans le fichier de signature sont ceux enregistrés lors
    de la pseudonymisation. Si les fichiers ont été déplacés, la vérification
    des chemins absolus échouera — c'est un comportement intentionnel.
    """
    if not signature_path.exists():
        _fatal(f"Fichier de signature introuvable : {signature_path}")

    results = verify_signature(signature_path, secret)

    # Vérification globale du document en premier
    if not results.get("document", False):
        _fatal(
            "Signature invalide — le document de signature a été altéré ou "
            "la clé utilisée est incorrecte."
        )

    # Vérification des rôles critiques pour la dépseudonymisation
    critical_roles = {"pseudonymise", "correspondance"}
    failures = {role: ok for role, ok in results.items() if not ok and role in critical_roles}

    if failures:
        detail = ", ".join(sorted(failures.keys()))
        _fatal(
            f"Intégrité compromise — fichiers altérés ou déplacés : {detail}\n"
            "Dépseudonymisation bloquée."
        )

    # Avertissement non bloquant pour les rôles secondaires (source, manifeste)
    soft_failures = {
        role: ok for role, ok in results.items()
        if not ok and role not in critical_roles and role != "document"
    }
    if soft_failures:
        detail = ", ".join(sorted(soft_failures.keys()))
        print(
            f"[AVERTISSEMENT] Vérification partielle — rôles non critiques altérés : {detail}",
            file=sys.stderr,
        )


# ---------------------------------------------------------------------------
# Dépseudonymisation
# ---------------------------------------------------------------------------


def _build_reverse_maps(
    mapping_df: pd.DataFrame,
) -> Dict[str, Dict[str, str]]:
    """
    Construit les tables de correspondance inverse par colonne.

    Format retourné
    ---------------
    ``{colonne: {valeur_pseudonymisee: valeur_originale}}``

    Notes
    -----
    En cas de collision (même pseudonyme pour deux valeurs originales différentes,
    ce qui ne devrait pas se produire avec HMAC-SHA256 non tronqué), la première
    occurrence est conservée et un avertissement est émis.
    """
    reverse: Dict[str, Dict[str, str]] = {}

    for col, group in mapping_df.groupby("colonne"):
        col_map: Dict[str, str] = {}
        for _, row in group.iterrows():
            pseudo = str(row["valeur_pseudonymisee"])
            original = str(row["valeur_originale"])
            if pseudo in col_map and col_map[pseudo] != original:
                print(
                    f"[AVERTISSEMENT] Collision détectée pour la colonne '{col}', "
                    f"pseudonyme '{pseudo}' — première occurrence conservée.",
                    file=sys.stderr,
                )
            else:
                col_map[pseudo] = original
        reverse[str(col)] = col_map

    return reverse


def _restore(
    df: pd.DataFrame,
    reverse_maps: Dict[str, Dict[str, str]],
) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """
    Applique la dépseudonymisation sur le DataFrame.

    Seules les colonnes présentes à la fois dans le DataFrame et dans
    la table de correspondance sont traitées. Les valeurs sans correspondance
    (pseudonymes inconnus) sont laissées inchangées et comptabilisées.

    Parameters
    ----------
    df:
        DataFrame pseudonymisé.
    reverse_maps:
        Tables inverses par colonne issues de ``_build_reverse_maps``.

    Returns
    -------
    df_restored : pd.DataFrame
        DataFrame avec les valeurs originales restaurées.
    orphans : dict
        ``{colonne: nombre_de_valeurs_sans_correspondance}``
    """
    df_restored = df.copy()
    orphans: Dict[str, int] = {}

    for col, col_map in reverse_maps.items():
        if col not in df_restored.columns:
            continue

        series = df_restored[col]
        non_null_mask = series.notna()

        if not non_null_mask.any():
            continue

        s_str = series[non_null_mask].astype(str)

        # Valeurs sans correspondance dans le mapping
        unknown = s_str[~s_str.isin(col_map)]
        if not unknown.empty:
            orphans[col] = int(unknown.nunique())
            print(
                f"[AVERTISSEMENT] Colonne '{col}' — {orphans[col]} pseudonyme(s) "
                "sans correspondance, valeurs conservées telles quelles.",
                file=sys.stderr,
            )

        df_restored.loc[non_null_mask, col] = s_str.map(col_map).fillna(s_str)

    return df_restored, orphans


# ---------------------------------------------------------------------------
# Rapport de dépseudonymisation
# ---------------------------------------------------------------------------


def _report_path(output_path: Path) -> Path:
    """Retourne le chemin du rapport JSON de dépseudonymisation."""
    return output_path.with_name(output_path.name + ".rapport_depseudo.json")


def _write_report(
    *,
    run_id: str,
    created_at: str,
    input_path: Path,
    mapping_path: Path,
    signature_path: Path,
    output_path: Path,
    output_fmt: str,
    columns_restored: List[str],
    columns_skipped: List[str],
    orphans: Dict[str, int],
    secret_fingerprint: str,
) -> Path:
    """
    Écrit le rapport JSON de l'opération de dépseudonymisation.

    Le rapport ne contient aucune valeur originale ni pseudonyme —
    uniquement des métadonnées opérationnelles et des compteurs.
    """
    report = {
        "id_execution":    run_id,
        "horodatage":      created_at,
        "operation":       "depseudonymisation",
        "entree": {
            "pseudonymise":   str(input_path),
            "correspondance": str(mapping_path),
            "signature":      str(signature_path),
        },
        "sortie": {
            "chemin": str(output_path),
            "format": output_fmt,
        },
        "colonnes_restaurees": columns_restored,
        "colonnes_ignorees":   columns_skipped,
        "orphelins_par_colonne": orphans,
        "statut": "partiel" if orphans else "complet",
        "empreinte_secret": secret_fingerprint,
    }

    rpath = _report_path(output_path)
    rpath.parent.mkdir(parents=True, exist_ok=True)
    with open(rpath, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return rpath


# ---------------------------------------------------------------------------
# Utilitaire
# ---------------------------------------------------------------------------


def _fatal(message: str) -> None:
    """Affiche une erreur sur stderr et termine avec le code 1."""
    print(f"ERREUR : {message}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Point d'entrée CLI
# ---------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(
        description=(
            "Dépseudonymise un fichier à partir de la table de correspondance. "
            "La vérification de signature est obligatoire."
        )
    )
    parser.add_argument(
        "--input",     required=True,
        help="Fichier pseudonymisé à restaurer",
    )
    parser.add_argument(
        "--mapping",   required=True,
        help="Table de correspondance produite lors de la pseudonymisation",
    )
    parser.add_argument(
        "--signature", required=True,
        help="Fichier de signature (.signature.json) produit lors de la pseudonymisation",
    )
    parser.add_argument(
        "--output",    required=True,
        help="Fichier restauré en sortie",
    )
    parser.add_argument("--sheet",    default=None,    help="Feuille XLSX (optionnel)")
    parser.add_argument("--sep",      default=",",     help="Séparateur CSV (défaut : ',')")
    parser.add_argument("--encoding", default="utf-8", help="Encodage CSV (défaut : utf-8)")

    args = parser.parse_args(argv)

    input_path     = Path(args.input)
    mapping_path   = Path(args.mapping)
    sig_path       = Path(args.signature)
    output_path    = Path(args.output)

    # Lecture du secret
    secret = _secret_from_env()
    fp     = _secret_fingerprint(secret)
    run_id     = _run_id()
    created_at = _now_iso()

    # ── 1. Vérification d'intégrité (bloquante) ──────────────────────────────
    _check_signature(
        signature_path=sig_path,
        secret=secret,
        input_path=input_path,
        mapping_path=mapping_path,
    )

    # ── 2. Lecture des fichiers ───────────────────────────────────────────────
    df_pseudo, _ = _read_pseudonymized(
        input_path, sheet=args.sheet, sep=args.sep, encoding=args.encoding
    )
    mapping_df = _read_mapping(mapping_path, sep=args.sep, encoding=args.encoding)

    # ── 3. Construction des tables inverses ──────────────────────────────────
    reverse_maps = _build_reverse_maps(mapping_df)

    columns_in_mapping  = set(reverse_maps.keys())
    columns_in_file     = set(df_pseudo.columns)
    columns_restored    = sorted(columns_in_mapping & columns_in_file)
    columns_skipped     = sorted(columns_in_mapping - columns_in_file)

    if columns_skipped:
        print(
            f"[INFO] Colonnes présentes dans le mapping mais absentes du fichier "
            f"(ignorées) : {columns_skipped}",
            file=sys.stderr,
        )

    # ── 4. Restauration ──────────────────────────────────────────────────────
    df_restored, orphans = _restore(df_pseudo, reverse_maps)

    # ── 5. Écriture du fichier restauré ──────────────────────────────────────
    output_fmt = _write_restored(
        df_restored, output_path,
        sheet=args.sheet, sep=args.sep, encoding=args.encoding,
    )

    # ── 6. Rapport ───────────────────────────────────────────────────────────
    report_path = _write_report(
        run_id=run_id,
        created_at=created_at,
        input_path=input_path,
        mapping_path=mapping_path,
        signature_path=sig_path,
        output_path=output_path,
        output_fmt=output_fmt,
        columns_restored=columns_restored,
        columns_skipped=columns_skipped,
        orphans=orphans,
        secret_fingerprint=fp,
    )

    # ── 7. Résumé console ────────────────────────────────────────────────────
    print(json.dumps({
        "id_execution":      run_id,
        "colonnes_restaurees": columns_restored,
        "colonnes_ignorees":   columns_skipped,
        "orphelins":           orphans,
        "statut":              "partiel" if orphans else "complet",
        "sortie":              str(output_path),
        "rapport":             str(report_path),
    }, ensure_ascii=False))

    return 2 if orphans else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:
        # Aucune donnée sensible dans le message d'erreur
        print(f"Erreur : {type(exc).__name__} : {exc}", file=sys.stderr)
        sys.exit(1)