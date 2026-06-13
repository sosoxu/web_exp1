<template>
  <el-card>
    <template #header>
      <div class="card-header">
        <span>选择模块和参数</span>
        <div>
          <el-button @click="$emit('prev')">上一步</el-button>
          <el-button type="primary" @click="handleNext" :disabled="store.selectedParams.length === 0">下一步</el-button>
        </div>
      </div>
    </template>

    <el-alert
      v-if="store.selectedParams.length >= 10"
      title="已选择10个参数，建议不超过10个参数以保证组合数量可控"
      type="warning"
      :closable="false"
      show-icon
      style="margin-bottom: 12px"
    />

    <el-row :gutter="20">
      <!-- 模块搜索与列表 -->
      <el-col :span="8">
        <div class="section-title">模块列表</div>
        <el-input v-model="moduleKeyword" placeholder="搜索模块名称" clearable @input="searchModules" style="margin-bottom: 12px">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <div class="module-list" v-loading="modulesLoading">
          <div
            v-for="mod in modules"
            :key="mod.id"
            class="module-item"
            :class="{
              active: selectedModuleId === mod.id,
              'has-params': getModuleParamCount(mod.name) > 0
            }"
            @click="selectModule(mod)"
          >
            <span class="module-name">{{ mod.name }}</span>
            <div class="module-meta">
              <el-tag v-if="getModuleParamCount(mod.name) > 0" size="small" type="success">
                已选{{ getModuleParamCount(mod.name) }}
              </el-tag>
              <el-tag size="small" type="info">{{ mod.param_count }}个参数</el-tag>
            </div>
          </div>
          <el-empty v-if="modules.length === 0 && !modulesLoading" description="暂无模块" />
        </div>
        <el-pagination
          v-model:current-page="modulePage"
          :page-size="20"
          :total="moduleTotal"
          layout="prev, pager, next"
          small
          @current-change="loadModules"
          style="margin-top: 10px"
        />
      </el-col>

      <!-- 参数列表 -->
      <el-col :span="16">
        <div class="section-title">
          {{ currentModuleName ? `${currentModuleName} - 参数列表` : '请先选择模块' }}
        </div>
        <div class="param-list" v-loading="paramsLoading">
          <el-table
            ref="paramTableRef"
            :data="params"
            stripe
            size="small"
            @selection-change="handleParamSelect"
            row-key="id"
          >
            <el-table-column type="selection" width="40" :selectable="() => store.selectedParams.length < 10 || isRowSelected(arguments[0])" />
            <el-table-column prop="name" label="参数名" min-width="120" />
            <el-table-column prop="display" label="显示名" min-width="150" show-overflow-tooltip />
            <el-table-column label="类型" width="100">
              <template #default="{ row }">
                <el-tag size="small">{{ row.type_val }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="数值类型" width="80">
              <template #default="{ row }">
                <span>{{ row.vtype }}</span>
              </template>
            </el-table-column>
            <el-table-column label="范围/尺寸" min-width="140" show-overflow-tooltip>
              <template #default="{ row }">
                <span v-if="row.type_val === 'VECTOR' && row.col">长度: {{ row.col }}</span>
                <span v-else-if="row.type_val === 'MATRIX' && row.row_val && row.col">{{ row.row_val }} x {{ row.col }}</span>
                <span v-else-if="row.type_val === 'MMATRIX' && row.row_val">{{ row.row_val }}行</span>
                <span v-else-if="row.min_val || row.max_val">{{ row.min_val || '-∞' }} ~ {{ row.max_val || '∞' }}</span>
                <span v-else-if="row.select_items">{{ row.select_items }}</span>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column prop="default_val" label="默认值" width="80" show-overflow-tooltip />
          </el-table>
        </div>

        <!-- 已选参数 - 按模块分组 -->
        <div class="selected-params" v-if="store.selectedParams.length > 0">
          <div class="section-title">
            已选参数 ({{ store.selectedParams.length }}/10)
            <el-button type="danger" size="small" text @click="clearAllParams" style="margin-left: 8px">清空全部</el-button>
          </div>
          <div v-for="group in groupedParams" :key="group.moduleName" class="param-group">
            <div class="group-header">
              <el-tag type="primary" size="small">{{ group.moduleName }}</el-tag>
              <span class="group-count">{{ group.params.length }}个参数</span>
              <el-button type="danger" size="small" text @click="removeModuleParams(group.moduleName)">移除</el-button>
            </div>
            <div class="tag-list">
              <el-tag
                v-for="sp in group.params"
                :key="`${sp.module_name}.${sp.param.name}`"
                closable
                @close="store.removeParam(sp.module_name, sp.param.name); restoreTableSelection()"
                class="param-tag"
              >
                {{ sp.param.name }}
                <span class="tag-type">({{ sp.param.type_val }}/{{ sp.param.vtype }})</span>
              </el-tag>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>
  </el-card>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useExperimentStore } from '../stores/experiment'
import { getModules, getModuleParams } from '../api/modules'
import type { Module, Param } from '../types'

const emit = defineEmits(['next', 'prev'])
const store = useExperimentStore()

const modules = ref<Module[]>([])
const modulesLoading = ref(false)
const moduleKeyword = ref('')
const modulePage = ref(1)
const moduleTotal = ref(0)
const selectedModuleId = ref<number | null>(null)
const currentModuleName = ref('')

