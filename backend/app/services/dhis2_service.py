from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.base import PeriodType
from app.models.facility import Facility
from app.models.indicator import Indicator
from app.schemas.dhis2 import Dhis2ConnectionStatus
from app.schemas.facility import Dhis2FacilitySearchResult
from app.schemas.indicator import Dhis2DataElementSearchResult

DHIS2_SUCCESS = "SUCCESS"
DHIS2_NO_DATA = "NO_DATA"
DHIS2_ERROR = "ERROR"
DHIS2_NOT_CONFIGURED = "NOT_CONFIGURED"
HMIS_105_DATASET_HINT = "HMIS 105"

_DHIS2_ACTIVE_SESSION: dict[str, str] = {}


def is_dhis2_configured() -> bool:
    settings = get_settings()
    return bool(
        (
            _DHIS2_ACTIVE_SESSION.get("base_url")
            and _DHIS2_ACTIVE_SESSION.get("username")
            and _DHIS2_ACTIVE_SESSION.get("password")
        )
        or (settings.dhis2_base_url and settings.dhis2_username and settings.dhis2_password)
    )


def _client() -> httpx.Client:
    if _DHIS2_ACTIVE_SESSION.get("username") and _DHIS2_ACTIVE_SESSION.get("password"):
        return httpx.Client(
            timeout=15.0,
            auth=(_DHIS2_ACTIVE_SESSION["username"], _DHIS2_ACTIVE_SESSION["password"]),
        )
    settings = get_settings()
    username = getattr(settings, "dhis2_username", "")
    password = getattr(settings, "dhis2_password", "")
    if username and password:
        return httpx.Client(timeout=15.0, auth=(username, password))
    raise RuntimeError("DHIS2 manager session is not active.")


def _base_url() -> str:
    return (_DHIS2_ACTIVE_SESSION.get("base_url") or get_settings().dhis2_base_url).rstrip("/")


def sign_in_to_dhis2(*, base_url: str | None, username: str, password: str) -> Dhis2ConnectionStatus:
    checked_at = datetime.now(UTC)
    normalized_base_url = (base_url or get_settings().dhis2_base_url).strip().rstrip("/")
    if not normalized_base_url:
        return Dhis2ConnectionStatus(
            connected=False,
            signed_in=False,
            base_url="",
            last_checked_at=checked_at,
            message="DHIS2 base URL is required.",
        )

    try:
        with httpx.Client(timeout=15.0, auth=(username, password)) as client:
            response = client.get(f"{normalized_base_url}/me.json", params={"fields": "id,name"})
            response.raise_for_status()
    except httpx.HTTPError:
        clear_dhis2_session()
        return Dhis2ConnectionStatus(
            connected=False,
            signed_in=False,
            base_url=normalized_base_url,
            last_checked_at=checked_at,
            message="Could not sign in to DHIS2. Check username, password, base URL, or network.",
        )

    _DHIS2_ACTIVE_SESSION.clear()
    _DHIS2_ACTIVE_SESSION.update(
        {
            "base_url": normalized_base_url,
            "username": username,
            "password": password,
            "signed_in_at": checked_at.isoformat(),
        }
    )
    return Dhis2ConnectionStatus(
        connected=True,
        signed_in=True,
        base_url=normalized_base_url,
        last_checked_at=checked_at,
        message="DHIS2 sign-in successful.",
    )


def clear_dhis2_session() -> None:
    _DHIS2_ACTIVE_SESSION.clear()


def probe_dhis2_reachability(base_url: str | None = None) -> bool:
    """Lightweight, credential-free reachability check.

    Hits the DHIS2 base URL with a short-timeout GET and treats any HTTP response
    (even 401 / 403) as 'reachable' — what we care about is whether the server is
    on the network. Connection failures or timeouts return False.
    """
    target = (base_url or _base_url()).rstrip("/")
    if not target:
        return False
    try:
        with httpx.Client(timeout=httpx.Timeout(5.0, connect=4.0)) as client:
            response = client.get(target)
        return 100 <= response.status_code < 600
    except httpx.HTTPError:
        return False


