<template>
  <div class="tech-panel run-log">
    <div class="panel-header">
      <el-icon><Document /></el-icon>
      <span>运行日志</span>
      <span v-if="logs.length > 0" class="log-count">{{ logs.length }} 条</span>
    </div>
    
    <div class="log-container scrollbar-tech" ref="logContainer">
      <template v-if="logs.length > 0">
        <div 
          v-for="(log, index) in logs" 
          :key="index"
          :class="['log-entry', `level-${log.level.toLowerCase()}`]"
        >
          <span class="log-time">{{ log.timestamp }}</span>
          <span class="log-level">{{ log.level }}</span>
          <span class="log-message">{{ log.message }}</span>
        </div>
      </template>
      
      <div v-else class="empty-state">
        <el-icon :size="36"><Document /></el-icon>
        <p>暂无日志</p>
        <p class="hint">执行排仓操作后将显示实时日志</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { Document } from '@element-plus/icons-vue'

const props = defineProps<{
  logs: Array<{level: string, message: string, timestamp: string}>
}>()

const logContainer = ref<HTMLElement | null>(null)

watch(() => props.logs.length, async () => {
  await nextTick()
  if (logContainer.value) {
    logContainer.value.scrollTop = logContainer.value.scrollHeight
  }
})
</script>

<style scoped lang="scss">
.run-log {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 260px;
  
  .panel-header {
    .log-count {
      margin-left: auto;
      padding: 2px 10px;
      background: rgba(0, 150, 255, 0.1);
      border: 1px solid rgba(0, 200, 255, 0.15);
      border-radius: 12px;
      font-size: 11px;
      color: var(--primary-cyan);
      font-weight: 500;
      transition: all 0.3s ease;
    }
    
    &:hover .log-count {
      background: rgba(0, 200, 255, 0.15);
      border-color: rgba(0, 230, 255, 0.3);
      box-shadow: 0 0 10px rgba(0, 200, 255, 0.2);
    }
  }
  
  .log-container {
    flex: 1;
    overflow-y: auto;
    background: rgba(6, 20, 50, 0.3);
    border: 1px solid rgba(0, 150, 255, 0.1);
    border-radius: 12px;
    padding: 12px;
    max-height: 340px;
    transition: all 0.3s ease;
    
    &:hover {
      border-color: rgba(0, 200, 255, 0.2);
      box-shadow: inset 0 0 20px rgba(0, 200, 255, 0.05);
    }
  }
}

.log-entry {
  padding: 8px 12px;
  margin-bottom: 4px;
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.5;
  display: flex;
  gap: 10px;
  font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: default;
  position: relative;
  overflow: hidden;
  
  // 左侧指示条
  &::before {
    content: '';
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 3px;
    opacity: 0;
    transition: opacity 0.2s ease;
  }
  
  // 背景光晕
  &::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(90deg, rgba(255,255,255,0.03), transparent);
    opacity: 0;
    transition: opacity 0.2s ease;
    pointer-events: none;
  }
  
  &:hover {
    transform: translateX(4px);
    
    &::before {
      opacity: 0.6;
    }
    
    &::after {
      opacity: 1;
    }
    
    .log-time {
      color: var(--text-secondary);
    }
  }
  
  .log-time {
    color: var(--text-muted);
    flex-shrink: 0;
    min-width: 140px;
    transition: color 0.2s ease;
  }
  
  .log-level {
    flex-shrink: 0;
    width: 48px;
    text-align: center;
    font-weight: 600;
    font-size: 10px;
    letter-spacing: 0.5px;
    padding: 2px 6px;
    border-radius: 4px;
    transition: all 0.2s ease;
  }
  
  .log-message {
    word-break: break-all;
    flex: 1;
  }
  
  // 不同级别的样式
  &.level-info {
    background: rgba(31, 111, 235, 0.04);
    
    &::before { background: #58a6ff; }
    .log-level { 
      color: #58a6ff; 
      background: rgba(88, 166, 255, 0.1);
    }
    .log-message { color: #c9d1d9; }
    
    &:hover {
      background: rgba(31, 111, 235, 0.08);
      .log-level { 
        background: rgba(88, 166, 255, 0.2);
        box-shadow: 0 0 8px rgba(88, 166, 255, 0.2);
      }
    }
  }
  
  &.level-success {
    background: rgba(35, 134, 54, 0.05);
    
    &::before { background: #3fb950; }
    .log-level { 
      color: #3fb950; 
      background: rgba(63, 185, 80, 0.1);
    }
    .log-message { color: #c9d1d9; }
    
    &:hover {
      background: rgba(35, 134, 54, 0.1);
      .log-level { 
        background: rgba(63, 185, 80, 0.2);
        box-shadow: 0 0 8px rgba(63, 185, 80, 0.2);
      }
    }
  }
  
  &.level-error {
    background: rgba(218, 54, 51, 0.05);
    
    &::before { background: #f85149; }
    .log-level { 
      color: #f85149; 
      background: rgba(248, 81, 73, 0.1);
    }
    .log-message { color: #f85149; }
    
    &:hover {
      background: rgba(218, 54, 51, 0.1);
      .log-level { 
        background: rgba(248, 81, 73, 0.2);
        box-shadow: 0 0 8px rgba(248, 81, 73, 0.2);
      }
    }
  }
  
  &.level-warning {
    background: rgba(210, 153, 34, 0.04);
    
    &::before { background: #e3b341; }
    .log-level { 
      color: #e3b341; 
      background: rgba(227, 179, 65, 0.1);
    }
    .log-message { color: #e3b341; }
    
    &:hover {
      background: rgba(210, 153, 34, 0.08);
      .log-level { 
        background: rgba(227, 179, 65, 0.2);
        box-shadow: 0 0 8px rgba(227, 179, 65, 0.2);
      }
    }
  }
  
  &.level-progress {
    background: rgba(163, 113, 247, 0.04);
    
    &::before { background: #a371f7; }
    .log-level { 
      color: #a371f7; 
      background: rgba(163, 113, 247, 0.1);
    }
    .log-message { color: #c9d1d9; }
    
    &:hover {
      background: rgba(163, 113, 247, 0.08);
      .log-level { 
        background: rgba(163, 113, 247, 0.2);
        box-shadow: 0 0 8px rgba(163, 113, 247, 0.2);
      }
    }
  }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 180px;
  color: var(--text-muted);
  
  .el-icon {
    margin-bottom: 12px;
    opacity: 0.25;
    transition: all 0.3s ease;
  }
  
  &:hover .el-icon {
    opacity: 0.5;
    transform: scale(1.1);
    filter: drop-shadow(0 0 10px rgba(0, 200, 255, 0.3));
  }
  
  p {
    margin: 3px 0;
    font-size: 13px;
    
    &.hint {
      font-size: 12px;
      opacity: 0.6;
      margin-top: 6px;
    }
  }
}

// 减少动画偏好
@media (prefers-reduced-motion: reduce) {
  .run-log {
    .log-entry,
    .log-container,
    .log-count,
    .el-icon {
      transition: none !important;
      transform: none !important;
    }
  }
}
</style>
