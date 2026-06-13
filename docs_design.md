# 参数试验系统 - 设计文档

## 1. 系统架构

### 1.1 整体架构

```
┌─────────────────────────────────────────────────┐
│                   Vue 3 前端                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │模块选择   │ │参数描述   │ │组合表展示        │ │
│  │组件       │ │与解析组件 │ │与管理组件        │ │
│  └──────────┘ └──────────┘ └──────────────────┘ │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │参数信息   │ │约束管理   │ │试验管理组件      │ │
│  │组件       │ │组件       │ │                  │ │
│  └──────────┘ └──────────┘ └──────────────────┘ │
└───────────────────────┬─────────────────────────┘
                        │ HTTP/REST API
┌───────────────────────┴─────────────────────────┐
│                FastAPI 后端                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │模块参数   │ │LLM解析   │ │组合生成          │ │
│  │API       │ │服务      │ │服务              │ │
│  └──────────┘ └──────────┘ └──────────────────┘ │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │约束处理   │ │试验管理   │ │数据导出          │ │
│  │服务       │ │服务      │ │服务              │ │
│  └──────────┘ └──────────┘ └──────────────────┘ │
└───────┬───────────────┬─────────────────────────┘
        │               │
┌───────┴───────┐ ┌─────┴───────────┐ ┌───────────┐
│ SQLite(只读)  │ │ PostgreSQL      │ │ DeepSeek  │
│ geomods_2.0.db│ │ 业务数据库      │ │ API       │
└───────────────┘ └─────────────────┘ └───────────┘
```

### 1.2 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端 | Vue 3 + TypeScript | 组合式API，组件化开发 |
| UI框架 | Element Plus | 成熟的Vue3组件库 |
| 状态管理 | Pinia | Vue3推荐的状态管理 |
| HTTP客户端 | Axios | 前端HTTP请求 |
| 后端 | Python 3.11 + FastAPI | 高性能异步框架 |
| ORM | SQLAlchemy 2.0 | PostgreSQL数据操作 |
| SQLite访问 | sqlite3 | Python内置，只读访问 |
| LLM | DeepSeek API | 大模型解析服务 |
| 数据库 | PostgreSQL 15+ | 业务数据存储 |
| 数据导出 | openpyxl / pandas | Excel/CSV导出 |

## 2. 数据库设计

### 2.1 PostgreSQL 业务表设计

