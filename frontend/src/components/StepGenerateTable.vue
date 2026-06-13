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
    <div v-if="store.combinations.length > 0" class="combination-table-wrapper">
      <div class="table-actions">
        <el-button type="success" size="small" @click="handleExport('csv')">
          <el-icon><Download /></el-icon> 导出CSV
        </el-button>
        <el-button type="success" size="small" @click="handleExport('xlsx')">
          <el-icon><Download /></el-icon> 导出Excel
        </el-button>
        <el-checkbox v-model="showOnlyValid" style="margin-left: 16px">仅显示有效组合</el-checkbox>
      </div>

      <el-table
        :data="displayCombinations"
        stripe
        border
        size="small"
        style="width: 100%"
        max-height="600"
      >
        <el-table-column prop="index" label="Index" width="80" fixed />
        <el-table-column
          v-for="key in paramKeys"
          :key="key"
          :label="key"
          min-width="150"
        >
          <template #default="{ row }">
            <span :class="{ 'na-value': row.combination_data[key] === 'N/A' }">
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
      </el-table>

      <div class="pagination-wrapper" v-if="store.totalCombinations > 100">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="filteredTotal"
          layout="total, prev, pager, next"
          @current-change="loadPage"
        />
      </div>
    </div>

    <el-empty v-else-if="!generating" description="请点击"生成组合"按钮" />
  </el-card>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useExperimentStore } from '../stores/experiment'
import { generateCombinations, getCombinations, exportCombinations } from '../api/modules'

const emit = defineEmits(['prev'])
const store = useExperimentStore()

const generating = ref(false)
const showOnlyValid = ref(true)
const currentPage = ref(1)
const pageSize = ref(50)

const paramKeys = computed(() => {
  if (store.combinations.length > 0) {
    return Object.keys(store.combinations[0].combination_data)
  }
  return store.selectedParams.map(sp => `${sp.module_name}.${sp.param.name}`)
})

const displayCombinations = computed(() => {
  let items = store.combinations
  if (showOnlyValid.value) {
    items = items.filter(c => c.is_valid)
  }
  return items
})

const filteredTotal = computed(() => {
  if (showOnlyValid.value) {
    return store.filteredCombinations
  }
  return store.totalCombinations
})

function formatValue(val: any) {
  if (val === 'N/A') return 'N/A'
  if (Array.isArray(val)) return `[${val.join(', ')}]`
  return String(val)
}

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

    ElMessage.success(`生成完成：共${res.total_combinations}条组合，有效${res.filtered_combinations}条`)
  } catch (e: any) {
    ElMessage.error(e.message || '生成组合失败')
  } finally {
    generating.value = false
  }
}

async function loadPage() {
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

async function handleExport(format: string) {
  if (!store.experimentId) {
    ElMessage.warning('请先保存试验')
    return
  }
  try {
    const res: any = await exportCombinations(store.experimentId, format)
    const blob = new Blob([res], {
      type: format === 'csv' ? 'text/csv' : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `combinations_${store.experimentId}.${format}`
    a.click()
    URL.revokeObjectURL(url)
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
}

.stats-row {
  display: flex;
  gap: 40px;
  margin-bottom: 20px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
}

.combination-table-wrapper {
  margin-top: 16px;
}

.table-actions {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
}

.na-value {
  color: #c0c4cc;
  font-style: italic;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