const params = ref<Param[]>([])
const paramsLoading = ref(false)
const paramTableRef = ref<any>(null)

// 按模块分组的已选参数
const groupedParams = computed(() => {
  const groups: Record<string, { moduleName: string; params: typeof store.selectedParams }> = {}
  for (const sp of store.selectedParams) {
    if (!groups[sp.module_name]) {
      groups[sp.module_name] = { moduleName: sp.module_name, params: [] }
    }
    groups[sp.module_name].params.push(sp)
  }
  return Object.values(groups)
})

// 获取某模块已选参数数量
function getModuleParamCount(moduleName: string): number {
  return store.selectedParams.filter(sp => sp.module_name === moduleName).length
}

// 判断行是否已被选中（用于限制10个参数时的selectable）
function isRowSelected(row: Param): boolean {
  if (!currentModuleName.value) return false
  return store.selectedParams.some(
    sp => sp.module_name === currentModuleName.value && sp.param.name === row.name
  )
}

async function loadModules() {
  modulesLoading.value = true
  try {
    const res: any = await getModules({
      keyword: moduleKeyword.value || undefined,
      page: modulePage.value,
      page_size: 20
    })
    modules.value = res.items || []
    moduleTotal.value = res.total || 0
  } catch (e: any) {
    ElMessage.error(e.message || '加载模块失败')
  } finally {
    modulesLoading.value = false
  }
}

function searchModules() {
  modulePage.value = 1
  loadModules()
}

async function selectModule(mod: Module) {
  selectedModuleId.value = mod.id
  currentModuleName.value = mod.name
  paramsLoading.value = true
  try {
    const res: any = await getModuleParams(mod.id)
    params.value = res || []
    // 等待表格渲染后恢复勾选状态
    await nextTick()
    restoreTableSelection()
  } catch (e: any) {
    ElMessage.error(e.message || '加载参数失败')
  } finally {
    paramsLoading.value = false
  }
}

// 恢复当前模块参数表格的勾选状态
function restoreTableSelection() {
  if (!paramTableRef.value) return
  const table = paramTableRef.value
  table.clearSelection()
  for (const row of params.value) {
    const isSelected = store.selectedParams.some(
      sp => sp.module_name === currentModuleName.value && sp.param.name === row.name
    )
    if (isSelected) {
      table.toggleRowSelection(row, true)
    }
  }
}

function handleParamSelect(selection: Param[]) {
  if (!selectedModuleId.value) return

  // 检查是否超过10个参数上限
  const otherModuleParams = store.selectedParams.filter(
    sp => sp.module_name !== currentModuleName.value
  )
  if (selection.length + otherModuleParams.length > 10) {
    ElMessage.warning('参数总数不能超过10个')
    // 恢复到之前的状态
    nextTick(() => restoreTableSelection())
    return
  }

  // 添加新选中的参数
  for (const p of selection) {
    store.addParam({
      module_id: selectedModuleId.value!,
      module_name: currentModuleName.value,
      param: { ...p, module_name: currentModuleName.value }
    })
  }
  // 移除取消选中的参数
  const selectedKeys = new Set(selection.map(p => `${currentModuleName.value}.${p.name}`))
  for (const sp of store.selectedParams) {
    if (sp.module_name === currentModuleName.value && !selectedKeys.has(`${sp.module_name}.${sp.param.name}`)) {
      store.removeParam(sp.module_name, sp.param.name)
    }
  }
}

function removeModuleParams(moduleName: string) {
  const moduleParams = store.selectedParams.filter(sp => sp.module_name === moduleName)
  for (const sp of moduleParams) {
    store.removeParam(sp.module_name, sp.param.name)
  }
  // 如果当前正在查看该模块，刷新勾选状态
  if (currentModuleName.value === moduleName) {
    nextTick(() => restoreTableSelection())
  }
}

function clearAllParams() {
  // 逐个移除以触发store的响应式更新
  const allParams = [...store.selectedParams]
  for (const sp of allParams) {
    store.removeParam(sp.module_name, sp.param.name)
  }
  nextTick(() => restoreTableSelection())
}

function handleNext() {
  emit('next')
}

onMounted(loadModules)
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-title {
  font-weight: 600;
  margin-bottom: 12px;
  color: #303133;
  display: flex;
  align-items: center;
}

.module-list {
  height: 500px;
  overflow-y: auto;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
}

.module-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  cursor: pointer;
  border-bottom: 1px solid #f0f0f0;
  transition: background 0.2s;
}

.module-item:hover {
  background: #f5f7fa;
}

.module-item.active {
  background: #ecf5ff;
  border-left: 3px solid #409eff;
}

.module-item.has-params {
  border-left: 3px solid #67c23a;
}

.module-item.active.has-params {
  border-left: 3px solid #409eff;
}

.module-name {
  font-weight: 500;
}

.module-meta {
  display: flex;
  gap: 4px;
  align-items: center;
}

.param-list {
  height: 300px;
  overflow-y: auto;
}

.selected-params {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #e4e7ed;
}

.param-group {
  margin-bottom: 12px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 6px;
}

.group-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.group-count {
  color: #909399;
  font-size: 13px;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.param-tag {
  max-width: 300px;
}

.tag-type {
  color: #909399;
  font-size: 12px;
  margin-left: 4px;
}
</style>
