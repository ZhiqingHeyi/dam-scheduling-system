<template>
  <div class="tech-panel plan-visualization">
    <div class="panel-header">
      <el-icon><TrendCharts /></el-icon>
      <span>计划可视化</span>
    </div>

    <!-- 排仓计算中炫酷动画 -->
    <div v-if="isRunning" class="scheduling-loading">
      <!-- 网格背景动效 -->
      <div class="loading-grid-bg"></div>

      <!-- 数据流粒子 -->
      <div class="data-stream">
        <span v-for="i in 24" :key="i" class="stream-particle" :style="{
          '--angle': (i * 15) + 'deg',
          '--delay': (i * 0.12) + 's',
          '--duration': (2.4 + (i % 5) * 0.3) + 's'
        }"></span>
      </div>

      <!-- 中心动画核心 -->
      <div class="loading-core">
        <!-- 外层旋转环 - 双层反向 -->
        <div class="ring ring-outer">
          <div class="ring-track"></div>
          <div class="ring-arc"></div>
          <div class="ring-dots">
            <span v-for="i in 8" :key="i" :style="{ transform: `rotate(${i * 45}deg)` }"></span>
          </div>
        </div>

        <!-- 中层旋转环 -->
        <div class="ring ring-middle">
          <div class="ring-track"></div>
          <div class="ring-arc"></div>
        </div>

        <!-- 内层脉动核心 -->
        <div class="ring ring-inner">
          <div class="core-pulse"></div>
          <div class="core-pulse core-pulse-2"></div>
          <div class="core-center">
            <div class="core-icon">AI</div>
          </div>
        </div>

        <!-- 周围轨道粒子 -->
        <div class="orbit-particles">
          <span v-for="i in 6" :key="i" class="orbit-dot" :style="{
            transform: `rotate(${i * 60}deg) translateX(110px)`,
            animationDelay: (i * -0.8) + 's'
          }"></span>
        </div>
      </div>

      <!-- 状态文字 -->
      <div class="loading-text-block">
        <div class="loading-title">
          <span class="title-text">算法智能排仓计算中</span>
          <span class="title-dots">
            <span class="dot"></span>
            <span class="dot"></span>
            <span class="dot"></span>
          </span>
        </div>
        <div class="loading-stage">
          <span class="stage-arrow">▸</span>
          <span class="stage-text">{{ currentStageText }}</span>
        </div>
      </div>

      <!-- 进度条 -->
      <div class="loading-progress">
        <div class="progress-track">
          <div class="progress-fill" :style="{ width: currentProgress + '%' }">
            <div class="progress-glow"></div>
            <div class="progress-stripes"></div>
          </div>
        </div>
        <div class="progress-info">
          <span class="progress-percent">{{ Math.round(currentProgress) }}%</span>
          <span class="progress-hint">请稍候，正在生成最优排仓方案</span>
        </div>
      </div>

      <!-- 底部状态指示 -->
      <div class="loading-status-bar">
        <div class="status-item">
          <span class="status-led led-green"></span>
          <span>系统就绪</span>
        </div>
        <div class="status-item">
          <span class="status-led led-cyan active"></span>
          <span>算法引擎运行中</span>
        </div>
        <div class="status-item">
          <span class="status-led led-blue active"></span>
          <span>数据流同步</span>
        </div>
      </div>
    </div>
    
    <div v-else-if="vizData && vizData.available" class="viz-content">
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
  isRunning?: boolean
}>()

const activeTab = ref<'fixed' | 'nextMonth' | 'rolling'>('fixed')
const chartRef = ref<HTMLElement | null>(null)
let chartInstance: echarts.ECharts | null = null

// 排仓计算阶段动画
const schedulingStages = [
  { text: '加载坝段基础数据', progress: 12 },
  { text: '同步已浇筑仓位信息', progress: 25 },
  { text: '构建仓位评价指标矩阵', progress: 38 },
  { text: '计算AHP-熵权组合权重', progress: 52 },
  { text: '执行高差约束自适应推理', progress: 65 },
  { text: '动态规划智能仓面排序', progress: 78 },
  { text: '缆机调度与间歇优化', progress: 90 },
  { text: '生成可视化排仓方案', progress: 100 }
]
const currentStageIndex = ref(0)
const currentProgress = ref(0)
let stageTimer: number | null = null
let progressTimer: number | null = null

