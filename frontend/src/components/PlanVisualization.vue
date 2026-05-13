<template>
  <div class="tech-panel plan-visualization">
    <div class="panel-header">
      <el-icon><TrendCharts /></el-icon>
      <span>计划可视化</span>
    </div>
    
    <div v-if="vizData && vizData.available" class="viz-content">
      <div class="chart-tabs">
        <button 
          :class="['tab-item', { active: activeTab === 'fixed' }]"
          @click="activeTab = 'fixed'"
        >
          <span class="tab-text">固定周期-本月度</span>
          <span v-if="fixedWindowRange" class="tab-range">{{ fixedWindowRange }}</span>
          <span class="tab-indicator"></span>
        </button>
        <button 
          :class="['tab-item', { active: activeTab === 'nextMonth' }]"
          @click="activeTab = 'nextMonth'"
        >
          <span class="tab-text">固定周期-下月度</span>
          <span v-if="nextMonthWindowRange" class="tab-range">{{ nextMonthWindowRange }}</span>
          <span class="tab-indicator"></span>
        </button>
        <button 
          :class="['tab-item', { active: activeTab === 'rolling' }]"
          @click="activeTab = 'rolling'"
        >
          <span class="tab-text">滚动周期-三十天</span>
          <span v-if="rollingWindowRange" class="tab-range">{{ rollingWindowRange }}</span>
          <span class="tab-indicator"></span>
        </button>
      </div>
      
      <div class="chart-area">
        <div v-if="hasData" ref="chartRef" class="chart-container"></div>
        <div v-else class="chart-empty">
          <el-icon :size="32"><TrendCharts /></el-icon>
          <p>{{ emptyMessage }}</p>
          <p class="hint">请调整排仓日期范围或切换周期查看</p>
        </div>
        <div v-if="hasData" class="chart-footer">
          <div class="legend-items">
            <span class="legend-item">
              <span class="legend-block legend-poured"></span>已浇筑(A段)
            </span>
            <span class="legend-item">
              <span class="legend-block legend-planned"></span>计划浇筑(B/C段)
            </span>
            <span class="legend-separator">|</span>
            <span class="legend-text">灰色块内数字为仓号，彩色块内数字为浇筑序号</span>
          </div>
        </div>
      </div>
    </div>
    
    <div v-else class="empty-state">
      <el-icon :size="40"><TrendCharts /></el-icon>
      <p>暂无可视化数据</p>
      <p class="hint">运行排仓后将自动生成图表</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { TrendCharts } from '@element-plus/icons-vue'
import * as echarts from 'echarts'

const props = defineProps<{
  vizData: any
}>()

const activeTab = ref<'fixed' | 'nextMonth' | 'rolling'>('fixed')
const chartRef = ref<HTMLElement | null>(null)
let chartInstance: echarts.ECharts | null = null

const currentData = computed(() => {
  if (!props.vizData || !props.vizData.available) return null
  if (activeTab.value === 'fixed') return props.vizData.fixedWindow
  if (activeTab.value === 'nextMonth') return props.vizData.nextMonthWindow
  return props.vizData.rollingWindow
})

const hasData = computed(() => {
  return currentData.value && currentData.value.warehouses && currentData.value.warehouses.length > 0
})

const emptyMessage = computed(() => {
  if (activeTab.value === 'fixed') return '固定周期-本月度内无排仓数据'
  if (activeTab.value === 'nextMonth') return '固定周期-下月度内无排仓数据'
  return '滚动周期-三十天内无排仓数据'
})

const formatRange = (start: string, end: string) => {
  if (!start || !end) return ''
  try {
    const s = new Date(start)
    const e = new Date(end)
    const fmt = (d: Date) => `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, '0')}.${String(d.getDate()).padStart(2, '0')}`
    return `${fmt(s)} - ${fmt(e)}`
  } catch {
    return ''
  }
}

const fixedWindowRange = computed(() => {
  if (!props.vizData?.fixedWindow) return ''
  return formatRange(props.vizData.fixedWindow.windowStart, props.vizData.fixedWindow.windowEnd)
})

const nextMonthWindowRange = computed(() => {
  if (!props.vizData?.nextMonthWindow) return ''
  return formatRange(props.vizData.nextMonthWindow.windowStart, props.vizData.nextMonthWindow.windowEnd)
})

const rollingWindowRange = computed(() => {
  if (!props.vizData?.rollingWindow) return ''
  return formatRange(props.vizData.rollingWindow.windowStart, props.vizData.rollingWindow.windowEnd)
})

