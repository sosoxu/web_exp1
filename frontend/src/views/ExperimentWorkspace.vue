<template>
  <el-container class="workspace-container">
    <el-header class="app-header">
      <div class="header-left">
        <el-button text @click="$router.push('/')"><el-icon><ArrowLeft /></el-icon> <span class="back-text">返回</span></el-button>
        <h1 class="app-title">{{ store.experimentName || '新建试验' }}</h1>
      </div>
      <div class="header-right">
        <el-button type="success" @click="handleSave" :loading="saving">
          <el-icon><Check /></el-icon> <span class="btn-text">保存</span>
        </el-button>
      </div>
    </el-header>

    <el-main class="page-container">
      <!-- 试验基本信息 -->
      <el-card class="section-card" v-if="currentStep === 0">
        <template #header>
          <span>试验信息</span>
        </template>
        <el-form :model="store" :label-width="isMobile ? '80px' : '100px'" label-position="top" :class="{ 'mobile-form': isMobile }">
          <el-form-item label="试验名称">
            <el-input v-model="store.experimentName" placeholder="请输入试验名称" />
          </el-form-item>
          <el-form-item label="试验描述">
            <el-input v-model="store.experimentDescription" type="textarea" :rows="2" placeholder="请输入试验描述（可选）" />
          </el-form-item>
        </el-form>
        <div class="form-actions">
          <el-button type="primary" @click="currentStep = 1" :disabled="!store.experimentName">下一步：选择参数</el-button>
        </div>
      </el-card>

      <!-- 步骤导航 -->
      <el-steps
        :active="currentStep - 1"
        finish-status="success"
        v-if="currentStep > 0"
        class="step-nav"
        :class="{ 'step-nav-simple': isMobile }"
        :direction="isMobile ? 'vertical' : 'horizontal'"
        simple
      >
        <el-step title="选择参数" :icon="isMobile ? undefined : undefined" />
        <el-step title="描述取值" />
        <el-step title="生成组合" />
      </el-steps>

      <!-- Step1: 选择模块和参数 -->
      <StepSelectParams v-if="currentStep === 1" @next="currentStep = 2" @prev="currentStep = 0" />

      <!-- Step2: 描述参数取值 -->
      <StepDescribeValues v-if="currentStep === 2" @next="currentStep = 3" @prev="currentStep = 1" />

      <!-- Step3: 生成组合表 -->
      <StepGenerateTable v-if="currentStep === 3" @prev="currentStep = 2" />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useExperimentStore } from '../stores/experiment'
import { createExperiment, saveExperimentConfig, getExperiment, getCombinations } from '../api/modules'
import type { SelectedParam, ParsedParamValue, ParsedConstraint } from '../types'
import StepSelectParams from '../components/StepSelectParams.vue'
import StepDescribeValues from '../components/StepDescribeValues.vue'
import StepGenerateTable from '../components/StepGenerateTable.vue'

const route = useRoute()
const store = useExperimentStore()
const currentStep = ref(0)
const saving = ref(false)

