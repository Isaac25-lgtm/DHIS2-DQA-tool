import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base, get_db_session
from app.main import app
from app.models.base import UserRole
from app.models.facility import Facility
from app.models.indicator import Indicator
from app.models.user import User
from app.security import get_password_hash


def _test_database_url() -> str:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL-backed tests.")
    return database_url


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(_test_database_url(), pool_pre_ping=True)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db_session] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def seeded_manager(db_session: Session) -> User:
    manager = User(
        full_name="System Manager",
        email="admin@ucmb-dqa.local",
        hashed_password=get_password_hash("ChangeMe123!"),
        role=UserRole.MANAGER,
        is_active=True,
    )
    db_session.add(manager)
    db_session.commit()
    db_session.refresh(manager)
    return manager


@pytest.fixture()
def seeded_viewer(db_session: Session) -> User:
    viewer = User(
        full_name="Read Only User",
        email="viewer@ucmb-dqa.local",
        hashed_password=get_password_hash("ChangeMe123!"),
        role=UserRole.VIEWER,
        is_active=True,
    )
    db_session.add(viewer)
    db_session.commit()
    db_session.refresh(viewer)
    return viewer


@pytest.fixture()
def seeded_assessor(db_session: Session) -> User:
    assessor = User(
        full_name="Assigned Assessor",
        email="assessor@ucmb-dqa.local",
        hashed_password=get_password_hash("ChangeMe123!"),
        role=UserRole.ASSESSOR,
        is_active=True,
    )
    db_session.add(assessor)
    db_session.commit()
    db_session.refresh(assessor)
    return assessor


@pytest.fixture()
def seeded_assessor_two(db_session: Session) -> User:
    assessor = User(
        full_name="Other Assessor",
        email="other-assessor@ucmb-dqa.local",
        hashed_password=get_password_hash("ChangeMe123!"),
        role=UserRole.ASSESSOR,
        is_active=True,
    )
    db_session.add(assessor)
    db_session.commit()
    db_session.refresh(assessor)
    return assessor


@pytest.fixture()
def seeded_reviewer(db_session: Session) -> User:
    reviewer = User(
        full_name="Round Reviewer",
        email="reviewer@ucmb-dqa.local",
        hashed_password=get_password_hash("ChangeMe123!"),
        role=UserRole.REVIEWER,
        is_active=True,
    )
    db_session.add(reviewer)
    db_session.commit()
    db_session.refresh(reviewer)
    return reviewer


@pytest.fixture()
def active_facility(db_session: Session) -> Facility:
    facility = Facility(
        facility_name="Bukomansimbi HC IV",
        district="Bukomansimbi",
        facility_type="HC IV",
        ownership="PNFP",
        dhis2_org_unit_uid="bukomansimbi001",
        is_active=True,
        notes="Assessment round fixture facility",
    )
    db_session.add(facility)
    db_session.commit()
    db_session.refresh(facility)
    return facility


@pytest.fixture()
def active_indicator(db_session: Session) -> Indicator:
    indicator = Indicator(
        indicator_name="Fixture Indicator",
        indicator_group="Maternity",
        hmis_code="FIX-ROUND-001",
        dhis2_uid_or_operand="FixRound12345",
        data_element_uid="FixRound12345",
        category_option_combo_uid=None,
        dataset_name="HMIS 105:02-03",
        hmis_section="Maternity",
        source_register="Maternity register",
        category_combo=None,
        value_type="integer",
        is_active=True,
        is_required_by_default=True,
        default_discrepancy_threshold_percent=5.0,
        is_death_indicator=False,
        sort_order=1,
        notes="Assessment round fixture indicator",
    )
    db_session.add(indicator)
    db_session.commit()
    db_session.refresh(indicator)
    return indicator


def _login(client: TestClient, email: str, password: str) -> str:
    response = client.post(
        "/api/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture()
def manager_token(client: TestClient, seeded_manager: User) -> str:
    return _login(client, seeded_manager.email, "ChangeMe123!")


@pytest.fixture()
def viewer_token(client: TestClient, seeded_viewer: User) -> str:
    return _login(client, seeded_viewer.email, "ChangeMe123!")


@pytest.fixture()
def assessor_token(client: TestClient, seeded_assessor: User) -> str:
    return _login(client, seeded_assessor.email, "ChangeMe123!")


@pytest.fixture()
def assessor_two_token(client: TestClient, seeded_assessor_two: User) -> str:
    return _login(client, seeded_assessor_two.email, "ChangeMe123!")


@pytest.fixture()
def reviewer_token(client: TestClient, seeded_reviewer: User) -> str:
    return _login(client, seeded_reviewer.email, "ChangeMe123!")
