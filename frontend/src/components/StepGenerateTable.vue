<template>
  <el-card>
    <template #header>
      <div class="card-header">
        <span>生成参数组合表</span>
        <div>
          <el-button @click="$emit('prev')">上一步</el-button>
          <el-button type="primary" @click="generateTable" :loading="generating">生成组合</el-button>
        </div>
      </div>
    </template>

    <!-- 统计信息 -->
    <div v-if="store.totalCombinations > 0" class="stats-row">
      <el-statistic title="总组合数" :value="store.totalCombinations" />
      <el-statistic title="有效组合数" :value="store.filteredCombinations" />
      <el-statistic title="无效组合数" :value="store.totalCombinations - store.filteredCombinations" />
    </div>

    <!-- 组合表 -->
    <div v-if="pagedCombinations.length > 0" class="combination-table-wrapper">
      <div class="table-actions">
        <div class="actions-left">
          <el-button type="success" size="small" @click="handleExport('csv')">
            <el-icon><Download /></el-icon> 导出CSV
          </el-button>
          <el-button type="success" size="small" @click="handleExport('xlsx')">
            <el-icon><Download /></el-icon> 导出Excel
          </el-button>
          <el-button type="danger" size="small" @click="handleBatchDelete" :disabled="selectedIds.length === 0">
            <el-icon><Delete /></el-icon> 删除选中 ({{ selectedIds.length }})
          </el-button>
        </div>
        <div class="actions-right">
          <el-checkbox v-model="showOnlyValid">仅显示有效组合</el-checkbox>
        </div>
      </div>

      <el-table
        ref="tableRef"
        :data="pagedCombinations"
        stripe
        border
        size="small"
        style="width: 100%"
        max-height="600"
        @selection-change="handleSelectionChange"
        row-key="index"
      >
        <el-table-column type="selection" width="45" />
        <el-table-column prop="index" label="#" width="70" fixed />
        <el-table-column
          v-for="key in paramKeys"
          :key="key"
          :label="key"
          min-width="150"
        >
          <template #default="{ row }">
            <span v-if="editingId === row.index && editingKey === key" class="edit-cell">
              <el-input
                v-model="editingValue"
                size="small"
                @keyup.enter="saveEdit(row)"
                @keyup.escape="cancelEdit"
                @blur="saveEdit(row)"
                autofocus
              />
            </span>
            <span
              v-else
              :class="{ 'na-value': row.combination_data[key] === 'N/A', 'editable-cell': row.id }"
              @dblclick="startEdit(row, key)"
            >
              {{ formatValue(row.combination_data[key]) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="有效" width="80" fixed="right">
          <template #default="{ row }">
            <el-tag :type="row.is_valid ? 'success' : 'danger'" size="small">
              {{ row.is_valid ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button type="danger" size="small" link @click="handleDelete(row)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[20, 50, 100, 200]"
          :total="displayTotal"
          layout="total, sizes, prev, pager, next"
          @current-change="onPageChange"
          @size-change="onPageSizeChange"
        />
      </div>
    </div>

    <el-empty v-else-if="!generating" description="请点击生成组合按钮" />
  </el-card>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useExperimentStore } from '../stores/experiment'
import {
  generateCombinations, getCombinations, exportCombinations,
  updateCombination, deleteCombination, batchDeleteCombinations
} from '../api/modules'

const emit = defineEmits(['prev'])
const store = useExperimentStore()

const generating = ref(false)
const showOnlyValid = ref(true)
const currentPage = ref(1)
const pageSize = ref(50)
const selectedIds = ref<number[]>([])
const selectedRows = ref<any[]>([])

// 编辑相关
const editingId = ref<number | null>(null)
const editingKey = ref('')
const editingValue = ref('')
const tableRef = ref()

const paramKeys = computed(() => {
  if (store.combinations.length > 0) {
    return Object.keys(store.combinations[0].combination_data)
  }
  return store.selectedParams.map(sp => `${sp.module_name}.${sp.param.name}`)
})

// 过滤后的组合
const filteredCombinations = computed(() => {
  if (showOnlyValid.value) {
    return store.combinations.filter(c => c.is_valid)
  }
  return store.combinations
})

const displayTotal = computed(() => {
  if (showOnlyValid.value) {
    return store.filteredCombinations
  }
  return store.totalCombinations
})

// 前端分页
const pagedCombinations = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredCombinations.value.slice(start, start + pageSize.value)
})

// 如果有experimentId，使用后端分页
const useServerPaging = computed(() => !!store.experimentId && store.totalCombinations > 100)

watch(showOnlyValid, () => {
  currentPage.value = 1
  if (useServerPaging.value) {
    loadFromServer()
  }
})

function onPageChange() {
  if (useServerPaging.value) {
    loadFromServer()
  }
}

function onPageSizeChange() {
  currentPage.value = 1
  if (useServerPaging.value) {
    loadFromServer()
  }
}

async function loadFromServer() {
  if (!store.experimentId) return
  try {
    const res: any = await getCombinations(store.experimentId, {
      page: currentPage.value,
      page_size: pageSize.value,
      is_valid: showOnlyValid.value || undefined
    })
    store.combinations = res.items || []
  } catch (e: any) {
    ElMessage.error(e.message || '加载组合失败')
  }
}

function formatValue(val: any) {
  if (val === 'N/A') return 'N/A'
  if (Array.isArray(val)) {
    if (val.length > 0 && Array.isArray(val[0])) {
      return val.map((r: any[]) => `[${r.join(', ')}]`).join('; ')
    }
    return `[${val.join(', ')}]`
  }
  return String(val)
}

// 编辑功能
function startEdit(row: any, key: string) {
  if (!row.id) {
    ElMessage.warning('请先保存试验后再编辑')
    return
  }
  editingId.value = row.index
  editingKey.value = key
  const val = row.combination_data[key]
  editingValue.value = Array.isArray(val) ? JSON.stringify(val) : String(val)
}

async function saveEdit(row: any) {
  if (editingId.value === null) return
  const key = editingKey.value
  let newValue: any = editingValue.value

  // 尝试解析JSON（数组类型）
  try {
    const parsed = JSON.parse(newValue)
    if (Array.isArray(parsed)) {
      newValue = parsed
    }
  } catch {
    // 保持字符串
  }

  // 更新本地数据
  row.combination_data[key] = newValue

  // 如果有id，同步到后端
  if (row.id && store.experimentId) {
    try {
      await updateCombination(store.experimentId, row.id, {
        combination_data: row.combination_data
      })
      ElMessage.success('修改成功')
    } catch (e: any) {
      ElMessage.error(e.message || '修改失败')
    }
  }

  cancelEdit()
}

function cancelEdit() {
  editingId.value = null
  editingKey.value = ''
  editingValue.value = ''
}

// 删除功能
async function handleDelete(row: any) {
  try {
    await ElMessageBox.confirm('确定要删除此组合吗？', '提示', { type: 'warning' })

    if (row.id && store.experimentId) {
      await deleteCombination(store.experimentId, row.id)
      ElMessage.success('删除成功')
      // 重新加载
      if (useServerPaging.value) {
        loadFromServer()
      } else {
        store.combinations = store.combinations.filter(c => c.index !== row.index)
        store.totalCombinations--
        if (row.is_valid) store.filteredCombinations--
      }
    } else {
      store.combinations = store.combinations.filter(c => c.index !== row.index)
      store.totalCombinations--
      if (row.is_valid) store.filteredCombinations--
    }
  } catch { /* 取消 */ }
}

// 批量删除
function handleSelectionChange(rows: any[]) {
  selectedRows.value = rows
  selectedIds.value = rows.filter(r => r.id).map(r => r.id)
}

async function handleBatchDelete() {
  if (selectedIds.value.length === 0) {
    ElMessage.warning('请先选择要删除的组合')
    return
  }

  try {
    await ElMessageBox.confirm(`确定要删除选中的 ${selectedIds.value.length} 条组合吗？`, '提示', { type: 'warning' })

    if (store.experimentId) {
      await batchDeleteCombinations(store.experimentId, selectedIds.value)
      ElMessage.success('批量删除成功')
      if (useServerPaging.value) {
        loadFromServer()
      }
    }

    // 本地也移除
    const deleteIndices = new Set(selectedRows.value.map(r => r.index))
    const deletedValid = selectedRows.value.filter(r => r.is_valid).length
    store.combinations = store.combinations.filter(c => !deleteIndices.has(c.index))
    store.totalCombinations -= deleteIndices.size
    store.filteredCombinations -= deletedValid
    selectedIds.value = []
    selectedRows.value = []
  } catch { /* 取消 */ }
}

// 生成组合
async function generateTable() {
  generating.value = true
  try {
    const params = store.selectedParams.map(sp => {
      const key = `${sp.module_name}.${sp.param.name}`
      const pv = store.paramValues[key]
      return {
        module_name: sp.module_name,
        param_name: sp.param.name,
        type_val: sp.param.type_val,
        vtype: sp.param.vtype,
        values: pv?.values || []
      }
    })

    const res: any = await generateCombinations({
      experiment_id: store.experimentId || undefined,
      params,
      constraints: store.customConstraints,
      dependency_constraints: []
    })

    store.totalCombinations = res.total_combinations
    store.filteredCombinations = res.filtered_combinations
    store.combinations = res.preview || []

    if (res.experiment_id && !store.experimentId) {
      store.experimentId = res.experiment_id
    }

    currentPage.value = 1
    ElMessage.success(`生成完成：共${res.total_combinations}条组合，有效${res.filtered_combinations}条`)
  } catch (e: any) {
    ElMessage.error(e.message || '生成组合失败')
  } finally {
    generating.value = false
  }
}

// 导出
async function handleExport(format: string) {
  if (!store.experimentId) {
    ElMessage.warning('请先保存试验后再导出')
    return
  }
  try {
    const res: any = await exportCombinations(store.experimentId, format)
    const blob = res.data || res
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `combinations_${store.experimentId}.${format}`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (e: any) {
    ElMessage.error(e.message || '导出失败')
  }
}
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.stats-row {
  display: flex;
  gap: 40px;
  margin-bottom: 20px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
  flex-wrap: wrap;
}

.combination-table-wrapper {
  margin-top: 16px;
  overflow-x: auto;
}

.table-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 8px;
}

.actions-left {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.actions-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.na-value {
  color: #c0c4cc;
  font-style: italic;
}

.editable-cell {
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 2px;
}

.editable-cell:hover {
  background: #ecf5ff;
}

.edit-cell {
  width: 100%;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

/* 平板 */
@media (max-width: 1024px) {
  .stats-row {
    gap: 24px;
  }
}

/* 手机 */
@media (max-width: 768px) {
  .stats-row {
    gap: 16px;
    padding: 12px;
  }

  .table-actions {
    flex-direction: column;
    align-items: flex-start;
  }

  .pagination-wrapper {
    justify-content: center;
  }
}
</style>
