import json
from typing import Any, Optional

from app.schemas.schemas import ParamInfoForLLM, ParsedParamValue


class ParseService:
    """参数解析后处理：校验和规范化"""

    def validate_and_normalize(
        self,
        param: ParamInfoForLLM,
        parsed_values: list[Any]
    ) -> tuple[list[Any], list[str]]:
        """
        校验和规范化解析结果

        Returns:
            (normalized_values, errors)
        """
        errors = []
        type_val = param.type_val
        vtype = param.vtype.lower()

        if type_val == "SINGLE":
            normalized, errs = self._validate_single(param, parsed_values)
            errors.extend(errs)
        elif type_val == "SELECT":
            normalized, errs = self._validate_select(param, parsed_values)
            errors.extend(errs)
        elif type_val == "VECTOR":
            normalized, errs = self._validate_vector(param, parsed_values)
            errors.extend(errs)
        elif type_val == "MATRIX":
            normalized, errs = self._validate_matrix(param, parsed_values)
            errors.extend(errs)
        elif type_val == "MMATRIX":
            normalized, errs = self._validate_mmatrix(param, parsed_values)
            errors.extend(errs)
        else:
            normalized = parsed_values
            errors.append(f"未知的type_val: {type_val}")

        return normalized, errors

    def _convert_type(self, value: Any, vtype: str) -> tuple[Any, Optional[str]]:
        """将值转换为指定类型"""
        vtype_lower = vtype.lower()
        try:
            if vtype_lower == "int":
                return int(float(str(value))), None
            elif vtype_lower in ("float", "double"):
                return float(str(value)), None
            elif vtype_lower == "string":
                return str(value), None
            elif vtype_lower == "bool":
                if isinstance(value, bool):
                    return value, None
                s = str(value).lower()
                if s in ("true", "1", "yes"):
                    return True, None
                elif s in ("false", "0", "no"):
                    return False, None
                return value, f"无法将'{value}'转换为Bool"
            elif vtype_lower in ("numstr", "numstr"):
                return str(value), None
            elif vtype_lower == "header":
                return str(value), None
            else:
                return value, None
        except (ValueError, TypeError) as e:
            return value, f"类型转换失败: {value} -> {vtype}: {e}"

    def _check_range(self, value: Any, min_val: Optional[str], max_val: Optional[str], vtype: str) -> Optional[str]:
        """检查值是否在范围内"""
        vtype_lower = vtype.lower()
        if vtype_lower not in ("int", "float", "double"):
            return None

        try:
            num_val = float(str(value))
            if min_val is not None and min_val != "":
                min_num = float(min_val)
                if num_val < min_num:
                    return f"值{value}小于最小值{min_val}"
            if max_val is not None and max_val != "":
                max_num = float(max_val)
                if num_val > max_num:
                    return f"值{value}大于最大值{max_val}"
        except (ValueError, TypeError):
            pass
        return None

    def _validate_single(self, param: ParamInfoForLLM, values: list[Any]) -> tuple[list[Any], list[str]]:
        """校验SINGLE类型"""
        errors = []
        normalized = []
        for v in values:
            converted, err = self._convert_type(v, param.vtype)
            if err:
                errors.append(f"参数{param.param_name}: {err}")
                continue
            range_err = self._check_range(converted, param.min_val, param.max_val, param.vtype)
            if range_err:
                errors.append(f"参数{param.param_name}: {range_err}")
            normalized.append(converted)
        return normalized, errors

    def _validate_select(self, param: ParamInfoForLLM, values: list[Any]) -> tuple[list[Any], list[str]]:
        """校验SELECT类型"""
        errors = []
        normalized = []
        select_items = []
        if param.select_items:
            try:
                select_items = json.loads(param.select_items)
            except json.JSONDecodeError:
                select_items = []

        for v in values:
            str_v = str(v)
            if select_items and str_v not in select_items:
                errors.append(f"参数{param.param_name}: 值'{str_v}'不在可选项{select_items}中")
                continue
            normalized.append(str_v)
        return normalized, errors

    def _validate_vector(self, param: ParamInfoForLLM, values: list[Any]) -> tuple[list[Any], list[str]]:
        """校验VECTOR类型"""
        errors = []
        normalized = []
        expected_len = param.col or 1

        for i, v in enumerate(values):
            if not isinstance(v, list):
                errors.append(f"参数{param.param_name}第{i+1}组: 应为数组，实际为{type(v).__name__}")
                continue
            if len(v) != expected_len:
                errors.append(f"参数{param.param_name}第{i+1}组: 长度应为{expected_len}，实际为{len(v)}")
                # 不跳过，仍然尝试转换

            converted_arr = []
            for j, elem in enumerate(v):
                converted, err = self._convert_type(elem, param.vtype)
                if err:
                    errors.append(f"参数{param.param_name}第{i+1}组第{j+1}个元素: {err}")
                else:
                    range_err = self._check_range(converted, param.min_val, param.max_val, param.vtype)
                    if range_err:
                        errors.append(f"参数{param.param_name}第{i+1}组第{j+1}个元素: {range_err}")
                converted_arr.append(converted if not err else elem)
            normalized.append(converted_arr)
        return normalized, errors

    def _validate_matrix(self, param: ParamInfoForLLM, values: list[Any]) -> tuple[list[Any], list[str]]:
        """校验MATRIX类型"""
        errors = []
        normalized = []
        rows = param.row_val or 1
        cols = param.col or 1
        expected_len = rows * cols

        for i, v in enumerate(values):
            if not isinstance(v, list):
                errors.append(f"参数{param.param_name}第{i+1}组: 应为数组，实际为{type(v).__name__}")
                continue
            if len(v) != expected_len:
                errors.append(f"参数{param.param_name}第{i+1}组: 元素数量应为{expected_len}({rows}x{cols})，实际为{len(v)}")

            converted_arr = []
            for j, elem in enumerate(v):
                converted, err = self._convert_type(elem, param.vtype)
                if err:
                    errors.append(f"参数{param.param_name}第{i+1}组第{j+1}个元素: {err}")
                else:
                    range_err = self._check_range(converted, param.min_val, param.max_val, param.vtype)
                    if range_err:
                        errors.append(f"参数{param.param_name}第{i+1}组第{j+1}个元素: {range_err}")
                converted_arr.append(converted if not err else elem)
            normalized.append(converted_arr)
        return normalized, errors

    def _validate_mmatrix(self, param: ParamInfoForLLM, values: list[Any]) -> tuple[list[Any], list[str]]:
        """校验MMATRIX类型"""
        errors = []
        normalized = []
        rows = param.row_val or 1
        cols_def = []
        if param.cols_def:
            try:
                cols_def = json.loads(param.cols_def)
            except json.JSONDecodeError:
                errors.append(f"参数{param.param_name}: cols_def格式错误")
                return values, errors

        num_cols = len(cols_def)
        expected_len = rows * num_cols

        for i, v in enumerate(values):
            if not isinstance(v, list):
                errors.append(f"参数{param.param_name}第{i+1}组: 应为数组，实际为{type(v).__name__}")
                continue
            if len(v) != expected_len:
                errors.append(f"参数{param.param_name}第{i+1}组: 元素数量应为{expected_len}({rows}x{num_cols})，实际为{len(v)}")

            converted_arr = []
            for j, elem in enumerate(v):
                col_idx = j % num_cols if num_cols > 0 else 0
                col_vtype = cols_def[col_idx].get("vtype", "String") if col_idx < len(cols_def) else "String"
                converted, err = self._convert_type(elem, col_vtype)
                if err:
                    errors.append(f"参数{param.param_name}第{i+1}组第{j+1}个元素: {err}")
                else:
                    col_min = cols_def[col_idx].get("min_val") if col_idx < len(cols_def) else None
                    col_max = cols_def[col_idx].get("max_val") if col_idx < len(cols_def) else None
                    range_err = self._check_range(converted, col_min, col_max, col_vtype)
                    if range_err:
                        errors.append(f"参数{param.param_name}第{i+1}组第{j+1}个元素: {range_err}")
                converted_arr.append(converted if not err else elem)
            normalized.append(converted_arr)
        return normalized, errors


parse_service = ParseService()
