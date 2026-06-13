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
            :class="{ active: selectedModuleId === mod.id }"
            @click="selectModule(mod)"
          >
            <span class="module-name">{{ mod.name }}</span>
            <el-tag size="small" type="info">{{ mod.param_count }}个参数</el-tag>
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
          <el-table :data="params" stripe size="small" @selection-change="handleParamSelect" ref="paramTableRef">
            <el-table-column type="selection" width="40" />
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
            <el-table-column label="范围" min-width="120" show-overflow-tooltip>
              <template #default="{ row }">
                <span v-if="row.min_val || row.max_val">{{ row.min_val || '-∞' }} ~ {{ row.max_val || '∞' }}</span>
                <span v-else-if="row.select_items">{{ row.select_items }}</span>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column prop="default_val" label="默认值" width="80" show-overflow-tooltip />
          </el-table>
        </div>

        <!-- 已选参数 -->
        <div class="selected-params" v-if="store.selectedParams.length > 0">
          <div class="section-title">已选参数 ({{ store.selectedParams.length }})</div>
          <div class="tag-list">
            <el-tag
              v-for="sp in store.selectedParams"
              :key="`${sp.module_name}.${sp.param.name}`"
              closable
              @close="store.removeParam(sp.module_name, sp.param.name)"
              class="param-tag"
            >
              {{ sp.module_name }}.{{ sp.param.name }}
              <span class="tag-type">({{ sp.param.type_val }}/{{ sp.param.vtype }})</span>
            </el-tag>
          </div>
        </div>
      </el-col>
    </el-row>
  </el-card>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
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
  } catch (e: any) {
    ElMessage.error(e.message || '加载参数失败')
  } finally {
    paramsLoading.value = false
  }
}

function handleParamSelect(selection: Param[]) {
  // 添加新选中的参数
  for (const p of selection) {
    if (!selectedModuleId.value) continue
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

.module-name {
  font-weight: 500;
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
