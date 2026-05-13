<template>
  <div class="tech-panel run-parameters">
    <div class="panel-header">
      <el-icon><Setting /></el-icon>
      <span>启动智能排仓</span>
    </div>
    
    <div class="action-buttons">
      <el-button 
        type="primary" 
        :loading="isLoading"
        @click="handleRunScheduling"
        class="btn-primary btn-tech-primary"
      >
        <el-icon><VideoPlay /></el-icon>
        {{ isLoading ? '计算中...' : '生成排仓' }}
      </el-button>
      
      <el-button 
        class="btn-secondary btn-tech-secondary"
        @click="handleRefresh"
      >
        <el-icon><Refresh /></el-icon>
        刷新展示
      </el-button>
    </div>
    
    <div class="date-group">
      <div class="date-item">
        <label class="date-label">开始日期</label>
        <el-date-picker
          v-model="form.startDate"
          type="date"
          placeholder="选择日期"
          format="YYYY/MM/DD"
          value-format="YYYY-MM-DD"
          style="width: 100%"
          :disabled-date="(date: Date) => date > new Date()"
          class="date-picker-tech"
        />
      </div>
    </div>
    
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Setting, VideoPlay, Refresh } from '@element-plus/icons-vue'

const props = defineProps<{
  isRunning: boolean
}>()

const emit = defineEmits(['start-scheduling', 'refresh-visualization'])

const isLoading = ref(props.isRunning)

const form = ref({
  startDate: new Date().toISOString().split('T')[0],
  alpha: 0.5
})

const handleRunScheduling = () => {
  emit('start-scheduling', {
    start_date: form.value.startDate?.replace(/-/g, '/'),
    alpha: form.value.alpha
  })
}

const handleRefresh = () => {
  emit('refresh-visualization')
}
</script>

<style scoped lang="scss">
.run-parameters {
  .action-buttons {
    display: flex;
    gap: 12px;
    margin-bottom: 20px;
    
    .btn-primary,
    .btn-secondary {
      flex: 1;
      height: 40px;
      font-size: 14px;
      font-weight: 600;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      border-radius: 10px;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      position: relative;
      overflow: hidden;
      
      .el-icon {
        font-size: 16px;
        transition: transform 0.3s ease;
      }
      
      &:hover .el-icon {
        transform: scale(1.1);
      }
    }
    
    .btn-primary {
      background: rgba(0, 150, 255, 0.08);
      border: 1px solid rgba(0, 200, 255, 0.25);
      color: var(--text-primary);
      backdrop-filter: blur(10px);
      
      &::before {
        content: '';
        position: absolute;
        inset: 0;
        background: linear-gradient(
          135deg,
          rgba(0, 200, 255, 0.1) 0%,
          transparent 50%,
          rgba(0, 240, 255, 0.1) 100%
        );
        opacity: 0;
        transition: opacity 0.3s ease;
      }
      
      &:hover {
        background: rgba(0, 200, 255, 0.15);
        border-color: var(--primary-cyan);
        color: var(--primary-cyan);
        box-shadow: 0 0 20px rgba(0, 200, 255, 0.2);
        transform: translateY(-1px);
        
        &::before {
          opacity: 1;
        }
      }
      
      &:active {
        transform: translateY(0);
      }
    }
    
    .btn-secondary {
      background: rgba(0, 150, 255, 0.08);
      border: 1px solid rgba(0, 200, 255, 0.25);
      color: var(--text-primary);
      backdrop-filter: blur(10px);
      
      &::before {
        content: '';
        position: absolute;
        inset: 0;
        background: linear-gradient(
          135deg,
          rgba(0, 200, 255, 0.1) 0%,
          transparent 50%,
          rgba(0, 240, 255, 0.1) 100%
        );
        opacity: 0;
        transition: opacity 0.3s ease;
      }
      
      &:hover {
        background: rgba(0, 200, 255, 0.15);
        border-color: var(--primary-cyan);
        color: var(--primary-cyan);
        box-shadow: 0 0 20px rgba(0, 200, 255, 0.2);
        transform: translateY(-1px);
        
        &::before {
          opacity: 1;
        }
      }
      
      &:active {
        transform: translateY(0);
      }
    }
  }
  
  .date-group {
    padding: 16px 0;
    border-top: 1px solid rgba(0, 150, 255, 0.12);
    border-bottom: 1px solid rgba(0, 150, 255, 0.12);
    margin-bottom: 18px;
    
    .date-item {
      .date-label {
        display: block;
        font-size: 12px;
        color: var(--text-secondary);
        margin-bottom: 6px;
        font-weight: 500;
      }
    }
  }
  
  .info-note {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 12px;
    background: rgba(0, 150, 255, 0.05);
    border: 1px solid rgba(0, 200, 255, 0.15);
    border-radius: 10px;
    font-size: 12px;
    color: var(--text-secondary);
    line-height: 1.5;
    transition: all 0.3s ease;
    
    &:hover {
      background: rgba(0, 200, 255, 0.08);
      border-color: rgba(0, 230, 255, 0.25);
    }
    
    .el-icon {
      color: var(--primary-cyan);
      flex-shrink: 0;
      margin-top: 1px;
    }
  }
}

// 减少动画偏好
@media (prefers-reduced-motion: reduce) {
  .run-parameters {
    .btn-primary,
    .btn-secondary,
    .info-note {
      transition: none !important;
      transform: none !important;
    }
  }
}
</style>