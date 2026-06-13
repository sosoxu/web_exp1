import api from './index'

// 模块列表
export function getModules(params: { keyword?: string; page?: number; page_size?: number }) {
  return api.get('/modules', { params })
}

// 模块参数
export function getModuleParams(moduleId: number) {
  return api.get(`/modules/${moduleId}/params`)
}

// 模块依赖关系
export function getModuleDependencies(moduleId: number) {
  return api.get(`/modules/${moduleId}/dependencies`)
}

// LLM解析参数取值
export function parseParams(data: {
  params: any[]
  description: string
  constraints?: string
}) {
  return api.post('/llm/parse-params', data)
}

// LLM解析约束条件
export function parseConstraints(data: {
  params: any[]
  constraint_description: string
}) {
  return api.post('/llm/parse-constraints', data)
}

// 生成组合
export function generateCombinations(data: {
  experiment_id?: number
  params: any[]
  constraints: any[]
  dependency_constraints: any[]
}) {
  return api.post('/combinations/generate', data)
}

// 获取组合列表
export function getCombinations(experimentId: number, params: {
  page?: number
  page_size?: number
  is_valid?: boolean
}) {
  return api.get(`/combinations/${experimentId}`, { params })
}

// 导出组合
export function exportCombinations(experimentId: number, format: string) {
  return api.get(`/combinations/${experimentId}/export`, {
    params: { format },
    responseType: 'blob'
  })
}

// 创建试验
export function createExperiment(data: { name: string; description?: string }) {
  return api.post('/experiments', data)
}

// 获取试验列表
export function getExperiments(params: { page?: number; page_size?: number }) {
  return api.get('/experiments', { params })
}

// 获取试验详情
export function getExperiment(id: number) {
  return api.get(`/experiments/${id}`)
}

// 更新试验
export function updateExperiment(id: number, data: any) {
  return api.put(`/experiments/${id}`, data)
}

// 删除试验
export function deleteExperiment(id: number) {
  return api.delete(`/experiments/${id}`)
}

// 保存试验配置
export function saveExperimentConfig(id: number, data: any) {
  return api.post(`/experiments/${id}/save-config`, data)
}