const getPlannedColor = (order: number, maxOrder: number) => {
  const t = maxOrder > 1 ? (order - 1) / (maxOrder - 1) : 0
  const r = Math.round(30 + t * 200)
  const g = Math.round(120 + (1 - t) * 100)
  const b = Math.round(255 - t * 180)
  return `rgb(${r},${g},${b})`
}

const updateChart = () => {
  if (!chartRef.value) return
  
  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value, 'dark')
  }
  
  if (!currentData.value) return
  
  const data = currentData.value
  const dams = data.dams || []
  const warehouses = data.warehouses || []

  if (warehouses.length === 0) return

  const damMap: Record<number, number> = {}
  dams.forEach((d: number, i: number) => { damMap[d] = i })

  const pouredItems = warehouses.filter((wh: any) => wh.segment === 'A')
  const plannedItems = warehouses.filter((wh: any) => wh.segment !== 'A')

  const sortedPlanned = [...plannedItems].sort((a: any, b: any) => {
    const ta = new Date(a.startTime).getTime()
    const tb = new Date(b.startTime).getTime()
    return ta - tb
  })

  const sortedPoured = [...pouredItems].sort((a: any, b: any) => {
    return a.layerId - b.layerId
  })

  const maxPlannedOrder = sortedPlanned.length

  const seriesData: any[] = []

  sortedPoured.forEach((wh: any) => {
    const damIdx = damMap[wh.damId] ?? -1
    if (damIdx < 0) return
    const bottomElev = wh.bottomElev ?? (wh.elevation ?? wh.layerId * 3) - 3
    const topElev = wh.topElev ?? (wh.elevation ?? wh.layerId * 3)
    seriesData.push({
      value: [damIdx, bottomElev, topElev, wh.layerId],
      itemStyle: { color: 'rgb(90,90,100)', borderColor: 'rgba(60,60,70,0.6)', borderWidth: 1 },
      _wh: wh,
      _isPoured: true
    })
  })

  sortedPlanned.forEach((wh: any, idx: number) => {
    const damIdx = damMap[wh.damId] ?? -1
    if (damIdx < 0) return
    const bottomElev = wh.bottomElev ?? (wh.elevation ?? wh.layerId * 3) - 3
    const topElev = wh.topElev ?? (wh.elevation ?? wh.layerId * 3)
    const order = idx + 1
    const color = getPlannedColor(order, maxPlannedOrder)
    seriesData.push({
      value: [damIdx, bottomElev, topElev, order],
      itemStyle: { color: color, borderColor: 'rgba(0,150,255,0.3)', borderWidth: 1 },
      _wh: wh,
      _isPoured: false
    })
  })

  const allBottoms = warehouses.map((wh: any) => wh.bottomElev ?? (wh.elevation ?? wh.layerId * 3) - 3)
  const allTops = warehouses.map((wh: any) => wh.topElev ?? (wh.elevation ?? wh.layerId * 3))
  const minElev = Math.floor(Math.min(...allBottoms) / 3) * 3 - 3
  const maxElev = Math.ceil(Math.max(...allTops) / 3) * 3 + 3

  const blockWidth = 32

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(13, 17, 23, 0.95)',
      borderColor: '#30363d',
      borderWidth: 1,
      padding: [12, 16],
      textStyle: { color: '#e6edf3', fontSize: 13 },
      formatter: (params: any) => {
        const wh = params.data._wh
        if (!wh) return ''
        const segLabel = wh.segment === 'A' ? '已浇筑(A段)' : `计划(${wh.segment}段)`
        const topStr = wh.topElev ? `${wh.topElev}m` : ''
        const bottomStr = wh.bottomElev ? `${wh.bottomElev}m` : ''
        const elevInfo = topStr && bottomStr ? `${bottomStr} ~ ${topStr}` : (topStr || '')
        const timeStr = wh.startTime ? wh.startTime.substring(0, 10) : ''
        return `<strong>${wh.warehouseId}</strong><br/>` +
          `坝段：${wh.damId}<br/>` +
          `层号：${wh.layerId}${elevInfo ? ' / 高程：' + elevInfo : ''}<br/>` +
          `状态：${segLabel}<br/>` +
          `时间：${timeStr}`
      }
    },
    grid: {
      top: 30,
      left: 65,
      right: 20,
      bottom: 50,
      containLabel: false
    },
    xAxis: {
      type: 'category',
      data: dams.map((d: number) => String(d)),
      axisLine: { lineStyle: { color: 'rgba(0,150,255,0.2)' } },
      axisLabel: {
        color: 'var(--text-secondary)',
        fontSize: 10,
        interval: 0,
        rotate: dams.length > 20 ? 45 : 0
      },
      name: '坝段号',
      nameTextStyle: { color: 'var(--text-muted)', padding: [15, 0, 0, 0] },
      splitLine: { show: false }
    },
    yAxis: {
      type: 'value',
      min: minElev,
      max: maxElev,
      interval: Math.ceil((maxElev - minElev) / 15) * 3 || 3,
      axisLine: { lineStyle: { color: 'rgba(0,150,255,0.2)' } },
      axisLabel: {
        color: 'var(--text-secondary)',
        fontSize: 10,
        formatter: (val: number) => val + 'm'
      },
      splitLine: { lineStyle: { color: 'rgba(0,150,255,0.06)', type: 'dashed' } },
      name: '高程(m)',
      nameTextStyle: { color: 'var(--text-muted)' }
    },
    series: [
      {
        type: 'custom',
        renderItem: (params: any, api: any) => {
          const damIdx = api.value(0)
          const bottomElev = api.value(1)
          const topElev = api.value(2)
          const numValue = api.value(3)

          const bottomCoord = api.coord([damIdx, bottomElev])
          const topCoord = api.coord([damIdx, topElev])
          const halfW = blockWidth / 2

          const itemData = seriesData[params.dataIndex]
          const color = itemData?.itemStyle?.color || '#58a6ff'
          const isPoured = itemData?._isPoured || false
          const wh = itemData?._wh

          const rectX = bottomCoord[0] - halfW
          const rectY = topCoord[1]
          const rectW = blockWidth
          const rectH = Math.max(bottomCoord[1] - topCoord[1], 4)

          const children: any[] = [
            {
              type: 'rect',
              shape: { x: rectX, y: rectY, width: rectW, height: rectH },
              style: {
                fill: color,
                stroke: isPoured ? 'rgba(60,60,70,0.6)' : 'rgba(0,150,255,0.3)',
                lineWidth: 1
              }
            }
          ]

          const centerX = bottomCoord[0]
          const centerY = rectY + rectH / 2

          if (isPoured && wh) {
            children.push({
              type: 'text',
              style: {
                text: wh.warehouseId,
                x: centerX,
                y: centerY,
                textAlign: 'center',
                textVerticalAlign: 'middle',
                fill: 'rgba(200,200,210,0.85)',
                fontSize: rectH > 12 ? 7 : 5,
                fontWeight: 400
              }
            })
          } else if (!isPoured && numValue) {
            children.push({
              type: 'text',
              style: {
                text: String(numValue),
                x: centerX,
                y: centerY,
                textAlign: 'center',
                textVerticalAlign: 'middle',
                fill: '#fff',
                fontSize: rectH > 12 ? 9 : 7,
                fontWeight: 600
              }
            })
          }

          return {
            type: 'group',
            children
          }
        },
        data: seriesData,
        emphasis: {
          itemStyle: {
            shadowBlur: 15,
            shadowColor: 'rgba(0,240,255,0.5)',
            borderColor: '#00f0ff',
            borderWidth: 2
          }
        },
        animationDelay: (idx: number) => idx * 15
      }
    ],
    animationEasing: 'cubicOut',
    animationDuration: 800
  }
  
  chartInstance.setOption(option, true)
}

