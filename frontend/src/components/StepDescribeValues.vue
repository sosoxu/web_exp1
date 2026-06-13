<template>
  <el-card>
    <template #header>
      <div class="card-header">
        <span>描述参数取值</span>
        <div>
          <el-button @click="batchParse" :loading="batchParsing" :disabled="!hasAnyDescription" type="success">
            批量解析
          </el-button>
          <el-button @click="batchDefault">全部默认值</el-button>
          <el-button @click="$emit('prev')">上一步</el-button>
          <el-button type="primary" @click="handleNext" :disabled="!allParamsConfirmed">下一步</el-button>
        </div>
      </div>
    </template>

    <!-- 按模块分组显示参数取值描述 -->
    <div class="param-descriptions">
      <div v-for="group in groupedParams" :key="group.moduleName" class="module-group">
        <div class="module-group-header">
          <el-tag type="primary">{{ group.moduleName }}</el-tag>
          <span class="group-progress">{{ getGroupProgress(group) }}</span>
        </div>

        <div v-for="sp in group.params" :key="`${sp.module_name}.${sp.param.name}`" class="param-desc-item">
          <div class="param-info">
            <span class="param-key">{{ sp.param.name }}</span>
            <el-tag size="small" type="info">{{ sp.param.type_val }}</el-tag>
            <el-tag size="small">{{ sp.param.vtype }}</el-tag>
            <span class="param-range" v-if="sp.param.type_val === 'VECTOR' && sp.param.col">
              长度: {{ sp.param.col }}
            </span>
            <span class="param-range" v-if="sp.param.type_val === 'MATRIX' && sp.param.row_val && sp.param.col">
              大小: {{ sp.param.row_val }} x {{ sp.param.col }}
            </span>
            <span class="param-range" v-if="sp.param.type_val === 'MMATRIX' && sp.param.row_val">
              行数: {{ sp.param.row_val }}<template v-if="sp.param.cols_def">, 列定义: {{ formatColsDef(sp.param.cols_def) }}</template>
            </span>
            <span class="param-range" v-if="sp.param.min_val || sp.param.max_val">
              范围: {{ sp.param.min_val || '-∞' }} ~ {{ sp.param.max_val || '∞' }}
            </span>
            <span class="param-range" v-if="sp.param.select_items">
              选项: {{ sp.param.select_items }}
            </span>
            <span class="param-range" v-if="sp.param.default_val">
              默认: {{ sp.param.default_val }}
            </span>
          </div>
          <div class="param-input-row">
            <el-input
              v-model="descriptions[`${sp.module_name}.${sp.param.name}`]"
              placeholder="用自然语言描述参数取值，如：取1到10，间隔为2"
              clearable
            />
            <el-button type="primary" @click="parseParam(sp)" :loading="parsingKey === `${sp.module_name}.${sp.param.name}`">
              解析
            </el-button>
            <el-button @click="useDefault(sp)">默认值</el-button>
          </div>

          <!-- 解析结果 -->
          <div v-if="store.paramValues[`${sp.module_name}.${sp.param.name}`]" class="parsed-result">
            <div class="result-header">
              <span class="result-label">解析结果：</span>
              <el-tag type="success" size="small">已解析</el-tag>
            </div>
            <ParamValueEditor
              :param="sp.param"
              :module-name="sp.module_name"
              :values="store.paramValues[`${sp.module_name}.${sp.param.name}`].values"
              @update="handleValueUpdate(sp, $event)"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- 约束条件 -->
    <el-divider>约束条件（可选）</el-divider>
    <div class="constraint-section">
      <el-input
        v-model="constraintDesc"
        type="textarea"
        :rows="2"
        placeholder="用自然语言描述参数间的约束，如：当module1.pb为Up时，module2.pa只能取1到5"
      />
      <el-button type="warning" @click="parseConstraint" :loading="parsingConstraint" style="margin-top: 8px">
        添加约束
      </el-button>

      <div v-if="store.customConstraints.length > 0" class="constraint-list">
        <div v-for="(c, idx) in store.customConstraints" :key="idx" class="constraint-item">
          <el-tag type="warning" closable @close="store.removeConstraint(idx)">
            {{ c.source_module }}.{{ c.source_param }} {{ c.operator }} {{ c.target_module }}.{{ c.target_param }}
            <span v-if="c.constraint_value !== null && c.constraint_value !== undefined"> (值: {{ c.constraint_value }})</span>
          </el-tag>
          <span class="constraint-desc">{{ c.description }}</span>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ref, computed, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { useExperimentStore } from '../stores/experiment'
