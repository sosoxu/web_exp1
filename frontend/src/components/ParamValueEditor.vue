<template>
  <div class="param-value-editor">
    <div class="values-display">
      <template v-if="param.type_val === 'SINGLE'">
        <el-tag v-for="(v, i) in values" :key="i" class="value-tag" closable @close="removeValue(i)">
          {{ v }}
        </el-tag>
        <el-button size="small" @click="addSingleValue">添加值</el-button>
      </template>

      <template v-else-if="param.type_val === 'SELECT'">
        <el-tag v-for="(v, i) in values" :key="i" class="value-tag" closable @close="removeValue(i)">
          {{ v }}
        </el-tag>
        <el-button size="small" @click="addSelectValue">添加选项</el-button>
      </template>

      <template v-else-if="param.type_val === 'VECTOR'">
        <div v-for="(arr, i) in values" :key="i" class="array-item">
          <span class="array-label">第{{ i + 1 }}组:</span>
          <el-tag closable @close="removeValue(i)" class="value-tag">
            [{{ Array.isArray(arr) ? arr.join(', ') : arr }}]
          </el-tag>
        </div>
        <el-button size="small" @click="addVectorValue">添加组</el-button>
      </template>

      <template v-else-if="param.type_val === 'MATRIX' || param.type_val === 'MMATRIX'">
        <div v-for="(arr, i) in values" :key="i" class="array-item">
          <span class="array-label">第{{ i + 1 }}组:</span>
          <el-tag closable @close="removeValue(i)" class="value-tag">
            [{{ Array.isArray(arr) ? arr.join(', ') : arr }}]
          </el-tag>
        </div>
        <el-button size="small" @click="addMatrixValue">添加组</el-button>
      </template>
    </div>

    <!-- 编辑对话框 -->
    <el-dialog v-model="editDialogVisible" :title="editDialogTitle" width="500px">
      <el-form label-width="80px">
        <el-form-item label="值">
          <el-input v-model="editValue" placeholder="输入值，多个值用逗号分隔" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmEdit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { Param } from '../types'

const props = defineProps<{
  param: Param
  moduleName: string
  values: any[]
}>()

const emit = defineEmits(['update'])

const editDialogVisible = ref(false)
const editValue = ref('')
const editMode = ref<'single' | 'select' | 'vector' | 'matrix'>('single')
const editDialogTitle = computed(() => {
  const map: Record<string, string> = {
    single: '添加单一值',
    select: '添加选项值',
    vector: '添加数组组',
    matrix: '添加矩阵组'
  }
  return map[editMode.value] || '添加值'
})

function removeValue(index: number) {
  const newValues = [...props.values]
  newValues.splice(index, 1)
  emit('update', newValues)
}

function addSingleValue() {
  editMode.value = 'single'
  editValue.value = ''
  editDialogVisible.value = true
}

function addSelectValue() {
  editMode.value = 'select'
  editValue.value = ''
  editDialogVisible.value = true
}

function addVectorValue() {
  editMode.value = 'vector'
  editValue.value = ''
  editDialogVisible.value = true
}

function addMatrixValue() {
  editMode.value = 'matrix'
  editValue.value = ''
  editDialogVisible.value = true
}

function confirmEdit() {
  const newValues = [...props.values]
  const input = editValue.value.trim()

  if (editMode.value === 'single') {
    // 尝试类型转换
    let val: any = input
    if (props.param.vtype.toLowerCase() === 'int') {
      val = parseInt(input)
    } else if (['float', 'double'].includes(props.param.vtype.toLowerCase())) {
      val = parseFloat(input)
    }
    newValues.push(val)
  } else if (editMode.value === 'select') {
    newValues.push(input)
  } else if (editMode.value === 'vector') {
    // 解析为数组
    const arr = input.split(',').map(s => {
      s = s.trim()
      if (props.param.vtype.toLowerCase() === 'int') return parseInt(s)
      if (['float', 'double'].includes(props.param.vtype.toLowerCase())) return parseFloat(s)
      return s
    })
    newValues.push(arr)
  } else if (editMode.value === 'matrix') {
    // 解析为扁平数组
    const arr = input.split(',').map(s => {
      s = s.trim()
      if (props.param.type_val === 'MMATRIX') return s
      if (props.param.vtype.toLowerCase() === 'int') return parseInt(s)
      if (['float', 'double'].includes(props.param.vtype.toLowerCase())) return parseFloat(s)
      return s
    })
    newValues.push(arr)
  }

  emit('update', newValues)
  editDialogVisible.value = false
}
</script>

<style scoped>
.values-display {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.value-tag {
  max-width: 400px;
}

.array-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.array-label {
  font-size: 13px;
  color: #606266;
  white-space: nowrap;
}
</style>