def check_dhis2_connection() -> Dhis2ConnectionStatus:
    """Report DHIS2 status to callers.

    Returns three independent signals:
      reachability: "reachable" | "unreachable" | "not_configured"
      signed_in:    has a manager signed in (server-side session present)
      connected:    legacy boolean — true only if reachable AND signed in AND we can
                    successfully call /me.json with the cached credentials.
    """
    checked_at = datetime.now(UTC)
    base_url = _base_url()

    if not base_url:
        return Dhis2ConnectionStatus(
            connected=False,
            signed_in=False,
            base_url="",
            last_checked_at=checked_at,
            message="DHIS2 base URL is not configured.",
            reachability="not_configured",
        )

    reachable = probe_dhis2_reachability(base_url)
    reachability: str = "reachable" if reachable else "unreachable"

    if not reachable:
        return Dhis2ConnectionStatus(
            connected=False,
            signed_in=is_dhis2_configured(),
            base_url=base_url,
            last_checked_at=checked_at,
            message=(
                "DHIS2 is currently unreachable. The platform will continue to accept "
                "assessment data; managers can refresh DHIS2 values once "
                "the connection returns."
            ),
            reachability="unreachable",
        )

    if not is_dhis2_configured():
        return Dhis2ConnectionStatus(
            connected=False,
            signed_in=False,
            base_url=base_url,
            last_checked_at=checked_at,
            message="DHIS2 is reachable but no manager is signed in. Sign in from Settings to enable live DHIS2 sync.",
            reachability=reachability,
        )

    try:
        with _client() as client:
            response = client.get(f"{base_url}/me.json", params={"fields": "id,name"})
            response.raise_for_status()
        return Dhis2ConnectionStatus(
            connected=True,
            signed_in=True,
            base_url=base_url,
            last_checked_at=checked_at,
            message="DHIS2 connection successful.",
            reachability=reachability,
        )
    except httpx.HTTPError:
        return Dhis2ConnectionStatus(
            connected=False,
            signed_in=False,
            base_url=base_url,
            last_checked_at=checked_at,
            message="DHIS2 is reachable but the saved credentials no longer work. Sign in again from Settings.",
            reachability=reachability,
        )


def _infer_facility_type(name: str) -> str:
    lowered = name.lower()
    if "hc iv" in lowered or "health centre iv" in lowered:
        return "HC IV"
    if "hc iii" in lowered or "health centre iii" in lowered:
        return "HC III"
    if "hc ii" in lowered or "health centre ii" in lowered:
        return "HC II"
    if "hospital" in lowered:
        return "Hospital"
    return "Other"


def search_dhis2_facilities(db: Session, query: str) -> list[Dhis2FacilitySearchResult]:
    if not is_dhis2_configured():
        return []
    cleaned = query.strip()
    if len(cleaned) < 2:
        return []

    endpoint = f"{_base_url()}/organisationUnits.json"
    filters = [f"name:ilike:{cleaned}", f"code:ilike:{cleaned}"]
    if 8 <= len(cleaned) <= 16 and " " not in cleaned:
        filters.append(f"id:eq:{cleaned}")
    items_by_id: dict[str, dict[str, Any]] = {}
    try:
        with _client() as client:
            for filter_value in filters:
                response = client.get(
                    endpoint,
                    params={
                        "filter": filter_value,
                        "fields": "id,code,name,path,level,parent[id,name]",
                        "pageSize": 20,
                    },
                )
                response.raise_for_status()
                payload = response.json()
                for item in payload.get("organisationUnits", []):
                    if isinstance(item, dict) and item.get("id"):
                        items_by_id[str(item["id"])] = item
    except (httpx.HTTPError, ValueError):
        return []

    imported_uids = set(
        db.scalars(
            select(Facility.dhis2_org_unit_uid).where(Facility.dhis2_org_unit_uid.is_not(None))
        )
    )
    results: list[Dhis2FacilitySearchResult] = []
    for item in items_by_id.values():
        if not isinstance(item, dict) or not item.get("id") or not item.get("name"):
            continue
        parent = item.get("parent") if isinstance(item.get("parent"), dict) else {}
        parent_name = parent.get("name")
        results.append(
            Dhis2FacilitySearchResult(
                dhis2_org_unit_uid=str(item["id"]),
                dhis2_code=item.get("code"),
                facility_name=str(item["name"]),
                district=str(parent_name or "Unknown district"),
                facility_type=_infer_facility_type(str(item["name"])),
                ownership=None,
                dhis2_path=item.get("path"),
                dhis2_parent_name=parent_name,
                dhis2_level=item.get("level"),
                already_imported=str(item["id"]) in imported_uids,
            )
        )
    return results


