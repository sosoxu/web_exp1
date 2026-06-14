export interface Module {
  id: number
  name: string
  version: string | null
  module_type: string | null
  data_transfer: string | null
  source_file: string | null
  param_count: number
}

export interface Dependency {
  id: number
  parameter_id: number
  param_name: string | null
  module_id: number | null
  module_name: string | null
  deparent: string
  interoper: string
  dep_values: string | null
}

export interface Param {
  id: number
  module_id: number
  name: string
  class_val: string | null
  display: string | null
  inmethod: string | null
  uiname: string | null
  no_val: string | null
  autoexp: string | null
  col: number | null
  vtype: string
  type_val: string
  row_val: number | null
  prec: number | null
  border_value: string | null
  max_val: string | null
  min_val: string | null
  default_val: string | null
  default_rows: string | null
  select_items: string | null
  cols_def: string | null
  title_row: string | null
  title_col: string | null
  comment: string | null
  module_name: string | null
  dependencies: Dependency[]
}

export interface SelectedParam {
  module_id: number
  module_name: string
  param: Param
}

export interface ParsedParamValue {
  module_name: string
  param_name: string
  values: any[]
  value_type: string | null
  confidence: number
}

export interface ParsedConstraint {
  source_module: string | null
  source_param: string | null
  target_module: string | null
  target_param: string | null
  operator: string
  constraint_value: any
  description: string | null
}

export interface CombinationItem {
  index: number
  combination_data: Record<string, any>
  is_valid: boolean
  invalid_reason: string | null
}

export interface Experiment {
  id: number
  name: string
  description: string | null
  status: string
  total_combinations: number
  filtered_combinations: number
  created_at: string | null
  updated_at: string | null
}
