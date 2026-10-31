"""
etl/transform_load.py
---------------------
Transforms raw openFDA JSON into relational rows and loads them
into the PostgreSQL schema defined in db/schema.sql.
"""

import os
import re
import logging
from datetime import datetime, date
from dotenv import load_dotenv
try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    psycopg2 = None
    execute_values = None

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

DRUG_ROLE_MAP = {"1": "suspect", "2": "concomitant", "3": "interacting"}
REPORTER_MAP  = {"1": "physician", "2": "pharmacist", "3": "other_hcp", "5": "consumer"}
REACTION_OUTCOME_MAP = {
    "1": "recovered", "2": "recovering", "3": "not_recovered",
    "4": "fatal", "5": "unknown", "6": "recovered_with_sequelae",
}
SEX_MAP = {"0": "unknown", "1": "male", "2": "female"}


def get_connection():
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        from urllib.parse import urlparse
        r = urlparse(database_url)
        return psycopg2.connect(
            host=r.hostname, port=r.port or 5432,
            dbname=r.path[1:], user=r.username, password=r.password,
            sslmode="require",
        )
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        dbname=os.getenv("DB_NAME", "pharmacovigilance"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def _parse_date(raw):
    if not raw:
        return None
    raw = str(raw).strip()
    for fmt in ("%Y%m%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


BRAND_GENERIC_MAP = {
    "adderall": "amphetamine",
    "ritalin": "methylphenidate",
    "concerta": "methylphenidate",
    "xanax": "alprazolam",
    "niravam": "alprazolam",
    "lexapro": "escitalopram",
    "celexa": "citalopram",
    "zyprexa": "olanzapine",
    "seroquel": "quetiapine",
    "klonopin": "clonazepam",
}


def _safe_float(val):
    if val is None:
        return None
    try:
        f = float(val)
        return f if f >= 0 else None
    except (TypeError, ValueError):
        return None


def _normalize_age_years(val, unit_code):
    """
    Normalizes patient age to years based on openFDA/ICH E2B age unit codes:
      800: Decade
      801: Year
      802: Month
      803: Week
      804: Day
      805: Hour

    Clinical Plausibility & Safety Checks:
      - Returns None if val is missing, malformed, negative, or invalid.
      - Returns None if unit_code is missing, empty, or unrecognized (never silently assumes years).
      - Returns None if normalized age exceeds 125.0 years (implausible outlier).
    """
    f = _safe_float(val)
    if f is None or f < 0:
        return None

    if unit_code is None or str(unit_code).strip() == "":
        log.warning(f"Missing age unit code for patient age value: {val}. Returning None to prevent silent unit misinterpretation.")
        return None

    unit = str(unit_code).strip()

    if unit == "800":       # Decade
        age_years = round(f * 10.0, 1)
    elif unit == "801":     # Year
        age_years = round(f, 1)
    elif unit == "802":     # Month
        age_years = round(f / 12.0, 1)
    elif unit == "803":     # Week
        age_years = round(f / 52.1429, 1)
    elif unit == "804":     # Day
        age_years = round(f / 365.25, 1)
    elif unit == "805":     # Hour
        age_years = round(f / 8766.0, 2)
    else:
        # Unrecognized unit code - do not silently misinterpret units
        log.warning(f"Unrecognized age unit code: {unit_code} for age {val}. Returning None.")
        return None

    # Biological plausibility validation (0 to 125 years)
    if age_years > 125.0:
        log.warning(f"Implausible normalized age: {age_years} years (from val={val}, unit={unit_code})")
        return None

    return age_years


def _normalize_weight_kg(val, unit_code=None):
    """
    Normalizes patient weight to kilograms.

    Source Verification & openFDA FAERS Convention:
      - In the openFDA /drug/event schema, patient weight is reported in 'patientweight'.
      - Per openFDA documentation and ICH E2B(R3) field B.1.7.2, FAERS patient weight is
        conventionally recorded directly in kilograms (kg), and openFDA does not provide a
        separate 'patientweightunit' field in its standard JSON hierarchy.
      - If an explicit unit is supplied or passed from downstream/alternative feeds:
          'kg', 'kgs', '001': treated as kilograms.
          'lbs', 'lb', '002': converted to kilograms via multiplying by 0.453592.
      - If unit_code is None or omitted, defaults to kg per openFDA FAERS convention.
      - Rejects missing, malformed, non-positive (<=0), and implausible values (<0.5 kg or >500 kg).
    """
    f = _safe_float(val)
    if f is None or f <= 0:
        return None

    unit = str(unit_code).strip().lower() if unit_code is not None and str(unit_code).strip() != "" else "kg"

    if unit in ("lbs", "lb", "002"):
        weight_kg = round(f * 0.453592, 2)
    elif unit in ("kg", "kgs", "001"):
        weight_kg = round(f, 2)
    else:
        log.warning(f"Unrecognized weight unit: {unit_code}. Rejecting value {val}.")
        return None

    # Biological plausibility validation (0.5 kg to 500.0 kg)
    if weight_kg < 0.5 or weight_kg > 500.0:
        log.warning(f"Implausible normalized weight: {weight_kg} kg (from val={val}, unit={unit_code})")
        return None

    return weight_kg


def _normalize_drug_name(name):
    """
    Normalizes whitespace and casing, and checks against verified brand-to-generic dictionary.
    """
    if not name:
        return None
    cleaned = re.sub(r'\s+', ' ', str(name).strip().lower())
    # Strip common salt suffixes for clean generic comparison if needed
    for brand, generic in BRAND_GENERIC_MAP.items():
        if cleaned == brand:
            return generic
    return cleaned


def _flag(val):
    if val is None:
        return None
    return str(val) == "1"


def transform_report(raw, drug_brand):
    safety_id = raw.get("safetyreportid")
    if not safety_id:
        return None

    pt = raw.get("patient", {})
    raw_reactions = pt.get("reaction", [])
    if isinstance(raw_reactions, dict):
        raw_reactions = [raw_reactions]

    reactions = []
    has_fatal_reaction = False
    for r in raw_reactions:
        out_code = str(r.get("reactionoutcome", "")).strip()
        outcome_label = REACTION_OUTCOME_MAP.get(out_code, None)
        if out_code == "4" or outcome_label == "fatal":
            has_fatal_reaction = True
        reactions.append({
            "reaction_term": r.get("reactionmeddrapt"),
            "outcome":       outcome_label,
        })

    is_serious_death = _flag(raw.get("seriousnessdeath"))
    # Report-level clinical outcome: 'fatal' if serious death flag or fatal reaction reported.
    # Note: FAERS death flags indicate that patient death was reported as an event outcome,
    # NOT proof that the drug caused death. Causality cannot be inferred from spontaneous reports.
    report_outcome = "fatal" if (is_serious_death or has_fatal_reaction) else None

    report = {
        "safety_report_id":        str(safety_id),
        "receipt_date":            _parse_date(raw.get("receiptdate")),
        "receive_date":            _parse_date(raw.get("receivedate")),
        "serious":                 _flag(raw.get("serious")),
        "serious_death":           is_serious_death,
        "serious_hospitalization": _flag(raw.get("seriousnesshospitalization")),
        "serious_lifethreat":      _flag(raw.get("seriousnesslifethreatening")),
        "serious_disability":      _flag(raw.get("seriousnessdisabling")),
        "serious_congenital":      _flag(raw.get("seriousnesscongenitalanomali")),
        "serious_other":           _flag(raw.get("seriousnessother")),
        "reporter_country":        raw.get("occurcountry"),
        "reporter_qualification":  REPORTER_MAP.get(
            str(raw.get("primarysource", {}).get("qualification", "")), None),
        "outcome":                 report_outcome,
    }

    patient = {
        "age_years": _normalize_age_years(pt.get("patientonsetage"), pt.get("patientonsetageunit")),
        "sex":       SEX_MAP.get(str(pt.get("patientsex", "")), None),
        "weight_kg": _normalize_weight_kg(pt.get("patientweight")),
    }

    raw_drugs = pt.get("drug", [])
    if isinstance(raw_drugs, dict):
        raw_drugs = [raw_drugs]

    drugs = []
    for d in raw_drugs:
        role_code = str(d.get("drugcharacterization", ""))
        medicinal_prod = d.get("medicinalproduct")
        openfda_generic = d.get("openfda", {}).get("generic_name", [None])[0]

        # Determine normalized generic name
        raw_target = openfda_generic or medicinal_prod
        norm_generic = _normalize_drug_name(raw_target)

        drugs.append({
            "medicinal_product": medicinal_prod,
            "generic_name":      norm_generic,
            "manufacturer_name": d.get("openfda", {}).get("manufacturer_name", [None])[0],
            "drug_role":         role_code,
            "drug_role_label":   DRUG_ROLE_MAP.get(role_code, "unknown"),
            "indication":        d.get("drugindication"),
        })

    return {"report": report, "patient": patient, "drugs": drugs, "reactions": reactions}


def load_report(cur, transformed, etl_run_id):
    report = transformed["report"]

    cur.execute("""
        INSERT INTO reports (
            safety_report_id, receipt_date, receive_date,
            serious, serious_death, serious_hospitalization,
            serious_lifethreat, serious_disability, serious_congenital, serious_other,
            reporter_country, reporter_qualification, outcome, etl_run_id
        ) VALUES (
            %(safety_report_id)s, %(receipt_date)s, %(receive_date)s,
            %(serious)s, %(serious_death)s, %(serious_hospitalization)s,
            %(serious_lifethreat)s, %(serious_disability)s, %(serious_congenital)s, %(serious_other)s,
            %(reporter_country)s, %(reporter_qualification)s, %(outcome)s, %(etl_run_id)s
        )
        ON CONFLICT (safety_report_id) DO NOTHING
        RETURNING id
    """, {**report, "etl_run_id": etl_run_id})

    row = cur.fetchone()
    if not row:
        return False

    report_id = row[0]

    p = transformed["patient"]
    cur.execute("""
        INSERT INTO patients (report_id, age_years, sex, weight_kg)
        VALUES (%s, %s, %s, %s)
    """, (report_id, p["age_years"], p["sex"], p["weight_kg"]))

    if transformed["drugs"]:
        execute_values(cur, """
            INSERT INTO drugs
                (report_id, medicinal_product, generic_name, manufacturer_name,
                 drug_role, drug_role_label, indication)
            VALUES %s
        """, [(
            report_id, d["medicinal_product"], d["generic_name"],
            d["manufacturer_name"], d["drug_role"], d["drug_role_label"], d["indication"],
        ) for d in transformed["drugs"]])

    if transformed["reactions"]:
        execute_values(cur, """
            INSERT INTO reactions (report_id, reaction_term, outcome)
            VALUES %s
        """, [(report_id, r["reaction_term"], r["outcome"])
              for r in transformed["reactions"]])

    return True


def transform_load_drug(raw_records, drug_brand):
    stats = {"extracted": len(raw_records), "loaded": 0, "skipped": 0, "errors": 0}

    log_conn = get_connection()
    log_conn.autocommit = True
    with log_conn.cursor() as log_cur:
        log_cur.execute("""
            INSERT INTO etl_runs (drug_name, endpoint, rows_extracted, status)
            VALUES (%s, %s, %s, 'started')
            RETURNING id
        """, (drug_brand, "/drug/event", len(raw_records)))
        etl_run_id = log_cur.fetchone()[0]

    conn = get_connection()
    seen_ids = set()

    try:
        for raw in raw_records:
            try:
                transformed = transform_report(raw, drug_brand)
                if not transformed:
                    stats["skipped"] += 1
                    continue

                sid = transformed["report"]["safety_report_id"]
                if sid in seen_ids:
                    stats["skipped"] += 1
                    continue
                seen_ids.add(sid)

                with conn:
                    with conn.cursor() as cur:
                        inserted = load_report(cur, transformed, etl_run_id)
                        if inserted:
                            stats["loaded"] += 1
                        else:
                            stats["skipped"] += 1

            except Exception as e:
                conn.rollback()
                log.warning("Error on report: %s", e)
                stats["errors"] += 1
    finally:
        conn.close()

    final_status = "complete" if stats["errors"] == 0 else ("partial_error" if stats["loaded"] > 0 else "error")
    with log_conn.cursor() as log_cur:
        log_cur.execute("""
            UPDATE etl_runs
            SET rows_loaded = %s, rows_skipped = %s,
                status = %s, error_message = %s, completed_at = NOW()
            WHERE id = %s
        """, (
            stats["loaded"], stats["skipped"], final_status,
            f"{stats['errors']} record(s) failed during load" if stats["errors"] > 0 else None,
            etl_run_id
        ))
    log_conn.close()

    log.info("%(d)s: loaded=%(l)s skipped=%(s)s errors=%(e)s", {
        "d": drug_brand, "l": stats["loaded"],
        "s": stats["skipped"], "e": stats["errors"]
    })
    return stats


def run_full_etl(extracted_data):
    total = {"loaded": 0, "skipped": 0, "errors": 0}
    for brand, records in extracted_data.items():
        stats = transform_load_drug(records, brand)
        for k in ("loaded", "skipped", "errors"):
            total[k] += stats[k]
    log.info("ETL complete - loaded: %s skipped: %s errors: %s",
             total["loaded"], total["skipped"], total["errors"])
    return total


if __name__ == "__main__":
    from extract import extract_all
    data = extract_all()
    run_full_etl(data)
