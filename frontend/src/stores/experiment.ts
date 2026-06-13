import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { SelectedParam, ParsedParamValue, ParsedConstraint, CombinationItem } from '../types'

export const useExperimentStore = defineStore('experiment', () => {
  // 当前试验
  const experimentId = ref<number | null>(null)
  const experimentName = ref('')
  const experimentDescription = ref('')

  // Step1: 选择的模块和参数
  const selectedParams = ref<SelectedParam[]>([])

  // Step2: 参数取值
  const paramValues = ref<Record<string, ParsedParamValue>>({})
  const customConstraints = ref<ParsedConstraint[]>([])

  // Step3: 组合结果
  const combinations = ref<CombinationItem[]>([])
  const totalCombinations = ref(0)
  const filteredCombinations = ref(0)

  // 当前步骤
  const currentStep = ref(0)

  // 计算属性
  const paramKeys = computed(() => {
    return selectedParams.value.map(sp => `${sp.module_name}.${sp.param.name}`)
  })

  // 方法
  function addParam(param: SelectedParam) {
    const key = `${param.module_name}.${param.param.name}`
    if (!selectedParams.value.find(p => `${p.module_name}.${p.param.name}` === key)) {
      selectedParams.value.push(param)
    }
  }

  function removeParam(moduleName: string, paramName: string) {
    const key = `${moduleName}.${paramName}`
    selectedParams.value = selectedParams.value.filter(
      p => `${p.module_name}.${p.param.name}` !== key
    )
    // 同时移除取值
    delete paramValues.value[key]
  }

  function setParamValue(key: string, value: ParsedParamValue) {
    paramValues.value[key] = value
  }

  function removeParamValue(key: string) {
    delete paramValues.value[key]
  }

  function addConstraint(constraint: ParsedConstraint) {
    customConstraints.value.push(constraint)
  }

  function removeConstraint(index: number) {
    customConstraints.value.splice(index, 1)
  }

  function reset() {
    experimentId.value = null
    experimentName.value = ''
    experimentDescription.value = ''
    selectedParams.value = []
    paramValues.value = {}
    customConstraints.value = []
    combinations.value = []
    totalCombinations.value = 0
    filteredCombinations.value = 0
    currentStep.value = 0
  }

  return {
    experimentId, experimentName, experimentDescription,
    selectedParams, paramValues, customConstraints,
    combinations, totalCombinations, filteredCombinations,
    currentStep, paramKeys,
    addParam, removeParam, setParamValue, removeParamValue,
    addConstraint, removeConstraint, reset
  }
})
