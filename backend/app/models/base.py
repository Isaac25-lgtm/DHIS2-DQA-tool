import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )


class UserRole(str, enum.Enum):
    MANAGER = "MANAGER"
    ASSESSOR = "ASSESSOR"
    REVIEWER = "REVIEWER"
    VIEWER = "VIEWER"


class PeriodType(str, enum.Enum):
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    ANNUAL = "ANNUAL"
    CUSTOM = "CUSTOM"


class AssessmentRoundStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    IN_PROGRESS = "IN_PROGRESS"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"


class AssessmentFacilityStatus(str, enum.Enum):
    NOT_STARTED = "NOT_STARTED"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    DRAFT_SAVED = "DRAFT_SAVED"
    PENDING_SYNC = "PENDING_SYNC"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    RETURNED_FOR_CORRECTION = "RETURNED_FOR_CORRECTION"
    APPROVED = "APPROVED"
    CLOSED = "CLOSED"


class AssessmentTeamRole(str, enum.Enum):
    TEAM_LEAD = "TEAM_LEAD"
    TEAM_MEMBER = "TEAM_MEMBER"


class DqaValueStatus(str, enum.Enum):
    NOT_STARTED = "NOT_STARTED"
    DRAFT = "DRAFT"
    SAVED = "SAVED"
    SUBMITTED = "SUBMITTED"
    REVIEWED = "REVIEWED"
    RETURNED_FOR_CORRECTION = "RETURNED_FOR_CORRECTION"


class Dhis2ExtractionType(str, enum.Enum):
    FIELD_TIME_PULL = "FIELD_TIME_PULL"
    MANAGER_REVIEW_REFRESH = "MANAGER_REVIEW_REFRESH"


class ComparisonStatus(str, enum.Enum):
    NOT_COMPARED = "NOT_COMPARED"
    COMPARED = "COMPARED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    COMPARISON_FAILED = "COMPARISON_FAILED"


class DqaIssueType(str, enum.Enum):
    NO_ISSUE = "NO_ISSUE"
    REGISTER_TO_HMIS_SUMMARIZATION_ERROR = "REGISTER_TO_HMIS_SUMMARIZATION_ERROR"
    DHIS2_DATA_ENTRY_ERROR = "DHIS2_DATA_ENTRY_ERROR"
    MULTIPLE_STAGE_ERROR = "MULTIPLE_STAGE_ERROR"
    SOURCE_DOCUMENT_ISSUE = "SOURCE_DOCUMENT_ISSUE"
    HMIS105_REPORT_MISSING = "HMIS105_REPORT_MISSING"
    DHIS2_VALUE_MISSING = "DHIS2_VALUE_MISSING"
    VALUE_MISSING = "VALUE_MISSING"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class SeverityLevel(str, enum.Enum):
    EXACT = "EXACT"
    MINOR = "MINOR"
    MODERATE = "MODERATE"
    MAJOR = "MAJOR"
    CRITICAL = "CRITICAL"
    MISSING = "MISSING"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class CorrectiveActionStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    VERIFIED = "VERIFIED"
    CLOSED = "CLOSED"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"


class ReportStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    GENERATED = "GENERATED"
    REVIEWED = "REVIEWED"
    APPROVED = "APPROVED"
    EXPORTED = "EXPORTED"
    ARCHIVED = "ARCHIVED"


class ReportType(str, enum.Enum):
    FACILITY_DQA_REPORT = "FACILITY_DQA_REPORT"
    CONSOLIDATED_UCMB_DQA_REPORT = "CONSOLIDATED_UCMB_DQA_REPORT"
    CORRECTIVE_ACTION_REPORT = "CORRECTIVE_ACTION_REPORT"
    EXECUTIVE_SUMMARY = "EXECUTIVE_SUMMARY"


class AiGenerationLogStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED_NO_API_KEY = "SKIPPED_NO_API_KEY"
    VALIDATION_FAILED = "VALIDATION_FAILED"


class ExportType(str, enum.Enum):
    DOCX = "DOCX"
    PDF = "PDF"
    XLSX = "XLSX"


class ExportStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


def enum_column(enum_class: type[enum.Enum], name: str) -> Enum:
    return Enum(enum_class, name=name)
