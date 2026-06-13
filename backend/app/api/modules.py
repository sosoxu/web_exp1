from typing import Optional

from fastapi import APIRouter, Query

from app.utils.sqlite_client import sqlite_client
from app.schemas.schemas import ModuleListResponse, ParamItem, DependencyItem

router = APIRouter(prefix="/api/modules", tags=["模块与参数"])


@router.get("", response_model=ModuleListResponse)
async def list_modules(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """获取模块列表"""
    result = sqlite_client.get_modules(keyword=keyword, page=page, page_size=page_size)
    return ModuleListResponse(total=result["total"], items=result["items"])


@router.get("/{module_id}/params", response_model=list[ParamItem])
async def get_module_params(module_id: int):
    """获取模块的参数列表"""
    params = sqlite_client.get_params_by_module(module_id)
    module = sqlite_client.get_module_by_id(module_id)
    for p in params:
        p["module_name"] = module["name"] if module else None
    return params


@router.get("/{module_id}/dependencies", response_model=list[DependencyItem])
async def get_module_dependencies(module_id: int):
    """获取模块参数的依赖关系"""
    deps = sqlite_client.get_dependencies_by_module(module_id)
    return deps