#### 2.1.1 试验表（experiments）
```sql
CREATE TABLE experiments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'draft',  -- draft/configured/completed
    total_combinations INTEGER DEFAULT 0,
    filtered_combinations INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 2.1.2 试验模块选择表（experiment_modules）
```sql
CREATE TABLE experiment_modules (
    id SERIAL PRIMARY KEY,
    experiment_id INTEGER NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    module_name VARCHAR(200) NOT NULL,
    module_id INTEGER NOT NULL,  -- 对应SQLite中的modules.id
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 2.1.3 试验参数选择表（experiment_params）
```sql
CREATE TABLE experiment_params (
    id SERIAL PRIMARY KEY,
    experiment_id INTEGER NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    module_name VARCHAR(200) NOT NULL,
    param_name VARCHAR(200) NOT NULL,
    param_id INTEGER NOT NULL,  -- 对应SQLite中的parameters.id
    type_val VARCHAR(20) NOT NULL,  -- SINGLE/SELECT/VECTOR/MATRIX/MMATRIX
    vtype VARCHAR(20) NOT NULL,     -- Int/Float/String/...
    raw_description TEXT,           -- 用户的自然语言描述
    parsed_values JSONB,            -- 大模型解析后的取值结果
    is_confirmed BOOLEAN DEFAULT FALSE,  -- 用户是否确认
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 2.1.4 试验约束表（experiment_constraints）
```sql
CREATE TABLE experiment_constraints (
    id SERIAL PRIMARY KEY,
    experiment_id INTEGER NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    constraint_type VARCHAR(20) NOT NULL,  -- dependency/custom
    source_module VARCHAR(200),     -- 约束源模块名
    source_param VARCHAR(200),      -- 约束源参数名
    target_module VARCHAR(200),     -- 约束目标模块名
    target_param VARCHAR(200),      -- 约束目标参数名
    operator VARCHAR(20),           -- 操作符：eq/neq/gt/lt/gte/lte/in/not_in
    constraint_value JSONB,         -- 约束值
    raw_description TEXT,           -- 用户原始描述（自定义约束时）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 2.1.5 参数组合表（param_combinations）
```sql
CREATE TABLE param_combinations (
    id SERIAL PRIMARY KEY,
    experiment_id INTEGER NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    combination_index INTEGER NOT NULL,  -- 组合序号
    combination_data JSONB NOT NULL,     -- 组合数据 {"ModuleA.param1": value1, ...}
    is_valid BOOLEAN DEFAULT TRUE,       -- 是否通过约束检查
    invalid_reason TEXT,                 -- 不通过原因
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2.2 SQLite 数据读取策略

SQLite数据库作为只读数据源，后端通过Python内置sqlite3模块直接读取，不通过ORM。

**核心查询：**
- 模块列表：`SELECT * FROM modules WHERE name LIKE ?`
- 模块参数：`SELECT * FROM parameters WHERE module_id = ?`
- 参数依赖：`SELECT * FROM dependencies WHERE parameter_id IN (...)`
- 参数详情：`SELECT * FROM parameters WHERE id = ?`

## 3. API 设计

### 3.1 模块与参数 API

#### GET /api/modules
获取模块列表，支持搜索分页
```
Query: keyword?, page?, page_size?
Response: { total, items: [{ id, name, version, module_type, param_count }] }
```

#### GET /api/modules/{module_id}/params
获取模块的参数列表
```
Response: [{ id, name, display, type_val, vtype, min_val, max_val, default_val,
             select_items, cols_def, row_val, col, title_row, title_col, comment }]
```

#### GET /api/modules/{module_id}/dependencies
获取模块参数的依赖关系
```
Response: [{ param_id, param_name, deparent, interoper, dep_values }]
```

### 3.2 LLM 解析 API

#### POST /api/llm/parse-params
解析用户自然语言描述的参数取值
```
Request: {
    params: [{
        module_name, param_name, type_val, vtype,
        min_val, max_val, default_val, select_items,
        cols_def, row_val, col, title_row, title_col
    }],
    description: string,  // 用户的自然语言描述
    constraints: string?  // 用户描述的约束条件
}
Response: {
    parsed: [{
        module_name, param_name,
        values: [...],          // 解析出的取值列表
        value_type: string,     // 值的表达类型
        confidence: number      // 解析置信度 0-1
    }],
    constraints: [{
        source_module, source_param,
        target_module, target_param,
        operator, constraint_value,
        description: string
    }],
    raw_llm_response: string    // 大模型原始响应（调试用）
}
```

#### POST /api/llm/parse-constraints
解析用户描述的约束条件
```
Request: {
    params: [{ module_name, param_name, type_val, vtype, ... }],
    constraint_description: string
}
Response: {
    constraints: [{
        source_module, source_param,
        target_module, target_param,
        operator, constraint_value,
        description
    }]
}
```

### 3.3 组合生成 API

#### POST /api/combinations/generate
生成参数组合表
```
Request: {
    experiment_id: integer,
    params: [{
        module_name, param_name, type_val, vtype,
        values: [...]  // 已确认的取值列表
    }],
    constraints: [{
        source_module, source_param,
        target_module, target_param,
        operator, constraint_value
    }],
    dependency_constraints: [{
        param_id, deparent, dep_values
    }]
}
Response: {
    total_combinations: integer,
    filtered_combinations: integer,
    preview: [{ index, combination_data }],  // 前N条预览
    task_id: string  // 异步任务ID（组合量大时）
}
```

#### GET /api/combinations/{experiment_id}
获取组合表（分页）
```
Query: page?, page_size?, is_valid?
Response: { total, items: [{ index, combination_data, is_valid, invalid_reason }] }
```

#### GET /api/combinations/{experiment_id}/export
导出组合表
```
Query: format=csv|xlsx
Response: 文件下载
```

### 3.4 试验管理 API

#### POST /api/experiments
创建试验
```
Request: { name, description? }
Response: { id, name, description, status, created_at }
```

#### GET /api/experiments
获取试验列表
```
Query: page?, page_size?
Response: { total, items: [{ id, name, description, status, total_combinations, created_at }] }
```

#### GET /api/experiments/{id}
获取试验详情
```
Response: { id, name, description, status, modules, params, constraints, combinations_count }
```

#### PUT /api/experiments/{id}
更新试验
```
Request: { name?, description?, status? }
Response: { id, name, description, status }
```

#### DELETE /api/experiments/{id}
删除试验

#### POST /api/experiments/{id}/save-config
保存试验配置（模块选择、参数取值、约束）
```
Request: {
    modules: [{ module_id, module_name }],
    params: [{ module_name, param_name, param_id, type_val, vtype,
               raw_description, parsed_values }],
    constraints: [{ ... }]
}
```

## 4. 前端设计

### 4.1 页面结构

```
┌─────────────────────────────────────────────────────┐
│  顶部导航栏                                          │
│  [Logo] 参数试验系统    [试验列表] [新建试验]         │
├─────────────────────────────────────────────────────┤
│                                                     │
│  试验工作区（步骤式流程）                              │
│                                                     │
│  Step 1: 选择模块和参数                              │
│  ┌───────────────────────────────────────────────┐  │
│  │ 模块搜索 [________]  [搜索]                    │  │
│  │                                               │  │
│  │ ┌─────────────┐  ┌─────────────────────────┐ │  │
│  │ │ 模块列表     │  │ 参数列表                 │ │  │
│  │ │ ☐ absest    │  │ ☑ compid (Int/SINGLE)   │ │  │
│  │ │ ☑ adaptsub  │  │ ☑ leftshift (Float/SNG) │ │  │
│  │ │ ☐ adaptsub3d│  │ ☐ timewindow (Float/SNG)│ │  │
│  │ │ ...         │  │ ...                      │ │  │
│  │ └─────────────┘  └─────────────────────────┘ │  │
│  │                                               │  │
│  │ 已选参数:                                      │  │
│  │ [adaptsub.leftshift ×] [adaptsub.compid ×]   │  │
│  └───────────────────────────────────────────────┘  │
│                                                     │
│  Step 2: 描述参数取值                                │
│  ┌───────────────────────────────────────────────┐  │
│  │ 参数取值描述                                    │  │
│  │ ┌─────────────────────────────────────────┐   │  │
│  │ │ adaptsub.leftshift (Float, SINGLE)       │   │  │
│  │ │ 范围: -3.4e+38 ~ 3.4e+38, 默认: 5       │   │  │
│  │ │ 描述: [1到10，间隔为2___________] [解析]  │   │  │
│  │ │ 结果: [1, 3, 5, 7, 9]  [编辑]           │   │  │
│  │ ├─────────────────────────────────────────┤   │  │
│  │ │ adaptsub.hodsrc (String, SELECT)         │   │  │
│  │ │ 选项: ["First break","VSP first break"]  │   │  │
│  │ │ 描述: [选所有_______________] [解析]      │   │  │
│  │ │ 结果: ["First break","VSP first break"]  │   │  │
│  │ │        [编辑]                             │   │  │
│  │ └─────────────────────────────────────────┘   │  │
│  │                                               │  │
│  │ 约束条件描述（可选）                             │  │
│  │ [________________________________] [添加约束]  │  │
│  │ 已添加约束:                                    │  │
│  │ - 当hodsrc为"First break"时，leftshift > 0    │  │
│  └───────────────────────────────────────────────┘  │
│                                                     │
│  Step 3: 生成组合表                                  │
│  ┌───────────────────────────────────────────────┐  │
│  │ 总组合数: 10  过滤后: 8                         │  │
│  │                                               │  │
│  │ ┌─────────────────────────────────────────┐   │  │
│  │ │ index │ leftshift │ hodsrc        │ ... │   │  │
│  │ │   1   │     1     │ First break   │ ... │   │  │
│  │ │   2   │     3     │ First break   │ ... │   │  │
│  │ │   3   │     5     │ First break   │ ... │   │  │
│  │ │  ...  │    ...    │ ...           │ ... │   │  │
│  │ └─────────────────────────────────────────┘   │  │
│  │                                               │  │
│  │ [导出CSV] [导出Excel] [保存试验]               │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### 4.2 组件设计

#### 4.2.1 可复用组件

| 组件名 | 功能 | 复用场景 |
|--------|------|----------|
| ModuleSelector | 模块搜索与选择 | Step1、试验详情 |
| ParamSelector | 参数列表与选择 | Step1、试验详情 |
| SelectedParams | 已选参数标签展示 | Step1、Step2 |
| ParamValueEditor | 参数取值编辑器 | Step2、约束编辑 |
| LlmParseInput | LLM解析输入框 | Step2 |
| ConstraintEditor | 约束条件编辑 | Step2、约束管理 |
| CombinationTable | 组合表展示 | Step3、试验详情 |
| StepWizard | 步骤导航 | 试验工作区 |
| SearchInput | 通用搜索输入框 | 模块搜索、参数搜索 |
| DataExport | 数据导出按钮组 | Step3、试验详情 |

#### 4.2.2 页面组件

| 组件名 | 功能 |
|--------|------|
| ExperimentList | 试验列表页 |
| ExperimentWorkspace | 试验工作区（包含Step1-3） |
| StepSelectParams | Step1：选择模块和参数 |
| StepDescribeValues | Step2：描述参数取值 |
| StepGenerateTable | Step3：生成组合表 |

### 4.3 状态管理（Pinia Store）

```typescript
// experiment.store.ts
interface ExperimentState {
    // 当前试验
    currentExperiment: Experiment | null;

    // Step1: 选择的模块和参数
    selectedModules: Module[];
    selectedParams: SelectedParam[];

    // Step2: 参数取值
    paramValues: ParamValueMap;  // key: "moduleName.paramName"
    customConstraints: Constraint[];

    // Step3: 组合结果
    combinations: Combination[];
    totalCombinations: number;
    filteredCombinations: number;
}
```

## 5. 后端设计

### 5.1 项目结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI应用入口
│   ├── config.py               # 配置管理
│   ├── database.py             # PostgreSQL数据库连接
│   ├── models/                 # SQLAlchemy模型
│   │   ├── __init__.py
│   │   ├── experiment.py
│   │   ├── experiment_module.py
│   │   ├── experiment_param.py
│   │   ├── experiment_constraint.py
│   │   └── param_combination.py
│   ├── schemas/                # Pydantic请求/响应模型
│   │   ├── __init__.py
│   │   ├── module.py
│   │   ├── param.py
│   │   ├── llm.py
│   │   ├── combination.py
│   │   └── experiment.py
│   ├── services/               # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── module_service.py   # 模块参数查询
│   │   ├── llm_service.py      # DeepSeek API调用
│   │   ├── parse_service.py    # 参数解析逻辑
│   │   ├── combination_service.py  # 组合生成
│   │   ├── constraint_service.py   # 约束处理
│   │   └── export_service.py   # 数据导出
│   ├── api/                    # API路由
│   │   ├── __init__.py
│   │   ├── modules.py
│   │   ├── llm.py
│   │   ├── combinations.py
│   │   └── experiments.py
│   └── utils/
│       ├── __init__.py
│       └── sqlite_client.py    # SQLite只读客户端
├── alembic/                    # 数据库迁移
├── tests/
├── requirements.txt
└── .env
```

### 5.2 核心服务设计

#### 5.2.1 LLM解析服务（llm_service.py）

```python
class LLMService:
    """DeepSeek API调用服务"""

    async def parse_param_values(
        self,
        params: list[ParamInfo],
        description: str
    ) -> ParseResult:
        """
        调用DeepSeek解析参数取值

        Prompt设计：
        1. 系统提示：说明任务背景，定义参数类型体系
        2. 参数信息：注入参数的type_val、vtype、范围、选项等
        3. 用户描述：用户的自然语言输入
        4. 输出格式：要求JSON格式输出
        """

    async def parse_constraints(
        self,
        params: list[ParamInfo],
        description: str
    ) -> list[Constraint]:
        """解析用户描述的约束条件"""
```

**LLM Prompt设计策略：**

```
系统提示：
你是一个参数试验助手。用户会描述模块参数的取值，你需要根据参数的类型定义，
将自然语言描述解析为结构化的参数取值。

参数类型说明：
- SINGLE: 单一值，参数只有一个值
- SELECT: 枚举选择，从select_items中选择
- VECTOR: 一维数组，长度由col决定，每个元素类型为vtype
- MATRIX: 二维矩阵，行数row_val×列数col，所有元素类型为vtype
- MMATRIX: 混合矩阵，行数row_val×列数由cols_def决定，每列类型可能不同

数值类型说明：
- Int: 整数  - Float: 浮点数  - String: 字符串
- Bool: 布尔值  - Double: 双精度浮点数

输出格式：
{
  "params": [
    {
      "module_name": "xxx",
      "param_name": "xxx",
      "values": [...],       // 取值列表
      "value_type": "..."    // 值类型描述
    }
  ],
  "constraints": [
    {
      "source": { "module": "xxx", "param": "xxx" },
      "target": { "module": "xxx", "param": "xxx" },
      "operator": "gt",      // eq/neq/gt/lt/gte/lte/in/not_in
      "value": ...,
      "description": "..."
    }
  ]
}

参数定义：
{params_info}

用户描述：
{user_description}
```

#### 5.2.2 组合生成服务（combination_service.py）

```python
class CombinationService:
    """参数组合生成服务"""

    def generate_combinations(
        self,
        param_values: dict[str, list],  # key: "module.param", value: 取值列表
        constraints: list[Constraint],
        dependency_constraints: list[DependencyConstraint]
    ) -> list[Combination]:
        """
        生成参数组合

        1. 计算笛卡尔积
        2. 应用依赖约束过滤
        3. 应用自定义约束过滤
        4. 返回有效组合
        """

    def _apply_dependency_filter(
        self,
        combination: dict,
        dependencies: list[DependencyConstraint]
    ) -> tuple[bool, str]:
        """应用依赖约束：如果父参数值不在dep_values中，子参数应标记为N/A"""

    def _apply_custom_filter(
        self,
        combination: dict,
        constraints: list[Constraint]
    ) -> tuple[bool, str]:
        """应用自定义约束"""
```

#### 5.2.3 约束处理服务（constraint_service.py）

```python
class ConstraintService:
    """约束处理服务"""

    def get_param_dependencies(
        self,
        param_ids: list[int]
    ) -> list[DependencyInfo]:
        """从SQLite获取参数的依赖关系"""

    def evaluate_constraint(
        self,
        combination: dict,
        constraint: Constraint
    ) -> bool:
        """评估单个约束是否满足"""

    def filter_combinations(
        self,
        combinations: list[dict],
        constraints: list[Constraint]
    ) -> list[dict]:
        """过滤不满足约束的组合"""
```

### 5.3 参数值解析后处理

大模型返回解析结果后，后端需进行校验和后处理：

```python
class ParseService:
    """参数解析后处理"""

    def validate_and_normalize(
        self,
        param: ParamInfo,
        parsed_values: list
    ) -> list:
        """
        校验和规范化解析结果

        1. 类型校验：确保值符合vtype
        2. 范围校验：确保值在min_val和max_val之间
        3. SELECT校验：确保值在select_items中
        4. 维度校验：
           - VECTOR: 确保长度等于col
           - MATRIX: 确保形状为row_val×col
           - MMATRIX: 确保形状为row_val×cols_def.length
        5. 类型转换：将字符串转为正确的数值类型
        """
```

## 6. 关键流程设计

### 6.1 参数取值解析流程

```
用户输入描述
    │
    ▼
前端发送请求 → POST /api/llm/parse-params
    │
    ▼
后端构建Prompt（注入参数定义信息）
    │
    ▼
调用DeepSeek API
    │
    ▼
解析LLM返回的JSON
    │
    ▼
后处理：类型校验、范围校验、维度校验
    │
    ▼
返回结构化结果给前端
    │
    ▼
前端展示解析结果 → 用户可编辑修改
    │
    ▼
用户确认 → 保存到experiment_params
```

### 6.2 组合生成流程

```
用户点击"生成组合"
    │
    ▼
前端收集已确认的参数取值和约束
    │
    ▼
后端接收请求
    │
    ▼
1. 从SQLite查询参数依赖关系
    │
    ▼
2. 计算笛卡尔积
   - 对每个参数的取值列表做笛卡尔积
   - SINGLE: 每个值是一个取值
   - SELECT: 每个选项是一个取值
   - VECTOR/MATRIX/MMATRIX: 每组数据是一个取值
    │
    ▼
3. 应用依赖约束
   - 遍历每条依赖关系
   - 如果父参数值不在dep_values中，子参数标记N/A
    │
    ▼
4. 应用自定义约束
   - 遍历每条自定义约束
   - 不满足的组合标记为invalid
    │
    ▼
5. 统计有效/无效组合数
    │
    ▼
6. 保存到param_combinations表
    │
    ▼
返回结果（含预览数据）
```

### 6.3 依赖约束处理逻辑

```
依赖关系：参数A依赖参数B，dep_values = ["v1", "v2"]

含义：当参数B的值为v1或v2时，参数A才生效

处理方式：
1. 在组合表中，如果B的值在dep_values中：
   - A列正常显示其取值
2. 如果B的值不在dep_values中：
   - A列显示N/A（表示该参数在此组合中不生效）
   - 该组合仍然保留，但A参数标记为不生效

注意：依赖约束不会剔除组合，只会标记某些参数为N/A
自定义约束才会剔除不符合条件的组合
```

## 7. 配置管理

### 7.1 环境变量

```env
# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=param_experiment
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# DeepSeek API
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# SQLite
SQLITE_DB_PATH=./data/geomods_2.0.db

# Application
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=true

# 组合限制
MAX_COMBINATIONS=100000
```

## 8. 部署方案

### 8.1 开发环境

```yaml
# docker-compose.dev.yml
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: param_experiment
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - ./data:/app/data
    depends_on:
      - postgres

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app
    depends_on:
      - backend

volumes:
  pgdata:
```

### 8.2 生产环境

使用Nginx反向代理，前端构建静态文件，后端Gunicorn+Uvicorn部署。

## 9. 安全考虑

- DeepSeek API Key 存储在环境变量中，不硬编码
- PostgreSQL 连接信息通过环境变量配置
- API接口添加CORS配置
- 前端不直接访问SQLite数据库
- 参数值输入做SQL注入防护（使用ORM参数化查询）
- 组合数量上限防止资源耗尽
