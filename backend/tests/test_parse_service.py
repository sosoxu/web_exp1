"""参数解析服务测试"""
import pytest
from app.services.parse_service import parse_service
from app.schemas.schemas import ParamInfoForLLM


class TestParseService:
    """参数解析后处理测试"""

    def test_validate_single_int(self):
        """测试SINGLE类型Int校验"""
        param = ParamInfoForLLM(
            module_name="A", param_name="pa",
            type_val="SINGLE", vtype="Int",
            min_val="0", max_val="100"
        )
        values, errors = parse_service.validate_and_normalize(param, [1, 50, 100])
        assert values == [1, 50, 100]
        assert len(errors) == 0

    def test_validate_single_int_out_of_range(self):
        """测试SINGLE类型Int超出范围"""
        param = ParamInfoForLLM(
            module_name="A", param_name="pa",
            type_val="SINGLE", vtype="Int",
            min_val="0", max_val="100"
        )
        values, errors = parse_service.validate_and_normalize(param, [1, 200])
        assert len(errors) > 0
        assert "大于最大值" in errors[0]

    def test_validate_single_float(self):
        """测试SINGLE类型Float校验"""
        param = ParamInfoForLLM(
            module_name="A", param_name="pa",
            type_val="SINGLE", vtype="Float",
            min_val="0", max_val="100"
        )
        values, errors = parse_service.validate_and_normalize(param, [1.5, "3.5"])
        assert 1.5 in values
        assert 3.5 in values

    def test_validate_select(self):
        """测试SELECT类型校验"""
        param = ParamInfoForLLM(
            module_name="A", param_name="pb",
            type_val="SELECT", vtype="String",
            select_items='["Up", "Down", "Left", "Right"]'
        )
        values, errors = parse_service.validate_and_normalize(param, ["Up", "Down"])
        assert values == ["Up", "Down"]
        assert len(errors) == 0

    def test_validate_select_invalid_option(self):
        """测试SELECT类型无效选项"""
        param = ParamInfoForLLM(
            module_name="A", param_name="pb",
            type_val="SELECT", vtype="String",
            select_items='["Up", "Down"]'
        )
        values, errors = parse_service.validate_and_normalize(param, ["Up", "Invalid"])
        assert len(errors) > 0
        assert "不在可选项" in errors[0]

    def test_validate_vector(self):
        """测试VECTOR类型校验"""
        param = ParamInfoForLLM(
            module_name="A", param_name="pc",
            type_val="VECTOR", vtype="Int",
            min_val="0", max_val="256", col=5
        )
        values, errors = parse_service.validate_and_normalize(
            param, [[1, 2, 3, 4, 5], [11, 12, 13, 14, 15]]
        )
        assert len(values) == 2
        assert values[0] == [1, 2, 3, 4, 5]

    def test_validate_vector_wrong_length(self):
        """测试VECTOR类型长度错误"""
        param = ParamInfoForLLM(
            module_name="A", param_name="pc",
            type_val="VECTOR", vtype="Int",
            col=5
        )
        values, errors = parse_service.validate_and_normalize(
            param, [[1, 2, 3]]  # 长度应为5
        )
        assert len(errors) > 0
        assert "长度应为5" in errors[0]

    def test_validate_matrix(self):
        """测试MATRIX类型校验"""
        param = ParamInfoForLLM(
            module_name="A", param_name="pd",
            type_val="MATRIX", vtype="Float",
            min_val="1", max_val="10",
            row_val=2, col=3
        )
        values, errors = parse_service.validate_and_normalize(
            param, [[1, 2, 3, 4, 5, 6]]
        )
        assert len(values) == 1
        assert values[0] == [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]

    def test_validate_matrix_wrong_size(self):
        """测试MATRIX类型大小错误"""
        param = ParamInfoForLLM(
            module_name="A", param_name="pd",
            type_val="MATRIX", vtype="Float",
            row_val=2, col=3
        )
        values, errors = parse_service.validate_and_normalize(
            param, [[1, 2, 3]]  # 应为6个元素
        )
        assert len(errors) > 0
        assert "元素数量应为6" in errors[0]

    def test_validate_mmatrix(self):
        """测试MMATRIX类型校验"""
        param = ParamInfoForLLM(
            module_name="A", param_name="pe",
            type_val="MMATRIX", vtype="String",
            row_val=2,
            cols_def='[{"vtype": "Int", "min_val": "0", "max_val": "100"}, {"vtype": "String"}]'
        )
        values, errors = parse_service.validate_and_normalize(
            param, [[1, "aaa", 2, "bbb"]]
        )
        assert len(values) == 1
        assert values[0][0] == 1
        assert values[0][1] == "aaa"

    def test_validate_single_bool(self):
        """测试Bool类型校验"""
        param = ParamInfoForLLM(
            module_name="A", param_name="pf",
            type_val="SINGLE", vtype="Bool"
        )
        values, errors = parse_service.validate_and_normalize(param, [True, "false", 1])
        assert values[0] is True
        assert values[1] is False
        assert values[2] is True

    def test_validate_string_type(self):
        """测试String类型不做范围校验"""
        param = ParamInfoForLLM(
            module_name="A", param_name="pg",
            type_val="SINGLE", vtype="String",
            min_val="0", max_val="100"
        )
        values, errors = parse_service.validate_and_normalize(param, ["hello", "world"])
        assert values == ["hello", "world"]
        assert len(errors) == 0
