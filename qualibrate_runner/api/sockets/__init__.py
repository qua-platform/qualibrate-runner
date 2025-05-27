from fastapi import APIRouter

from .common import common_ws_router

base_ws_router = APIRouter(prefix="/ws")
base_ws_router.include_router(common_ws_router)
