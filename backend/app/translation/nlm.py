"""Client for the free NLM Clinical Table Search Service (no API key).
Docs: https://clinicaltables.nlm.nih.gov/

Responses are positional arrays, e.g. for ICD-10-CM with df=code,name:
    [1, ["R10.9"], null, [["R10.9", "Unspecified abdominal pain"]]]
     ^total ^codes  ^extra ^one display array per code, in the order of `df`
"""
import time

import httpx

BASE_URL = "https://clinicaltables.nlm.nih.gov/api"
TIMEOUT = httpx.Timeout(5.0)        # seconds per attempt
RETRIES = 2                         # extra attempts after the first, for network errors and 5xx
BACKOFF_SECONDS = (0.5, 1.0)

# Which NLM table to search for each code system, and which fields to read back.
TABLES = {
    "HCPCS": {"path": "hcpcs/v3/search", "df": ["code", "long_desc", "short_desc"]},
    "ICD-10-CM": {"path": "icd10cm/v3/search", "df": ["code", "name"]},
}


class NLMUnavailable(Exception):
    """NLM could not be reached (timeout, network error, 5xx, rate limit, bad response)."""


def parse_search_response(data: list, df_fields: list[str]) -> list[dict]:
    """Turns NLM's positional array into a list of clean dicts keyed by the df field names."""
    if not isinstance(data, list) or len(data) < 4:
        raise NLMUnavailable("Unexpected NLM response shape")
    codes, displays = data[1] or [], data[3] or []
    results = []
    for code, values in zip(codes, displays):
        row = dict(zip(df_fields, values))
        row["code"] = code
        results.append(row)
    return results


def search(system: str, code: str, client: httpx.Client | None = None) -> list[dict]:
    """Searches one NLM table by code. Retries on network errors and 5xx, then raises NLMUnavailable."""
    table = TABLES[system]
    params = {"terms": code, "sf": "code", "df": ",".join(table["df"]), "maxList": 20}
    own_client = client is None
    client = client or httpx.Client(timeout=TIMEOUT)
    try:
        last_error: Exception | None = None
        for attempt in range(RETRIES + 1):
            try:
                resp = client.get(f"{BASE_URL}/{table['path']}", params=params)
                if resp.status_code >= 500:
                    raise NLMUnavailable(f"NLM returned HTTP {resp.status_code}")
                if resp.status_code != 200:  # 4xx incl. 429 rate limit: retrying won't help
                    raise NLMUnavailable(f"NLM returned HTTP {resp.status_code}")
                return parse_search_response(resp.json(), table["df"])
            except (httpx.TimeoutException, httpx.TransportError, NLMUnavailable, ValueError) as exc:
                last_error = exc
                retryable = not (isinstance(exc, NLMUnavailable) and "HTTP 4" in str(exc))
                if not retryable or attempt == RETRIES:
                    break
                time.sleep(BACKOFF_SECONDS[min(attempt, len(BACKOFF_SECONDS) - 1)])
        raise NLMUnavailable(str(last_error))
    finally:
        if own_client:
            client.close()