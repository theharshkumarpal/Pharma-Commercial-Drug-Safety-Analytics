"""
etl/extract.py
--------------
Pulls adverse event reports from the openFDA /drug/event endpoint
for each of the six target mental-health medications.

Handles:
  - Pagination (limit/skip)
  - Optional API key via .env
  - Rate-limit backoff (429 responses)
  - Per-drug raw JSON saved to data/raw/ for reproducibility
"""

import os
import time
import json
import logging
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Target drugs — brand name used for API query, generic stored too
# ------------------------------------------------------------------
DRUGS = [
    {"brand": "adderall",        "generic": "amphetamine"},
    {"brand": "ritalin",         "generic": "methylphenidate"},
    {"brand": "xanax",           "generic": "alprazolam"},
    {"brand": "lexapro",         "generic": "escitalopram"},
    {"brand": "zyprexa",         "generic": "olanzapine"},
    {"brand": "seroquel",        "generic": "quetiapine"},
]

BASE_URL   = "https://api.fda.gov/drug/event.json"
DEFAULT_PAGE_SIZE = int(os.getenv("OPENFDA_PAGE_SIZE", "100"))  # openFDA max per request is 100
DEFAULT_MAX_PAGES = int(os.getenv("OPENFDA_MAX_PAGES", "10"))   # default 10 pages × 100 = 1,000 reports
RAW_DIR    = Path(__file__).parent.parent / "data" / "raw"


def _build_params(drug_name: str, generic: str, skip: int, page_size: int = DEFAULT_PAGE_SIZE,
                  start_date: str = None, end_date: str = None) -> dict:
    """
    Build openFDA query params using both brand and generic name fields.
    Optionally supports receiptdate range filtering: [YYYYMMDD TO YYYYMMDD].
    Uses ' AND ' conjunction syntax (requests will URL-encode cleanly).
    """
    parts = [
        f'patient.drug.openfda.brand_name:"{drug_name}"',
        f'patient.drug.openfda.generic_name:"{generic}"'
    ]
    if start_date and end_date:
        parts.append(f'receiptdate:[{start_date} TO {end_date}]')
    elif start_date:
        parts.append(f'receiptdate:[{start_date} TO 20991231]')

    search_query = " AND ".join(parts)

    params = {
        "search": search_query,
        "limit":  min(max(page_size, 1), 100),
        "skip":   skip,
    }
    api_key = os.getenv("OPENFDA_API_KEY")
    if api_key:
        params["api_key"] = api_key
    return params


def _fetch_page(drug: dict, skip: int, page_size: int = DEFAULT_PAGE_SIZE,
                start_date: str = None, end_date: str = None,
                retries: int = 4, initial_backoff: float = 1.0) -> list[dict]:
    """
    Fetch one page of results with exponential backoff on 429, timeouts, and transient 5xx errors.
    """
    params = _build_params(drug["brand"], drug["generic"], skip, page_size=page_size,
                           start_date=start_date, end_date=end_date)
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(BASE_URL, params=params, timeout=30)
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    return data.get("results", [])
                except json.JSONDecodeError as jde:
                    log.error(f"Malformed JSON for {drug['brand']} at skip={skip}: {jde}")
                    return []
            elif resp.status_code == 404:
                # openFDA returns 404 when no records match or beyond total matches
                log.info(f"No further records found for {drug['brand']} at skip={skip} (HTTP 404).")
                return []
            elif resp.status_code == 429:
                wait = initial_backoff * (2 ** (attempt - 1))
                log.warning(f"Rate limited (HTTP 429) on {drug['brand']}. Backing off {wait:.1f}s (attempt {attempt}/{retries})")
                time.sleep(wait)
            elif resp.status_code in (500, 502, 503, 504):
                wait = initial_backoff * (2 ** (attempt - 1))
                log.warning(f"Server error (HTTP {resp.status_code}) for {drug['brand']}. Retrying in {wait:.1f}s (attempt {attempt}/{retries})")
                time.sleep(wait)
            else:
                log.error(f"HTTP {resp.status_code} client error for {drug['brand']}: {resp.text[:200]}")
                return []
        except requests.RequestException as e:
            wait = initial_backoff * (2 ** (attempt - 1))
            log.warning(f"Request exception for {drug['brand']} ({e}). Retrying in {wait:.1f}s (attempt {attempt}/{retries})")
            if attempt == retries:
                log.error(f"Max retries reached for {drug['brand']} at skip={skip}.")
                return []
            time.sleep(wait)
    return []


def extract_drug(drug: dict, page_size: int = DEFAULT_PAGE_SIZE,
                 max_pages: int = DEFAULT_MAX_PAGES,
                 start_date: str = None, end_date: str = None) -> list[dict]:
    """
    Extract adverse event reports for a single drug.
    Logs requested, received, and saved records with parameter audit metadata.
    Clearly flags when extraction reaches max_pages limit.
    """
    brand = drug["brand"]
    generic = drug["generic"]
    all_results = []
    extraction_start = datetime.now()

    log.info(f"Starting extraction for {brand} ({generic}) | page_size={page_size}, max_pages={max_pages}, date_range={start_date} to {end_date}")
    capped = False

    for page in range(max_pages):
        skip = page * page_size
        results = _fetch_page(drug, skip, page_size=page_size,
                              start_date=start_date, end_date=end_date)
        if not results:
            break
        all_results.extend(results)
        log.info(f"  {brand}: page {page + 1}/{max_pages} -> received {len(results)} records (running total: {len(all_results)})")
        if len(results) < page_size:
            # End of available dataset
            break
        if page == max_pages - 1:
            capped = True
        time.sleep(0.25)

    if capped:
        log.warning(f"Extraction for {brand} hit configured cap of {max_pages * page_size} records. More records may exist in openFDA.")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RAW_DIR / f"{brand}_raw.json"

    # Save raw records accompanied by extraction metadata for auditability and reproducibility
    payload = {
        "metadata": {
            "brand": brand,
            "generic": generic,
            "extracted_at": extraction_start.isoformat(),
            "records_count": len(all_results),
            "page_size": page_size,
            "max_pages": max_pages,
            "is_capped": capped,
            "start_date": start_date,
            "end_date": end_date,
        },
        "results": all_results,
    }
    with open(out_path, "w") as f:
        json.dump(payload, f, default=str)
    log.info(f"  Saved {len(all_results)} raw records to {out_path} (capped={capped})")

    return all_results


def extract_all(page_size: int = DEFAULT_PAGE_SIZE,
                max_pages: int = DEFAULT_MAX_PAGES,
                start_date: str = None, end_date: str = None) -> dict[str, list[dict]]:
    """
    Extract all target drugs.
    Returns {brand_name: [raw_report, ...]}
    """
    results = {}
    for drug in DRUGS:
        results[drug["brand"]] = extract_drug(
            drug, page_size=page_size, max_pages=max_pages,
            start_date=start_date, end_date=end_date
        )
    return results


if __name__ == "__main__":
    from datetime import datetime
    data = extract_all()
    for brand, records in data.items():
        print(f"{brand}: {len(records)} records extracted")
