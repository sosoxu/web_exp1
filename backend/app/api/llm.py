from fastapi import APIRouter, HTTPException

from app.schemas.schemas import (
    ParseParamsRequest, ParseParamsResponse,
    ParseConstraintsRequest, ParseConstraintsResponse
)
from app.services.llm_service import llm_service
from app.services.parse_service import parse_service

router = APIRouter(prefix="/api/llm", tags=["LLM解析"])


@router.post("/parse-params", response_model=ParseParamsResponse)
async def parse_params(request: ParseParamsRequest):
    """解析用户自然语言描述的参数取值"""
    try:
        result = await llm_service.parse_param_values(
            params=request.params,
            description=request.description,
            constraints=request.constraints
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM解析失败: {str(e)}")

    # 后处理：校验和规范化
    for i, parsed_param in enumerate(result.parsed):
        # 找到对应的参数定义
        param_info = None
        for p in request.params:
            if p.module_name == parsed_param.module_name and p.param_name == parsed_param.param_name:
                param_info = p
                break

        if param_info and parsed_param.values:
            normalized, errors = parse_service.validate_and_normalize(param_info, parsed_param.values)
            result.parsed[i].values = normalized
            if errors:
                # 将校验错误信息附加到value_type中
                existing_type = result.parsed[i].value_type or ""
                result.parsed[i].value_type = f"{existing_type} | 校验警告: {'; '.join(errors)}".strip()

    return result


@router.post("/parse-constraints", response_model=ParseConstraintsResponse)
async def parse_constraints(request: ParseConstraintsRequest):
    """解析用户描述的约束条件"""
    try:
        constraints = await llm_service.parse_constraints(
            params=request.params,
            constraint_description=request.constraint_description
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM解析约束失败: {str(e)}")

    return ParseConstraintsResponse(constraints=constraints)
