#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests nominaux — pseudonymize.py

Couverture
----------
- _hmac_pseudonym        : déterminisme, troncature, sensibilité à la clé
- _secret_from_env       : secret valide, absent, trop court
- _secret_fingerprint    : format et stabilité de l'empreinte
- _detect_format         : extensions supportées et non supportées
- _build_mapping_and_transform : cas nominal CSV, valeurs nulles, doublons
- _build_manifest        : structure et taux global
- main (intégration)     : exécution complète sur fichier CSV temporaire

Jeu de données intégré (voir fixture ``sample_df``)
"""

import json
import os
from pathlib import Path
from typing import Dict

import pandas as pd
import pytest

# Import des fonctions à tester
from pseudonymize import (
    _build_manifest,
    _build_mapping_and_transform,
    _detect_format,
    _hmac_pseudonym,
    _manifest_path,
    _secret_fingerprint,
    _secret_from_env,
    _sha256_file,
    _sign_files,
    _signature_path,
    main,
    verify_signature,
)


# ---------------------------------------------------------------------------
# Constantes de test
# ---------------------------------------------------------------------------

VALID_SECRET = "s3cr3t_de_test_suffisamment_long_32car"  # 38 caractères
SHORT_SECRET  = "court"


# ---------------------------------------------------------------------------
# Jeu de données
# ---------------------------------------------------------------------------

SAMPLE_DATA = {
    "identifiant_client": ["CLI001", "CLI002", "CLI003", "CLI001", "CLI004"],
    "email": [
        "alice@example.com",
        "bob@example.com",
        "charlie@example.com",
        "alice@example.com",   # doublon intentionnel pour tester la déduplication
        None,                  # valeur nulle intentionnelle
    ],
    "telephone": [
        "0601020304",
        "0602030405",
        "0603040506",
        "0601020304",          # doublon
        "0604050607",
    ],
    "montant_commande": ["120.50", "85.00", "200.00", "45.00", "310.75"],  # colonne non pseudonymisée
}


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """DataFrame de référence pour les tests unitaires."""
    return pd.DataFrame(SAMPLE_DATA)


@pytest.fixture
def secret_env(monkeypatch):
    """Injecte le secret valide dans l'environnement pour la durée du test."""
    monkeypatch.setenv("PSEUDONYMIZER_SECRET", VALID_SECRET)
    return VALID_SECRET


# ---------------------------------------------------------------------------
# _hmac_pseudonym
# ---------------------------------------------------------------------------


class TestHmacPseudonym:
    SECRET_BYTES = VALID_SECRET.encode("utf-8")

    def test_deterministe(self):
        """Une même valeur produit toujours le même pseudonyme."""
        p1 = _hmac_pseudonym(self.SECRET_BYTES, "alice@example.com", 22)
        p2 = _hmac_pseudonym(self.SECRET_BYTES, "alice@example.com", 22)
        assert p1 == p2

    def test_troncature_respectee(self):
        """Le pseudonyme est tronqué à la longueur demandée."""
        p = _hmac_pseudonym(self.SECRET_BYTES, "test@example.com", 10)
        assert len(p) == 10

    def test_sans_troncature(self):
        """truncate=0 retourne le pseudonyme complet (43 caractères base64)."""
        p = _hmac_pseudonym(self.SECRET_BYTES, "test@example.com", 0)
        assert len(p) == 43  # SHA-256 → 32 bytes → 43 base64 sans padding

    def test_sensibilite_a_la_cle(self):
        """Deux clés différentes produisent des pseudonymes différents."""
        key_a = b"cleA_suffisamment_longue_pour_le_test__"
        key_b = b"cleB_suffisamment_longue_pour_le_test__"
        assert _hmac_pseudonym(key_a, "valeur", 22) != _hmac_pseudonym(key_b, "valeur", 22)

    def test_sensibilite_a_la_valeur(self):
        """Deux valeurs différentes produisent des pseudonymes différents."""
        p1 = _hmac_pseudonym(self.SECRET_BYTES, "alice@example.com", 22)
        p2 = _hmac_pseudonym(self.SECRET_BYTES, "bob@example.com",   22)
        assert p1 != p2

    def test_strip_normalisation(self):
        """Les espaces en début/fin de valeur sont ignorés."""
        p1 = _hmac_pseudonym(self.SECRET_BYTES, "alice@example.com",   22)
        p2 = _hmac_pseudonym(self.SECRET_BYTES, "  alice@example.com ", 22)
        assert p1 == p2


