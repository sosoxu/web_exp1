import json
import httpx
from typing import Optional

from app.config import settings
from app.schemas.schemas import (
    ParamInfoForLLM, ParsedParamValue, ParsedConstraint, ParseParamsResponse
)


class LLMService:
    """DeepSeek API调用服务"""

    def __init__(self):
        self.api_key = settings.DEEPSEEK_API_KEY
        self.base_url = settings.DEEPSEEK_BASE_URL
        self.model = settings.DEEPSEEK_MODEL

    def _build_parse_prompt(self, params: list[ParamInfoForLLM], description: str, constraints: Optional[str] = None) -> list[dict]:
        """构建解析参数取值的Prompt"""
        params_info = []
        for p in params:
            info = {
                "module_name": p.module_name,
                "param_name": p.param_name,
                "type_val": p.type_val,
                "vtype": p.vtype,
            }
            if p.min_val is not None:
                info["min_val"] = p.min_val
            if p.max_val is not None:
                info["max_val"] = p.max_val
            if p.default_val is not None:
                info["default_val"] = p.default_val
            if p.select_items:
                info["select_items"] = p.select_items
            if p.cols_def:
                info["cols_def"] = p.cols_def
            if p.row_val is not None:
                info["row_val"] = p.row_val
            if p.col is not None:
                info["col"] = p.col
            if p.title_row:
                info["title_row"] = p.title_row
            if p.title_col:
                info["title_col"] = p.title_col
            params_info.append(info)

        system_prompt = """你是一个参数试验助手。用户会描述模块参数的取值，你需要根据参数的类型定义，将自然语言描述解析为结构化的参数取值。

参数类型说明（type_val）：
- SINGLE: 单一值，参数只有一个值。用户可以指定一个值、多个值、一个范围等。
- SELECT: 枚举选择，从select_items中选择一个或多个值。用户说"所有"或"全部"时返回所有选项。
- VECTOR: 一维数组，长度由col决定，每个元素类型为vtype。用户可以描述多组数组。
- MATRIX: 二维矩阵，行数row_val×列数col，所有元素类型为vtype。用户按行提供数据，系统自动按行列数切分。
- MMATRIX: 混合矩阵，行数row_val×列数由cols_def决定，每列类型可能不同。用户按行提供数据。

数值类型说明（vtype）：
- Int: 整数
- Float: 浮点数
- Double: 双精度浮点数
- String: 字符串
- Bool: 布尔值（true/false）
- NumStr: 数字字符串

重要规则：
1. 对于SINGLE类型，values是一个列表，每个元素是一个单一值。例如pa取1到10间隔2，则values=[1,3,5,7,9]
2. 对于SELECT类型，values是一个列表，每个元素是一个选项字符串。例如pb选所有，则values=["Up","Down","Left","Right"]
3. 对于VECTOR类型，values是一个列表，每个元素是一个数组。例如pc包括3组数据，则values=[[1,2,3,4,5],[11,12,13,14,15],[21,22,23,24,25]]
4. 对于MATRIX类型，values是一个列表，每个元素是一个一维数组（按行展开）。例如pd大小2x3，用户说1,2,3,4,5,6，则values=[[1,2,3,4,5,6]]
5. 对于MMATRIX类型，values是一个列表，每个元素是一个一维数组（按行展开）。例如pe大小2x2，用户说1,aaa,2,bbb，则values=[[1,"aaa",2,"bbb"]]
6. 所有值必须符合参数的vtype类型
7. 数值类型的值必须在min_val和max_val范围内
8. SELECT类型的值必须在select_items中

输出格式（严格JSON）：
{
  "params": [
    {
      "module_name": "模块名",
      "param_name": "参数名",
      "values": [取值列表],
      "value_type": "值类型描述"
    }
  ],
  "constraints": [
    {
      "source_module": "源模块名",
      "source_param": "源参数名",
      "target_module": "目标模块名",
      "target_param": "目标参数名",
      "operator": "操作符(eq/neq/gt/lt/gte/lte/in/not_in)",
      "value": 约束值,
      "description": "约束描述"
    }
  ]
}

只输出JSON，不要输出其他内容。"""

        user_content = f"参数定义：\n{json.dumps(params_info, ensure_ascii=False, indent=2)}\n\n用户描述：\n{description}"
        if constraints:
            user_content += f"\n\n用户指定的约束条件：\n{constraints}"

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

    async def parse_param_values(
        self,
        params: list[ParamInfoForLLM],
        description: str,
        constraints: Optional[str] = None
    ) -> ParseParamsResponse:
        """调用DeepSeek解析参数取值"""
        messages = self._build_parse_prompt(params, description, constraints)

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.1,
                    "max_tokens": 4096
                }
            )
            response.raise_for_status()
            result = response.json()

        raw_content = result["choices"][0]["message"]["content"]

        # 解析JSON
        parsed_data = self._extract_json(raw_content)

        parsed_params = []
        for p in parsed_data.get("params", []):
            parsed_params.append(ParsedParamValue(
                module_name=p.get("module_name", ""),
                param_name=p.get("param_name", ""),
                values=p.get("values", []),
                value_type=p.get("value_type", ""),
                confidence=1.0
            ))

        parsed_constraints = []
        for c in parsed_data.get("constraints", []):
            parsed_constraints.append(ParsedConstraint(
                source_module=c.get("source_module"),
                source_param=c.get("source_param"),
                target_module=c.get("target_module"),
                target_param=c.get("target_param"),
                operator=c.get("operator", "eq"),
                constraint_value=c.get("value"),
                description=c.get("description", "")
            ))

        return ParseParamsResponse(
            parsed=parsed_params,
            constraints=parsed_constraints,
            raw_llm_response=raw_content
        )

    async def parse_constraints(
        self,
        params: list[ParamInfoForLLM],
        constraint_description: str
    ) -> list[ParsedConstraint]:
        """解析用户描述的约束条件"""
        params_info = []
        for p in params:
            info = {"module_name": p.module_name, "param_name": p.param_name, "type_val": p.type_val, "vtype": p.vtype}
            if p.select_items:
                info["select_items"] = p.select_items
            params_info.append(info)

        system_prompt = """你是一个参数试验助手。用户会描述参数之间的约束条件，你需要将其解析为结构化的约束规则。

约束操作符：eq(等于), neq(不等于), gt(大于), lt(小于), gte(大于等于), lte(小于等于), in(在列表中), not_in(不在列表中)

输出格式（严格JSON）：
{
  "constraints": [
    {
      "source_module": "源模块名",
      "source_param": "源参数名",
      "target_module": "目标模块名",
      "target_param": "目标参数名",
      "operator": "操作符",
      "value": 约束值,
      "description": "约束描述"
    }
  ]
}

只输出JSON，不要输出其他内容。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"参数定义：\n{json.dumps(params_info, ensure_ascii=False, indent=2)}\n\n约束描述：\n{constraint_description}"}
        ]

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.1,
                    "max_tokens": 2048
                }
            )
            response.raise_for_status()
            result = response.json()

        raw_content = result["choices"][0]["message"]["content"]
        parsed_data = self._extract_json(raw_content)

        constraints = []
        for c in parsed_data.get("constraints", []):
            constraints.append(ParsedConstraint(
                source_module=c.get("source_module"),
                source_param=c.get("source_param"),
                target_module=c.get("target_module"),
                target_param=c.get("target_param"),
                operator=c.get("operator", "eq"),
                constraint_value=c.get("value"),
                description=c.get("description", "")
            ))

        return constraints

    def _extract_json(self, text: str) -> dict:
        """从LLM响应中提取JSON"""
        # 尝试直接解析
        text = text.strip()
        if text.startswith("```"):
            # 移除markdown代码块
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # 尝试找到JSON部分
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
            return {"params": [], "constraints": []}


llm_service = LLMService()
