<template>
  <div class="dashboard-container">
    <!-- 网格背景 -->
    <div class="grid-overlay"></div>

    <div class="dashboard-grid">
      <!-- 左侧：浇筑进度同步 + 运行参数 -->
      <aside class="left-panel">
        <div
          ref="dbPanelRef"
          class="panel-wrapper panel-cursor-glow"
        >
          <div class="cursor-glow-effect"></div>
          <DatabaseConfig
            @config-saved="handleConfigSaved"
            @sync-database="handleSyncDatabase"
          />
        </div>
        <div
          ref="paramPanelRef"
          class="panel-wrapper panel-cursor-glow"
        >
          <div class="cursor-glow-effect"></div>
          <RunParameters
            :is-running="isRunning"
            @start-scheduling="handleStartScheduling"
            @refresh-visualization="handleRefreshVisualization"
          />
        </div>
        <div
          ref="compressPanelRef"
          class="panel-wrapper panel-cursor-glow"
        >
          <div class="cursor-glow-effect"></div>
          <ScheduleCompression
            ref="scheduleCompressionRef"
            :is-running="isRunning"
            @start-compression="handleStartCompression"
          />
        </div>
      </aside>

      <!-- 中间：结果摘要 + 计划可视化 (主区域) -->
      <main class="center-panel">
        <div
          ref="resultPanelRef"
          class="panel-wrapper main-content panel-cursor-glow"
        >
          <div class="cursor-glow-effect"></div>
          <ResultSummary :result-data="schedulingResult" />
        </div>
        <div
          ref="vizPanelRef"
          class="panel-wrapper main-content panel-cursor-glow"
        >
          <div class="cursor-glow-effect"></div>
          <PlanVisualization :viz-data="visualizationData" :is-running="isRunning" />
        </div>
      </main>

      <!-- 右侧：结果文件 + 运行日志 -->
      <aside class="right-panel">
        <div
          ref="filePanelRef"
          class="panel-wrapper panel-cursor-glow"
        >
          <div class="cursor-glow-effect"></div>
          <FileManagement :output-files="outputFiles" @file-action="handleFileAction" />
        </div>
        <div
          ref="logPanelRef"
          class="panel-wrapper panel-cursor-glow"
        >
          <div class="cursor-glow-effect"></div>
          <RunLog :logs="logs" />
        </div>
      </aside>
    </div>

    <!-- 文件预览对话框 -->
    <el-dialog
      v-model="previewVisible"
      :title="previewTitle"
      width="85%"
      top="5vh"
      class="preview-dialog"
      destroy-on-close
    >
      <div class="preview-content">
        <div class="preview-info">
          <el-tag size="small" type="info">共 {{ previewData.rows }} 行</el-tag>
          <el-tag size="small" type="info">{{ previewData.columns?.length || 0 }} 列</el-tag>
        </div>
        <el-table
          :data="previewData.head"
          height="60vh"
          class="preview-table"
          border
          stripe
        >
          <el-table-column
            v-for="col in previewData.columns"
            :key="col"
            :prop="col"
            :label="col"
            min-width="120"
            show-overflow-tooltip
          />
        </el-table>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import DatabaseConfig from '@/components/DatabaseConfig.vue'
import RunParameters from '@/components/RunParameters.vue'
import ScheduleCompression from '@/components/ScheduleCompression.vue'
import RunLog from '@/components/RunLog.vue'
import ResultSummary from '@/components/ResultSummary.vue'
import PlanVisualization from '@/components/PlanVisualization.vue'
import FileManagement from '@/components/FileManagement.vue'
import api from '@/utils/api'
import { useCursorGlow, useGlobalInteractions } from '@/composables/useInteractions'

const isRunning = ref(false)
const logs = ref<Array<{level: string, message: string, timestamp: string}>>([])
const schedulingResult = ref<any>(null)
const visualizationData = ref<any>(null)
const outputFiles = ref<any>([])

const previewVisible = ref(false)
const previewTitle = ref('文件预览')
const previewData = ref<any>({
  rows: 0,
  columns: [],
  head: []
})

