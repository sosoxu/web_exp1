import json
import itertools
from typing import Any, Optional

from app.schemas.schemas import (
    ParsedConstraint, DependencyConstraintForCombination, ParamValueForCombination,
    CombinationItem
)
from app.config import settings


class CombinationService:
    """参数组合生成服务"""

    def generate_combinations(
        self,
        params: list[ParamValueForCombination],
        constraints: list[ParsedConstraint],
        dependency_constraints: list[DependencyConstraintForCombination]
    ) -> tuple[list[CombinationItem], int, int]:
        """
        生成参数组合

        Returns:
            (combinations, total_count, filtered_count)
        """
        # 1. 构建参数取值列表
        param_keys = []
        param_value_lists = []

        for p in params:
            key = f"{p.module_name}.{p.param_name}"
            param_keys.append(key)
            param_value_lists.append(p.values)

        if not param_value_lists:
            return [], 0, 0

        # 2. 计算笛卡尔积
        total_count = 1
        for vl in param_value_lists:
            total_count *= len(vl)

        if total_count > settings.MAX_COMBINATIONS:
            raise ValueError(
                f"组合数量{total_count}超过最大限制{settings.MAX_COMBINATIONS}，"
                f"请减少参数取值数量"
            )

        # 3. 生成所有组合
        combinations = []
        index = 1
        for combo in itertools.product(*param_value_lists):
            combo_dict = {}
            for key, value in zip(param_keys, combo):
                combo_dict[key] = value

            # 4. 应用依赖约束
            combo_dict, dep_invalid_reasons = self._apply_dependency_constraints(
                combo_dict, dependency_constraints
            )

            # 5. 应用自定义约束
            is_valid, custom_invalid_reason = self._apply_custom_constraints(
                combo_dict, constraints
            )

            invalid_reasons = dep_invalid_reasons
            if custom_invalid_reason:
                invalid_reasons.append(custom_invalid_reason)

            # 依赖约束违规也标记为无效
            is_valid = len(invalid_reasons) == 0

            combinations.append(CombinationItem(
                index=index,
                combination_data=combo_dict,
                is_valid=is_valid,
                invalid_reason="; ".join(invalid_reasons) if invalid_reasons else None
            ))
            index += 1

        total = len(combinations)
        filtered = sum(1 for c in combinations if c.is_valid)

        return combinations, total, filtered

    def _apply_dependency_constraints(
        self,
        combination: dict[str, Any],
        dependencies: list[DependencyConstraintForCombination]
    ) -> tuple[dict[str, Any], list[str]]:
        """
        应用依赖约束

        如果父参数值不在dep_values中，子参数标记为不生效（保留原始值，记录原因）
        """
        reasons = []
        result = dict(combination)

        for dep in dependencies:
            parent_key = f"{dep.module_name}.{dep.deparent}"
            child_key = f"{dep.module_name}.{dep.param_name}"

            if parent_key not in result or child_key not in result:
                continue

            parent_value = result[parent_key]

            # 将父参数值转为字符串进行比较
            parent_str = str(parent_value)

            # dep_values是JSON字符串列表
            dep_values = dep.dep_values
            if isinstance(dep_values, str):
                try:
                    dep_values = json.loads(dep_values)
                except json.JSONDecodeError:
                    dep_values = [dep_values]

            if parent_str not in dep_values:
                # 父参数值不在dep_values中，子参数不生效
                # 保留原始值，仅记录原因
                reasons.append(
                    f"依赖约束: {parent_key}={parent_str}不在{dep_values}中，"
                    f"{child_key}不生效"
                )

        return result, reasons

    def _apply_custom_constraints(
        self,
        combination: dict[str, Any],
        constraints: list[ParsedConstraint]
    ) -> tuple[bool, Optional[str]]:
        """应用自定义约束"""
        for constraint in constraints:
            source_key = f"{constraint.source_module}.{constraint.source_param}"
            target_key = f"{constraint.target_module}.{constraint.target_param}"

            if source_key not in combination or target_key not in combination:
                continue

            source_val = combination[source_key]
            target_val = combination[target_key]
            constraint_val = constraint.constraint_value

            if not self._evaluate_constraint(source_val, target_val, constraint_val, constraint.operator):
                return False, (
                    f"约束不满足: {source_key}({source_val}) {constraint.operator} "
                    f"{target_key}({target_val}), 期望值: {constraint_val}"
                )

        return True, None

    def _evaluate_constraint(
        self,
        source_val: Any,
        target_val: Any,
        constraint_val: Any,
        operator: str
    ) -> bool:
        """评估单个约束"""
        try:
            if operator == "eq":
                return str(source_val) == str(constraint_val)
            elif operator == "neq":
                return str(source_val) != str(constraint_val)
            elif operator == "gt":
                return float(str(source_val)) > float(str(constraint_val))
            elif operator == "lt":
                return float(str(source_val)) < float(str(constraint_val))
            elif operator == "gte":
                return float(str(source_val)) >= float(str(constraint_val))
            elif operator == "lte":
                return float(str(source_val)) <= float(str(constraint_val))
            elif operator == "in":
                if isinstance(constraint_val, list):
                    return str(source_val) in [str(v) for v in constraint_val]
                return str(source_val) in str(constraint_val)
            elif operator == "not_in":
                if isinstance(constraint_val, list):
                    return str(source_val) not in [str(v) for v in constraint_val]
                return str(source_val) not in str(constraint_val)
            else:
                return True
        except (ValueError, TypeError):
            return True


combination_service = CombinationService()