# ---------------------------------------------------------------------------
# _secret_from_env
# ---------------------------------------------------------------------------


class TestSecretFromEnv:
    def test_secret_valide(self, monkeypatch):
        monkeypatch.setenv("PSEUDONYMIZER_SECRET", VALID_SECRET)
        assert _secret_from_env() == VALID_SECRET

    def test_secret_absent_leve_runtime_error(self, monkeypatch):
        monkeypatch.delenv("PSEUDONYMIZER_SECRET", raising=False)
        with pytest.raises(RuntimeError, match="Secret absent"):
            _secret_from_env()

    def test_secret_trop_court_leve_value_error(self, monkeypatch):
        monkeypatch.setenv("PSEUDONYMIZER_SECRET", SHORT_SECRET)
        with pytest.raises(ValueError, match="trop court"):
            _secret_from_env()


# ---------------------------------------------------------------------------
# _secret_fingerprint
# ---------------------------------------------------------------------------


class TestSecretFingerprint:
    def test_format(self):
        """L'empreinte respecte le format sha256:<16 hex>."""
        fp = _secret_fingerprint(VALID_SECRET)
        assert fp.startswith("sha256:")
        hex_part = fp.split(":")[1]
        assert len(hex_part) == 16
        assert all(c in "0123456789abcdef" for c in hex_part)

    def test_stabilite(self):
        """La même clé produit toujours la même empreinte."""
        assert _secret_fingerprint(VALID_SECRET) == _secret_fingerprint(VALID_SECRET)

    def test_deux_cles_differentes(self):
        """Deux clés distinctes produisent des empreintes distinctes."""
        assert _secret_fingerprint(VALID_SECRET) != _secret_fingerprint(VALID_SECRET + "x")

    def test_secret_non_divulgue(self):
        """L'empreinte ne contient pas le secret."""
        fp = _secret_fingerprint(VALID_SECRET)
        assert VALID_SECRET not in fp


# ---------------------------------------------------------------------------
# _detect_format
# ---------------------------------------------------------------------------


class TestDetectFormat:
    @pytest.mark.parametrize("filename,expected", [
        ("fichier.csv",     "csv"),
        ("fichier.parquet", "parquet"),
        ("fichier.pq",      "parquet"),
        ("fichier.xlsx",    "xlsx"),
        ("FICHIER.CSV",     "csv"),    # insensible à la casse
    ])
    def test_formats_supportes(self, filename, expected):
        assert _detect_format(Path(filename)) == expected

    def test_format_non_supporte_leve_value_error(self):
        with pytest.raises(ValueError, match="non supportée"):
            _detect_format(Path("fichier.json"))


# ---------------------------------------------------------------------------
# _build_mapping_and_transform
# ---------------------------------------------------------------------------


