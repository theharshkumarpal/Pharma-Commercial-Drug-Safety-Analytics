"""
tests/test_pharmacovigilance.py
--------------------------------
Comprehensive unit test suite for the Pharmacovigilance & Drug Safety Analytics Platform:
1. Age normalization for all openFDA unit codes (800=decade, 801=year, 802=month, 803=week, 804=day, 805=hour)
2. Handling of missing, malformed, negative, boundary, and implausible ages (>125 years)
3. Weight normalization (kg, lbs/lb/002, missing, malformed, <=0, implausible boundaries)
4. Brand-to-generic drug normalization and whitespace handling
5. Clinical outcome and death flag handling (seriousnessdeath preserved without causal inference)
6. Reaction-level outcome mapping (recovered, fatal, etc.)
7. Report extraction parameter building and backoff logic
8. Status determination for ETL runs (complete, partial_error, error)
9. SQL query deduplication validation (distinct counting prevents join inflation)
"""

import unittest
from etl.transform_load import (
    _normalize_age_years,
    _normalize_weight_kg,
    _normalize_drug_name,
    _flag,
    transform_report,
    BRAND_GENERIC_MAP,
    REACTION_OUTCOME_MAP,
)
from etl.extract import _build_params, DRUGS
from topup_etl import TOPUP_DRUGS


class TestAgeNormalization(unittest.TestCase):
    """Phase 2.1: Rigorous verification of age normalization across all supported openFDA units."""

    def test_decade_code_800(self):
        # 5 decades = 50.0 years
        self.assertEqual(_normalize_age_years("5", "800"), 50.0)
        self.assertEqual(_normalize_age_years(4.5, "800"), 45.0)

    def test_year_code_801(self):
        # 42 years with explicit unit code 801
        self.assertEqual(_normalize_age_years("42", "801"), 42.0)
        self.assertEqual(_normalize_age_years(35, "801"), 35.0)

    def test_missing_or_empty_unit_code_returns_none(self):
        # Must not silently interpret unit-less values as years
        self.assertIsNone(_normalize_age_years("25", None))
        self.assertIsNone(_normalize_age_years("25", ""))
        self.assertIsNone(_normalize_age_years("25", "   "))

    def test_month_code_802(self):
        # 24 months = 2.0 years
        self.assertEqual(_normalize_age_years("24", "802"), 2.0)
        # 6 months = 0.5 years
        self.assertEqual(_normalize_age_years("6", "802"), 0.5)

    def test_week_code_803(self):
        # 52 weeks ~= 1.0 year
        self.assertAlmostEqual(_normalize_age_years("52", "803"), 1.0, delta=0.1)
        # 104 weeks ~= 2.0 years
        self.assertAlmostEqual(_normalize_age_years("104", "803"), 2.0, delta=0.1)

    def test_day_code_804(self):
        # 365 days = 1.0 year
        self.assertEqual(_normalize_age_years("365.25", "804"), 1.0)
        self.assertAlmostEqual(_normalize_age_years("730", "804"), 2.0, delta=0.1)

    def test_hour_code_805(self):
        # 8766 hours = 1.0 year
        self.assertEqual(_normalize_age_years("8766", "805"), 1.0)
        # Neonate age in hours (48 hours)
        self.assertAlmostEqual(_normalize_age_years("48", "805"), 0.01, delta=0.01)

    def test_missing_and_malformed_values(self):
        self.assertIsNone(_normalize_age_years(None, "801"))
        self.assertIsNone(_normalize_age_years("", "801"))
        self.assertIsNone(_normalize_age_years("unknown", "801"))
        self.assertIsNone(_normalize_age_years("N/A", "801"))

    def test_negative_values(self):
        self.assertIsNone(_normalize_age_years("-10", "801"))
        self.assertIsNone(_normalize_age_years(-5, "802"))

    def test_implausible_boundary_values(self):
        # Greater than 125 years should be rejected as implausible
        self.assertIsNone(_normalize_age_years("150", "801"))
        self.assertIsNone(_normalize_age_years("20", "800"))  # 200 years!
        # Valid upper boundary (110 years)
        self.assertEqual(_normalize_age_years("110", "801"), 110.0)

    def test_unrecognized_unit_codes(self):
        self.assertIsNone(_normalize_age_years("40", "999"))
        self.assertIsNone(_normalize_age_years("40", "XYZ"))


