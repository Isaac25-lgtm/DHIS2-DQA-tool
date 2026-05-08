from fastapi import APIRouter

from app.routers.assessment_workspace import router as assessment_workspace_router
from app.routers.analytics import router as analytics_router
from app.routers.assessment_rounds import router as assessment_rounds_router
from app.routers.assessment_teams import router as assessment_teams_router
from app.routers.auth import router as auth_router
from app.routers.comparison import router as comparison_router
from app.routers.corrective_actions import router as corrective_actions_router
from app.routers.dqa_values import router as dqa_values_router
from app.routers.dhis2 import router as dhis2_router
from app.routers.exports import router as exports_router
from app.routers.facilities import router as facilities_router
from app.routers.health import router as health_router
from app.routers.indicators import router as indicators_router
from app.routers.notifications import router as notifications_router
from app.routers.reports import router as reports_router
from app.routers.submissions import router as submissions_router
from app.routers.sync import router as sync_router
from app.routers.system import router as system_router
from app.routers.users import router as users_router

api_router = APIRouter()
api_router.include_router(assessment_workspace_router)
api_router.include_router(analytics_router)
api_router.include_router(assessment_rounds_router)
api_router.include_router(assessment_teams_router)
api_router.include_router(auth_router)
api_router.include_router(comparison_router)
api_router.include_router(corrective_actions_router)
api_router.include_router(dqa_values_router)
api_router.include_router(dhis2_router)
api_router.include_router(exports_router)
api_router.include_router(sync_router)
api_router.include_router(users_router)
api_router.include_router(facilities_router)
api_router.include_router(indicators_router)
api_router.include_router(notifications_router)
api_router.include_router(reports_router)
api_router.include_router(submissions_router)
api_router.include_router(system_router)
api_router.include_router(health_router)