class TestBuildMappingAndTransform:
    COLUMNS = ["email", "telephone"]

    def _run(self, df):
        return _build_mapping_and_transform(
            df=df,
            columns=self.COLUMNS,
            secret=VALID_SECRET,
            truncate=22,
            run_id="test-run-001",
            created_at="2026-03-27T06:00:00+00:00",
        )

    def test_colonnes_non_pseudonymisees_inchangees(self, sample_df):
        """Les colonnes non listées ne sont pas modifiées."""
        df_pseudo, _, _ = self._run(sample_df)
        pd.testing.assert_series_equal(
            df_pseudo["montant_commande"],
            sample_df["montant_commande"],
        )
        pd.testing.assert_series_equal(
            df_pseudo["identifiant_client"],
            sample_df["identifiant_client"],
        )

    def test_colonnes_pseudonymisees_differentes_des_originales(self, sample_df):
        """Les valeurs pseudonymisées diffèrent des valeurs originales."""
        df_pseudo, _, _ = self._run(sample_df)
        # Vérification sur les valeurs non nulles uniquement
        mask = sample_df["email"].notna()
        assert not (df_pseudo.loc[mask, "email"] == sample_df.loc[mask, "email"]).any()

    def test_determinisme_sur_doublons(self, sample_df):
        """Deux lignes avec la même valeur originale ont le même pseudonyme."""
        df_pseudo, _, _ = self._run(sample_df)
        # CLI001 apparaît en index 0 et 3 → email identique
        assert df_pseudo.loc[0, "email"] == df_pseudo.loc[3, "email"]

    def test_valeur_nulle_preservee(self, sample_df):
        """Les valeurs nulles restent nulles après pseudonymisation."""
        df_pseudo, _, _ = self._run(sample_df)
        assert pd.isna(df_pseudo.loc[4, "email"])

    def test_mapping_contient_les_bonnes_colonnes(self, sample_df):
        """La table de correspondance contient les colonnes attendues."""
        _, mapping_df, _ = self._run(sample_df)
        expected_cols = {
            "id_execution", "colonne", "valeur_originale",
            "valeur_pseudonymisee", "algorithme", "horodatage_creation",
        }
        assert expected_cols.issubset(set(mapping_df.columns))

    def test_mapping_deduplique(self, sample_df):
        """Chaque valeur unique n'apparaît qu'une fois dans le mapping."""
        _, mapping_df, _ = self._run(sample_df)
        email_mapping = mapping_df[mapping_df["colonne"] == "email"]
        assert email_mapping["valeur_originale"].nunique() == len(email_mapping)

    def test_stats_taux_complet(self, sample_df):
        """Le taux est 1.0 pour les colonnes sans valeur nulle."""
        _, _, stats = self._run(sample_df)
        assert stats["telephone"]["taux"] == 1.0

    def test_stats_taux_partiel_si_nulls(self, sample_df):
        """Le taux est < 1.0 pour les colonnes avec des valeurs nulles."""
        _, _, stats = self._run(sample_df)
        # email a 1 valeur nulle sur 5 lignes → non_nul = 4
        assert stats["email"]["non_nul"] == 4.0
        assert stats["email"]["taux"] == 1.0  # taux = transformees / non_nul


# ---------------------------------------------------------------------------
# _build_manifest
# ---------------------------------------------------------------------------


class TestBuildManifest:
    def _make_manifest(self, tmp_path):
        df = pd.DataFrame(SAMPLE_DATA)
        stats = {
            "email":     {"non_nul": 4.0, "transformees": 4.0, "taux": 1.0},
            "telephone": {"non_nul": 5.0, "transformees": 5.0, "taux": 1.0},
        }
        return _build_manifest(
            run_id="test-run-001",
            created_at="2026-03-27T06:00:00+00:00",
            input_path=tmp_path / "entree.csv",
            input_fmt="csv",
            df_in=df,
            requested_columns=["email", "telephone", "colonne_absente"],
            effective_columns=["email", "telephone"],
            missing_columns=["colonne_absente"],
            stats=stats,
            truncate=22,
            secret_fingerprint="sha256:abcdef1234567890",
            output_path=tmp_path / "sortie.csv",
            output_fmt="csv",
            mapping_path=tmp_path / "mapping.parquet",
            mapping_fmt="parquet",
            mapping_rows=7,
        )

    def test_structure_cles_principales(self, tmp_path):
        m = self._make_manifest(tmp_path)
        for key in ["id_execution", "horodatage_creation", "entree",
                    "colonnes_demandees", "colonnes_effectives", "colonnes_absentes",
                    "pseudonymisation", "sorties"]:
            assert key in m

    def test_taux_global_calcule(self, tmp_path):
        m = self._make_manifest(tmp_path)
        # 4 + 5 = 9 éligibles, toutes transformées → 1.0
        assert m["pseudonymisation"]["taux_global"] == 1.0

    def test_colonnes_absentes_reportees(self, tmp_path):
        m = self._make_manifest(tmp_path)
        assert "colonne_absente" in m["colonnes_absentes"]

    def test_empreinte_secret_presente(self, tmp_path):
        m = self._make_manifest(tmp_path)
        assert m["pseudonymisation"]["empreinte_secret"] == "sha256:abcdef1234567890"


# ---------------------------------------------------------------------------
# Test d'intégration — main()
# ---------------------------------------------------------------------------


