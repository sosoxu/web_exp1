from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.experiment import Experiment, ParamCombination
from app.schemas.schemas import (
    GenerateCombinationsRequest, GenerateCombinationsResponse,
    CombinationListResponse, CombinationItem, UpdateCombinationRequest
)
from app.services.combination_service import combination_service
from app.services.export_service import export_service
from app.utils.sqlite_client import sqlite_client

router = APIRouter(prefix="/api/combinations", tags=["组合生成"])


@router.post("/generate", response_model=GenerateCombinationsResponse)
async def generate_combinations(request: GenerateCombinationsRequest, db: AsyncSession = Depends(get_db)):
    """生成参数组合表"""
    # 自动加载所选参数的依赖约束
    dependency_constraints = list(request.dependency_constraints)
    param_ids = []
    for p in request.params:
        # 通过模块名和参数名查找参数ID
        try:
            modules = sqlite_client.get_modules(keyword=p.module_name)
            for mod in modules.get("items", []):
                if mod["name"] == p.module_name:
                    params_list = sqlite_client.get_params_by_module(mod["id"])
                    for param in params_list:
                        if param["name"] == p.param_name:
                            param_ids.append(param["id"])
                    break
        except Exception:
            pass

    if param_ids:
        try:
            deps = sqlite_client.get_dependencies_by_param_ids(param_ids)
            for dep in deps:
                # 检查是否已经在请求中提供
                already_exists = any(
                    dc.param_id == dep.get("parameter_id") and dc.deparent == dep.get("deparent")
                    for dc in dependency_constraints
                )
                if not already_exists:
                    dep_values = dep.get("dep_values", "[]")
                    if isinstance(dep_values, str):
                        import json
                        try:
                            dep_values = json.loads(dep_values)
                        except json.JSONDecodeError:
                            dep_values = [dep_values]
                    from app.schemas.schemas import DependencyConstraintForCombination
                    dependency_constraints.append(DependencyConstraintForCombination(
                        param_id=dep.get("parameter_id", 0),
                        param_name=dep.get("param_name", ""),
                        module_name=dep.get("module_name", ""),
                        deparent=dep.get("deparent", ""),
                        dep_values=dep_values if isinstance(dep_values, list) else [dep_values]
                    ))
        except Exception:
            pass

    try:
        combinations, total, filtered = combination_service.generate_combinations(
            params=request.params,
            constraints=request.constraints,
            dependency_constraints=dependency_constraints
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 如果指定了experiment_id，保存到数据库
    if request.experiment_id:
        # 清除旧组合
        await db.execute(
            delete(ParamCombination).where(ParamCombination.experiment_id == request.experiment_id)
        )

        # 批量插入新组合
        for combo in combinations:
            db_combo = ParamCombination(
                experiment_id=request.experiment_id,
                combination_index=combo.index,
                combination_data=combo.combination_data,
                is_valid=combo.is_valid,
                invalid_reason=combo.invalid_reason
            )
            db.add(db_combo)

        # 更新试验统计
        exp = await db.get(Experiment, request.experiment_id)
        if exp:
            exp.total_combinations = total
            exp.filtered_combinations = filtered
            exp.status = "configured"

        await db.commit()

    # 返回预览（前100条）
    preview = []
    for i, combo in enumerate(combinations[:100]):
        preview.append(CombinationItem(
            id=None,
            index=combo.index,
            combination_data=combo.combination_data,
            is_valid=combo.is_valid,
            invalid_reason=combo.invalid_reason
        ))

    return GenerateCombinationsResponse(
        total_combinations=total,
        filtered_combinations=filtered,
        preview=preview,
        experiment_id=request.experiment_id
    )


@router.get("/{experiment_id}", response_model=CombinationListResponse)
async def get_combinations(
    experiment_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    is_valid: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """获取组合表（分页）"""
    query = select(ParamCombination).where(ParamCombination.experiment_id == experiment_id)
    count_query = select(func.count()).select_from(ParamCombination).where(
        ParamCombination.experiment_id == experiment_id
    )

    if is_valid is not None:
        query = query.where(ParamCombination.is_valid == is_valid)
        count_query = count_query.where(ParamCombination.is_valid == is_valid)

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.order_by(ParamCombination.combination_index).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    db_combos = result.scalars().all()

    items = [
        CombinationItem(
            id=c.id,
            index=c.combination_index,
            combination_data=c.combination_data,
            is_valid=c.is_valid,
            invalid_reason=c.invalid_reason
        )
        for c in db_combos
    ]

    return CombinationListResponse(total=total, items=items)


@router.get("/{experiment_id}/export")
async def export_combinations(
    experiment_id: int,
    format: str = Query("csv", pattern="^(csv|xlsx)$"),
    db: AsyncSession = Depends(get_db)
):
    """导出组合表"""
    query = select(ParamCombination).where(
        ParamCombination.experiment_id == experiment_id,
        ParamCombination.is_valid == True
    ).order_by(ParamCombination.combination_index)
    result = await db.execute(query)
    db_combos = result.scalars().all()

    if not db_combos:
        raise HTTPException(status_code=404, detail="没有可导出的组合数据")

    # 获取参数键
    first_combo = db_combos[0].combination_data
    param_keys = list(first_combo.keys())

    combos_data = [
        {
            "index": c.combination_index,
            "combination_data": c.combination_data
        }
        for c in db_combos
    ]

    if format == "csv":
        csv_content = export_service.export_csv(combos_data, param_keys)
        return StreamingResponse(
            iter([csv_content]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=combinations_{experiment_id}.csv"}
        )
    else:
        xlsx_bytes = export_service.export_xlsx(combos_data, param_keys)
        return StreamingResponse(
            iter([xlsx_bytes]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=combinations_{experiment_id}.xlsx"}
        )


@router.put("/{experiment_id}/combinations/{combination_id}")
async def update_combination(
    experiment_id: int,
    combination_id: int,
    request: UpdateCombinationRequest,
    db: AsyncSession = Depends(get_db)
):
    """修改单条组合"""
    combo = await db.get(ParamCombination, combination_id)
    if not combo or combo.experiment_id != experiment_id:
        raise HTTPException(status_code=404, detail="组合不存在")

    if request.combination_data is not None:
        combo.combination_data = request.combination_data
    if request.is_valid is not None:
        combo.is_valid = request.is_valid
    if request.invalid_reason is not None:
        combo.invalid_reason = request.invalid_reason

    await db.commit()
    await db.refresh(combo)

    return {"message": "修改成功", "id": combo.id}


@router.delete("/{experiment_id}/combinations/{combination_id}")
async def delete_combination(
    experiment_id: int,
    combination_id: int,
    db: AsyncSession = Depends(get_db)
):
    """删除单条组合"""
    combo = await db.get(ParamCombination, combination_id)
    if not combo or combo.experiment_id != experiment_id:
        raise HTTPException(status_code=404, detail="组合不存在")

    await db.delete(combo)

    # 更新试验统计
    exp = await db.get(Experiment, experiment_id)
    if exp:
        if combo.is_valid:
            exp.filtered_combinations = max(0, exp.filtered_combinations - 1)
        exp.total_combinations = max(0, exp.total_combinations - 1)

    await db.commit()
    return {"message": "删除成功"}


@router.post("/{experiment_id}/combinations/batch-delete")
async def batch_delete_combinations(
    experiment_id: int,
    request: dict,
    db: AsyncSession = Depends(get_db)
):
    """批量删除组合"""
    ids = request.get("ids", [])
    if not ids:
        raise HTTPException(status_code=400, detail="请选择要删除的组合")

    deleted_valid = 0
    deleted_total = 0
    for cid in ids:
        combo = await db.get(ParamCombination, cid)
        if combo and combo.experiment_id == experiment_id:
            if combo.is_valid:
                deleted_valid += 1
            deleted_total += 1
            await db.delete(combo)

    # 更新试验统计
    exp = await db.get(Experiment, experiment_id)
    if exp:
        exp.filtered_combinations = max(0, exp.filtered_combinations - deleted_valid)
        exp.total_combinations = max(0, exp.total_combinations - deleted_total)

    await db.commit()
    return {"message": f"成功删除 {deleted_total} 条组合"}
