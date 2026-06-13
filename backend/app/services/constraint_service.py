import json
from typing import Any, Optional

from app.schemas.schemas import ParsedConstraint
from app.utils.sqlite_client import sqlite_client


class ConstraintService:
    """约束处理服务"""

    def get_param_dependencies(self, param_ids: list[int]) -> list[dict]:
        """从SQLite获取参数的依赖关系"""
        return sqlite_client.get_dependencies_by_param_ids(param_ids)

    def build_dependency_constraints(self, param_ids: list[int]) -> list[dict]:
        """构建依赖约束信息"""
        deps = self.get_param_dependencies(param_ids)
        result = []
        for dep in deps:
            dep_values = dep.get("dep_values", "[]")
            if isinstance(dep_values, str):
                try:
                    dep_values = json.loads(dep_values)
                except json.JSONDecodeError:
                    dep_values = [dep_values]
            result.append({
                "param_id": dep["parameter_id"],
                "param_name": dep["param_name"],
                "module_name": dep.get("module_name", ""),
                "deparent": dep["deparent"],
                "dep_values": dep_values
            })
        return result

    def evaluate_constraint(
        self,
        combination: dict[str, Any],
        constraint: ParsedConstraint
    ) -> bool:
        """评估单个约束是否满足"""
        source_key = f"{constraint.source_module}.{constraint.source_param}"
        target_key = f"{constraint.target_module}.{constraint.target_param}"

        if source_key not in combination or target_key not in combination:
            return True

        source_val = combination[source_key]
        constraint_val = constraint.constraint_value

        try:
            if constraint.operator == "eq":
                return str(source_val) == str(constraint_val)
            elif constraint.operator == "neq":
                return str(source_val) != str(constraint_val)
            elif constraint.operator == "gt":
                return float(str(source_val)) > float(str(constraint_val))
            elif constraint.operator == "lt":
                return float(str(source_val)) < float(str(constraint_val))
            elif constraint.operator == "gte":
                return float(str(source_val)) >= float(str(constraint_val))
            elif constraint.operator == "lte":
                return float(str(source_val)) <= float(str(constraint_val))
            elif constraint.operator == "in":
                if isinstance(constraint_val, list):
                    return str(source_val) in [str(v) for v in constraint_val]
                return str(source_val) in str(constraint_val)
            elif constraint.operator == "not_in":
                if isinstance(constraint_val, list):
                    return str(source_val) not in [str(v) for v in constraint_val]
                return str(source_val) not in str(constraint_val)
        except (ValueError, TypeError):
            return True

        return True


constraint_service = ConstraintService()
