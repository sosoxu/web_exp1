from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.experiment import (
    Experiment, ExperimentModule, ExperimentParam,
    ExperimentConstraint, ParamCombination
)
from app.schemas.schemas import (
    ExperimentCreate, ExperimentUpdate, ExperimentResponse,
    ExperimentDetail, SaveConfigRequest
)

router = APIRouter(prefix="/api/experiments", tags=["试验管理"])


@router.post("", response_model=ExperimentResponse)
async def create_experiment(request: ExperimentCreate, db: AsyncSession = Depends(get_db)):
    """创建试验"""
    exp = Experiment(name=request.name, description=request.description)
    db.add(exp)
    await db.commit()
    await db.refresh(exp)
    return exp


@router.get("", response_model=dict)
async def list_experiments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """获取试验列表"""
    count_query = select(func.count()).select_from(Experiment)
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = select(Experiment).order_by(Experiment.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    experiments = result.scalars().all()

    items = [ExperimentResponse.model_validate(exp) for exp in experiments]
    return {"total": total, "items": items}


@router.get("/{experiment_id}", response_model=ExperimentDetail)
async def get_experiment(experiment_id: int, db: AsyncSession = Depends(get_db)):
    """获取试验详情"""
    exp = await db.get(Experiment, experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="试验不存在")

    # 获取关联数据
    modules_result = await db.execute(
        select(ExperimentModule).where(ExperimentModule.experiment_id == experiment_id)
    )
    modules = [{"module_name": m.module_name, "module_id": m.module_id} for m in modules_result.scalars().all()]

    params_result = await db.execute(
        select(ExperimentParam).where(ExperimentParam.experiment_id == experiment_id)
    )
    params = [
        {
            "module_name": p.module_name, "param_name": p.param_name,
            "param_id": p.param_id, "type_val": p.type_val, "vtype": p.vtype,
            "raw_description": p.raw_description, "parsed_values": p.parsed_values,
            "is_confirmed": p.is_confirmed
        }
        for p in params_result.scalars().all()
    ]

    constraints_result = await db.execute(
        select(ExperimentConstraint).where(ExperimentConstraint.experiment_id == experiment_id)
    )
    constraints = [
        {
            "constraint_type": c.constraint_type,
            "source_module": c.source_module, "source_param": c.source_param,
            "target_module": c.target_module, "target_param": c.target_param,
            "operator": c.operator, "constraint_value": c.constraint_value,
            "raw_description": c.raw_description
        }
        for c in constraints_result.scalars().all()
    ]

    detail = ExperimentDetail(
        id=exp.id, name=exp.name, description=exp.description,
        status=exp.status, total_combinations=exp.total_combinations,
        filtered_combinations=exp.filtered_combinations,
        created_at=exp.created_at, updated_at=exp.updated_at,
        modules=modules, params=params, constraints=constraints
    )
    return detail


@router.put("/{experiment_id}", response_model=ExperimentResponse)
async def update_experiment(experiment_id: int, request: ExperimentUpdate, db: AsyncSession = Depends(get_db)):
    """更新试验"""
    exp = await db.get(Experiment, experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="试验不存在")

    if request.name is not None:
        exp.name = request.name
    if request.description is not None:
        exp.description = request.description
    if request.status is not None:
        exp.status = request.status
    exp.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(exp)
    return exp


@router.delete("/{experiment_id}")
async def delete_experiment(experiment_id: int, db: AsyncSession = Depends(get_db)):
    """删除试验"""
    exp = await db.get(Experiment, experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="试验不存在")

    await db.delete(exp)
    await db.commit()
    return {"message": "删除成功"}


@router.post("/{experiment_id}/save-config")
async def save_config(experiment_id: int, request: SaveConfigRequest, db: AsyncSession = Depends(get_db)):
    """保存试验配置"""
    exp = await db.get(Experiment, experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="试验不存在")

    # 清除旧配置
    await db.execute(delete(ExperimentModule).where(ExperimentModule.experiment_id == experiment_id))
    await db.execute(delete(ExperimentParam).where(ExperimentParam.experiment_id == experiment_id))
    await db.execute(delete(ExperimentConstraint).where(ExperimentConstraint.experiment_id == experiment_id))

    # 保存模块
    for m in request.modules:
        db.add(ExperimentModule(
            experiment_id=experiment_id,
            module_name=m.get("module_name", ""),
            module_id=m.get("module_id", 0)
        ))

    # 保存参数
    for p in request.params:
        db.add(ExperimentParam(
            experiment_id=experiment_id,
            module_name=p.get("module_name", ""),
            param_name=p.get("param_name", ""),
            param_id=p.get("param_id", 0),
            type_val=p.get("type_val", "SINGLE"),
            vtype=p.get("vtype", "String"),
            raw_description=p.get("raw_description"),
            parsed_values=p.get("parsed_values"),
            is_confirmed=p.get("is_confirmed", False)
        ))

    # 保存约束
    for c in request.constraints:
        db.add(ExperimentConstraint(
            experiment_id=experiment_id,
            constraint_type=c.get("constraint_type", "custom"),
            source_module=c.get("source_module"),
            source_param=c.get("source_param"),
            target_module=c.get("target_module"),
            target_param=c.get("target_param"),
            operator=c.get("operator"),
            constraint_value=c.get("constraint_value"),
            raw_description=c.get("raw_description")
        ))

    exp.updated_at = datetime.utcnow()
    await db.commit()
    return {"message": "配置保存成功"}