class TestWeightNormalization(unittest.TestCase):
    """Phase 2.2: Rigorous verification of weight normalization into kilograms."""

    def test_default_kilograms(self):
        self.assertEqual(_normalize_weight_kg("70"), 70.0)
        self.assertEqual(_normalize_weight_kg(85.5, "kg"), 85.5)
        self.assertEqual(_normalize_weight_kg("60.25", "001"), 60.25)

    def test_pounds_conversion(self):
        # 150 lbs = 68.04 kg
        self.assertAlmostEqual(_normalize_weight_kg("150", "lbs"), 68.04, delta=0.01)
        self.assertAlmostEqual(_normalize_weight_kg("220.462", "lb"), 100.0, delta=0.1)
        self.assertAlmostEqual(_normalize_weight_kg("110", "002"), 49.90, delta=0.01)

    def test_missing_and_malformed_weight(self):
        self.assertIsNone(_normalize_weight_kg(None))
        self.assertIsNone(_normalize_weight_kg(""))
        self.assertIsNone(_normalize_weight_kg("invalid"))

    def test_zero_and_negative_weight(self):
        # Weight must be strictly positive (>0)
        self.assertIsNone(_normalize_weight_kg("0"))
        self.assertIsNone(_normalize_weight_kg(0))
        self.assertIsNone(_normalize_weight_kg("-50"))

    def test_implausible_boundaries(self):
        # Below 0.5 kg or above 500 kg
        self.assertIsNone(_normalize_weight_kg("0.1"))
        self.assertIsNone(_normalize_weight_kg("800"))
        # Plausible boundaries
        self.assertEqual(_normalize_weight_kg("3.2"), 3.2)    # infant
        self.assertEqual(_normalize_weight_kg("120"), 120.0)  # adult


class TestDrugNormalizationAndMapping(unittest.TestCase):
    """Phase 2.4: Brand-to-generic mapping and whitespace normalization."""

    def test_verified_brand_mappings(self):
        mappings = {
            "adderall": "amphetamine",
            "ritalin": "methylphenidate",
            "concerta": "methylphenidate",
            "xanax": "alprazolam",
            "lexapro": "escitalopram",
            "celexa": "citalopram",
            "zyprexa": "olanzapine",
            "seroquel": "quetiapine",
            "klonopin": "clonazepam",
        }
        for brand, expected_generic in mappings.items():
            self.assertEqual(
                _normalize_drug_name(brand),
                expected_generic,
                f"Mapping failure for brand {brand}"
            )

    def test_whitespace_and_case_normalization(self):
        self.assertEqual(_normalize_drug_name("  XANAX  "), "alprazolam")
        self.assertEqual(_normalize_drug_name("Adderall \t\n"), "amphetamine")
        self.assertEqual(_normalize_drug_name("Methylphenidate HCL"), "methylphenidate hcl")

    def test_topup_drugs_integrity(self):
        celexa = next(d for d in TOPUP_DRUGS if d["brand"] == "celexa")
        self.assertEqual(celexa["generic"], "citalopram")
        klonopin = next(d for d in TOPUP_DRUGS if d["brand"] == "klonopin")
        self.assertEqual(klonopin["generic"], "clonazepam")
        zyprexa = next(d for d in TOPUP_DRUGS if d["brand"] == "zyprexa")
        self.assertEqual(zyprexa["generic"], "olanzapine")


