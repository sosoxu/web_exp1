import { describe, it, expect, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useExperimentStore } from '../stores/experiment'
import type { SelectedParam } from '../types'

// 创建mock参数
function createMockParam(overrides: Record<string, any> = {}) {
  return {
    id: 1,
    module_id: 1,
    name: 'test_param',
    class_val: null,
    display: 'Test Parameter',
    inmethod: 'DIRECT',
    uiname: null,
    no_val: null,
    autoexp: null,
    col: 1,
    vtype: 'Int',
    type_val: 'SINGLE',
    row_val: 1,
    prec: null,
    border_value: null,
    max_val: '100',
    min_val: '0',
    default_val: '0',
    default_rows: null,
    select_items: null,
    cols_def: null,
    title_row: null,
    title_col: null,
    comment: null,
    module_name: 'test_module',
    ...overrides
  }
}

describe('ExperimentStore', () => {
  let store: ReturnType<typeof useExperimentStore>

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useExperimentStore()
    store.reset()
  })

  it('初始状态正确', () => {
    expect(store.experimentId).toBeNull()
    expect(store.experimentName).toBe('')
    expect(store.selectedParams).toEqual([])
    expect(store.currentStep).toBe(0)
  })

  it('添加参数', () => {
    const param = createMockParam()
    store.addParam({
      module_id: 1,
      module_name: 'test_module',
      param
    })
    expect(store.selectedParams.length).toBe(1)
    expect(store.selectedParams[0].param.name).toBe('test_param')
  })

  it('不重复添加参数', () => {
    const param = createMockParam()
    store.addParam({ module_id: 1, module_name: 'test_module', param })
    store.addParam({ module_id: 1, module_name: 'test_module', param })
    expect(store.selectedParams.length).toBe(1)
  })

  it('移除参数', () => {
    const param = createMockParam()
    store.addParam({ module_id: 1, module_name: 'test_module', param })
    store.removeParam('test_module', 'test_param')
    expect(store.selectedParams.length).toBe(0)
  })

  it('设置参数取值', () => {
    store.setParamValue('test_module.test_param', {
      module_name: 'test_module',
      param_name: 'test_param',
      values: [1, 3, 5, 7, 9],
      value_type: '范围取值',
      confidence: 1.0
    })
    expect(store.paramValues['test_module.test_param'].values).toEqual([1, 3, 5, 7, 9])
  })

  it('移除参数时同时移除取值', () => {
    const param = createMockParam()
    store.addParam({ module_id: 1, module_name: 'test_module', param })
    store.setParamValue('test_module.test_param', {
      module_name: 'test_module',
      param_name: 'test_param',
      values: [1, 2],
      value_type: 'test',
      confidence: 1.0
    })
    store.removeParam('test_module', 'test_param')
    expect(store.paramValues['test_module.test_param']).toBeUndefined()
  })

  it('添加约束', () => {
    store.addConstraint({
      source_module: 'A',
      source_param: 'pa',
      target_module: 'A',
      target_param: 'pb',
      operator: 'gt',
      constraint_value: 3,
      description: 'pa必须大于3'
    })
    expect(store.customConstraints.length).toBe(1)
  })

  it('移除约束', () => {
    store.addConstraint({
      source_module: 'A',
      source_param: 'pa',
      target_module: 'A',
      target_param: 'pb',
      operator: 'gt',
      constraint_value: 3,
      description: 'pa必须大于3'
    })
    store.removeConstraint(0)
    expect(store.customConstraints.length).toBe(0)
  })

  it('重置状态', () => {
    const param = createMockParam()
    store.addParam({ module_id: 1, module_name: 'test_module', param })
    store.experimentName = 'test'
    store.currentStep = 2
    store.reset()
    expect(store.experimentName).toBe('')
    expect(store.selectedParams).toEqual([])
    expect(store.currentStep).toBe(0)
  })

  it('paramKeys计算属性', () => {
    const param1 = createMockParam({ name: 'pa' })
    const param2 = createMockParam({ name: 'pb', module_name: 'other_module' })
    store.addParam({ module_id: 1, module_name: 'test_module', param: param1 })
    store.addParam({ module_id: 2, module_name: 'other_module', param: param2 })
    expect(store.paramKeys).toEqual(['test_module.pa', 'other_module.pb'])
  })
})
