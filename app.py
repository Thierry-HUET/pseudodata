#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Interface Web Streamlit – pseudodata

Démarrage :
    streamlit run app.py [-- --server.port <PORT>]

Configuration du port via variable d'environnement :
    export STREAMLIT_PORT=8502
    streamlit run app.py

Le port par défaut est 8501 (comportement natif Streamlit).
La variable STREAMLIT_PORT est lue au démarrage et injectée dans la
configuration via le mécanisme d'option serveur de Streamlit.
"""

from __future__ import annotations

import io
import json
import os
import tempfile
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Configuration du port via variable d'environnement
# ---------------------------------------------------------------------------
# Streamlit lit os.environ["STREAMLIT_SERVER_PORT"] avant le démarrage du
# serveur. On positionne cette variable si STREAMLIT_PORT est défini,
# afin que la valeur soit prise en compte même lors d'un `streamlit run app.py`
# sans argument --server.port explicite.
_port_env = os.environ.get("STREAMLIT_PORT", "").strip()
if _port_env:
    os.environ.setdefault("STREAMLIT_SERVER_PORT", _port_env)

# ---------------------------------------------------------------------------
# Import des modules métier
# ---------------------------------------------------------------------------
from pseudonymize import (
    _build_manifest,
    _build_mapping_and_transform,
    _now_iso,
    _run_id,
    _secret_fingerprint,
    _secret_from_env,
    _sign_files,
    _write_output,
    _write_mapping,
    DEFAULT_TRUNCATE,
    ENV_SECRET,
)

# ---------------------------------------------------------------------------
# Constantes UI
# ---------------------------------------------------------------------------

APP_TITLE = "Pseudonymisation de données"
LOGO_PATH = Path(__file__).parent / "src" / "static" / "logo_anonyx_pseudo.png"
SUPPORTED_EXTENSIONS = [".csv", ".parquet", ".xlsx"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_uploaded_file(uploaded_file, sep: str, encoding: str) -> Optional[pd.DataFrame]:
    """Lit un fichier uploadé et retourne un DataFrame ou None en cas d'erreur."""
    suffix = Path(uploaded_file.name).suffix.lower()
    try:
        if suffix == ".csv":
            return pd.read_csv(uploaded_file, sep=sep, encoding=encoding, dtype=str)
        elif suffix in (".parquet", ".pq"):
            return pd.read_parquet(uploaded_file)
        elif suffix == ".xlsx":
            return pd.read_excel(uploaded_file, dtype=str)
    except Exception as exc:
        st.error(f"Erreur de lecture : {exc}")
    return None


def _df_to_bytes(df: pd.DataFrame, fmt: str, sep: str, encoding: str) -> bytes:
    """Sérialise un DataFrame en bytes selon le format cible."""
    buf = io.BytesIO()
    if fmt == "csv":
        df.to_csv(buf, index=False, sep=sep, encoding=encoding)
    elif fmt == "parquet":
        df.to_parquet(buf, index=False)
    else:
        df.to_excel(buf, index=False)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Page principale