import { parseParams, parseConstraints } from '../api/modules'
import ParamValueEditor from './ParamValueEditor.vue'
import type { SelectedParam } from '../types'

const emit = defineEmits(['next', 'prev'])
const store = useExperimentStore()

const descriptions = reactive<Record<string, string>>({})
const parsingKey = ref('')
const constraintDesc = ref('')
const parsingConstraint = ref(false)
const batchParsing = ref(false)

// 按模块分组
const groupedParams = computed(() => {
  const groups: Record<string, { moduleName: string; params: SelectedParam[] }> = {}
  for (const sp of store.selectedParams) {
    if (!groups[sp.module_name]) {
      groups[sp.module_name] = { moduleName: sp.module_name, params: [] }
    }
    groups[sp.module_name].params.push(sp)
  }
  return Object.values(groups)
})

// 是否有任何描述已输入
const hasAnyDescription = computed(() => {
  return Object.values(descriptions).some(d => d && d.trim())
})

const allParamsConfirmed = computed(() => {
  return store.selectedParams.every(sp => {
    const key = `${sp.module_name}.${sp.param.name}`
    return store.paramValues[key] && store.paramValues[key].values.length > 0
  })
})

// 获取模块分组中已解析的进度
function getGroupProgress(group: { moduleName: string; params: SelectedParam[] }): string {
  const confirmed = group.params.filter(sp => {
    const key = `${sp.module_name}.${sp.param.name}`
    return store.paramValues[key] && store.paramValues[key].values.length > 0
  }).length
  return `${confirmed}/${group.params.length} 已解析`
}

function formatColsDef(colsDef: string): string {
  try {
    const cols = JSON.parse(colsDef)
    if (Array.isArray(cols)) {
      return `${cols.length}列 (${cols.map((c: any) => c.vtype || c.type || '?').join(', ')})`
    }
    return colsDef
  } catch {
    return colsDef
  }
}

async function parseParam(sp: SelectedParam) {
  const key = `${sp.module_name}.${sp.param.name}`
  const desc = descriptions[key]
  if (!desc) {
    ElMessage.warning('请先输入参数取值描述')
    return
  }

  parsingKey.value = key
  try {
    const paramInfo = {
      module_name: sp.module_name,
      param_name: sp.param.name,
      type_val: sp.param.type_val,
      vtype: sp.param.vtype,
      min_val: sp.param.min_val,
      max_val: sp.param.max_val,
      default_val: sp.param.default_val,
      select_items: sp.param.select_items,
      cols_def: sp.param.cols_def,
      row_val: sp.param.row_val,
      col: sp.param.col,
      title_row: sp.param.title_row,
      title_col: sp.param.title_col
    }

    const res: any = await parseParams({
      params: [paramInfo],
      description: desc
    })

    if (res.parsed && res.parsed.length > 0) {
      store.setParamValue(key, res.parsed[0])
      ElMessage.success(`${sp.param.name} 解析成功`)
    } else {
      ElMessage.warning(`${sp.param.name} 未能解析出参数取值`)
    }
  } catch (e: any) {
    ElMessage.error(e.message || '解析失败')
  } finally {
    parsingKey.value = ''
  }
}

// 批量解析：将所有有描述但未解析的参数一起发给LLM
async function batchParse() {
  const unresolved = store.selectedParams.filter(sp => {
    const key = `${sp.module_name}.${sp.param.name}`
    const desc = descriptions[key]
    return desc && desc.trim() && !(store.paramValues[key] && store.paramValues[key].values.length > 0)
  })

  if (unresolved.length === 0) {
    ElMessage.info('没有需要解析的参数（请先输入描述）')
    return
  }

  batchParsing.value = true
  try {
    const paramInfos = unresolved.map(sp => ({
      module_name: sp.module_name,
      param_name: sp.param.name,
      type_val: sp.param.type_val,
      vtype: sp.param.vtype,
      min_val: sp.param.min_val,
      max_val: sp.param.max_val,
      default_val: sp.param.default_val,
      select_items: sp.param.select_items,
      cols_def: sp.param.cols_def,
      row_val: sp.param.row_val,
      col: sp.param.col,
      title_row: sp.param.title_row,
      title_col: sp.param.title_col
    }))

    // 构建合并的描述
    const descParts = unresolved.map(sp => {
      const key = `${sp.module_name}.${sp.param.name}`
      return `${sp.module_name}.${sp.param.name}: ${descriptions[key]}`
    })
    const combinedDesc = descParts.join('\n')

    const res: any = await parseParams({
      params: paramInfos,
      description: combinedDesc
    })

    if (res.parsed && res.parsed.length > 0) {
      let successCount = 0
      for (const parsed of res.parsed) {
        const key = `${parsed.module_name}.${parsed.param_name}`
        if (parsed.values && parsed.values.length > 0) {
          store.setParamValue(key, parsed)
          successCount++
        }
      }
      ElMessage.success(`批量解析完成：${successCount}/${unresolved.length} 个参数解析成功`)
    } else {
      ElMessage.warning('未能解析出任何参数取值')
    }
  } catch (e: any) {
    ElMessage.error(e.message || '批量解析失败')
  } finally {
    batchParsing.value = false
  }
}