// 面板引用
const dbPanelRef = ref<HTMLElement | null>(null)
const paramPanelRef = ref<HTMLElement | null>(null)
const compressPanelRef = ref<HTMLElement | null>(null)
const resultPanelRef = ref<HTMLElement | null>(null)
const vizPanelRef = ref<HTMLElement | null>(null)
const filePanelRef = ref<HTMLElement | null>(null)
const logPanelRef = ref<HTMLElement | null>(null)

const scheduleCompressionRef = ref<InstanceType<typeof ScheduleCompression> | null>(null)

// 全局交互检测
useGlobalInteractions()

// 为每个面板添加光标跟随光晕效果
useCursorGlow(dbPanelRef, { glowSize: 400, glowColor: 'rgba(0, 240, 255, 0.06)' })
useCursorGlow(paramPanelRef, { glowSize: 400, glowColor: 'rgba(0, 240, 255, 0.06)' })
useCursorGlow(compressPanelRef, { glowSize: 400, glowColor: 'rgba(0, 240, 255, 0.06)' })
useCursorGlow(resultPanelRef, { glowSize: 500, glowColor: 'rgba(0, 200, 255, 0.05)' })
useCursorGlow(vizPanelRef, { glowSize: 600, glowColor: 'rgba(0, 180, 255, 0.04)' })
useCursorGlow(filePanelRef, { glowSize: 400, glowColor: 'rgba(0, 240, 255, 0.06)' })
useCursorGlow(logPanelRef, { glowSize: 400, glowColor: 'rgba(0, 240, 255, 0.06)' })

let ws: WebSocket | null = null

onMounted(() => {
  connectWebSocket()
  loadOutputFiles()
})

onUnmounted(() => {
  if (ws) ws.close()
})

