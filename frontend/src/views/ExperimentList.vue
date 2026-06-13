<template>
  <el-container>
    <el-header class="app-header">
      <div class="header-left">
        <h1 class="app-title" @click="$router.push('/')">参数试验系统</h1>
      </div>
      <div class="header-right">
        <el-button type="primary" @click="$router.push('/experiment/new')">
          <el-icon><Plus /></el-icon> 新建试验
        </el-button>
      </div>
    </el-header>
    <el-main class="page-container">
      <div class="page-header">
        <h2>试验列表</h2>
      </div>

      <el-table :data="experiments" stripe v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="试验名称" min-width="200" />
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="total_combinations" label="总组合数" width="120" />
        <el-table-column prop="filtered_combinations" label="有效组合数" width="120" />
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="$router.push(`/experiment/${row.id}`)">查看</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="loadExperiments"
        />
      </div>
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getExperiments, deleteExperiment } from '../api/modules'
import type { Experiment } from '../types'

const experiments = ref<Experiment[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

function statusType(status: string) {
  const map: Record<string, string> = { draft: 'info', configured: 'warning', completed: 'success' }
  return map[status] || 'info'
}

function statusLabel(status: string) {
  const map: Record<string, string> = { draft: '草稿', configured: '已配置', completed: '已完成' }
  return map[status] || status
}

function formatDate(dateStr: string | null) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

async function loadExperiments() {
  loading.value = true
  try {
    const res: any = await getExperiments({ page: page.value, page_size: pageSize.value })
    experiments.value = res.items || []
    total.value = res.total || 0
  } catch (e: any) {
    ElMessage.error(e.message || '加载试验列表失败')
  } finally {
    loading.value = false
  }
}

async function handleDelete(id: number) {
  try {
    await ElMessageBox.confirm('确定要删除此试验吗？', '提示', { type: 'warning' })
    await deleteExperiment(id)
    ElMessage.success('删除成功')
    loadExperiments()
  } catch { /* 取消 */ }
}

onMounted(loadExperiments)
</script>

<style scoped>
.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 20px;
  height: 60px;
}

.app-title {
  font-size: 18px;
  font-weight: 600;
  color: #409eff;
  cursor: pointer;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}
</style>
