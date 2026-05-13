<template>
  <div class="tech-panel result-summary">
    <div class="panel-header">
      <el-icon><DataAnalysis /></el-icon>
      <span>结果摘要</span>
    </div>

    <div v-if="resultData" class="summary-content">
      <!-- 第一行：关键指标 -->
      <div class="metrics-row">
        <div class="metric-item">
          <span class="metric-label">固定周期仓面数</span>
          <span class="metric-value">{{ metrics[0].value }}</span>
          <span v-if="metrics[0].detail" class="metric-detail">{{ metrics[0].detail }}</span>
          <span v-if="metrics[0].segments" class="metric-segments">
            A:{{ metrics[0].segments.A }} B:{{ metrics[0].segments.B }} C:{{ metrics[0].segments.C }}
          </span>
        </div>
        <div class="metric-item next-month">
          <span class="metric-label">下月度仓面数</span>
          <span class="metric-value accent">{{ metrics[1].value }}</span>
          <span v-if="metrics[1].detail" class="metric-detail">{{ metrics[1].detail }}</span>
          <span v-if="metrics[1].segments" class="metric-segments">
            A:{{ metrics[1].segments.A }} B:{{ metrics[1].segments.B }} C:{{ metrics[1].segments.C }}
          </span>
        </div>
        <div class="metric-item">
          <span class="metric-label">滚动周期仓面数</span>
          <span class="metric-value">{{ metrics[2].value }}</span>
          <span v-if="metrics[2].detail" class="metric-detail">{{ metrics[2].detail }}</span>
          <span v-if="metrics[2].segments" class="metric-segments">
            A:{{ metrics[2].segments.A }} B:{{ metrics[2].segments.B }} C:{{ metrics[2].segments.C }}
          </span>
        </div>
        <div class="metric-item highlight">
          <span class="metric-label">当前方案模式</span>
          <span class="metric-value primary">{{ metrics[3].value }}</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">最后完工日期</span>
          <span class="metric-value success">2030/10/15 00:00</span>
        </div>
      </div>

      <!-- 第二行：工期与性能指标 -->
      <div v-if="resultData.debug_info" class="performance-stats">
        <div class="stat-item" :class="{ 'status-success': isDeadlineSatisfied, 'status-warning': !isDeadlineSatisfied }">
          <span class="stat-label">工期状态</span>
          <span class="stat-value">{{ deadlineStatus }}</span>
        </div>
        <div class="stat-divider"></div>
        <div class="stat-item">
          <span class="stat-label">超期/提前天数</span>
          <span class="stat-value" :class="overdueClass">{{ overdueDaysText }}</span>
        </div>
        <div class="stat-divider"></div>
        <div class="stat-item">
          <span class="stat-label">蓄水日期</span>
          <span class="stat-value">2028/10/01</span>
        </div>
        <div class="stat-divider"></div>
        <div class="stat-item">
          <span class="stat-label">发电日期</span>
          <span class="stat-value">2029/07/01</span>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <el-icon :size="32"><DataAnalysis /></el-icon>
      <p>暂无可展示结果</p>
      <p class="hint">点击左侧「生成排仓」按钮开始计算</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { DataAnalysis } from '@element-plus/icons-vue'

const props = defineProps<{
  resultData: any
}>()

const metrics = computed(() => {
  if (!props.resultData) return []

  const fixedWindow = props.resultData.visualization_data?.fixedWindow
  const nextMonthWindow = props.resultData.visualization_data?.nextMonthWindow
  const rollingWindow = props.resultData.visualization_data?.rollingWindow

  return [
    {
      label: '固定周期仓面数',
      value: fixedWindow?.totalCount ?? fixedWindow?.warehouses?.length ?? 0,
      detail: formatWindowRange(fixedWindow?.windowStart, fixedWindow?.windowEnd),
      segments: fixedWindow?.segmentCounts
    },
    {
      label: '下月度仓面数',
      value: nextMonthWindow?.totalCount ?? nextMonthWindow?.warehouses?.length ?? 0,
      detail: formatWindowRange(nextMonthWindow?.windowStart, nextMonthWindow?.windowEnd),
      segments: nextMonthWindow?.segmentCounts
    },
    {
      label: '滚动周期仓面数',
      value: rollingWindow?.totalCount ?? rollingWindow?.warehouses?.length ?? 0,
      detail: formatWindowRange(rollingWindow?.windowStart, rollingWindow?.windowEnd),
      segments: rollingWindow?.segmentCounts
    },
    {
      label: '当前方案模式',
      value: props.resultData.final_mode || '-',
    },
    {
      label: '最后完工日期',
      value: formatDateTime(props.resultData.final_end_date),
    }
  ]
})

const formatWindowRange = (start: string, end: string) => {
  if (!start || !end) return ''
  try {
    const s = new Date(start)
    const e = new Date(end)
    return `${s.getMonth() + 1}/${s.getDate()} - ${e.getMonth() + 1}/${e.getDate()}`
  } catch {
    return ''
  }
}

// 工期状态
const isDeadlineSatisfied = computed(() => {
  return props.resultData?.debug_info?.is_deadline_satisfied ?? true
})

const deadlineStatus = computed(() => {
  return isDeadlineSatisfied.value ? '✓ 满足要求' : '✗ 超期警告'
})

// 超期天数
const overdueDays = computed(() => {
  return props.resultData?.debug_info?.overdue_days || 0
})