def _extract_hmis_code(item: dict[str, Any]) -> str | None:
    for key in ("code", "name", "shortName"):
        raw_value = item.get(key)
        if not raw_value:
            continue
        tokens = str(raw_value).replace(".", " ").replace("_", " ").split()
        for token in tokens:
            cleaned = token.strip(":-,;()").upper()
            if cleaned.startswith("105-"):
                return cleaned
    return item.get("code")


def search_dhis2_data_elements(db: Session, query: str) -> list[Dhis2DataElementSearchResult]:
    if not is_dhis2_configured():
        return []
    cleaned = query.strip()
    if len(cleaned) < 2:
        return []

    endpoint = f"{_base_url()}/dataElements.json"
    filters = [
        f"identifiable:token:{cleaned}",
        f"code:ilike:{cleaned}",
        f"name:ilike:{cleaned}",
        f"shortName:ilike:{cleaned}",
    ]
    normalized_code = cleaned.upper().replace(" ", "")
    if normalized_code != cleaned:
        filters.append(f"code:ilike:{normalized_code}")
    if "-" not in normalized_code and len(normalized_code) <= 12:
        filters.append(f"code:ilike:105-{normalized_code}")
    if 8 <= len(cleaned) <= 16 and " " not in cleaned:
        filters.append(f"id:eq:{cleaned}")

    fields = "id,name,shortName,code,valueType,aggregationType,categoryCombo[id,name],dataSetElements[dataSet[id,name]]"
    items_by_id: dict[str, dict[str, Any]] = {}
    try:
        with _client() as client:
            for filter_value in dict.fromkeys(filters):
                response = client.get(
                    endpoint,
                    params={
                        "filter": filter_value,
                        "fields": fields,
                        "pageSize": 20,
                    },
                )
                response.raise_for_status()
                payload = response.json()
                for item in payload.get("dataElements", []):
                    if isinstance(item, dict) and item.get("id"):
                        items_by_id[str(item["id"])] = item
    except (httpx.HTTPError, ValueError):
        return []

    imported_identifiers = set(
        db.scalars(
            select(Indicator.dhis2_uid_or_operand).where(Indicator.dhis2_uid_or_operand.is_not(None))
        )
    )
    results: list[Dhis2DataElementSearchResult] = []
    for item in items_by_id.values():
        if not isinstance(item, dict) or not item.get("id") or not item.get("name"):
            continue
        datasets = [
            element.get("dataSet", {}).get("name")
            for element in item.get("dataSetElements", [])
            if isinstance(element, dict)
        ]
        dataset_name = next((name for name in datasets if name and HMIS_105_DATASET_HINT in name), None)
        if not dataset_name:
            dataset_name = next((name for name in datasets if name), None)
        category_combo = item.get("categoryCombo") if isinstance(item.get("categoryCombo"), dict) else {}
        identifier = str(item["id"])
        results.append(
            Dhis2DataElementSearchResult(
                data_element_uid=identifier,
                dhis2_uid_or_operand=identifier,
                name=str(item["name"]),
                short_name=item.get("shortName"),
                hmis_code=_extract_hmis_code(item),
                value_type=item.get("valueType"),
                aggregation_type=item.get("aggregationType"),
                category_combo=category_combo.get("name"),
                dataset_name=dataset_name,
                already_imported=identifier in imported_identifiers,
            )
        )
    return results


def normalize_reporting_period(reporting_period: str, period_type: PeriodType) -> str:
    raw_value = reporting_period.strip()
    if period_type == PeriodType.MONTHLY:
        return raw_value.replace("-", "")
    if period_type == PeriodType.QUARTERLY:
        return raw_value.replace("-", "").upper()
    return raw_value


def _empty_result(
    identifier: str,
    *,
    status: str,
    extracted_at: datetime,
    error_message: str | None = None,
) -> dict[str, Any]:
    return {
        "identifier": identifier,
        "value": None,
        "status": status,
        "error_message": error_message,
        "extracted_at": extracted_at,
    }


