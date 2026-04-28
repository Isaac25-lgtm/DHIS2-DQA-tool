from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

FACILITY_TYPES = {"Hospital", "HC IV", "HC III", "HC II", "Other"}
OWNERSHIP_TYPES = {"PNFP", "Government", "Private", "Other"}


def normalize_optional_uid(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        raise ValueError("DHIS2 org unit UID cannot be blank when provided.")
    return normalized


class FacilityBase(BaseModel):
    facility_name: str = Field(min_length=2, max_length=255)
    district: str = Field(min_length=2, max_length=255)
    facility_type: str
    ownership: str
    dhis2_org_unit_uid: str | None = None
    dhis2_code: str | None = None
    dhis2_path: str | None = None
    dhis2_parent_name: str | None = None
    dhis2_level: int | None = None
    notes: str | None = None

    @field_validator("facility_name", "district", mode="before")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("facility_type")
    @classmethod
    def validate_facility_type(cls, value: str) -> str:
        normalized = value.strip()
        if normalized not in FACILITY_TYPES:
            raise ValueError(f"Facility type must be one of: {', '.join(sorted(FACILITY_TYPES))}.")
        return normalized

    @field_validator("ownership")
    @classmethod
    def validate_ownership(cls, value: str) -> str:
        normalized = value.strip()
        if normalized not in OWNERSHIP_TYPES:
            raise ValueError(f"Ownership must be one of: {', '.join(sorted(OWNERSHIP_TYPES))}.")
        return normalized

    @field_validator("dhis2_org_unit_uid")
    @classmethod
    def validate_uid(cls, value: str | None) -> str | None:
        return normalize_optional_uid(value)

    @field_validator("dhis2_code", "dhis2_path", "dhis2_parent_name", "notes", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class FacilityCreate(FacilityBase):
    is_active: bool = True


class FacilityUpdate(FacilityBase):
    is_active: bool = True


class FacilityRead(BaseModel):
    id: uuid.UUID
    facility_name: str
    district: str
    facility_type: str
    ownership: str
    dhis2_org_unit_uid: str | None
    dhis2_code: str | None
    dhis2_path: str | None
    dhis2_parent_name: str | None
    dhis2_level: int | None
    is_active: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Dhis2FacilitySearchResult(BaseModel):
    dhis2_org_unit_uid: str
    dhis2_code: str | None = None
    facility_name: str
    district: str
    facility_type: str = "Other"
    ownership: str | None = None
    dhis2_path: str | None = None
    dhis2_parent_name: str | None = None
    dhis2_level: int | None = None
    already_imported: bool = False


class FacilityImportFromDhis2(BaseModel):
    dhis2_org_unit_uid: str = Field(min_length=1, max_length=64)
    dhis2_code: str | None = None
    facility_name: str = Field(min_length=2, max_length=255)
    district: str = Field(min_length=2, max_length=255)
    facility_type: str = "Other"
    ownership: str = "Other"
    dhis2_path: str | None = None
    dhis2_parent_name: str | None = None
    dhis2_level: int | None = None

    @field_validator("facility_type")
    @classmethod
    def validate_import_facility_type(cls, value: str) -> str:
        normalized = value.strip() or "Other"
        return normalized if normalized in FACILITY_TYPES else "Other"

    @field_validator("ownership")
    @classmethod
    def validate_import_ownership(cls, value: str) -> str:
        normalized = value.strip() or "Other"
        return normalized if normalized in OWNERSHIP_TYPES else "Other"

    @field_validator("dhis2_org_unit_uid", "facility_name", "district")
    @classmethod
    def strip_required_import_strings(cls, value: str) -> str:
        return value.strip()