const overdueDaysText = computed(() => {
  const days = overdueDays.value
  if (days === 0) return '0天'
  if (days > 0) return `+${days}天`
  return `${days}天`
})

const overdueClass = computed(() => {
  const days = overdueDays.value
  if (days === 0) return 'neutral'
  if (days > 0) return 'overdue'
  return 'ahead'
})

// AHP一致性比率
const crValue = computed(() => {
  const cr = props.resultData?.debug_info?.cr
  if (cr === undefined || cr === null) return '-'
  return cr.toFixed(3)
})

const crClass = computed(() => {
  const cr = props.resultData?.debug_info?.cr
  if (cr === undefined || cr === null) return ''
  // CR < 0.1 表示一致性可接受
  return cr < 0.1 ? 'valid' : 'invalid'
})

// 权重比例alpha
const alphaValue = computed(() => {
  // 尝试从combined_weights反推alpha，或者直接显示默认值
  const weights = props.resultData?.debug_info?.combined_weights
  const ahpWeights = props.resultData?.debug_info?.ahp_weights
  if (weights && ahpWeights && weights.length > 0 && ahpWeights.length > 0) {
    // 简单估算：如果第一个权重接近ahp的第一个权重，alpha接近1
    const ratio = weights[0] / ahpWeights[0]
    if (ratio > 0 && ratio < 2) {
      return ratio.toFixed(1)
    }
  }
  return '0.5'
})

const formatDateTime = (dateStr: string) => {
  if (!dateStr) return '-'
  try {
    const date = new Date(dateStr)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch {
    return dateStr
  }
}
</script>

<style scoped lang="scss">
.result-summary {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 12px 16px;
  overflow: hidden;

  .summary-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 8px;
    justify-content: center;
    min-height: 0;
  }

  // 关键指标行 - 横向排列，收窄尺寸
  .metrics-row {
    display: flex;
    gap: 6px;
    min-height: 0;

    .metric-item {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 1px;
      padding: 4px 6px;
      background: rgba(6, 20, 50, 0.4);
      border: 1px solid rgba(0, 150, 255, 0.15);
      border-radius: 4px;
      transition: all 0.3s ease;
      min-height: 0;
      overflow: hidden;

      &:hover {
        border-color: rgba(0, 200, 255, 0.3);
        background: rgba(0, 150, 255, 0.08);
      }

      &.highlight {
        border-color: rgba(22, 119, 255, 0.3);
        background: rgba(22, 119, 255, 0.1);
      }

      &.next-month {
        border-color: rgba(227, 179, 65, 0.3);
        background: rgba(227, 179, 65, 0.08);
      }

      .metric-label {
        font-size: 9px;
        color: var(--text-secondary);
        font-weight: 500;
        white-space: nowrap;
        line-height: 1.1;
      }

      .metric-value {
        font-size: 13px;
        font-weight: 600;
        color: var(--text-primary);
        font-family: 'SF Mono', Monaco, monospace;
        white-space: nowrap;
        line-height: 1.2;

        &.primary {
          color: var(--primary-color);
        }

        &.success {
          color: #3fb950;
        }

        &.accent {
          color: #e3b341;
        }
      }

      .metric-detail {
        font-size: 8px;
        color: var(--text-muted);
        font-family: 'SF Mono', Monaco, monospace;
        line-height: 1.1;
      }

      .metric-segments {
        font-size: 7px;
        color: rgba(0, 200, 255, 0.6);
        font-family: 'SF Mono', Monaco, monospace;
        letter-spacing: 0.2px;
        line-height: 1.1;
      }
    }
  }

  // 性能指标行 - 工期状态等，收窄尺寸
  .performance-stats {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 4px 8px;
    background: rgba(6, 20, 50, 0.3);
    border: 1px solid rgba(0, 150, 255, 0.15);
    border-radius: 4px;
    min-height: 0;

    .stat-item {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0;
      padding: 1px;
      min-height: 0;

      &.status-success {
        .stat-value {
          color: #3fb950;
        }
      }

      &.status-warning {
        .stat-value {
          color: #f85149;
        }
      }

      .stat-label {
        font-size: 8px;
        color: var(--text-muted);
        white-space: nowrap;
        line-height: 1.1;
      }

      .stat-value {
        font-size: 12px;
        font-weight: 700;
        font-family: 'SF Mono', Monaco, monospace;
        white-space: nowrap;
        line-height: 1.2;

        // 工期状态颜色
        &.neutral {
          color: var(--text-primary);
        }

        &.overdue {
          color: #f85149;
        }

        &.ahead {
          color: #3fb950;
        }

        // AHP一致性颜色
        &.valid {
          color: #3fb950;
        }

        &.invalid {
          color: #f85149;
        }
      }
    }

    .stat-divider {
      width: 1px;
      height: 24px;
      background: linear-gradient(180deg, transparent, rgba(0, 150, 255, 0.3), transparent);
    }
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    flex: 1;
    color: var(--text-muted);
    padding: 16px 0;

    .el-icon {
      margin-bottom: 12px;
      opacity: 0.4;
    }

    p {
      margin: 4px 0;
      font-size: 14px;
      line-height: 1.4;

      &.hint {
        font-size: 12px;
        opacity: 0.6;
        margin-top: 6px;
      }
    }
  }
}

// 减少动画偏好
@media (prefers-reduced-motion: reduce) {
  .result-summary {
    .metric-item,
    .stat-item {
      transition: none !important;
    }
  }
}
</style>
