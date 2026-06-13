<template>
  <el-container>
    <el-header class="app-header">
      <div class="header-left">
        <h1 class="app-title" @click="$router.push('/')">参数试验系统</h1>
      </div>
      <div class="header-right">
        <el-button type="primary" @click="$router.push('/experiment/new')">
          <el-icon><Plus /></el-icon> <span class="btn-text">新建试验</span>
        </el-button>
      </div>
    </el-header>
    <el-main class="page-container">
      <div class="page-header">
        <h2>试验列表</h2>
      </div>

      <!-- 桌面端：表格 -->
      <el-table :data="experiments" stripe v-loading="loading" style="width: 100%" class="hidden-mobile">
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

      <!-- 移动端：卡片列表 -->
      <div class="mobile-card-list hidden-desktop" v-loading="loading">
        <div v-for="exp in experiments" :key="exp.id" class="exp-card" @click="$router.push(`/experiment/${exp.id}`)">
          <div class="exp-card-header">
            <span class="exp-card-name">{{ exp.name }}</span>
            <el-tag :type="statusType(exp.status)" size="small">{{ statusLabel(exp.status) }}</el-tag>
          </div>
          <div class="exp-card-body">
            <div class="exp-card-row">
              <span class="exp-card-label">ID</span>
              <span>{{ exp.id }}</span>
            </div>
            <div class="exp-card-row">
              <span class="exp-card-label">组合数</span>
              <span>{{ exp.total_combinations }} (有效: {{ exp.filtered_combinations }})</span>
            </div>
            <div class="exp-card-row">
              <span class="exp-card-label">创建时间</span>
              <span>{{ formatDate(exp.created_at) }}</span>
            </div>
          </div>
          <div class="exp-card-actions">
            <el-button size="small" @click.stop="$router.push(`/experiment/${exp.id}`)">查看</el-button>
            <el-button size="small" type="danger" @click.stop="handleDelete(exp.id)">删除</el-button>
          </div>
        </div>
        <el-empty v-if="experiments.length === 0 && !loading" description="暂无试验" />
      </div>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          :layout="isMobile ? 'prev, pager, next' : 'total, prev, pager, next'"
          @current-change="loadExperiments"
        />
      </div>
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getExperiments, deleteExperiment } from '../api/modules'
import type { Experiment } from '../types'

const experiments = ref<Experiment[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 响应式检测
const windowWidth = ref(window.innerWidth)
const isMobile = computed(() => windowWidth.value <= 768)

function onResize() { windowWidth.value = window.innerWidth }
onMounted(() => { window.addEventListener('resize', onResize); loadExperiments() })
onUnmounted(() => { window.removeEventListener('resize', onResize) })

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

/* 响应式显示控制 */
.hidden-mobile { display: block; }
.hidden-desktop { display: none; }

@media (max-width: 768px) {
  .hidden-mobile { display: none; }
  .hidden-desktop { display: block; }

  .app-header {
    padding: 0 12px;
    height: 50px;
  }

  .app-title {
    font-size: 16px;
  }

  .btn-text {
    display: none;
  }

  .pagination-wrapper {
    justify-content: center;
  }
}

/* 移动端卡片样式 */
.mobile-card-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.exp-card {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 12px;
  cursor: pointer;
  transition: box-shadow 0.2s;
}

.exp-card:active {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.exp-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.exp-card-name {
  font-weight: 600;
  font-size: 15px;
  color: #303133;
}

.exp-card-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 8px;
}

.exp-card-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: #606266;
}

.exp-card-label {
  color: #909399;
}

.exp-card-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  border-top: 1px solid #f0f0f0;
  padding-top: 8px;
}
</style>
