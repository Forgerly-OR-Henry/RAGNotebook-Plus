from fastapi.routing import APIRouter
from fastapi.responses import JSONResponse
from starlette import status as http_status

from core.background_init import init_manager
from core.success_response import success_response
from db.db_config import check_database_connection
from mvc.repositories.runtime_store import check_runtime_store_connection

health_router = APIRouter(prefix="/health")

@health_router.get("/live", tags=["健康检查"], summary="健康检查")
async def get_health_application_status():
    """健康检查-存活"""
    return success_response(
        message="health application status",
        data={
            "status": "ok"
        }
    )

@health_router.get("/ready", tags=["健康检查"], summary="健康检查")
async def get_health_readiness():
    """健康检查-就绪"""
    database_status = await check_database_connection()
    runtime_store_status = await check_runtime_store_connection()
    model_runtime_status = init_manager.status_snapshot()
    ready = (
        database_status
        and runtime_store_status
        and model_runtime_status["status"] == "ready"
    )
    readiness_status = "ok" if ready else "failed" if model_runtime_status["status"] == "failed" else "starting"
    data = {
        "status": readiness_status,
        "checks": {
            "database": database_status,
            "runtime_store": runtime_store_status,
            "model_runtime": model_runtime_status,
        },
    }
    if ready:
        return success_response(
            message="health readiness status",
            data=data
        )
    return JSONResponse(
        status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "code": http_status.HTTP_503_SERVICE_UNAVAILABLE,
            "message": "health readiness status",
            "data": data,
        },
    )

