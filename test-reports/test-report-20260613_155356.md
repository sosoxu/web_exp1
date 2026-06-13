# 测试报告

**生成时间**: 2026-06-13 15:53:56
**测试总数**: 64
**通过**: 64
**失败**: 0
**通过率**: 100.0%

---

## 1. 后端测试结果

| 指标 | 数值 |
|------|------|
| 总数 | 50 |
| 通过 | 50 |
| 失败 | 0 |

### 后端测试用例详情

| # | 测试名 | 结果 | 耗时(s) |
|---|--------|------|---------|
| 1 | `tests/test_combinations.py::TestCombinationService::test_single_params_cartesian` | ✅ 通过 | 0.000 |
| 2 | `tests/test_combinations.py::TestCombinationService::test_single_param_values` | ✅ 通过 | 0.000 |
| 3 | `tests/test_combinations.py::TestCombinationService::test_dependency_constraint` | ✅ 通过 | 0.000 |
| 4 | `tests/test_combinations.py::TestCombinationService::test_custom_constraint` | ✅ 通过 | 0.000 |
| 5 | `tests/test_combinations.py::TestCombinationService::test_empty_params` | ✅ 通过 | 0.000 |
| 6 | `tests/test_combinations.py::TestCombinationService::test_vector_param_combination` | ✅ 通过 | 0.000 |
| 7 | `tests/test_combinations.py::TestCombinationService::test_max_combinations_limit` | ✅ 通过 | 0.000 |
| 8 | `tests/test_experiments.py::TestExperimentsAPI::test_create_experiment` | ✅ 通过 | 0.000 |
| 9 | `tests/test_experiments.py::TestExperimentsAPI::test_create_experiment_without_description` | ✅ 通过 | 0.000 |
| 10 | `tests/test_experiments.py::TestExperimentsAPI::test_list_experiments` | ✅ 通过 | 0.000 |
| 11 | `tests/test_experiments.py::TestExperimentsAPI::test_get_experiment_detail` | ✅ 通过 | 0.000 |
| 12 | `tests/test_experiments.py::TestExperimentsAPI::test_update_experiment` | ✅ 通过 | 0.000 |
| 13 | `tests/test_experiments.py::TestExperimentsAPI::test_delete_experiment` | ✅ 通过 | 0.000 |
| 14 | `tests/test_experiments.py::TestExperimentsAPI::test_get_nonexistent_experiment` | ✅ 通过 | 0.000 |
| 15 | `tests/test_experiments.py::TestExperimentsAPI::test_save_experiment_config` | ✅ 通过 | 0.000 |
| 16 | `tests/test_modules.py::TestModulesAPI::test_list_modules_default` | ✅ 通过 | 0.000 |
| 17 | `tests/test_modules.py::TestModulesAPI::test_list_modules_with_keyword` | ✅ 通过 | 0.000 |
| 18 | `tests/test_modules.py::TestModulesAPI::test_list_modules_pagination` | ✅ 通过 | 0.000 |
| 19 | `tests/test_modules.py::TestModulesAPI::test_list_modules_empty_keyword` | ✅ 通过 | 0.000 |
| 20 | `tests/test_modules.py::TestModulesAPI::test_list_modules_not_found_keyword` | ✅ 通过 | 0.000 |
| 21 | `tests/test_modules.py::TestModuleParamsAPI::test_get_module_params` | ✅ 通过 | 0.000 |
| 22 | `tests/test_modules.py::TestModuleParamsAPI::test_get_module_params_has_module_name` | ✅ 通过 | 0.000 |
| 23 | `tests/test_modules.py::TestModuleParamsAPI::test_get_module_params_types` | ✅ 通过 | 0.000 |
| 24 | `tests/test_modules.py::TestModuleParamsAPI::test_get_module_params_select_items` | ✅ 通过 | 0.000 |
| 25 | `tests/test_modules.py::TestModuleParamsAPI::test_get_module_dependencies` | ✅ 通过 | 0.000 |
| 26 | `tests/test_modules.py::TestHealthAPI::test_health_check` | ✅ 通过 | 0.000 |
| 27 | `tests/test_parse_service.py::TestParseService::test_validate_single_int` | ✅ 通过 | 0.000 |
| 28 | `tests/test_parse_service.py::TestParseService::test_validate_single_int_out_of_range` | ✅ 通过 | 0.000 |
| 29 | `tests/test_parse_service.py::TestParseService::test_validate_single_float` | ✅ 通过 | 0.000 |
| 30 | `tests/test_parse_service.py::TestParseService::test_validate_select` | ✅ 通过 | 0.000 |
| 31 | `tests/test_parse_service.py::TestParseService::test_validate_select_invalid_option` | ✅ 通过 | 0.000 |
| 32 | `tests/test_parse_service.py::TestParseService::test_validate_vector` | ✅ 通过 | 0.000 |
| 33 | `tests/test_parse_service.py::TestParseService::test_validate_vector_wrong_length` | ✅ 通过 | 0.000 |
| 34 | `tests/test_parse_service.py::TestParseService::test_validate_matrix` | ✅ 通过 | 0.000 |
| 35 | `tests/test_parse_service.py::TestParseService::test_validate_matrix_wrong_size` | ✅ 通过 | 0.000 |
| 36 | `tests/test_parse_service.py::TestParseService::test_validate_mmatrix` | ✅ 通过 | 0.000 |
| 37 | `tests/test_parse_service.py::TestParseService::test_validate_single_bool` | ✅ 通过 | 0.000 |
| 38 | `tests/test_parse_service.py::TestParseService::test_validate_string_type` | ✅ 通过 | 0.000 |
| 39 | `tests/test_sqlite_client.py::TestSQLiteClient::test_get_modules` | ✅ 通过 | 0.000 |
| 40 | `tests/test_sqlite_client.py::TestSQLiteClient::test_get_modules_with_keyword` | ✅ 通过 | 0.000 |
| 41 | `tests/test_sqlite_client.py::TestSQLiteClient::test_get_modules_pagination` | ✅ 通过 | 0.000 |
| 42 | `tests/test_sqlite_client.py::TestSQLiteClient::test_get_module_by_id` | ✅ 通过 | 0.000 |
| 43 | `tests/test_sqlite_client.py::TestSQLiteClient::test_get_module_by_id_not_found` | ✅ 通过 | 0.000 |
| 44 | `tests/test_sqlite_client.py::TestSQLiteClient::test_get_params_by_module` | ✅ 通过 | 0.000 |
| 45 | `tests/test_sqlite_client.py::TestSQLiteClient::test_get_param_by_id` | ✅ 通过 | 0.000 |
| 46 | `tests/test_sqlite_client.py::TestSQLiteClient::test_get_params_by_ids` | ✅ 通过 | 0.000 |
| 47 | `tests/test_sqlite_client.py::TestSQLiteClient::test_get_dependencies_by_module` | ✅ 通过 | 0.000 |
| 48 | `tests/test_sqlite_client.py::TestSQLiteClient::test_get_param_with_module` | ✅ 通过 | 0.000 |
| 49 | `tests/test_sqlite_client.py::TestSQLiteClient::test_module_param_count` | ✅ 通过 | 0.000 |
| 50 | `tests/test_sqlite_client.py::TestSQLiteClient::test_get_dependencies_by_param_ids` | ✅ 通过 | 0.000 |