class TestMainIntegration:
    """Exécution complète via main() sur fichier CSV temporaire."""

    def test_execution_complete_csv(self, tmp_path, secret_env):
        """main() retourne 0 et produit les trois artefacts attendus."""
        # Préparation du fichier source
        input_path   = tmp_path / "entree.csv"
        output_path  = tmp_path / "sortie_pseudo.csv"
        mapping_path = tmp_path / "mapping.parquet"

        pd.DataFrame(SAMPLE_DATA).to_csv(input_path, index=False)

        rc = main([
            "--input",   str(input_path),
            "--output",  str(output_path),
            "--mapping", str(mapping_path),
            "--columns", "email,telephone",
        ])

        assert rc == 0

        # Les trois artefacts sont présents
        assert output_path.exists(),  "Fichier pseudonymisé absent"
        assert mapping_path.exists(), "Table de correspondance absente"
        manifest_path = output_path.with_name(output_path.name + ".manifeste.json")
        assert manifest_path.exists(), "Manifeste JSON absent"

    def test_manifeste_json_valide(self, tmp_path, secret_env):
        """Le manifeste produit est un JSON valide et structuré."""
        input_path   = tmp_path / "entree.csv"
        output_path  = tmp_path / "sortie_pseudo.csv"
        mapping_path = tmp_path / "mapping.parquet"

        pd.DataFrame(SAMPLE_DATA).to_csv(input_path, index=False)
        main([
            "--input",   str(input_path),
            "--output",  str(output_path),
            "--mapping", str(mapping_path),
            "--columns", "email,telephone",
        ])

        manifest_path = output_path.with_name(output_path.name + ".manifeste.json")
        with open(manifest_path, encoding="utf-8") as f:
            m = json.load(f)

        assert m["pseudonymisation"]["taux_global"] == 1.0
        assert "email"     in m["pseudonymisation"]["statistiques_par_colonne"]
        assert "telephone" in m["pseudonymisation"]["statistiques_par_colonne"]

    def test_colonne_absente_retourne_code_2(self, tmp_path, secret_env):
        """main() retourne 2 si une colonne demandée est absente du fichier."""
        input_path   = tmp_path / "entree.csv"
        output_path  = tmp_path / "sortie_pseudo.csv"
        mapping_path = tmp_path / "mapping.parquet"

        pd.DataFrame(SAMPLE_DATA).to_csv(input_path, index=False)

        rc = main([
            "--input",   str(input_path),
            "--output",  str(output_path),
            "--mapping", str(mapping_path),
            "--columns", "email,colonne_inexistante",
        ])

        assert rc == 2

    def test_colonne_non_pseudonymisee_inchangee(self, tmp_path, secret_env):
        """La colonne montant_commande n'est pas altérée par le traitement."""
        input_path   = tmp_path / "entree.csv"
        output_path  = tmp_path / "sortie_pseudo.csv"
        mapping_path = tmp_path / "mapping.parquet"

        df_source = pd.DataFrame(SAMPLE_DATA)
        df_source.to_csv(input_path, index=False)

        main([
            "--input",   str(input_path),
            "--output",  str(output_path),
            "--mapping", str(mapping_path),
            "--columns", "email,telephone",
        ])

        df_out = pd.read_csv(output_path, dtype=str)
        pd.testing.assert_series_equal(
            df_out["montant_commande"],
            df_source["montant_commande"],
        )


# ---------------------------------------------------------------------------
# _sha256_file
# ---------------------------------------------------------------------------


class TestSha256File:
    def test_stabilite(self, tmp_path):
        """Le même fichier produit toujours la même empreinte."""
        f = tmp_path / "fichier.txt"
        f.write_text("contenu stable", encoding="utf-8")
        assert _sha256_file(f) == _sha256_file(f)

    def test_sensibilite_modification(self, tmp_path):
        """Toute modification du contenu change l'empreinte."""
        f = tmp_path / "fichier.txt"
        f.write_text("contenu original", encoding="utf-8")
        sha_avant = _sha256_file(f)
        f.write_text("contenu modifie", encoding="utf-8")
        sha_apres = _sha256_file(f)
        assert sha_avant != sha_apres

    def test_format_hexadecimal_64_chars(self, tmp_path):
        """L'empreinte est une chaîne hexadécimale de 64 caractères."""
        f = tmp_path / "fichier.txt"
        f.write_bytes(b"\x00\xff\xab")
        sha = _sha256_file(f)
        assert len(sha) == 64
        assert all(c in "0123456789abcdef" for c in sha)


