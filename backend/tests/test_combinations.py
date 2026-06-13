"""组合生成服务测试"""
import pytest
from app.services.combination_service import combination_service
from app.schemas.schemas import (
    ParamValueForCombination, ParsedConstraint,
    DependencyConstraintForCombination
)


class TestCombinationService:
    """组合生成服务测试"""

    def test_single_params_cartesian(self):
        """测试单一参数笛卡尔积"""
        params = [
            ParamValueForCombination(
                module_name="A", param_name="pa",
                type_val="SINGLE", vtype="Int",
                values=[1, 3, 5]
            ),
            ParamValueForCombination(
                module_name="A", param_name="pb",
                type_val="SELECT", vtype="String",
                values=["Up", "Down"]
            )
        ]
        combos, total, filtered = combination_service.generate_combinations(
            params=params, constraints=[], dependency_constraints=[]
        )
        assert total == 6  # 3 * 2
        assert filtered == 6
        assert len(combos) == 6

    def test_single_param_values(self):
        """测试单参数取值"""
        params = [
            ParamValueForCombination(
                module_name="A", param_name="pa",
                type_val="SINGLE", vtype="Int",
                values=[1, 3, 5, 7, 9]
            )
        ]
        combos, total, filtered = combination_service.generate_combinations(
            params=params, constraints=[], dependency_constraints=[]
        )
        assert total == 5
        # 验证每个值
        values = [c.combination_data["A.pa"] for c in combos]
        assert values == [1, 3, 5, 7, 9]

    def test_dependency_constraint(self):
        """测试依赖约束"""
        params = [
            ParamValueForCombination(
                module_name="A", param_name="pb",
                type_val="SELECT", vtype="String",
                values=["Up", "Down"]
            ),
            ParamValueForCombination(
                module_name="A", param_name="pa",
                type_val="SINGLE", vtype="Int",
                values=[1, 2]
            )
        ]
        dep_constraints = [
            DependencyConstraintForCombination(
                param_id=1, param_name="pa", module_name="A",
                deparent="pb", dep_values=["Up"]
            )
        ]
        combos, total, filtered = combination_service.generate_combinations(
            params=params, constraints=[], dependency_constraints=dep_constraints
        )
        assert total == 4
        # 当pb=Down时，pa应该为N/A
        down_combos = [c for c in combos if c.combination_data["A.pb"] == "Down"]
        for c in down_combos:
            assert c.combination_data["A.pa"] == "N/A"

    def test_custom_constraint(self):
        """测试自定义约束"""
        params = [
            ParamValueForCombination(
                module_name="A", param_name="pa",
                type_val="SINGLE", vtype="Int",
                values=[1, 5, 10]
            ),
            ParamValueForCombination(
                module_name="A", param_name="pb",
                type_val="SINGLE", vtype="Int",
                values=[3, 7]
            )
        ]
        constraints = [
            ParsedConstraint(
                source_module="A", source_param="pa",
                target_module="A", target_param="pb",
                operator="gt", constraint_value=3,
                description="pa必须大于3"
            )
        ]
        combos, total, filtered = combination_service.generate_combinations(
            params=params, constraints=constraints, dependency_constraints=[]
        )
        assert total == 6
        # 只有pa>3的组合有效
        valid_combos = [c for c in combos if c.is_valid]
        for c in valid_combos:
            assert c.combination_data["A.pa"] > 3

    def test_empty_params(self):
        """测试空参数列表"""
        combos, total, filtered = combination_service.generate_combinations(
            params=[], constraints=[], dependency_constraints=[]
        )
        assert total == 0
        assert filtered == 0

    def test_vector_param_combination(self):
        """测试VECTOR类型参数组合"""
        params = [
            ParamValueForCombination(
                module_name="A", param_name="pc",
                type_val="VECTOR", vtype="Int",
                values=[[1, 2, 3], [4, 5, 6]]
            ),
            ParamValueForCombination(
                module_name="A", param_name="pa",
                type_val="SINGLE", vtype="Int",
                values=[10, 20]
            )
        ]
        combos, total, filtered = combination_service.generate_combinations(
            params=params, constraints=[], dependency_constraints=[]
        )
        assert total == 4  # 2 * 2

    def test_max_combinations_limit(self):
        """测试组合数量限制"""
        # 创建大量取值
        params = [
            ParamValueForCombination(
                module_name="A", param_name=f"p{i}",
                type_val="SINGLE", vtype="Int",
                values=list(range(100))
            )
            for i in range(3)
        ]
        with pytest.raises(ValueError, match="超过最大限制"):
            combination_service.generate_combinations(
                params=params, constraints=[], dependency_constraints=[]
            )