const connectWebSocket = () => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/ws/logs`
  
  ws = new WebSocket(wsUrl)
  
  ws.onopen = () => {
    logs.value.push({
      level: 'INFO',
      message: 'WebSocket 连接成功',
      timestamp: new Date().toLocaleString('zh-CN')
    })
  }
  
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      
      if (data.type === 'log') {
        logs.value.push({
          level: data.level,
          message: data.message,
          timestamp: data.timestamp
        })
        
        if (logs.value.length > 200) {
          logs.value = logs.value.slice(-100)
        }
      } else if (data.type === 'progress') {
        logs.value.push({
          level: 'PROGRESS',
          message: `[${data.step}/${data.total}] ${data.status}: ${data.detail}`,
          timestamp: new Date().toLocaleString('zh-CN')
        })
      } else if (data.type === 'result') {
        schedulingResult.value = data.data
        visualizationData.value = data.data.visualization_data || data.data.visualizationData
        isRunning.value = false
        loadOutputFiles()
      }
    } catch (e) {
      console.error('WebSocket message parse error:', e)
    }
  }
  
  ws.onerror = () => {
    // 部署到无 WebSocket 环境（如 Vercel）时静默处理
    console.warn('WebSocket 未能建立连接，系统将通过 HTTP 接口执行排仓')
  }
  
  ws.onclose = () => {
    console.warn('WebSocket 连接已关闭')
  }
}

const handleConfigSaved = async (config: any) => {
  try {
    await api.saveDatabaseConfig(config)
    logs.value.push({
      level: 'SUCCESS',
      message: `数据库连接配置已保存：${config.host}:${config.port} / ${config.database}`,
      timestamp: new Date().toLocaleString('zh-CN')
    })
  } catch (error: any) {
    logs.value.push({
      level: 'ERROR',
      message: `配置保存失败：${error.message}`,
      timestamp: new Date().toLocaleString('zh-CN')
    })
  }
}

const handleSyncDatabase = async () => {
  logs.value.push({
    level: 'INFO',
    message: '开始同步大坝浇筑进度...',
    timestamp: new Date().toLocaleString('zh-CN')
  })
  
  try {
    const response = await api.database.syncData()
    
    logs.value.push({
      level: 'SUCCESS',
      message: `大坝浇筑进度同步完成！基准计划：${response.data.details?.baseline_records || 0} 条记录`,
      timestamp: new Date().toLocaleString('zh-CN')
    })
  } catch (error: any) {
    logs.value.push({
      level: 'ERROR',
      message: `浇筑进度同步失败：${error.response?.data?.detail || error.message}`,
      timestamp: new Date().toLocaleString('zh-CN')
    })
  }
}

const handleStartScheduling = async (params: any) => {
  isRunning.value = true
  schedulingResult.value = null
  visualizationData.value = null
  
  logs.value.push({
    level: 'INFO',
    message: '开始执行排仓计算...',
    timestamp: new Date().toLocaleString('zh-CN')
  })
  
  try {
    const response = await api.runScheduling(params)
    
    schedulingResult.value = response.data
    visualizationData.value = response.data.visualization_data
    
    logs.value.push({
      level: 'SUCCESS',
      message: `排仓完成！方案：${response.data.final_mode}，最后完工日期：${response.data.final_end_date}`,
      timestamp: new Date().toLocaleString('zh-CN')
    })
    
    loadOutputFiles()
  } catch (error: any) {
    logs.value.push({
      level: 'ERROR',
      message: `排仓失败：${error.response?.data?.detail || error.message}`,
      timestamp: new Date().toLocaleString('zh-CN')
    })
  } finally {
    isRunning.value = false
  }
}

const handleStartCompression = async (params: any) => {
  isRunning.value = true
  schedulingResult.value = null
  visualizationData.value = null

  if (scheduleCompressionRef.value) {
    scheduleCompressionRef.value.setCompressing(true)
  }

  logs.value.push({
    level: 'INFO',
    message: '开始执行压缩工期排仓计算...',
    timestamp: new Date().toLocaleString('zh-CN')
  })

  try {
    const response = await api.runScheduling(params)

    schedulingResult.value = response.data
    visualizationData.value = response.data.visualization_data

    const debugInfo = response.data.debug_info || {}
    const compressionResult = {
      waterStorageOk: debugInfo.water_storage_satisfied || false,
      completionOk: debugInfo.completion_satisfied || false,
      originalEndDate: debugInfo.original_end_date || '-',
      compressedEndDate: response.data.final_end_date || '-',
      savedDays: debugInfo.saved_days || 0
    }

    if (scheduleCompressionRef.value) {
      scheduleCompressionRef.value.setCompressionResult(compressionResult)
    }

    logs.value.push({
      level: 'SUCCESS',
      message: `压缩排仓完成！方案：${response.data.final_mode}，完工日期：${response.data.final_end_date}，节约${debugInfo.saved_days || 0}天`,
      timestamp: new Date().toLocaleString('zh-CN')
    })

    loadOutputFiles()
  } catch (error: any) {
    if (scheduleCompressionRef.value) {
      scheduleCompressionRef.value.setCompressing(false)
    }
    logs.value.push({
      level: 'ERROR',
      message: `压缩排仓失败：${error.response?.data?.detail || error.message}`,
      timestamp: new Date().toLocaleString('zh-CN')
    })
  } finally {
    isRunning.value = false
  }
}

const handleRefreshVisualization = () => {
  logs.value.push({
    level: 'INFO',
    message: '可视化区域已刷新',
    timestamp: new Date().toLocaleString('zh-CN')
  })
}

const handleFileAction = async (action: string, filename: string, runFolder?: string) => {
  switch (action) {
    case 'download': {
      if (!runFolder) {
        logs.value.push({
          level: 'ERROR',
          message: '下载失败：缺少运行目录信息',
          timestamp: new Date().toLocaleString('zh-CN')
        })
        return
      }
      try {
        const response = await api.files.downloadRunFile(runFolder, filename)
        const blob = new Blob([response.data])
        const url = window.URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = filename
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        window.URL.revokeObjectURL(url)
        logs.value.push({
          level: 'SUCCESS',
          message: `文件下载成功：${filename}`,
          timestamp: new Date().toLocaleString('zh-CN')
        })
      } catch (error: any) {
        logs.value.push({
          level: 'ERROR',
          message: `文件下载失败：${error.response?.data?.detail || error.message}`,
          timestamp: new Date().toLocaleString('zh-CN')
        })
      }
      break
    }
    case 'download-run': {
      if (!runFolder) {
        logs.value.push({
          level: 'ERROR',
          message: '打包下载失败：缺少运行目录信息',
          timestamp: new Date().toLocaleString('zh-CN')
        })
        return
      }
      try {
        const response = await api.files.downloadRunFolder(runFolder)
        const blob = new Blob([response.data], { type: 'application/zip' })
        const url = window.URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = `${runFolder}.zip`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        window.URL.revokeObjectURL(url)
        logs.value.push({
          level: 'SUCCESS',
          message: `打包下载成功：${runFolder}.zip`,
          timestamp: new Date().toLocaleString('zh-CN')
        })
      } catch (error: any) {
        logs.value.push({
          level: 'ERROR',
          message: `打包下载失败：${error.response?.data?.detail || error.message}`,
          timestamp: new Date().toLocaleString('zh-CN')
        })
      }
      break
    }
    case 'preview': {
      if (!runFolder) {
        logs.value.push({
          level: 'ERROR',
          message: '预览失败：缺少运行目录信息',
          timestamp: new Date().toLocaleString('zh-CN')
        })
        return
      }
      try {
        const response = await api.files.previewRunFile(runFolder, filename)
        previewData.value = {
          rows: response.data.rows,
          columns: response.data.columns,
          head: response.data.head
        }
        previewTitle.value = filename
        previewVisible.value = true
        logs.value.push({
          level: 'INFO',
          message: `已打开文件预览：${filename}`,
          timestamp: new Date().toLocaleString('zh-CN')
        })
      } catch (error: any) {
        logs.value.push({
          level: 'ERROR',
          message: `文件预览失败：${error.response?.data?.detail || error.message}`,
          timestamp: new Date().toLocaleString('zh-CN')
        })
      }
      break
    }
  }
}

const loadOutputFiles = async () => {
  try {
    const response = await api.getOutputFiles()
    outputFiles.value = response.data.runs || []
  } catch (error) {
    console.error('Load output files error:', error)
  }
}
</script>

<style scoped lang="scss">
@import '@/styles/interactions.scss';

.dashboard-container {
  height: calc(100vh - 140px);
  overflow: hidden;
  position: relative;
}

// 网格背景
.grid-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-image: 
    linear-gradient(rgba(0, 200, 255, 0.02) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 200, 255, 0.02) 1px, transparent 1px);
  background-size: 40px 40px;
  pointer-events: none;
  z-index: 0;
  mask-image: radial-gradient(ellipse 90% 90% at 50% 50%, black 30%, transparent 70%);
  -webkit-mask-image: radial-gradient(ellipse 90% 90% at 50% 50%, black 30%, transparent 70%);
}

.dashboard-grid {
  display: grid;
  grid-template-columns: 360px 1fr 400px;
  gap: 24px;
  height: 100%;
  padding: 0 12px;
  position: relative;
  z-index: 1;
  
  // 面板容器样式 - 增强版
  .panel-wrapper {
    position: relative;
    background: linear-gradient(
      145deg,
      rgba(10, 30, 70, 0.4) 0%,
      rgba(6, 20, 50, 0.3) 50%,
      rgba(4, 15, 40, 0.35) 100%
    );
    backdrop-filter: blur(12px);
    border: 1px solid rgba(0, 200, 255, 0.15);
    border-radius: 20px;
    box-shadow: 
      0 8px 32px rgba(0, 0, 0, 0.3),
      inset 0 1px 0 rgba(255, 255, 255, 0.05),
      0 0 0 1px rgba(0, 200, 255, 0.03);
    overflow: hidden;
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    will-change: transform, box-shadow;
    
    // 顶部发光线条 - 增强
    &::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 1px;
      background: linear-gradient(90deg,
        transparent 0%,
        rgba(0, 200, 255, 0.4) 20%,
        rgba(0, 240, 255, 0.6) 50%,
        rgba(0, 200, 255, 0.4) 80%,
        transparent 100%
      );
      transition: all 0.4s ease;
      z-index: 2;
    }
    
    // 角落装饰效果
    &::after {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      width: 30px;
      height: 30px;
      border-top: 1px solid rgba(0, 200, 255, 0.2);
      border-left: 1px solid rgba(0, 200, 255, 0.2);
      border-top-left-radius: 20px;
      opacity: 0;
      transition: opacity 0.4s ease;
      pointer-events: none;
      z-index: 2;
    }
    
    // 悬停状态 - 增强效果
    &:hover {
      border-color: rgba(0, 230, 255, 0.35);
      box-shadow: 
        0 16px 48px rgba(0, 0, 0, 0.4),
        0 0 40px rgba(0, 200, 255, 0.12),
        inset 0 1px 0 rgba(255, 255, 255, 0.08);
      transform: translateY(-2px);
      
      &::before {
        background: linear-gradient(90deg,
          transparent 0%,
          rgba(0, 230, 255, 0.7) 20%,
          rgba(0, 255, 255, 0.9) 50%,
          rgba(0, 230, 255, 0.7) 80%,
          transparent 100%
        );
        box-shadow: 0 0 10px rgba(0, 240, 255, 0.5);
      }
      
      &::after {
        opacity: 1;
      }
    }
    
    // 组件内部控制padding，这里只提供容器
    > *:not(.cursor-glow-effect) {
      height: 100%;
      position: relative;
      z-index: 1;
    }
  }
  
  .left-panel {
    display: flex;
    flex-direction: column;
    gap: 16px;
    overflow-y: auto;
    padding: 4px;

    &::-webkit-scrollbar {
      width: 4px;
    }

    &::-webkit-scrollbar-thumb {
      background: linear-gradient(180deg, rgba(56,189,248,0.4), rgba(34,211,238,0.3));
      border-radius: 2px;
    }

    // 浇筑进度同步 - 压缩高度
    .panel-wrapper:nth-child(1) {
      flex: 0 0 auto;
    }

    // 启动智能排仓 - 保持适中
    .panel-wrapper:nth-child(2) {
      flex: 0 0 auto;
    }

    // 压缩工期 - 给予更多空间，内容超出时内部滚动
    .panel-wrapper:nth-child(3) {
      flex: 1;
      min-height: 320px;
      display: flex;
      flex-direction: column;

      > *:not(.cursor-glow-effect) {
        overflow-y: auto;

        &::-webkit-scrollbar {
          width: 4px;
        }

        &::-webkit-scrollbar-thumb {
          background: linear-gradient(180deg, rgba(56,189,248,0.4), rgba(34,211,238,0.3));
          border-radius: 2px;
        }
      }
    }
  }
  
  .center-panel {
    display: flex;
    flex-direction: column;
    gap: 16px;
    overflow-y: auto;
    padding: 4px;
    
    &::-webkit-scrollbar {
      width: 4px;
    }
    
    &::-webkit-scrollbar-thumb {
      background: linear-gradient(180deg, rgba(56,189,248,0.4), rgba(34,211,238,0.3));
      border-radius: 2px;
    }
    
    .main-content {
      min-height: 0;
    }
    
    // 结果摘要区域 - 增加高度确保内容完整显示
    .panel-wrapper:nth-child(1) {
      flex: 0 0 auto;
      min-height: 160px;
      max-height: 180px;
    }
    
    // 计划可视化区域 - 扩大展示面积
    .panel-wrapper:nth-child(2) {
      flex: 1;
      min-height: 480px;
    }
  }
  
  .right-panel {
    display: flex;
    flex-direction: column;
    gap: 20px;
    overflow-y: auto;
    padding: 4px;
    
    &::-webkit-scrollbar {
      width: 4px;
    }
    
    &::-webkit-scrollbar-thumb {
      background: linear-gradient(180deg, rgba(56,189,248,0.4), rgba(34,211,238,0.3));
      border-radius: 2px;
    }
  }
}

// 光标跟随光晕效果
.panel-cursor-glow {
  .cursor-glow-effect {
    position: absolute;
    width: 400px;
    height: 400px;
    background: radial-gradient(
      circle,
      rgba(0, 240, 255, 0.06) 0%,
      rgba(0, 200, 255, 0.03) 40%,
      transparent 70%
    );
    border-radius: 50%;
    pointer-events: none;
    opacity: 0;
    transition: opacity 0.4s ease;
    transform: translate(-50%, -50%);
    z-index: 0;
    left: var(--cursor-x, 50%);
    top: var(--cursor-y, 50%);
  }
  
  &:hover .cursor-glow-effect {
    opacity: 1;
  }
}

// 大屏适配 (1920px+)
@media (min-width: 1920px) {
  .dashboard-grid {
    grid-template-columns: 400px 1fr 440px;
    gap: 32px;
    padding: 0 24px;
    
    .panel-wrapper {
      border-radius: 24px;
      
      &::after {
        width: 40px;
        height: 40px;
        border-top-left-radius: 24px;
      }
      
      &:hover {
        transform: translateY(-3px);
      }
    }
  }
}

// 超宽屏适配 (2560px+)
@media (min-width: 2560px) {
  .dashboard-grid {
    grid-template-columns: 450px 1fr 500px;
    gap: 40px;
    max-width: 2400px;
    margin: 0 auto;
    
    .panel-wrapper {
      border-radius: 28px;
      
      &::after {
        border-top-left-radius: 28px;
      }
      
      &:hover {
        transform: translateY(-4px);
      }
    }
  }
}

// 小屏适配
@media (max-width: 1600px) {
  .dashboard-grid {
    grid-template-columns: 320px 1fr 360px;
    gap: 20px;
    padding: 0 8px;
  }
}

@media (max-width: 1400px) {
  .dashboard-grid {
    grid-template-columns: 280px 1fr 320px;
    gap: 16px;
  }
}

// 触摸设备优化
@media (hover: none) and (pointer: coarse) {
  .dashboard-grid .panel-wrapper:hover {
    transform: none;
  }
}

// 减少动画偏好
@media (prefers-reduced-motion: reduce) {
  .dashboard-grid .panel-wrapper {
    transition: none;

    &::before,
    &::after,
    .cursor-glow-effect {
      transition: none;
      animation: none;
    }

    &:hover {
      transform: none;
    }
  }
}

// 预览对话框样式
:deep(.preview-dialog) {
  border-radius: 16px;
  overflow: hidden;
  box-shadow:
    0 24px 80px rgba(0, 0, 0, 0.6),
    0 0 0 1px rgba(0, 200, 255, 0.2),
    0 0 60px rgba(0, 150, 255, 0.15);

  // 表格最外层边框 - 放在最外层确保优先级
  .el-table {
    border: 1px solid rgba(0, 200, 255, 0.5) !important;
  }

  .el-table--border {
    border: 1px solid rgba(0, 200, 255, 0.5) !important;
    box-shadow: 0 0 15px rgba(0, 200, 255, 0.2) !important;
  }

  .el-dialog__header {
    background: linear-gradient(145deg,
      rgba(15, 40, 80, 0.95) 0%,
      rgba(8, 25, 60, 0.95) 50%,
      rgba(6, 20, 50, 0.95) 100%
    );
    border-bottom: 1px solid rgba(0, 200, 255, 0.25);
    margin-right: 0;
    padding: 18px 24px;
    position: relative;

    // 顶部发光线条
    &::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 1px;
      background: linear-gradient(90deg,
        transparent 0%,
        rgba(0, 200, 255, 0.6) 20%,
        rgba(0, 240, 255, 0.9) 50%,
        rgba(0, 200, 255, 0.6) 80%,
        transparent 100%
      );
    }

    .el-dialog__title {
      color: #e0f7ff;
      font-size: 16px;
      font-weight: 600;
      letter-spacing: 0.5px;
      text-shadow: 0 0 20px rgba(0, 200, 255, 0.5);
    }

    .el-dialog__headerbtn {
      top: 50%;
      transform: translateY(-50%);
      right: 20px;

      .el-dialog__close {
        color: rgba(200, 230, 255, 0.6);
        font-size: 18px;
        transition: all 0.3s ease;

        &:hover {
          color: #00f0ff;
          transform: rotate(90deg);
        }
      }
    }
  }

  .el-dialog__body {
    background: linear-gradient(180deg,
      rgba(8, 25, 60, 0.95) 0%,
      rgba(6, 20, 50, 0.98) 50%,
      rgba(4, 15, 40, 0.98) 100%
    );
    padding: 20px 24px 24px;
    border: none;
  }

  .preview-content {
    .preview-info {
      display: flex;
      gap: 12px;
      margin-bottom: 16px;

      .el-tag {
        background: rgba(0, 150, 255, 0.12);
        border: 1px solid rgba(0, 200, 255, 0.25);
        color: #a0d8ff;
        font-size: 12px;
        padding: 4px 12px;
        border-radius: 6px;

        &:hover {
          background: rgba(0, 150, 255, 0.2);
          border-color: rgba(0, 230, 255, 0.4);
        }
      }
    }

    // 表格最外层边框
    .el-table {
      border: 1px solid rgba(0, 200, 255, 0.5) !important;
      background: transparent !important;
    }

    .preview-table {
      background: transparent !important;
      border-radius: 12px;
      overflow: hidden;
      border: 1px solid rgba(0, 200, 255, 0.5) !important;
      box-shadow:
        0 0 20px rgba(0, 150, 255, 0.15),
        inset 0 0 30px rgba(0, 100, 200, 0.05);

      // 强制整个表格背景透明
      &::before,
      &::after {
        display: none !important;
      }

      // 表格本身的外边框
      &.el-table--border {
        border: 1px solid rgba(0, 200, 255, 0.5) !important;
      }

      .el-table__inner-wrapper {
        background: transparent !important;
      }

      // 表头样式
      .el-table__header-wrapper {
        background: transparent !important;

        .el-table__header {
          background: transparent !important;
        }

        th {
          background: linear-gradient(180deg,
            rgba(0, 120, 200, 0.6) 0%,
            rgba(0, 100, 180, 0.5) 100%
          ) !important;
          color: #e0f7ff !important;
          font-weight: 600;
          font-size: 13px;
          border-color: rgba(0, 200, 255, 0.35) !important;
          border-bottom: 1px solid rgba(0, 200, 255, 0.35) !important;
          padding: 12px 8px;
          text-shadow: 0 0 10px rgba(0, 200, 255, 0.3);

          .cell {
            color: #e0f7ff !important;
          }
        }

        // 移除表头行的白色背景
        tr {
          background: transparent !important;
        }
      }

      // 表格主体
      .el-table__body-wrapper {
        background: rgba(4, 20, 50, 0.7) !important;

        .el-table__body {
          background: transparent !important;

          tr {
            background: transparent !important;

            td {
              background: rgba(8, 30, 70, 0.5) !important;
              color: #c8e0f5 !important;
              font-size: 13px;
              border-color: rgba(0, 180, 255, 0.2) !important;
              border-bottom: 1px solid rgba(0, 180, 255, 0.2) !important;
              padding: 10px 8px;
              transition: all 0.2s ease;

              .cell {
                color: #c8e0f5 !important;
              }
            }

            // 斑马纹 - 偶数行
            &.el-table__row--striped td {
              background: rgba(0, 100, 160, 0.15) !important;
            }

            // 悬停效果
            &:hover td {
              background: rgba(0, 180, 255, 0.18) !important;
              color: #ffffff !important;

              .cell {
                color: #ffffff !important;
              }
            }
          }
        }
      }

      // 边框处理 - 全部使用亮青色
      .el-table__border-left,
      .el-table__border-right,
      .el-table__border-bottom,
      .el-table__border-top {
        background-color: rgba(0, 200, 255, 0.5) !important;
      }

      // 表格边框 - 最外层
      &.el-table--border {
        border: 1px solid rgba(0, 200, 255, 0.5) !important;
        box-shadow: 0 0 15px rgba(0, 200, 255, 0.2);

        .el-table__cell {
          border-right: 1px solid rgba(0, 180, 255, 0.25) !important;
        }

        // 表头右边框
        th.is-right,
        th:not(.is-right) {
          border-right: 1px solid rgba(0, 180, 255, 0.25) !important;
        }

        // 单元格右边框
        td.is-right,
        td:not(.is-right) {
          border-right: 1px solid rgba(0, 180, 255, 0.2) !important;
        }
      }

      // 表格容器边框
      .el-table__wrapper {
        border: 1px solid rgba(0, 200, 255, 0.5) !important;
      }

      // 固定列背景
      .el-table__fixed,
      .el-table__fixed-right {
        background: rgba(6, 20, 50, 0.95) !important;

        &::before {
          background: transparent !important;
        }
      }

      // 滚动条样式
      .el-scrollbar__bar {
        background: rgba(0, 100, 150, 0.15);

        .el-scrollbar__thumb {
          background: linear-gradient(180deg,
            rgba(0, 200, 255, 0.6),
            rgba(0, 150, 255, 0.5)
          );
          border-radius: 4px;

          &:hover {
            background: linear-gradient(180deg,
              rgba(0, 230, 255, 0.8),
              rgba(0, 180, 255, 0.7)
            );
          }
        }
      }

      // 隐藏默认的白色遮罩
      .el-table__placeholder,
      .el-table__append-wrapper,
      .el-table__prepend-wrapper {
        background: transparent !important;
      }

      // 确保所有子元素都没有白色背景
      * {
        background-color: transparent;
      }
    }
  }
}
</style>
