<template>
  <div class="tech-panel schedule-compression">
    <div class="panel-header">
      <el-icon><Timer /></el-icon>
      <span>压缩工期</span>
    </div>

    <div class="compression-toggle">
      <el-checkbox v-model="form.enabled" class="checkbox-tech" size="small">
        启用压缩工期
      </el-checkbox>
    </div>

    <div class="constraint-section" :class="{ disabled: !form.enabled }">
      <div class="constraint-card compact">
        <div class="constraint-header">
          <span class="constraint-icon">💧</span>
          <span class="constraint-title">蓄水发电</span>
          <el-date-picker
            v-model="form.waterStorageDate"
            type="date"
            placeholder="蓄水日期"
            format="YYYY/MM/DD"
            value-format="YYYY-MM-DD"
            :disabled="!form.enabled"
            class="date-picker-inline"
          />
        </div>
        <div class="constraint-note">高程≤{{ form.waterStorageElevation }}m的仓面须在此之前完成</div>
      </div>

      <div class="constraint-card compact">
        <div class="constraint-header">
          <span class="constraint-icon">🏗️</span>
          <span class="constraint-title">完工日期</span>
          <el-date-picker
            v-model="form.completionDate"
            type="date"
            placeholder="完工日期"
            format="YYYY/MM/DD"
            value-format="YYYY-MM-DD"
            :disabled="!form.enabled"
            class="date-picker-inline"
          />
        </div>
        <div class="constraint-note">高程≥{{ form.waterStorageElevation }}m的仓面须在此之前完成</div>
      </div>
    </div>

    <div class="strategy-section" :class="{ disabled: !form.enabled }">
      <div class="section-title">压缩策略</div>

      <div class="strategy-item">
        <el-checkbox v-model="form.compressInterval" :disabled="!form.enabled" class="checkbox-tech" size="small">
          间歇时间压缩
        </el-checkbox>
        <div class="strategy-detail" v-if="form.compressInterval && form.enabled">
          <div class="detail-row">
            <label>压缩范围(天)</label>
            <div class="range-inputs">
              <el-input-number
                v-model="form.intervalMin"
                :min="7"
                :max="30"
                :step="1"
                :disabled="!form.enabled"
                controls-position="right"
                class="input-tech-sm"
              />
              <span class="range-sep">~</span>
              <el-input-number
                v-model="form.intervalMax"
                :min="7"
                :max="30"
                :step="1"
                :disabled="!form.enabled"
                controls-position="right"
                class="input-tech-sm"
              />
            </div>
          </div>
          <div class="detail-row">
            <label>压缩幅度(天)</label>
            <el-input-number
              v-model="form.intervalReduction"
              :min="1"
              :max="5"
              :step="1"
              :disabled="!form.enabled"
              controls-position="right"
              class="input-tech-sm"
            />
          </div>
        </div>
      </div>

      <div class="strategy-item">
        <el-checkbox v-model="form.criticalPathFirst" :disabled="!form.enabled" class="checkbox-tech" size="small">
          关键路径优先
        </el-checkbox>
        <div class="strategy-detail" v-if="form.criticalPathFirst && form.enabled">
          <div class="detail-row">
            <label>蓄水关键高程(m)</label>
            <el-input-number
              v-model="form.waterStorageElevation"
              :min="800"
              :max="1000"
              :step="5"
              :precision="0"
              :disabled="!form.enabled"
              controls-position="right"
              class="input-tech-sm"
            />
          </div>
        </div>
      </div>
    </div>

    <div class="compression-action">
      <el-button
        type="primary"
        :loading="isCompressing"
        :disabled="!form.enabled"
        @click="handleCompress"
        class="btn-compress"
        size="small"
      >
        <el-icon><CaretRight /></el-icon>
        {{ isCompressing ? '计算中...' : '执行压缩排仓' }}
      </el-button>
    </div>

    <div class="compression-result" v-if="compressionResult">
      <div class="result-item" :class="compressionResult.waterStorageOk ? 'ok' : 'fail'">
        <span class="result-label">蓄水发电</span>
        <span class="result-value">{{ compressionResult.waterStorageOk ? '✓' : '✗' }}</span>
      </div>
      <div class="result-item" :class="compressionResult.completionOk ? 'ok' : 'fail'">
        <span class="result-label">完工日期</span>
        <span class="result-value">{{ compressionResult.completionOk ? '✓' : '✗' }}</span>
      </div>
      <div class="result-item">
        <span class="result-label">节约</span>
        <span class="result-value highlight">{{ compressionResult.savedDays }}天</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Timer, CaretRight } from '@element-plus/icons-vue'

