import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000
})

// 请求拦截器
api.interceptors.request.use(
  (config) => config,
  (error) => Promise.reject(error)
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    // blob类型直接返回完整response，不提取data
    if (response.config.responseType === 'blob') {
      return response
    }
    return response.data
  },
  (error) => {
    const msg = error.response?.data?.detail || error.message || '请求失败'
    return Promise.reject(new Error(msg))
  }
)

export default api