const currentStageText = computed(() => schedulingStages[currentStageIndex.value]?.text || '')
const targetProgress = computed(() => schedulingStages[currentStageIndex.value]?.progress || 0)

watch(() => props.isRunning, (running) => {
  if (running) {
    currentStageIndex.value = 0
    currentProgress.value = 0
    // 阶段切换：每 1.4s 推进一个阶段
    stageTimer = window.setInterval(() => {
      if (currentStageIndex.value < schedulingStages.length - 1) {
        currentStageIndex.value++
      }
    }, 1400)
    // 进度条平滑推进
    progressTimer = window.setInterval(() => {
      const target = targetProgress.value
      const cur = currentProgress.value
      if (cur < target) {
        currentProgress.value = Math.min(target, cur + Math.max(0.5, (target - cur) * 0.18))
      }
    }, 50)
  } else {
    if (stageTimer) { clearInterval(stageTimer); stageTimer = null }
    if (progressTimer) { clearInterval(progressTimer); progressTimer = null }
    // 排仓完成，进度直接到 100
    currentProgress.value = 100
  }
}, { immediate: true })

onBeforeUnmount(() => {
  if (stageTimer) clearInterval(stageTimer)
  if (progressTimer) clearInterval(progressTimer)
})

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
  const rawDams = data.dams || []
  const warehouses = data.warehouses || []

  if (warehouses.length === 0) return

  // 补全坝段号为连续序列，确保标签与方块对齐（跨度超过50时不补全，避免标签过密）
  const dams = rawDams.length > 1
    ? (Math.max(...rawDams) - Math.min(...rawDams) + 1 <= 50
      ? Array.from({ length: Math.max(...rawDams) - Math.min(...rawDams) + 1 }, (_, i) => Math.min(...rawDams) + i)
      : [...rawDams].sort((a: number, b: number) => a - b))
    : rawDams

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
    return a.layerId - b.layerId || a.damId - b.damId
  })

  const maxPlannedOrder = sortedPlanned.length

  const seriesData: any[] = []

  sortedPoured.forEach((wh: any) => {
    const damIdx = damMap[wh.damId]
    if (damIdx === undefined) return
    const bottomElev = wh.bottomElev != null ? wh.bottomElev : (wh.elevation != null ? wh.elevation - 3 : wh.layerId * 3 - 3)
    const topElev = wh.topElev != null ? wh.topElev : (bottomElev + 3)
    if (topElev <= bottomElev || !isFinite(topElev) || !isFinite(bottomElev)) return
    seriesData.push({
      value: [damIdx, bottomElev, topElev, wh.layerId],
      itemStyle: { color: 'rgb(90,90,100)' },
      _wh: wh,
      _isPoured: true
    })
  })

  sortedPlanned.forEach((wh: any, idx: number) => {
    const damIdx = damMap[wh.damId]
    if (damIdx === undefined) return
    const bottomElev = wh.bottomElev != null ? wh.bottomElev : (wh.elevation != null ? wh.elevation - 3 : wh.layerId * 3 - 3)
    const topElev = wh.topElev != null ? wh.topElev : (bottomElev + 3)
    if (topElev <= bottomElev || !isFinite(topElev) || !isFinite(bottomElev)) return
    const order = idx + 1
    const color = getPlannedColor(order, maxPlannedOrder)
    seriesData.push({
      value: [damIdx, bottomElev, topElev, order],
      itemStyle: { color },
      _wh: wh,
      _isPoured: false
    })
  })

  const allBottoms = warehouses.map((wh: any) => wh.bottomElev != null ? wh.bottomElev : (wh.elevation != null ? wh.elevation - 3 : wh.layerId * 3 - 3)).filter((v: number) => isFinite(v))
  const allTops = warehouses.map((wh: any) => wh.topElev != null ? wh.topElev : (wh.elevation != null ? wh.elevation : wh.layerId * 3)).filter((v: number) => isFinite(v))
  if (allBottoms.length === 0 || allTops.length === 0) return
  const minElev = Math.floor(Math.min(...allBottoms) / 3) * 3 - 3
  const maxElev = Math.ceil(Math.max(...allTops) / 3) * 3 + 3

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
      axisLine: { lineStyle: { color: 'rgba(0,180,255,0.35)' } },
      axisLabel: {
        color: 'rgba(140,210,255,0.9)',
        fontSize: 10,
        interval: 0,
        rotate: dams.length > 20 ? 45 : 0
      },
      name: '坝段号',
      nameTextStyle: { color: 'rgba(0,200,255,0.7)', padding: [15, 0, 0, 0] },
      splitLine: { show: false }
    },
    yAxis: {
      type: 'value',
      min: minElev,
      max: maxElev,
      interval: Math.ceil((maxElev - minElev) / 15) * 3 || 3,
      axisLine: { lineStyle: { color: 'rgba(0,180,255,0.35)' } },
      axisLabel: {
        color: 'rgba(140,210,255,0.9)',
        fontSize: 10,
        formatter: (val: number) => val + 'm'
      },
      splitLine: { lineStyle: { color: 'rgba(0,150,255,0.08)', type: 'dashed' } },
      name: '高程(m)',
      nameTextStyle: { color: 'rgba(0,200,255,0.7)' }
    },
    series: [
      {
        type: 'custom',
        renderItem: (params: any, api: any) => {
          const damIdx = api.value(0)
          const bottomElev = api.value(1)
          const topElev = api.value(2)
          const numValue = api.value(3)

          // 计算坝段完整宽度，使仓位块紧密排列形成坝体
          // 使用 category 中心坐标 + bandWidth，确保与 xAxis 标签严格对齐
          const centerCoord = api.coord([damIdx, bottomElev])
          const bandWidth = api.size([1, 0])[0]
          const topCoord = api.coord([damIdx, topElev])

          const itemData = seriesData[params.dataIndex]
          const color = itemData?.itemStyle?.color || '#58a6ff'
          const isPoured = itemData?._isPoured || false
          const wh = itemData?._wh

          const rectX = centerCoord[0] - bandWidth / 2
          const rectY = topCoord[1]
          const rectW = bandWidth
          const rectH = Math.max(centerCoord[1] - topCoord[1], 2)

          const children: any[] = [
            {
              type: 'rect',
              shape: { x: rectX, y: rectY, width: rectW, height: rectH },
              style: {
                fill: color,
                stroke: isPoured ? 'rgba(40,40,50,0.5)' : 'rgba(0,100,255,0.15)',
                lineWidth: 0.5
              }
            }
          ]

          const centerX = rectX + rectW / 2
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
      },
      // 坝段横缝分界线
      {
        type: 'custom',
        renderItem: (_params: any, api: any) => {
          const boundaryIdx = api.value(0)
          const x = api.coord([boundaryIdx, 0])[0]
          const topY = api.coord([0, maxElev])[1]
          const bottomY = api.coord([0, minElev])[1]
          return {
            type: 'group',
            children: [{
              type: 'line',
              shape: { x1: x, y1: topY, x2: x, y2: bottomY },
              style: { stroke: 'rgba(0,150,255,0.15)', lineWidth: 1 },
              silent: true
            }]
          }
        },
        data: dams.length > 1 ? Array.from({ length: dams.length - 1 }, (_, i) => ({
          value: [i + 0.5]
        })) : [],
        silent: true,
        animation: false,
        z: 10
      }
    ],
    animationEasing: 'cubicOut',
    animationDuration: 800
  }
  
  chartInstance.setOption(option, true)
}