const props = defineProps<{
  isRunning: boolean
}>()

const emit = defineEmits(['start-compression'])

const isCompressing = ref(false)
const compressionResult = ref<any>(null)

const form = ref({
  enabled: false,
  waterStorageDate: '2028-10-01',
  waterStorageElevation: 920,
  completionDate: '2030-10-15',
  compressInterval: true,
  intervalMin: 14,
  intervalMax: 20,
  intervalReduction: 1,
  criticalPathFirst: true
})

const handleCompress = () => {
  if (!form.value.enabled) return
  isCompressing.value = true
  compressionResult.value = null

  emit('start-compression', {
    use_compression: true,
    water_storage_date: form.value.waterStorageDate?.replace(/-/g, '/'),
    water_storage_elevation: form.value.waterStorageElevation,
    completion_date: form.value.completionDate?.replace(/-/g, '/'),
    compress_interval: form.value.compressInterval,
    interval_min: form.value.intervalMin,
    interval_max: form.value.intervalMax,
    interval_reduction: form.value.intervalReduction,
    critical_path_first: form.value.criticalPathFirst
  })
}

const setCompressionResult = (result: any) => {
  compressionResult.value = result
  isCompressing.value = false
}

const setCompressing = (val: boolean) => {
  isCompressing.value = val
}

defineExpose({ setCompressionResult, setCompressing })
</script>

