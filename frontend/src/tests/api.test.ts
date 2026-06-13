import { describe, it, expect, vi, beforeEach } from 'vitest'
import api from '../api/index'

// Mock axios
vi.mock('../api/index', () => {
  return {
    default: {
      get: vi.fn(),
      post: vi.fn(),
      put: vi.fn(),
      delete: vi.fn()
    }
  }
})

import { getModules, getModuleParams, createExperiment, getExperiments } from '../api/modules'

describe('API模块', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('getModules - 获取模块列表', async () => {
    const mockData = { total: 423, items: [{ id: 1, name: 'absest' }] }
    vi.mocked(api.get).mockResolvedValue(mockData)
    const result = await getModules({ keyword: 'absest' })
    expect(api.get).toHaveBeenCalledWith('/modules', { params: { keyword: 'absest' } })
    expect(result).toEqual(mockData)
  })

  it('getModuleParams - 获取模块参数', async () => {
    const mockData = [{ id: 1, name: 'compid', type_val: 'SINGLE' }]
    vi.mocked(api.get).mockResolvedValue(mockData)
    const result = await getModuleParams(1)
    expect(api.get).toHaveBeenCalledWith('/modules/1/params')
    expect(result).toEqual(mockData)
  })

  it('createExperiment - 创建试验', async () => {
    const mockData = { id: 1, name: '测试试验', status: 'draft' }
    vi.mocked(api.post).mockResolvedValue(mockData)
    const result = await createExperiment({ name: '测试试验' })
    expect(api.post).toHaveBeenCalledWith('/experiments', { name: '测试试验' })
    expect(result).toEqual(mockData)
  })

  it('getExperiments - 获取试验列表', async () => {
    const mockData = { total: 1, items: [{ id: 1, name: '测试试验' }] }
    vi.mocked(api.get).mockResolvedValue(mockData)
    const result = await getExperiments({ page: 1, page_size: 20 })
    expect(api.get).toHaveBeenCalledWith('/experiments', { params: { page: 1, page_size: 20 } })
    expect(result).toEqual(mockData)
  })
})