# ---------------------------------------------------------------------------
# _sign_files
# ---------------------------------------------------------------------------


class TestSignFiles:
    def _make_files(self, tmp_path) -> Dict[str, Path]:
        files = {
            "source":        tmp_path / "entree.csv",
            "pseudonymise":  tmp_path / "sortie.csv",
            "correspondance": tmp_path / "mapping.parquet",
            "manifeste":     tmp_path / "sortie.csv.manifeste.json",
        }
        for p in files.values():
            p.write_text("contenu_fictif", encoding="utf-8")
        return files

    def test_structure_cles(self, tmp_path):
        """Le document de signature contient les clés attendues."""
        files = self._make_files(tmp_path)
        doc = _sign_files(
            secret=VALID_SECRET,
            run_id="run-001",
            created_at="2026-03-27T06:00:00+00:00",
            files=files,
        )
        for key in ["version", "id_execution", "horodatage", "algorithme",
                    "empreinte_secret", "fichiers", "hmac_document"]:
            assert key in doc

    def test_tous_les_roles_presents(self, tmp_path):
        """Chaque rôle fourni apparaît dans le document de signature."""
        files = self._make_files(tmp_path)
        doc = _sign_files(
            secret=VALID_SECRET, run_id="run-001",
            created_at="2026-03-27T06:00:00+00:00", files=files,
        )
        assert set(doc["fichiers"].keys()) == set(files.keys())

    def test_chaque_entree_contient_sha_et_hmac(self, tmp_path):
        """Chaque entrée de fichier contient chemin, sha256_contenu et hmac_fichier."""
        files = self._make_files(tmp_path)
        doc = _sign_files(
            secret=VALID_SECRET, run_id="run-001",
            created_at="2026-03-27T06:00:00+00:00", files=files,
        )
        for role, entry in doc["fichiers"].items():
            assert "chemin"         in entry, f"Clé 'chemin' absente pour {role}"
            assert "sha256_contenu" in entry, f"Clé 'sha256_contenu' absente pour {role}"
            assert "hmac_fichier"   in entry, f"Clé 'hmac_fichier' absente pour {role}"

    def test_liaison_run_id(self, tmp_path):
        """Deux run_id différents produisent des hmac_fichier différents."""
        files = self._make_files(tmp_path)
        kwargs = dict(secret=VALID_SECRET, created_at="2026-03-27T06:00:00+00:00", files=files)
        doc_a = _sign_files(**kwargs, run_id="run-AAA")
        doc_b = _sign_files(**kwargs, run_id="run-BBB")
        hmac_a = doc_a["fichiers"]["source"]["hmac_fichier"]
        hmac_b = doc_b["fichiers"]["source"]["hmac_fichier"]
        assert hmac_a != hmac_b, "Le HMAC doit dépendre du run_id"


# ---------------------------------------------------------------------------
# verify_signature
# ---------------------------------------------------------------------------