// 响应式检测
const windowWidth = ref(window.innerWidth)
const isMobile = computed(() => windowWidth.value <= 768)
function onResize() { windowWidth.value = window.innerWidth }
onMounted(async () => {
  window.addEventListener('resize', onResize)
  const id = route.params.id ? Number(route.params.id) : null

  // 新建试验时重置store
  if (!id) {
    store.reset()
    return
  }

  try {
    const res: any = await getExperiment(id)
    store.experimentId = res.id
    store.experimentName = res.name
    store.experimentDescription = res.description || ''

    // 恢复已选参数
    if (res.params && res.params.length > 0) {
      const restoredParams: SelectedParam[] = []
      const restoredValues: Record<string, ParsedParamValue> = {}

      for (const p of res.params) {
        const key = `${p.module_name}.${p.param_name}`

        // 从param_detail恢复完整参数信息，否则用基本信息构造
        const paramDetail = p.param_detail || {
          id: p.param_id,
          module_id: 0,
          name: p.param_name,
          type_val: p.type_val,
          vtype: p.vtype,
          col: null, row_val: null, min_val: null, max_val: null,
          default_val: null, select_items: null, cols_def: null,
          class_val: null, display: null, inmethod: null, uiname: null,
          no_val: null, autoexp: null, prec: null, border_value: null,
          default_rows: null, title_row: null, title_col: null,
          comment: null, module_name: p.module_name
        }

        // 查找module_id
        let moduleId = 0
        if (res.modules) {
          const mod = res.modules.find((m: any) => m.module_name === p.module_name)
          if (mod) moduleId = mod.module_id
        }

        restoredParams.push({
          module_id: moduleId,
          module_name: p.module_name,
          param: paramDetail
        })

        // 恢复参数取值
        if (p.parsed_values && p.parsed_values.length > 0) {
          restoredValues[key] = {
            module_name: p.module_name,
            param_name: p.param_name,
            values: p.parsed_values,
            value_type: p.raw_description || '',
            confidence: 1.0
          }
        }
      }

      store.selectedParams = restoredParams
      store.paramValues = restoredValues
      currentStep.value = 2
    }

    // 恢复约束
    if (res.constraints && res.constraints.length > 0) {
      store.customConstraints = res.constraints.map((c: any) => ({
        source_module: c.source_module,
        source_param: c.source_param,
        target_module: c.target_module,
        target_param: c.target_param,
        operator: c.operator,
        constraint_value: c.constraint_value,
        description: c.raw_description
      }))
    }

    // 恢复组合结果
    if (res.status === 'configured' || res.status === 'completed') {
      store.totalCombinations = res.total_combinations || 0
      store.filteredCombinations = res.filtered_combinations || 0
      currentStep.value = 3

      // 加载第一页组合数据
      try {
        const comboRes: any = await getCombinations(id, {
          page: 1,
          page_size: 50,
          is_valid: true
        })
        store.combinations = comboRes.items || []
      } catch {
        // 组合加载失败不影响页面
      }
    }
  } catch (e: any) {
    ElMessage.error(e.message || '加载试验失败')
  }
})
onUnmounted(() => { window.removeEventListener('resize', onResize) })

async function handleSave() {
  if (!store.experimentName) {
    ElMessage.warning('请输入试验名称')
    return
  }
  saving.value = true
  try {
    if (!store.experimentId) {
      const res: any = await createExperiment({
        name: store.experimentName,
        description: store.experimentDescription
      })
      store.experimentId = res.id
    }

    const modules = store.selectedParams.reduce((acc: any[], sp) => {
      if (!acc.find(m => m.module_id === sp.module_id)) {
        acc.push({ module_name: sp.module_name, module_id: sp.module_id })
      }
      return acc
    }, [])

    const params = store.selectedParams.map(sp => {
      const key = `${sp.module_name}.${sp.param.name}`
      const pv = store.paramValues[key]
      return {
        module_name: sp.module_name,
        param_name: sp.param.name,
        param_id: sp.param.id,
        type_val: sp.param.type_val,
        vtype: sp.param.vtype,
        raw_description: pv?.value_type || '',
        parsed_values: pv?.values || [],
        is_confirmed: !!pv
      }
    })

    const constraints = store.customConstraints.map(c => ({
      constraint_type: 'custom',
      source_module: c.source_module,
      source_param: c.source_param,
      target_module: c.target_module,
      target_param: c.target_param,
      operator: c.operator,
      constraint_value: c.constraint_value,
      raw_description: c.description
    }))

    await saveExperimentConfig(store.experimentId!, { modules, params, constraints })
    ElMessage.success('保存成功')
  } catch (e: any) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.workspace-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.workspace-container :deep(.el-main) {
  overflow-y: auto;
  flex: 1;
}

.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 20px;
  height: 60px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.app-title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.step-nav {
  margin-bottom: 24px;
}

.section-card {
  margin-bottom: 20px;
}

.form-actions {
  text-align: right;
}

@media (max-width: 768px) {
  .app-header {
    padding: 0 12px;
    height: 50px;
  }

  .app-title {
    font-size: 15px;
  }

  .back-text {
    display: none;
  }

  .btn-text {
    display: none;
  }

  .step-nav {
    margin-bottom: 16px;
  }

  .form-actions {
    text-align: center;
  }

  .mobile-form :deep(.el-form-item__label) {
    padding-bottom: 4px;
  }
}
</style>