let resizeHandler: (() => void) | null = null

watch(hasData, (val) => {
  if (!val && chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})

watch(currentData, async () => {
  await nextTick()
  if (hasData.value) {
    updateChart()
  }
}, { deep: true })

watch(activeTab, async () => {
  await nextTick()
  updateChart()
})

onMounted(() => {
  if (hasData.value) {
    updateChart()
  }
  resizeHandler = () => chartInstance?.resize()
  window.addEventListener('resize', resizeHandler)
})

onBeforeUnmount(() => {
  if (resizeHandler) {
    window.removeEventListener('resize', resizeHandler)
  }
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})
</script>

<style scoped lang="scss">
.plan-visualization {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  
  .viz-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
  
  .chart-tabs {
    display: flex;
    gap: 10px;
    margin-bottom: 14px;
    
    .tab-item {
      flex: 1;
      padding: 10px 14px;
      background: transparent;
      border: 1px solid rgba(0, 150, 255, 0.15);
      border-radius: 10px;
      color: var(--text-secondary);
      font-size: 12px;
      cursor: pointer;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      position: relative;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 4px;
      
      &::before {
        content: '';
        position: absolute;
        inset: 0;
        background: linear-gradient(135deg, 
          rgba(0, 128, 255, 0.1) 0%,
          rgba(0, 200, 255, 0.05) 100%
        );
        opacity: 0;
        transition: opacity 0.3s ease;
      }
      
      .tab-text {
        position: relative;
        z-index: 1;
        transition: all 0.3s ease;
      }
      
      .tab-range {
        position: relative;
        z-index: 1;
        font-size: 9px;
        color: var(--text-muted);
        font-family: 'SF Mono', Monaco, monospace;
        opacity: 0.7;
        transition: opacity 0.3s ease;
      }
      
      .tab-indicator {
        position: relative;
        z-index: 1;
        width: 40%;
        height: 2px;
        background: linear-gradient(90deg, transparent, #00f0ff, transparent);
        box-shadow: 0 0 8px #00f0ff;
        transform: scaleX(0);
        transition: transform 0.3s ease;
      }
      
      &:hover {
        border-color: rgba(0, 200, 255, 0.35);
        color: var(--primary-cyan);
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        
        &::before { opacity: 0.5; }
        .tab-indicator { transform: scaleX(0.5); }
      }
      
      &.active {
        border-color: rgba(0, 200, 255, 0.4);
        color: var(--primary-cyan);
        font-weight: 500;
        background: rgba(0, 128, 255, 0.08);
        
        &::before { opacity: 1; }
        .tab-indicator { transform: scaleX(1); }
      }
      
      &:active { transform: translateY(0); }
    }
  }
  
  .chart-area {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
    background: rgba(6, 20, 50, 0.2);
    border: 1px solid rgba(0, 150, 255, 0.1);
    border-radius: 12px;
    padding: 14px;
    transition: all 0.3s ease;
    
    &:hover {
      border-color: rgba(0, 200, 255, 0.2);
      box-shadow: inset 0 0 30px rgba(0, 200, 255, 0.05);
    }
  }
  
  .chart-container {
    flex: 1;
    width: 100%;
    min-height: 0;
  }
  
  .chart-empty {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 0;
    color: var(--text-muted);
    
    .el-icon {
      margin-bottom: 12px;
      opacity: 0.3;
      transition: all 0.3s ease;
    }
    
    &:hover .el-icon {
      opacity: 0.6;
      transform: scale(1.1);
      filter: drop-shadow(0 0 10px rgba(0, 200, 255, 0.3));
    }
    
    p {
      margin: 4px 0;
      font-size: 13px;
      
      &.hint {
        font-size: 12px;
        opacity: 0.6;
      }
    }
  }
  
  .chart-footer {
    margin-top: 10px;
    text-align: center;
    padding-top: 8px;
    border-top: 1px solid rgba(0, 150, 255, 0.1);
    
    .legend-items {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 12px;
      flex-wrap: wrap;
    }
    
    .legend-item {
      display: flex;
      align-items: center;
      gap: 5px;
      font-size: 11px;
      color: var(--text-secondary);
    }
    
    .legend-block {
      display: inline-block;
      width: 14px;
      height: 10px;
      border-radius: 2px;
    }
    
    .legend-poured {
      background: rgb(90, 90, 100);
      border: 1px solid rgba(60, 60, 70, 0.6);
    }
    
    .legend-planned {
      background: linear-gradient(90deg, #1e78ff, #e34a33);
      border: 1px solid rgba(0, 150, 255, 0.3);
    }
    
    .legend-separator {
      color: rgba(0, 150, 255, 0.2);
      font-size: 12px;
    }
    
    .legend-text {
      font-size: 10px;
      color: var(--text-muted);
    }
  }
  
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    flex: 1;
    min-height: 0;
    color: var(--text-muted);
    
    .el-icon {
      margin-bottom: 14px;
      opacity: 0.3;
      transition: all 0.3s ease;
    }
    
    &:hover .el-icon {
      opacity: 0.6;
      transform: scale(1.1);
      filter: drop-shadow(0 0 10px rgba(0, 200, 255, 0.3));
    }
    
    p {
      margin: 4px 0;
      font-size: 13px;
      
      &.hint {
        font-size: 12px;
        opacity: 0.65;
        margin-top: 8px;
      }
    }
  }
}

@media (prefers-reduced-motion: reduce) {
  .plan-visualization {
    .tab-item,
    .chart-area,
    .el-icon {
      transition: none !important;
      transform: none !important;
    }
  }
}
</style>
