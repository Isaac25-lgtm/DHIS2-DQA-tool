from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


def normalize_indicator_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class IndicatorBase(BaseModel):
    indicator_name: str = Field(min_length=2, max_length=255)
    indicator_group: str = Field(min_length=2, max_length=100)
    hmis_code: str = Field(min_length=2, max_length=100)
    dhis2_uid_or_operand: str | None = None
    dataset_name: str | None = None
    hmis_section: str | None = None
    source_register: str | None = None
    category_combo: str | None = None
    value_type: str = "integer"
    aggregation_type: str | None = None
    is_active: bool = True
    is_required_by_default: bool = True
    default_discrepancy_threshold_percent: float = 5.0
    is_death_indicator: bool = False
    sort_order: int = 0
    notes: str | None = None

    @field_validator(
        "indicator_name",
        "indicator_group",
        "hmis_code",
        "dataset_name",
        "hmis_section",
        "source_register",
        "category_combo",
        "value_type",
        "aggregation_type",
        "notes",
        mode="before",
    )
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        return normalize_indicator_text(value)

    @field_validator("dhis2_uid_or_operand", mode="before")
    @classmethod
    def normalize_uid(cls, value: str | None) -> str | None:
        return normalize_indicator_text(value)

    @field_validator("default_discrepancy_threshold_percent")
    @classmethod
    def validate_threshold(cls, value: float) -> float:
        if value < 0:
            raise ValueError("Discrepancy threshold must be zero or greater.")
        return value


class IndicatorCreate(IndicatorBase):
    pass


class IndicatorUpdate(IndicatorBase):
    pass


class IndicatorRead(BaseModel):
    id: uuid.UUID
    indicator_name: str
    indicator_group: str
    hmis_code: str
    dhis2_uid_or_operand: str | None
    data_element_uid: str | None
    category_option_combo_uid: str | None
    dataset_name: str | None
    hmis_section: str | None
    source_register: str | None
    category_combo: str | None
    value_type: str
    aggregation_type: str | None
    is_active: bool
    is_required_by_default: bool
    default_discrepancy_threshold_percent: float
    is_death_indicator: bool
    sort_order: int
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IndicatorSeedResponse(BaseModel):
    created: int
    updated: int
    skipped: int
    message: str


class Dhis2DataElementSearchResult(BaseModel):
    data_element_uid: str
    dhis2_uid_or_operand: str
    name: str
    short_name: str | None = None
    hmis_code: str | None = None
    value_type: str | None = None
    aggregation_type: str | None = None
    category_combo: str | None = None
    dataset_name: str | None = None
    already_imported: bool = False


class IndicatorImportFromDhis2(IndicatorBase):
    data_element_uid: str | None = None
    category_option_combo_uid: str | None = None