# ---------------------------------------------------------------------------


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")

    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=180)

    st.title(APP_TITLE)

    # ── Sidebar – paramètres ─────────────────────────────────────────────────
    with st.sidebar:
        st.header("Paramètres")

        sep = st.text_input("Séparateur CSV", value=",", max_chars=1)
        encoding = st.selectbox("Encodage CSV", ["utf-8", "utf-8-sig", "latin-1", "cp1252"])
        truncate = st.number_input(
            "Longueur des pseudonymes (0 = sans limite)",
            min_value=0, max_value=64,
            value=DEFAULT_TRUNCATE,
        )
        sheet = st.text_input("Feuille XLSX (optionnel)", value="")

        st.markdown("---")
        port_display = os.environ.get("STREAMLIT_SERVER_PORT", "8501")
        st.caption(f"Port Streamlit : **{port_display}**")
        st.caption(f"Clé active : variable `{ENV_SECRET}`")

    # ── Corps principal ──────────────────────────────────────────────────────
    uploaded = st.file_uploader(
        "Fichier source",
        type=[ext.lstrip(".") for ext in SUPPORTED_EXTENSIONS],
    )

    if uploaded is None:
        st.info("Déposez un fichier CSV, Parquet ou XLSX pour commencer.")
        return

    df = _read_uploaded_file(uploaded, sep=sep, encoding=encoding)
    if df is None:
        return

    st.subheader("Aperçu du fichier source")
    st.dataframe(df.head(20), use_container_width=True)
    st.caption(f"{df.shape[0]} lignes × {df.shape[1]} colonnes")

    # Sélection des colonnes à pseudonymiser
    columns_selected = st.multiselect(
        "Colonnes à pseudonymiser",
        options=list(df.columns),
    )

    if not columns_selected:
        st.warning("Sélectionnez au moins une colonne.")
        return

    if st.button("Lancer la pseudonymisation", type="primary"):
        # Vérification du secret
        try:
            secret = _secret_from_env()
        except (RuntimeError, ValueError) as exc:
            st.error(str(exc))
            return

        fp = _secret_fingerprint(secret)
        run_id = _run_id()
        created_at = _now_iso()

        with st.spinner("Pseudonymisation en cours…"):
            df_pseudo, mapping_df, stats = _build_mapping_and_transform(
                df=df,
                columns=columns_selected,
                secret=secret,
                truncate=int(truncate),
                run_id=run_id,
                created_at=created_at,
            )

        st.success("Pseudonymisation terminée.")

        # ── Résultats ────────────────────────────────────────────────────────
        st.subheader("Résultat pseudonymisé")
        st.dataframe(df_pseudo.head(20), use_container_width=True)

        # Statistiques par colonne
        st.subheader("Statistiques par colonne")
        stats_df = pd.DataFrame(stats).T.rename(columns={
            "non_nul": "Valeurs non nulles",
            "transformees": "Transformées",
            "taux": "Taux",
        })
        st.dataframe(stats_df, use_container_width=True)

        # ── Manifeste ────────────────────────────────────────────────────────
        src_fmt = Path(uploaded.name).suffix.lstrip(".")
        src_fmt = "parquet" if src_fmt in ("parquet", "pq") else src_fmt

        manifest = _build_manifest(
            run_id=run_id,
            created_at=created_at,
            input_path=Path(uploaded.name),
            input_fmt=src_fmt,
            df_in=df,
            requested_columns=columns_selected,
            effective_columns=columns_selected,
            missing_columns=[],
            stats=stats,
            truncate=int(truncate),
            secret_fingerprint=fp,
            output_path=Path(f"pseudo_{uploaded.name}"),
            output_fmt=src_fmt,
            mapping_path=Path(f"mapping_{uploaded.name}"),
            mapping_fmt=src_fmt,
            mapping_rows=int(mapping_df.shape[0]),
        )

        # ── Téléchargements ──────────────────────────────────────────────────
        st.subheader("Téléchargements")
        col1, col2, col3 = st.columns(3)

        pseudo_bytes = _df_to_bytes(df_pseudo, src_fmt, sep, encoding)
        col1.download_button(
            "📥 Fichier pseudonymisé",
            data=pseudo_bytes,
            file_name=f"pseudo_{uploaded.name}",
            mime="application/octet-stream",
        )

        mapping_bytes = _df_to_bytes(mapping_df, src_fmt, sep, encoding)
        col2.download_button(
            "📥 Table de correspondance",
            data=mapping_bytes,
            file_name=f"mapping_{uploaded.name}",
            mime="application/octet-stream",
        )

        manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
        col3.download_button(
            "📥 Manifeste JSON",
            data=manifest_bytes,
            file_name=f"pseudo_{uploaded.name}.manifeste.json",
            mime="application/json",
        )


if __name__ == "__main__":
    main()