## 2. 前端测试结果

| 指标 | 数值 |
|------|------|
| 总数 | 14 |
| 通过 | 14 |
| 失败 | 0 |

### 前端测试用例详情

| # | 测试名 | 结果 |
|---|--------|------|
| 1 | `API模块 getModules - 获取模块列表` | ✅ 通过 |
| 2 | `API模块 getModuleParams - 获取模块参数` | ✅ 通过 |
| 3 | `API模块 createExperiment - 创建试验` | ✅ 通过 |
| 4 | `API模块 getExperiments - 获取试验列表` | ✅ 通过 |
| 5 | `ExperimentStore 初始状态正确` | ✅ 通过 |
| 6 | `ExperimentStore 添加参数` | ✅ 通过 |
| 7 | `ExperimentStore 不重复添加参数` | ✅ 通过 |
| 8 | `ExperimentStore 移除参数` | ✅ 通过 |
| 9 | `ExperimentStore 设置参数取值` | ✅ 通过 |
| 10 | `ExperimentStore 移除参数时同时移除取值` | ✅ 通过 |
| 11 | `ExperimentStore 添加约束` | ✅ 通过 |
| 12 | `ExperimentStore 移除约束` | ✅ 通过 |
| 13 | `ExperimentStore 重置状态` | ✅ 通过 |
| 14 | `ExperimentStore paramKeys计算属性` | ✅ 通过 |

---

## 3. Bug清单

🎉 未发现Bug，所有测试通过！