// 批量设置默认值
function batchDefault() {
  for (const sp of store.selectedParams) {
    useDefault(sp, true)
  }
  ElMessage.success('已为所有参数设置默认值')
}

function useDefault(sp: SelectedParam, silent: boolean = false) {
  const key = `${sp.module_name}.${sp.param.name}`
  const p = sp.param

  if (p.type_val === 'SINGLE') {
    const defaultVal = p.default_val !== null && p.default_val !== undefined ? p.default_val : 0
    store.setParamValue(key, {
      module_name: sp.module_name,
      param_name: p.name,
      values: [defaultVal],
      value_type: '默认值',
      confidence: 1.0
    })
  } else if (p.type_val === 'SELECT') {
    const defaultVal = p.default_val || ''
    store.setParamValue(key, {
      module_name: sp.module_name,
      param_name: p.name,
      values: [defaultVal],
      value_type: '默认值',
      confidence: 1.0
    })
  } else if (p.default_rows) {
    try {
      const defaultRows = JSON.parse(p.default_rows)
      store.setParamValue(key, {
        module_name: sp.module_name,
        param_name: p.name,
        values: defaultRows,
        value_type: '默认值',
        confidence: 1.0
      })
    } catch {
      if (!silent) ElMessage.warning('默认值格式错误')
    }
  }
}

function handleValueUpdate(sp: SelectedParam, values: any[]) {
  const key = `${sp.module_name}.${sp.param.name}`
  const existing = store.paramValues[key]
  if (existing) {
    store.setParamValue(key, { ...existing, values })
  }
}

async function parseConstraint() {
  if (!constraintDesc.value) {
    ElMessage.warning('请输入约束条件描述')
    return
  }

  parsingConstraint.value = true
  try {
    const paramInfos = store.selectedParams.map(sp => ({
      module_name: sp.module_name,
      param_name: sp.param.name,
      type_val: sp.param.type_val,
      vtype: sp.param.vtype,
      select_items: sp.param.select_items
    }))

    const res: any = await parseConstraints({
      params: paramInfos,
      constraint_description: constraintDesc.value
    })

    if (res.constraints && res.constraints.length > 0) {
      for (const c of res.constraints) {
        store.addConstraint(c)
      }
      ElMessage.success(`添加了${res.constraints.length}条约束`)
      constraintDesc.value = ''
    } else {
      ElMessage.warning('未能解析出约束条件')
    }
  } catch (e: any) {
    ElMessage.error(e.message || '解析约束失败')
  } finally {
    parsingConstraint.value = false
  }
}

function handleNext() {
  emit('next')
}
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.param-descriptions {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.module-group {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 16px;
  background: #fafbfc;
}

.module-group-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #ebeef5;
}

.group-progress {
  color: #909399;
  font-size: 13px;
}

.param-desc-item {
  padding: 12px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  background: #fff;
  margin-bottom: 8px;
}

.param-desc-item:last-child {
  margin-bottom: 0;
}

.param-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.param-key {
  font-weight: 600;
  color: #303133;
}

.param-range {
  color: #909399;
  font-size: 13px;
}

.param-input-row {
  display: flex;
  gap: 8px;
}

.parsed-result {
  margin-top: 12px;
  padding: 12px;
  background: #f0f9eb;
  border-radius: 4px;
  border: 1px solid #e1f3d8;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.result-label {
  font-weight: 500;
  color: #67c23a;
}

.constraint-section {
  margin-top: 12px;
}

.constraint-list {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.constraint-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.constraint-desc {
  color: #909399;
  font-size: 13px;
}
</style>