class TestVerifySignature:
    def _prepare(self, tmp_path):
        """Prépare un jeu de fichiers signés et retourne (sig_path, files)."""
        files = {
            "source":        tmp_path / "entree.csv",
            "pseudonymise":  tmp_path / "sortie.csv",
            "correspondance": tmp_path / "mapping.parquet",
            "manifeste":     tmp_path / "sortie.csv.manifeste.json",
        }
        for p in files.values():
            p.write_text("contenu_fictif", encoding="utf-8")

        doc = _sign_files(
            secret=VALID_SECRET, run_id="run-001",
            created_at="2026-03-27T06:00:00+00:00", files=files,
        )
        sig_path = tmp_path / "sortie.csv.signature.json"
        sig_path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        return sig_path, files

    def test_verification_nominale(self, tmp_path):
        """Tous les résultats sont True sur des fichiers non modifiés."""
        sig_path, _ = self._prepare(tmp_path)
        results = verify_signature(sig_path, VALID_SECRET)
        assert all(results.values()), f"Échecs inattendus : {results}"

    def test_detection_alteration_fichier(self, tmp_path):
        """La modification d'un fichier est détectée."""
        sig_path, files = self._prepare(tmp_path)
        files["pseudonymise"].write_text("contenu_altere", encoding="utf-8")
        results = verify_signature(sig_path, VALID_SECRET)
        assert results["pseudonymise"] is False

    def test_fichier_absent_retourne_false(self, tmp_path):
        """Un fichier supprimé après signature est signalé False."""
        sig_path, files = self._prepare(tmp_path)
        files["correspondance"].unlink()
        results = verify_signature(sig_path, VALID_SECRET)
        assert results["correspondance"] is False

    def test_mauvaise_cle_retourne_false(self, tmp_path):
        """Une clé incorrecte invalide toutes les entrées."""
        sig_path, _ = self._prepare(tmp_path)
        results = verify_signature(sig_path, VALID_SECRET + "_mauvaise")
        assert not any(results.values())

    def test_document_integre(self, tmp_path):
        """La clé 'document' est True sur un document non altéré."""
        sig_path, _ = self._prepare(tmp_path)
        results = verify_signature(sig_path, VALID_SECRET)
        assert results["document"] is True

    def test_alteration_document_detectee(self, tmp_path):
        """La modification du fichier de signature lui-même est détectée."""
        sig_path, _ = self._prepare(tmp_path)
        doc = json.loads(sig_path.read_text(encoding="utf-8"))
        # Injection d'une entrée fantôme dans le document
        doc["fichiers"]["source"]["sha256_contenu"] = "a" * 64
        sig_path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        results = verify_signature(sig_path, VALID_SECRET)
        assert results["document"] is False


# ---------------------------------------------------------------------------
# Intégration — présence du fichier de signature dans main()
# ---------------------------------------------------------------------------


class TestMainSignatureIntegration:
    def test_fichier_signature_produit(self, tmp_path, secret_env):
        """main() produit un fichier .signature.json à côté du manifeste."""
        input_path   = tmp_path / "entree.csv"
        output_path  = tmp_path / "sortie_pseudo.csv"
        mapping_path = tmp_path / "mapping.parquet"

        pd.DataFrame(SAMPLE_DATA).to_csv(input_path, index=False)
        main([
            "--input",   str(input_path),
            "--output",  str(output_path),
            "--mapping", str(mapping_path),
            "--columns", "email,telephone",
        ])

        sig_path = output_path.with_name(output_path.name + ".signature.json")
        assert sig_path.exists(), "Fichier de signature absent"

    def test_signature_verifie_apres_execution(self, tmp_path, secret_env):
        """La signature produite par main() est immédiatement vérifiable."""
        input_path   = tmp_path / "entree.csv"
        output_path  = tmp_path / "sortie_pseudo.csv"
        mapping_path = tmp_path / "mapping.parquet"

        pd.DataFrame(SAMPLE_DATA).to_csv(input_path, index=False)
        main([
            "--input",   str(input_path),
            "--output",  str(output_path),
            "--mapping", str(mapping_path),
            "--columns", "email,telephone",
        ])

        sig_path = output_path.with_name(output_path.name + ".signature.json")
        results = verify_signature(sig_path, secret_env)
        assert all(results.values()), f"Vérification échouée : {results}"

    def test_alteration_detectee_apres_main(self, tmp_path, secret_env):
        """Toute modification post-exécution est détectée par verify_signature."""
        input_path   = tmp_path / "entree.csv"
        output_path  = tmp_path / "sortie_pseudo.csv"
        mapping_path = tmp_path / "mapping.parquet"

        pd.DataFrame(SAMPLE_DATA).to_csv(input_path, index=False)
        main([
            "--input",   str(input_path),
            "--output",  str(output_path),
            "--mapping", str(mapping_path),
            "--columns", "email,telephone",
        ])

        # Altération du fichier pseudonymisé après coup
        with open(output_path, "a", encoding="utf-8") as f:
            f.write("ligne,injectee,apres,signature\n")

        sig_path = output_path.with_name(output_path.name + ".signature.json")
        results = verify_signature(sig_path, secret_env)
        assert results["pseudonymise"] is False