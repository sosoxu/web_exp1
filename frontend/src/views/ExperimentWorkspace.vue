<template>
  <el-container>
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
import { createExperiment, saveExperimentConfig, getExperiment } from '../api/modules'
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
onMounted(() => {
  window.addEventListener('resize', onResize)
  const id = route.params.id ? Number(route.params.id) : null
  if (id) {
    getExperiment(id).then((res: any) => {
      store.experimentId = res.id
      store.experimentName = res.name
      store.experimentDescription = res.description || ''
      if (res.params && res.params.length > 0) currentStep.value = 2
      if (res.status === 'configured') currentStep.value = 3
    }).catch((e: any) => {
      ElMessage.error(e.message || '加载试验失败')
    })
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