def normalize_dhis2_analytics_response(
    payload: dict[str, Any],
    identifiers: list[str],
    *,
    extracted_at: datetime | None = None,
) -> dict[str, dict[str, Any]]:
    extracted_timestamp = extracted_at or datetime.now(UTC)
    normalized = {
        identifier: _empty_result(identifier, status=DHIS2_NO_DATA, extracted_at=extracted_timestamp)
        for identifier in identifiers
    }
    headers = payload.get("headers") or []
    rows = payload.get("rows") or []
    header_positions = {
        str(header.get("name", "")).lower(): index for index, header in enumerate(headers) if isinstance(header, dict)
    }
    dx_index = header_positions.get("dx")
    value_index = header_positions.get("value")
    if dx_index is None or value_index is None:
        return {
            identifier: _empty_result(
                identifier,
                status=DHIS2_ERROR,
                extracted_at=extracted_timestamp,
                error_message="DHIS2 analytics response did not include expected headers.",
            )
            for identifier in identifiers
        }

    for row in rows:
        if not isinstance(row, list) or dx_index >= len(row) or value_index >= len(row):
            continue
        identifier = str(row[dx_index])
        if identifier not in normalized:
            continue
        raw_value = row[value_index]
        if raw_value in (None, ""):
            continue
        try:
            parsed_value = int(float(raw_value))
        except (TypeError, ValueError):
            normalized[identifier] = _empty_result(
                identifier,
                status=DHIS2_ERROR,
                extracted_at=extracted_timestamp,
                error_message=f"DHIS2 returned a non-numeric value: {raw_value}",
            )
            continue
        current_value = normalized.get(identifier, {}).get("value")
        normalized[identifier] = {
            "identifier": identifier,
            "value": (int(current_value) if isinstance(current_value, int) else 0) + parsed_value,
            "status": DHIS2_SUCCESS,
            "error_message": None,
            "extracted_at": extracted_timestamp,
        }

    return normalized


def monthly_periods_between(start_date: date | None, end_date: date | None) -> list[str]:
    if not start_date or not end_date:
        return []

    current = date(start_date.year, start_date.month, 1)
    end_month = date(end_date.year, end_date.month, 1)
    if end_month < current:
        return []

    periods: list[str] = []
    while current <= end_month:
        periods.append(f"{current.year}{current.month:02d}")
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)
    return periods


def _analytics_params(*, identifiers: list[str], periods: list[str], facility_uid: str) -> list[tuple[str, str]]:
    return [
        ("dimension", f"dx:{';'.join(identifiers)}"),
        ("dimension", f"pe:{';'.join(periods)}"),
        ("dimension", f"ou:{facility_uid}"),
        ("displayProperty", "NAME"),
    ]


def fetch_dhis2_values(
    *,
    facility_uid: str,
    reporting_period: str,
    period_type: PeriodType,
    identifiers: list[str],
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, dict[str, Any]]:
    extracted_at = datetime.now(UTC)
    if not identifiers:
        return {}
    if not is_dhis2_configured():
        return {
            identifier: _empty_result(
                identifier,
                status=DHIS2_NOT_CONFIGURED,
                extracted_at=extracted_at,
                error_message="DHIS2 is not signed in. A manager must sign in to DHIS2 from Settings.",
            )
            for identifier in identifiers
        }

    periods = monthly_periods_between(start_date, end_date) or [normalize_reporting_period(reporting_period, period_type)]
    endpoint = f"{_base_url()}/analytics.json"

    try:
        with _client() as client:
            response = client.get(
                endpoint,
                params=_analytics_params(
                    identifiers=identifiers,
                    periods=periods,
                    facility_uid=facility_uid,
                ),
            )
            response.raise_for_status()
        payload = response.json()
        return normalize_dhis2_analytics_response(payload, identifiers, extracted_at=extracted_at)
    except (httpx.HTTPError, ValueError) as exc:
        return {
            identifier: _empty_result(
                identifier,
                status=DHIS2_ERROR,
                extracted_at=extracted_at,
                error_message=str(exc),
            )
            for identifier in identifiers
        }
