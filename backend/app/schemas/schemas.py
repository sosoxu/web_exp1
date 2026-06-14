from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


# ===== 模块相关 =====

class ModuleItem(BaseModel):
    id: int
    name: str
    version: Optional[str] = None
    module_type: Optional[str] = None
    data_transfer: Optional[str] = None
    source_file: Optional[str] = None
    param_count: int = 0


class ModuleListResponse(BaseModel):
    total: int
    items: list[ModuleItem]


# ===== 参数相关 =====

class ParamItem(BaseModel):
    id: int
    module_id: int
    name: str
    class_val: Optional[str] = None
    display: Optional[str] = None
    inmethod: Optional[str] = None
    uiname: Optional[str] = None
    no_val: Optional[str] = None
    autoexp: Optional[str] = None
    col: Optional[int] = None
    vtype: str = "String"
    type_val: str = "SINGLE"
    row_val: Optional[int] = None
    prec: Optional[int] = None
    border_value: Optional[str] = None
    max_val: Optional[str] = None
    min_val: Optional[str] = None
    default_val: Optional[str] = None
    default_rows: Optional[str] = None
    select_items: Optional[str] = None
    cols_def: Optional[str] = None
    title_row: Optional[str] = None
    title_col: Optional[str] = None
    comment: Optional[str] = None
    module_name: Optional[str] = None


class DependencyItem(BaseModel):
    id: int
    parameter_id: int
    param_name: Optional[str] = None
    module_id: Optional[int] = None
    module_name: Optional[str] = None
    deparent: str
    interoper: str = "YES"
    dep_values: Optional[str] = None


# ===== LLM解析相关 =====

class ParamInfoForLLM(BaseModel):
    module_name: str
    param_name: str
    type_val: str
    vtype: str
    min_val: Optional[str] = None
    max_val: Optional[str] = None
    default_val: Optional[str] = None
    select_items: Optional[str] = None
    cols_def: Optional[str] = None
    row_val: Optional[int] = None
    col: Optional[int] = None
    title_row: Optional[str] = None
    title_col: Optional[str] = None


class ParsedParamValue(BaseModel):
    module_name: str
    param_name: str
    values: list[Any]
    value_type: Optional[str] = None
    confidence: float = 1.0


class ParsedConstraint(BaseModel):
    source_module: Optional[str] = None
    source_param: Optional[str] = None
    target_module: Optional[str] = None
    target_param: Optional[str] = None
    operator: str
    constraint_value: Any = None
    description: Optional[str] = None


class ParseParamsRequest(BaseModel):
    params: list[ParamInfoForLLM]
    description: str
    constraints: Optional[str] = None


class ParseParamsResponse(BaseModel):
    parsed: list[ParsedParamValue]
    constraints: list[ParsedConstraint] = []
    raw_llm_response: Optional[str] = None


class ParseConstraintsRequest(BaseModel):
    params: list[ParamInfoForLLM]
    constraint_description: str


class ParseConstraintsResponse(BaseModel):
    constraints: list[ParsedConstraint]


# ===== 组合生成相关 =====

class ParamValueForCombination(BaseModel):
    module_name: str
    param_name: str
    type_val: str
    vtype: str
    values: list[Any]


class DependencyConstraintForCombination(BaseModel):
    param_id: int
    param_name: str
    module_name: str
    deparent: str
    dep_values: list[str]


class GenerateCombinationsRequest(BaseModel):
    experiment_id: Optional[int] = None
    params: list[ParamValueForCombination]
    constraints: list[ParsedConstraint] = []
    dependency_constraints: list[DependencyConstraintForCombination] = []


class CombinationItem(BaseModel):
    id: Optional[int] = None
    index: int
    combination_data: dict[str, Any]
    is_valid: bool = True
    invalid_reason: Optional[str] = None


class GenerateCombinationsResponse(BaseModel):
    total_combinations: int
    filtered_combinations: int
    preview: list[CombinationItem]
    experiment_id: Optional[int] = None


class CombinationListResponse(BaseModel):
    total: int
    items: list[CombinationItem]


# ===== 试验管理相关 =====

class ExperimentCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ExperimentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class ExperimentResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    status: str = "draft"
    total_combinations: int = 0
    filtered_combinations: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ExperimentDetail(ExperimentResponse):
    modules: list[dict] = []
    params: list[dict] = []
    constraints: list[dict] = []


class SaveConfigRequest(BaseModel):
    modules: list[dict]
    params: list[dict]
    constraints: list[dict] = []


class UpdateCombinationRequest(BaseModel):
    combination_data: Optional[dict[str, Any]] = None
    is_valid: Optional[bool] = None
    invalid_reason: Optional[str] = None
