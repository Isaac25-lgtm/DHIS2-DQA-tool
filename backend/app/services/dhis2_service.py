from __future__ import annotations

import base64
from datetime import UTC, date, datetime
import hashlib
import re
from typing import Any

import httpx
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal
from app.models.base import PeriodType
from app.models.dhis2_session import Dhis2Session
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
_DHIS2_SESSION_ID = "active"
_SEARCH_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+")


def _password_cipher() -> Fernet:
    digest = hashlib.sha256(get_settings().secret_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _encrypt_password(password: str) -> str:
    return _password_cipher().encrypt(password.encode("utf-8")).decode("utf-8")


def _decrypt_password(encrypted_password: str) -> str | None:
    try:
        return _password_cipher().decrypt(encrypted_password.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        return None


def _has_active_memory_session() -> bool:
    return bool(
        _DHIS2_ACTIVE_SESSION.get("base_url")
        and _DHIS2_ACTIVE_SESSION.get("username")
        and _DHIS2_ACTIVE_SESSION.get("password")
    )


def _load_persisted_session() -> bool:
    if _has_active_memory_session():
        return True
    try:
        with SessionLocal() as db:
            persisted = db.get(Dhis2Session, _DHIS2_SESSION_ID)
            if not persisted:
                return False
            password = _decrypt_password(persisted.encrypted_password)
            if not password:
                return False
            _DHIS2_ACTIVE_SESSION.clear()
            _DHIS2_ACTIVE_SESSION.update(
                {
                    "base_url": persisted.base_url,
                    "username": persisted.username,
                    "password": password,
                    "signed_in_at": persisted.signed_in_at.isoformat(),
                }
            )
            return True
    except Exception:
        return False


def _persist_session(
    *,
    base_url: str,
    username: str,
    password: str,
    signed_in_at: datetime,
    signed_in_by_user_id: Any = None,
) -> None:
    try:
        with SessionLocal() as db:
            persisted = db.get(Dhis2Session, _DHIS2_SESSION_ID)
            if not persisted:
                persisted = Dhis2Session(id=_DHIS2_SESSION_ID)
                db.add(persisted)
            persisted.base_url = base_url
            persisted.username = username
            persisted.encrypted_password = _encrypt_password(password)
            persisted.signed_in_at = signed_in_at
            persisted.signed_in_by_user_id = signed_in_by_user_id
            db.commit()
    except Exception:
        # The in-memory session remains usable even if persistence fails.
        return


def _delete_persisted_session() -> None:
    try:
        with SessionLocal() as db:
            persisted = db.get(Dhis2Session, _DHIS2_SESSION_ID)
            if persisted:
                db.delete(persisted)
                db.commit()
    except Exception:
        return


def is_dhis2_configured() -> bool:
    settings = get_settings()
    return bool(
        _has_active_memory_session()
        or _load_persisted_session()
        or (settings.dhis2_base_url and settings.dhis2_username and settings.dhis2_password)
    )


def _client() -> httpx.Client:
    _load_persisted_session()
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
    _load_persisted_session()
    return (_DHIS2_ACTIVE_SESSION.get("base_url") or get_settings().dhis2_base_url).rstrip("/")


def sign_in_to_dhis2(
    *,
    base_url: str | None,
    username: str,
    password: str,
    signed_in_by_user_id: Any = None,
) -> Dhis2ConnectionStatus:
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
        existing_session_available = is_dhis2_configured()
        return Dhis2ConnectionStatus(
            connected=False,
            signed_in=existing_session_available,
            base_url=normalized_base_url,
            last_checked_at=checked_at,
            message=(
                "Could not sign in to DHIS2. Check username, password, base URL, or network. "
                "Any existing DHIS2 session was kept."
            ),
            reachability="reachable" if probe_dhis2_reachability(normalized_base_url) else "unreachable",
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
    _persist_session(
        base_url=normalized_base_url,
        username=username,
        password=password,
        signed_in_at=checked_at,
        signed_in_by_user_id=signed_in_by_user_id,
    )
    return Dhis2ConnectionStatus(
        connected=True,
        signed_in=True,
        base_url=normalized_base_url,
        last_checked_at=checked_at,
        message="DHIS2 sign-in successful.",
        reachability="reachable",
    )


def clear_dhis2_session() -> None:
    _DHIS2_ACTIVE_SESSION.clear()
    _delete_persisted_session()


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
        session_available = is_dhis2_configured()
        return Dhis2ConnectionStatus(
            connected=False,
            signed_in=session_available,
            base_url=base_url,
            last_checked_at=checked_at,
            message=(
                "DHIS2 is reachable but the active session could not be verified. "
                "The session was kept; only use Sign out if you want to clear it."
                if session_available
                else "DHIS2 is reachable but no manager is signed in. Sign in again from Settings."
            ),
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
    return sorted(
        results,
        key=lambda item: (
            _search_rank(
                cleaned,
                [
                    item.facility_name,
                    item.dhis2_code,
                    item.dhis2_org_unit_uid,
                    item.district,
                    item.dhis2_parent_name,
                ],
            ),
            item.facility_name.lower(),
        ),
    )


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


def _build_data_element_search_filters(query: str) -> list[str]:
    cleaned = query.strip()
    compact = re.sub(r"\s+", "", cleaned)
    candidates = [cleaned, compact, cleaned.upper(), compact.upper()]
    candidates.extend(_SEARCH_TOKEN_PATTERN.findall(cleaned))

    filters: list[str] = []
    for candidate in dict.fromkeys(value for value in candidates if len(value) >= 2):
        filters.extend(
            [
                f"identifiable:token:{candidate}",
                f"code:ilike:{candidate}",
                f"name:ilike:{candidate}",
                f"shortName:ilike:{candidate}",
            ]
        )
        if "-" not in candidate and len(candidate) <= 12:
            filters.append(f"code:ilike:105-{candidate}")
        if 8 <= len(candidate) <= 16 and " " not in candidate:
            filters.append(f"id:eq:{candidate}")
    return list(dict.fromkeys(filters))


def _build_category_option_combo_search_filters(query: str) -> list[str]:
    cleaned = query.strip()
    compact = re.sub(r"\s+", "", cleaned)
    candidates = [cleaned, compact, cleaned.upper(), compact.upper()]
    candidates.extend(_SEARCH_TOKEN_PATTERN.findall(cleaned))

    filters: list[str] = []
    for candidate in dict.fromkeys(value for value in candidates if len(value) >= 2):
        filters.extend(
            [
                f"identifiable:token:{candidate}",
                f"name:ilike:{candidate}",
                f"code:ilike:{candidate}",
            ]
        )
        if 8 <= len(candidate) <= 16 and " " not in candidate:
            filters.append(f"id:eq:{candidate}")
    return list(dict.fromkeys(filters))


def _normalize_search_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _search_tokens(value: str) -> list[str]:
    return [token.lower() for token in _SEARCH_TOKEN_PATTERN.findall(value)]


def _search_rank(query: str, values: list[str | None]) -> int:
    cleaned = query.strip().lower()
    normalized_query = _normalize_search_text(cleaned)
    query_tokens = _search_tokens(query)
    significant_query_tokens = [token for token in query_tokens if len(token) >= 2]
    texts = [str(value).strip().lower() for value in values if value]
    normalized_texts = [_normalize_search_text(value) for value in texts]
    value_token_sets = [set(_search_tokens(value)) for value in texts]
    value_tokens = [token for value in texts for token in _search_tokens(value)]
    if not cleaned:
        return 99

    if any(value == cleaned or (normalized_query and value == normalized_query) for value in texts + normalized_texts):
        return 0

    if significant_query_tokens and any(
        set(significant_query_tokens).issubset(tokens) for tokens in value_token_sets
    ):
        return 1

    if any(
        value.startswith(cleaned)
        or (normalized_query and value.startswith(normalized_query))
        for value in texts + normalized_texts
    ):
        return 2

    if normalized_query and any(token == normalized_query for token in value_tokens):
        return 2

    if any(
        token.startswith(normalized_query)
        for token in value_tokens
        if normalized_query and len(normalized_query) >= 2
    ):
        return 3

    if any(cleaned in value or (normalized_query and normalized_query in value) for value in texts + normalized_texts):
        return 4

    combined = " ".join(texts)
    if significant_query_tokens and all(token in combined for token in significant_query_tokens):
        return 5

    if normalized_query and any(
        all(token in value for token in significant_query_tokens)
        for value in normalized_texts
    ):
        return 6

    return 7


def _search_sort_text(values: list[str | None]) -> str:
    for value in values:
        if value:
            return str(value).lower()
    return ""


def _dataset_name_for_data_element(item: dict[str, Any]) -> str | None:
    datasets = [
        element.get("dataSet", {}).get("name")
        for element in item.get("dataSetElements", [])
        if isinstance(element, dict)
    ]
    dataset_name = next((name for name in datasets if name and HMIS_105_DATASET_HINT in name), None)
    if not dataset_name:
        dataset_name = next((name for name in datasets if name), None)
    return dataset_name


def _category_combo_for_data_element(item: dict[str, Any]) -> dict[str, Any]:
    return item.get("categoryCombo") if isinstance(item.get("categoryCombo"), dict) else {}


def _category_option_combo_name(option_combo: dict[str, Any]) -> str:
    name = str(option_combo.get("name") or "").strip()
    if name:
        return name
    option_names = [
        str(option.get("name")).strip()
        for option in option_combo.get("categoryOptions", [])
        if isinstance(option, dict) and option.get("name")
    ]
    return ", ".join(option_names)


def _category_combo_label(category_combo_name: str | None, option_combo: dict[str, Any] | None = None) -> str | None:
    option_combo_name = _category_option_combo_name(option_combo or {}) if option_combo else None
    parts = [
        part
        for part in (category_combo_name, option_combo_name)
        if part and part.lower() not in {"default", "default category combo", "default option combo"}
    ]
    return " - ".join(dict.fromkeys(parts)) or category_combo_name or option_combo_name


def _data_element_search_result(
    item: dict[str, Any],
    *,
    identifier: str,
    category_combo_label: str | None,
    imported_identifiers: set[str],
    option_combo_name: str | None = None,
) -> Dhis2DataElementSearchResult:
    name = str(item["name"])
    if option_combo_name and option_combo_name.lower() not in name.lower():
        name = f"{name} - {option_combo_name}"

    return Dhis2DataElementSearchResult(
        data_element_uid=str(item["id"]),
        dhis2_uid_or_operand=identifier,
        name=name,
        short_name=item.get("shortName"),
        hmis_code=_extract_hmis_code(item),
        value_type=item.get("valueType"),
        aggregation_type=item.get("aggregationType"),
        category_combo=category_combo_label,
        dataset_name=_dataset_name_for_data_element(item),
        already_imported=identifier in imported_identifiers,
    )


def _build_data_element_search_results(
    item: dict[str, Any],
    *,
    category_option_combos: list[dict[str, Any]],
    imported_identifiers: set[str],
    include_plain_result: bool,
    allowed_option_combo_ids: set[str] | None = None,
) -> list[Dhis2DataElementSearchResult]:
    if not isinstance(item, dict) or not item.get("id") or not item.get("name"):
        return []

    identifier = str(item["id"])
    category_combo = _category_combo_for_data_element(item)
    category_combo_name = category_combo.get("name")
    results: list[Dhis2DataElementSearchResult] = []

    filtered_option_combos = [
        combo
        for combo in category_option_combos
        if isinstance(combo, dict)
        and combo.get("id")
        and (allowed_option_combo_ids is None or str(combo["id"]) in allowed_option_combo_ids)
    ]

    for option_combo in filtered_option_combos:
        option_combo_id = str(option_combo["id"])
        option_combo_name = _category_option_combo_name(option_combo)
        results.append(
            _data_element_search_result(
                item,
                identifier=f"{identifier}.{option_combo_id}",
                category_combo_label=_category_combo_label(category_combo_name, option_combo),
                imported_identifiers=imported_identifiers,
                option_combo_name=option_combo_name,
            )
        )

    if include_plain_result:
        results.append(
            _data_element_search_result(
                item,
                identifier=identifier,
                category_combo_label=_category_combo_label(category_combo_name),
                imported_identifiers=imported_identifiers,
            )
        )

    return results


def _matching_category_option_combos(
    client: httpx.Client,
    *,
    base_url: str,
    query: str,
) -> tuple[dict[str, list[dict[str, Any]]], set[str]]:
    endpoint = f"{base_url}/categoryOptionCombos.json"
    combos_by_category_combo: dict[str, list[dict[str, Any]]] = {}
    matching_combo_ids: set[str] = set()
    for filter_value in _build_category_option_combo_search_filters(query):
        try:
            response = client.get(
                endpoint,
                params={
                    "filter": filter_value,
                    "fields": "id,name,code,categoryCombo[id,name],categoryOptions[id,name,code]",
                    "pageSize": 50,
                },
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError):
            continue
        for combo in payload.get("categoryOptionCombos", []):
            if not isinstance(combo, dict) or not combo.get("id"):
                continue
            category_combo = combo.get("categoryCombo") if isinstance(combo.get("categoryCombo"), dict) else {}
            category_combo_id = category_combo.get("id")
            if not category_combo_id:
                continue
            combo.setdefault("categoryCombo", category_combo)
            combos_by_category_combo.setdefault(str(category_combo_id), []).append(combo)
            matching_combo_ids.add(str(combo["id"]))
    return combos_by_category_combo, matching_combo_ids


def _category_option_combos_for_category_combo(
    client: httpx.Client,
    *,
    base_url: str,
    category_combo_id: str,
) -> list[dict[str, Any]]:
    try:
        response = client.get(
            f"{base_url}/categoryCombos/{category_combo_id}.json",
            params={
                "fields": "id,name,categoryOptionCombos[id,name,code,categoryOptions[id,name,code]]",
            },
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError):
        return []

    return [
        combo
        for combo in payload.get("categoryOptionCombos", [])
        if isinstance(combo, dict) and combo.get("id")
    ]


def search_dhis2_data_elements(db: Session, query: str) -> list[Dhis2DataElementSearchResult]:
    if not is_dhis2_configured():
        return []
    cleaned = query.strip()
    if len(cleaned) < 2:
        return []

    base_url = _base_url()
    endpoint = f"{base_url}/dataElements.json"
    filters = _build_data_element_search_filters(cleaned)

    fields = "id,name,shortName,code,valueType,aggregationType,categoryCombo[id,name],dataSetElements[dataSet[id,name]]"
    items_by_id: dict[str, dict[str, Any]] = {}
    direct_match_ids: set[str] = set()
    category_combo_match_ids: dict[str, set[str]] = {}
    try:
        with _client() as client:
            combos_by_category_combo, matching_combo_ids = _matching_category_option_combos(
                client,
                base_url=base_url,
                query=cleaned,
            )
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
                        direct_match_ids.add(str(item["id"]))
            for category_combo_id, combos in combos_by_category_combo.items():
                try:
                    response = client.get(
                        endpoint,
                        params={
                            "filter": f"categoryCombo.id:eq:{category_combo_id}",
                            "fields": fields,
                            "pageSize": 50,
                        },
                    )
                    response.raise_for_status()
                    payload = response.json()
                except (httpx.HTTPError, ValueError):
                    continue
                allowed_combo_ids = {str(combo["id"]) for combo in combos if isinstance(combo, dict) and combo.get("id")}
                category_combo_match_ids.setdefault(category_combo_id, set()).update(allowed_combo_ids)
                for item in payload.get("dataElements", []):
                    if isinstance(item, dict) and item.get("id"):
                        items_by_id[str(item["id"])] = item
            category_combo_ids = {
                str(category_combo["id"])
                for item in items_by_id.values()
                for category_combo in [_category_combo_for_data_element(item)]
                if category_combo.get("id")
            }
            for category_combo_id in category_combo_ids:
                fetched_combos = _category_option_combos_for_category_combo(
                    client,
                    base_url=base_url,
                    category_combo_id=category_combo_id,
                )
                if fetched_combos:
                    combos_by_category_combo[category_combo_id] = fetched_combos
    except (httpx.HTTPError, ValueError):
        return []

    imported_identifiers = set(
        db.scalars(
            select(Indicator.dhis2_uid_or_operand).where(Indicator.dhis2_uid_or_operand.is_not(None))
        )
    )
    results: list[Dhis2DataElementSearchResult] = []
    seen_identifiers: set[str] = set()
    for item in items_by_id.values():
        category_combo = _category_combo_for_data_element(item)
        category_combo_id = str(category_combo.get("id") or "")
        item_id = str(item.get("id") or "")
        item_results = _build_data_element_search_results(
            item,
            category_option_combos=combos_by_category_combo.get(category_combo_id, []),
            imported_identifiers=imported_identifiers,
            include_plain_result=item_id in direct_match_ids,
            allowed_option_combo_ids=(
                None
                if item_id in direct_match_ids
                else category_combo_match_ids.get(category_combo_id, matching_combo_ids)
            ),
        )
        for result in item_results:
            if result.dhis2_uid_or_operand in seen_identifiers:
                continue
            seen_identifiers.add(result.dhis2_uid_or_operand)
            results.append(result)
    return sorted(
        results,
        key=lambda item: (
            _search_rank(
                cleaned,
                [
                    item.name,
                    item.short_name,
                    item.hmis_code,
                    item.dhis2_uid_or_operand,
                    item.data_element_uid,
                    item.category_combo,
                    item.dataset_name,
                ],
            ),
            item.name.lower(),
        ),
    )[:120]


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
    value: int | None = None,
    error_message: str | None = None,
) -> dict[str, Any]:
    return {
        "identifier": identifier,
        "value": value,
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
        identifier: _empty_result(identifier, status=DHIS2_NO_DATA, value=0, extracted_at=extracted_timestamp)
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