<style scoped lang="scss">
.schedule-compression {
  .compression-toggle {
    margin-bottom: 8px;
    padding-bottom: 8px;
    border-bottom: 1px solid rgba(0, 150, 255, 0.12);
  }

  .constraint-section {
    margin-bottom: 8px;

    &.disabled {
      opacity: 0.45;
      pointer-events: none;
    }

    .constraint-card {
      background: rgba(0, 150, 255, 0.04);
      border: 1px solid rgba(0, 200, 255, 0.12);
      border-radius: 8px;
      padding: 8px 10px;
      margin-bottom: 6px;
      transition: all 0.3s ease;

      &:hover {
        background: rgba(0, 150, 255, 0.07);
        border-color: rgba(0, 200, 255, 0.2);
      }

      &.compact {
        .constraint-header {
          display: flex;
          align-items: center;
          gap: 6px;
          margin-bottom: 4px;

          .constraint-icon {
            font-size: 12px;
            flex-shrink: 0;
          }

          .constraint-title {
            font-size: 12px;
            font-weight: 600;
            color: var(--text-primary);
            white-space: nowrap;
            flex-shrink: 0;
          }

          .date-picker-inline {
            flex: 1;
            min-width: 0;

            :deep(.el-input__wrapper) {
              background: rgba(6, 20, 50, 0.5) !important;
              border: 1px solid rgba(0, 150, 255, 0.2) !important;
              box-shadow: none !important;
              padding: 0 8px;
              height: 26px;
            }

            :deep(.el-input__inner) {
              font-size: 11px;
              color: var(--text-primary);
            }
          }
        }

        .constraint-note {
          font-size: 10px;
          color: var(--text-muted);
          line-height: 1.4;
        }
      }
    }
  }

  .strategy-section {
    margin-bottom: 8px;

    &.disabled {
      opacity: 0.45;
      pointer-events: none;
    }

    .section-title {
      font-size: 11px;
      font-weight: 600;
      color: var(--text-secondary);
      margin-bottom: 6px;
      padding-bottom: 4px;
      border-bottom: 1px solid rgba(0, 150, 255, 0.1);
      letter-spacing: 0.5px;
    }

    .strategy-item {
      margin-bottom: 6px;

      .strategy-detail {
        margin-top: 4px;
        margin-left: 22px;
        padding: 6px 8px;
        background: rgba(0, 150, 255, 0.04);
        border-radius: 6px;
        border: 1px solid rgba(0, 200, 255, 0.08);

        .detail-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 4px;

          &:last-child {
            margin-bottom: 0;
          }

          label {
            font-size: 10px;
            color: var(--text-secondary);
            white-space: nowrap;
            margin-right: 6px;
          }

          .range-inputs {
            display: flex;
            align-items: center;
            gap: 4px;

            .range-sep {
              color: var(--text-muted);
              font-size: 11px;
            }
          }
        }
      }
    }
  }

  .compression-action {
    margin-bottom: 8px;

    .btn-compress {
      width: 100%;
      height: 30px;
      font-size: 12px;
      font-weight: 600;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      border-radius: 8px;
      background: rgba(0, 150, 255, 0.08);
      border: 1px solid rgba(0, 200, 255, 0.25);
      color: var(--text-primary);
      backdrop-filter: blur(10px);
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

      &:hover:not(:disabled) {
        background: rgba(0, 200, 255, 0.15);
        border-color: var(--primary-cyan);
        color: var(--primary-cyan);
        box-shadow: 0 0 15px rgba(0, 200, 255, 0.2);
      }

      &:disabled {
        opacity: 0.4;
        cursor: not-allowed;
      }
    }
  }

  .compression-result {
    background: rgba(0, 150, 255, 0.05);
    border: 1px solid rgba(0, 200, 255, 0.15);
    border-radius: 8px;
    padding: 6px 10px;

    .result-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 2px 0;
      font-size: 11px;

      .result-label {
        color: var(--text-secondary);
      }

      .result-value {
        color: var(--text-primary);
        font-weight: 500;

        &.highlight {
          color: var(--primary-cyan);
          font-weight: 600;
        }
      }

      &.ok .result-value {
        color: var(--success-color);
      }

      &.fail .result-value {
        color: var(--danger-color);
      }
    }
  }

  .input-tech-sm {
    width: 85px;

    :deep(.el-input__wrapper) {
      background: rgba(6, 20, 50, 0.5) !important;
      border: 1px solid rgba(0, 150, 255, 0.2) !important;
      box-shadow: none !important;
      padding: 0 28px 0 8px;
      height: 26px;
    }

    :deep(.el-input__inner) {
      font-size: 12px;
      color: var(--text-primary);
      text-align: center;
    }

    // 调整右侧控制按钮位置和大小
    :deep(.el-input-number__decrease),
    :deep(.el-input-number__increase) {
      width: 22px;
      height: 12px;
      line-height: 12px;
      background: rgba(0, 100, 180, 0.3);
      border-color: rgba(0, 150, 255, 0.25);
      color: var(--text-secondary);
      font-size: 10px;

      &:hover {
        background: rgba(0, 150, 255, 0.4);
        color: var(--primary-cyan);
      }
    }

    :deep(.el-input-number__decrease) {
      bottom: 1px;
      right: 1px;
      top: auto;
      border-radius: 0 0 3px 0;
    }

    :deep(.el-input-number__increase) {
      top: 1px;
      right: 1px;
      border-radius: 0 3px 0 0;
    }
  }
}

@media (prefers-reduced-motion: reduce) {
  .schedule-compression {
    .btn-compress,
    .constraint-card {
      transition: none !important;
      transform: none !important;
    }
  }
}
</style>