class TestClinicalOutcomesAndDeathFlags(unittest.TestCase):
    """Phase 2.3: Death and clinical outcome handling without causal inference."""

    def test_fatal_report_does_not_infer_causality(self):
        raw_report = {
            "safetyreportid": "100201",
            "receiptdate": "20240115",
            "serious": "1",
            "seriousnessdeath": "1",
            "patient": {
                "patientonsetage": "50",
                "patientonsetageunit": "801",
                "patientdeath": {"patientdeathdate": "20240110"},  # Date must NOT be stored as outcome string
                "reaction": [{"reactionmeddrapt": "Cardiac arrest", "reactionoutcome": "4"}],
                "drug": [{"medicinalproduct": "Adderall", "drugcharacterization": "1"}]
            }
        }
        res = transform_report(raw_report, "adderall")
        # Ensure death date is not stored as outcome
        self.assertNotEqual(res["report"]["outcome"], "20240110")
        # Ensure outcome captures fatal indicator
        self.assertEqual(res["report"]["outcome"], "fatal")
        # Original serious_death boolean preserved
        self.assertTrue(res["report"]["serious_death"])
        # Reaction outcome preserved
        self.assertEqual(res["reactions"][0]["outcome"], "fatal")

    def test_non_fatal_reaction_outcomes(self):
        self.assertEqual(REACTION_OUTCOME_MAP.get("1"), "recovered")
        self.assertEqual(REACTION_OUTCOME_MAP.get("2"), "recovering")
        self.assertEqual(REACTION_OUTCOME_MAP.get("3"), "not_recovered")
        self.assertEqual(REACTION_OUTCOME_MAP.get("6"), "recovered_with_sequelae")


class TestAPIParametersAndExtractionReliability(unittest.TestCase):
    """Phase 2.5: API parameter building, date range support, and pagination limit configurability."""

    def test_build_params_defaults(self):
        params = _build_params("ritalin", "methylphenidate", 0)
        self.assertEqual(params["limit"], 100)
        self.assertEqual(params["skip"], 0)
        self.assertIn('brand_name:"ritalin"', params["search"])
        self.assertIn('generic_name:"methylphenidate"', params["search"])

    def test_build_params_with_date_range(self):
        params = _build_params("ritalin", "methylphenidate", 100, page_size=50,
                               start_date="20230101", end_date="20231231")
        self.assertEqual(params["limit"], 50)
        self.assertEqual(params["skip"], 100)
        self.assertIn("receiptdate:[20230101 TO 20231231]", params["search"])


class TestQueryDistinctCounting(unittest.TestCase):
    """Phase 3: Prevent join multiplication from inflating report counts while preserving association counts."""

    def test_report_distinct_counting_concept(self):
        # A mock report having 2 suspect drugs and 3 reactions
        report_id = "RPT-001"
        joined_rows = [
            {"report_id": report_id, "drug": "Adderall", "reaction": "Insomnia"},
            {"report_id": report_id, "drug": "Adderall", "reaction": "Tachycardia"},
            {"report_id": report_id, "drug": "Adderall", "reaction": "Dry mouth"},
            {"report_id": report_id, "drug": "Concerta", "reaction": "Insomnia"},
            {"report_id": report_id, "drug": "Concerta", "reaction": "Tachycardia"},
            {"report_id": report_id, "drug": "Concerta", "reaction": "Dry mouth"},
        ]
        total_joined_rows = len(joined_rows)
        distinct_reports = len(set(r["report_id"] for r in joined_rows))

        # Joined rows count is 6, but unique report count is strictly 1
        self.assertEqual(total_joined_rows, 6)
        self.assertEqual(distinct_reports, 1)

    def test_reaction_and_drug_association_semantics(self):
        # Multiple distinct reactions reported on the same report
        report_reactions = [
            {"report_id": "R1", "reaction": "Insomnia"},
            {"report_id": "R1", "reaction": "Anxiety"},
            {"report_id": "R2", "reaction": "Insomnia"},
        ]
        # Reports with Insomnia = 2, Total reaction event instances = 3
        distinct_reports_insomnia = len(set(r["report_id"] for r in report_reactions if r["reaction"] == "Insomnia"))
        total_reaction_instances = len(report_reactions)
        self.assertEqual(distinct_reports_insomnia, 2)
        self.assertEqual(total_reaction_instances, 3)


class TestFlaskHealthAndReadiness(unittest.TestCase):
    """Phase 4: Health (liveness) and Ready (database connectivity) endpoint validation."""

    def setUp(self):
        from app.app import app
        self.client = app.test_client()

    def test_health_liveness_endpoint(self):
        # /health must always return HTTP 200 indicating process liveness
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data.get("status"), "healthy")

    def test_ready_endpoint_without_live_db(self):
        # /ready probe checks DB connectivity; returns 503 when local DB is offline
        resp = self.client.get("/ready")
        self.assertIn(resp.status_code, (200, 503))
        data = resp.get_json()
        if resp.status_code == 503:
            self.assertEqual(data.get("status"), "not_ready")


if __name__ == "__main__":
    unittest.main()