let resizeHandler: (() => void) | null = null
let resizeTimer: number | null = null

watch(hasData, (val) => {
  if (!val && chartInstance) {
    try { chartInstance.dispose() } catch {}
    chartInstance = null
  }
})

watch([currentData, activeTab], async () => {
  await nextTick()
  await new Promise(resolve => requestAnimationFrame(resolve))
  if (hasData.value) {
    updateChart()
  }
}, { deep: true })

onMounted(() => {
  if (hasData.value) {
    updateChart()
  }
  resizeHandler = () => {
    if (resizeTimer) clearTimeout(resizeTimer)
    resizeTimer = window.setTimeout(() => {
      chartInstance?.resize()
      resizeTimer = null
    }, 200)
  }
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
  
  // ============ 排仓计算加载动画 ============
  .scheduling-loading {
    flex: 1;
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 0;
    padding: 24px;
    overflow: hidden;
    border-radius: 12px;
    background: radial-gradient(ellipse at center,
      rgba(0, 50, 120, 0.25) 0%,
      rgba(4, 20, 50, 0.5) 50%,
      rgba(2, 10, 30, 0.7) 100%);
    border: 1px solid rgba(0, 200, 255, 0.15);

    // 网格背景动效
    .loading-grid-bg {
      position: absolute;
      inset: 0;
      background-image:
        linear-gradient(rgba(0, 200, 255, 0.05) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0, 200, 255, 0.05) 1px, transparent 1px);
      background-size: 30px 30px;
      mask-image: radial-gradient(ellipse 70% 70% at 50% 50%, black 30%, transparent 75%);
      -webkit-mask-image: radial-gradient(ellipse 70% 70% at 50% 50%, black 30%, transparent 75%);
      animation: grid-drift 12s linear infinite;
      pointer-events: none;
    }

    // 数据流粒子（从四周向中心汇聚）
    .data-stream {
      position: absolute;
      inset: 0;
      pointer-events: none;

      .stream-particle {
        position: absolute;
        top: 50%;
        left: 50%;
        width: 3px;
        height: 3px;
        background: #00f0ff;
        border-radius: 50%;
        box-shadow: 0 0 8px #00f0ff, 0 0 16px rgba(0, 240, 255, 0.6);
        transform: translate(-50%, -50%) rotate(var(--angle)) translateX(280px);
        opacity: 0;
        animation: stream-in var(--duration) ease-in var(--delay) infinite;

        @keyframes stream-in {
          0% {
            transform: translate(-50%, -50%) rotate(var(--angle)) translateX(280px) scale(0.5);
            opacity: 0;
          }
          20% { opacity: 1; }
          80% { opacity: 1; }
          100% {
            transform: translate(-50%, -50%) rotate(var(--angle)) translateX(40px) scale(1.4);
            opacity: 0;
          }
        }
      }
    }

    // 中心动画核心
    .loading-core {
      position: relative;
      width: 240px;
      height: 240px;
      margin-bottom: 32px;
      display: flex;
      align-items: center;
      justify-content: center;

      // 通用环样式
      .ring {
        position: absolute;
        border-radius: 50%;
      }

      // 外层环
      .ring-outer {
        width: 240px;
        height: 240px;

        .ring-track {
          position: absolute;
          inset: 0;
          border: 1px solid rgba(0, 200, 255, 0.1);
          border-radius: 50%;
        }

        .ring-arc {
          position: absolute;
          inset: 0;
          border-radius: 50%;
          border: 2px solid transparent;
          border-top-color: #00f0ff;
          border-right-color: rgba(0, 240, 255, 0.4);
          box-shadow: 0 0 20px rgba(0, 240, 255, 0.3), inset 0 0 20px rgba(0, 240, 255, 0.1);
          animation: spin-cw 3s linear infinite;
        }

        .ring-dots {
          position: absolute;
          inset: 0;

          span {
            position: absolute;
            top: 50%;
            left: 50%;
            width: 6px;
            height: 6px;
            margin: -3px 0 0 -3px;
            background: #00f0ff;
            border-radius: 50%;
            box-shadow: 0 0 8px #00f0ff;
            transform-origin: 3px 3px;
            animation: spin-ccw 6s linear infinite;

            &::after {
              content: '';
              position: absolute;
              top: 50%;
              left: 50%;
              transform: translate(-50%, -50%) translateX(120px);
              width: 6px;
              height: 6px;
              background: #00f0ff;
              border-radius: 50%;
              box-shadow: 0 0 10px #00f0ff;
            }
          }
        }
      }

      // 中层环
      .ring-middle {
        width: 180px;
        height: 180px;

        .ring-track {
          position: absolute;
          inset: 0;
          border: 1px dashed rgba(0, 200, 255, 0.15);
          border-radius: 50%;
        }

        .ring-arc {
          position: absolute;
          inset: 0;
          border-radius: 50%;
          border: 2px solid transparent;
          border-bottom-color: #1e88ff;
          border-left-color: rgba(30, 136, 255, 0.4);
          box-shadow: 0 0 15px rgba(30, 136, 255, 0.4);
          animation: spin-ccw 4s linear infinite;
        }
      }

      // 内层脉动核心
      .ring-inner {
        width: 120px;
        height: 120px;
        display: flex;
        align-items: center;
        justify-content: center;

        .core-pulse {
          position: absolute;
          width: 100%;
          height: 100%;
          border-radius: 50%;
          background: radial-gradient(circle,
            rgba(0, 240, 255, 0.4) 0%,
            rgba(0, 150, 255, 0.2) 50%,
            transparent 70%);
          animation: pulse-out 2s ease-out infinite;
        }

        .core-pulse-2 {
          animation-delay: 1s;
          background: radial-gradient(circle,
            rgba(30, 136, 255, 0.35) 0%,
            rgba(0, 100, 200, 0.15) 50%,
            transparent 70%);
        }

        .core-center {
          position: relative;
          width: 70px;
          height: 70px;
          background: linear-gradient(145deg, #0a3a6e 0%, #06204a 100%);
          border: 1.5px solid rgba(0, 240, 255, 0.6);
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow:
            0 0 25px rgba(0, 240, 255, 0.6),
            inset 0 0 20px rgba(0, 200, 255, 0.3);
          z-index: 2;
          animation: core-breathe 2s ease-in-out infinite;

          .core-icon {
            font-size: 22px;
            font-weight: 700;
            color: #e0f7ff;
            font-family: 'SF Mono', Monaco, 'Consolas', monospace;
            letter-spacing: 1px;
            text-shadow: 0 0 10px #00f0ff, 0 0 20px rgba(0, 240, 255, 0.6);
          }
        }
      }

      // 周围轨道粒子
      .orbit-particles {
        position: absolute;
        inset: 0;
        pointer-events: none;

        .orbit-dot {
          position: absolute;
          top: 50%;
          left: 50%;
          width: 4px;
          height: 4px;
          margin: -2px 0 0 -2px;
          background: #00f0ff;
          border-radius: 50%;
          box-shadow: 0 0 8px #00f0ff, 0 0 16px rgba(0, 240, 255, 0.5);
          transform-origin: 2px 2px;
          animation: spin-cw 5s linear infinite;
        }
      }
    }

    // 状态文字
    .loading-text-block {
      text-align: center;
      margin-bottom: 20px;
      z-index: 2;

      .loading-title {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 4px;
        font-size: 22px;
        font-weight: 600;
        color: #e0f7ff;
        letter-spacing: 2px;
        margin-bottom: 10px;
        text-shadow: 0 0 12px rgba(0, 240, 255, 0.7), 0 0 24px rgba(0, 200, 255, 0.4);

        .title-text {
          background: linear-gradient(90deg, #00f0ff 0%, #80ffff 50%, #00f0ff 100%);
          background-size: 200% 100%;
          -webkit-background-clip: text;
          background-clip: text;
          -webkit-text-fill-color: transparent;
          animation: text-shimmer 3s linear infinite;
        }

        .title-dots {
          display: inline-flex;
          gap: 4px;
          margin-left: 4px;

          .dot {
            width: 6px;
            height: 6px;
            background: #00f0ff;
            border-radius: 50%;
            box-shadow: 0 0 8px #00f0ff;
            animation: dot-bounce 1.4s ease-in-out infinite;

            &:nth-child(2) { animation-delay: 0.2s; }
            &:nth-child(3) { animation-delay: 0.4s; }
          }
        }
      }

      .loading-stage {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        font-size: 13px;
        color: rgba(180, 220, 255, 0.85);
        font-family: 'SF Mono', Monaco, 'Consolas', monospace;
        letter-spacing: 0.5px;

        .stage-arrow {
          color: #00f0ff;
          animation: arrow-flash 1s ease-in-out infinite;
        }

        .stage-text {
          min-width: 220px;
          text-align: left;
          transition: all 0.3s ease;
        }
      }
    }

    // 进度条
    .loading-progress {
      width: 380px;
      max-width: 80%;
      z-index: 2;

      .progress-track {
        position: relative;
        height: 8px;
        background: rgba(0, 50, 100, 0.4);
        border: 1px solid rgba(0, 200, 255, 0.25);
        border-radius: 4px;
        overflow: hidden;
        box-shadow: inset 0 0 8px rgba(0, 100, 200, 0.3);

        .progress-fill {
          position: relative;
          height: 100%;
          background: linear-gradient(90deg, #0066cc 0%, #00aaff 50%, #00f0ff 100%);
          border-radius: 3px;
          box-shadow: 0 0 12px rgba(0, 240, 255, 0.7), 0 0 4px rgba(0, 240, 255, 0.5);
          transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
          overflow: hidden;

          .progress-glow {
            position: absolute;
            top: 0;
            right: 0;
            width: 30px;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.8));
            animation: glow-pulse 1.2s ease-in-out infinite;
          }

          .progress-stripes {
            position: absolute;
            inset: 0;
            background: repeating-linear-gradient(
              45deg,
              rgba(255, 255, 255, 0.15) 0px,
              rgba(255, 255, 255, 0.15) 8px,
              transparent 8px,
              transparent 16px
            );
            animation: stripes-move 0.8s linear infinite;
          }
        }
      }

      .progress-info {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 8px;
        font-size: 11px;
        font-family: 'SF Mono', Monaco, 'Consolas', monospace;

        .progress-percent {
          color: #00f0ff;
          font-weight: 600;
          font-size: 13px;
          text-shadow: 0 0 8px rgba(0, 240, 255, 0.5);
        }

        .progress-hint {
          color: rgba(160, 200, 240, 0.6);
        }
      }
    }

    // 底部状态指示
    .loading-status-bar {
      display: flex;
      gap: 24px;
      margin-top: 24px;
      padding: 10px 20px;
      background: rgba(0, 30, 70, 0.4);
      border: 1px solid rgba(0, 200, 255, 0.15);
      border-radius: 6px;
      z-index: 2;

      .status-item {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 11px;
        color: rgba(180, 220, 255, 0.7);
        font-family: 'SF Mono', Monaco, 'Consolas', monospace;

        .status-led {
          width: 7px;
          height: 7px;
          border-radius: 50%;
          display: inline-block;

          &.led-green {
            background: #00ff88;
            box-shadow: 0 0 6px #00ff88;
          }

          &.led-cyan {
            background: #00f0ff;
            box-shadow: 0 0 6px #00f0ff;
          }

          &.led-blue {
            background: #1e88ff;
            box-shadow: 0 0 6px #1e88ff;
          }

          &.active {
            animation: led-blink 1.5s ease-in-out infinite;
          }
        }
      }
    }
  }

  // 关键帧动画定义
  @keyframes grid-drift {
    0% { background-position: 0 0, 0 0; }
    100% { background-position: 30px 30px, 30px 30px; }
  }

  @keyframes spin-cw {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }

  @keyframes spin-ccw {
    from { transform: rotate(0deg); }
    to { transform: rotate(-360deg); }
  }

  @keyframes pulse-out {
    0% {
      transform: scale(0.6);
      opacity: 0.8;
    }
    100% {
      transform: scale(1.6);
      opacity: 0;
    }
  }

  @keyframes core-breathe {
    0%, 100% {
      transform: scale(1);
      box-shadow: 0 0 25px rgba(0, 240, 255, 0.6), inset 0 0 20px rgba(0, 200, 255, 0.3);
    }
    50% {
      transform: scale(1.08);
      box-shadow: 0 0 40px rgba(0, 240, 255, 0.9), inset 0 0 30px rgba(0, 200, 255, 0.5);
    }
  }

  @keyframes text-shimmer {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
  }

  @keyframes dot-bounce {
    0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; }
    40% { transform: scale(1.2); opacity: 1; }
  }

  @keyframes arrow-flash {
    0%, 100% { opacity: 0.4; transform: translateX(0); }
    50% { opacity: 1; transform: translateX(2px); }
  }

  @keyframes glow-pulse {
    0%, 100% { opacity: 0.5; }
    50% { opacity: 1; }
  }

  @keyframes stripes-move {
    0% { background-position: 0 0; }
    100% { background-position: 16px 0; }
  }

  @keyframes led-blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }

  // ============ 原可视化样式 ============
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
    min-height: 200px;
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

    // 加载动画在减少动画偏好下：保留必要的旋转，去除脉动和闪烁
    .scheduling-loading {
      .loading-grid-bg,
      .data-stream .stream-particle,
      .core-pulse,
      .core-center,
      .progress-stripes,
      .progress-glow,
      .ring-arc,
      .ring-dots span,
      .orbit-dot,
      .title-dots .dot,
      .stage-arrow,
      .status-led.active {
        animation: none !important;
      }

      .loading-title .title-text {
        -webkit-text-fill-color: #00f0ff;
        animation: none !important;
      }
    }
  }
}
</style>
