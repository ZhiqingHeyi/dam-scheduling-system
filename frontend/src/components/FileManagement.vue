<template>
  <div class="tech-panel file-management">
    <div class="panel-header">
      <el-icon><FolderOpened /></el-icon>
      <span>结果文件</span>
    </div>

    <div class="file-actions">
      <el-button
        size="small"
        @click="handleDownloadAll"
        class="btn-open-dir"
      >
        <el-icon><Download /></el-icon>
        下载本次文件
      </el-button>
    </div>

    <div v-if="outputFiles && outputFiles.length > 0" class="files-list scrollbar-tech">
      <div
        v-for="(run, runIdx) in outputFiles"
        :key="runIdx"
        class="run-group"
      >
        <div class="run-header">
          <el-icon :size="14"><Timer /></el-icon>
          <span>{{ run.runFolder }}</span>
          <span class="run-time">{{ run.timestamp }}</span>
        </div>

        <div class="file-grid">
          <div
            v-for="(file, fileIdx) in run.files"
            :key="fileIdx"
            :class="['file-card', getFileTypeClass(file.name)]"
          >
            <div class="file-main" @click="handleFilePreview(run.runFolder, file.name)">
              <el-icon><component :is="getFileIcon(file.type)" /></el-icon>
              <span class="file-name">{{ truncateName(file.name) }}</span>
              <span class="file-ext">{{ file.type }}</span>
            </div>
            <div class="file-download" @click.stop="handleFileDownload(run.runFolder, file.name)">
              <el-icon :size="12"><Download /></el-icon>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <el-icon :size="36"><FolderOpened /></el-icon>
      <p>暂无输出文件</p>
      <p class="hint">运行排仓后将生成结果文件</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { FolderOpened, Timer, Document, Picture, Download } from '@element-plus/icons-vue'

const props = defineProps<{
  outputFiles: any[]
}>()

const emit = defineEmits(['file-action'])

const getFileIcon = (type: string) => {
  const imageTypes = ['PNG', 'JPG', 'JPEG', 'SVG']
  return imageTypes.includes(type.toUpperCase()) ? 'Picture' : 'Document'
}

const getFileTypeClass = (name: string) => {
  if (name.includes('完整排仓')) return 'type-complete'
  if (name.includes('固定周期')) return 'type-fixed'
  if (name.includes('滚动周期')) return 'type-rolling'
  if (name.includes('年计划')) return 'type-year'
  return ''
}

const truncateName = (name: string) => {
  if (name.length <= 14) return name
  return name.slice(0, 12) + '..'
}

const handleFilePreview = (runFolder: string, filename: string) => {
  emit('file-action', 'preview', filename, runFolder)
}

const handleFileDownload = (runFolder: string, filename: string) => {
  emit('file-action', 'download', filename, runFolder)
}

const handleDownloadAll = () => {
  if (props.outputFiles.length === 0) return
  const latestRun = props.outputFiles[0]
  emit('file-action', 'download-run', '', latestRun.runFolder)
}
</script>

<style scoped lang="scss">
.file-management {
  .file-actions {
    margin-bottom: 14px;
    
    .btn-open-dir {
      width: 100%;
      height: 32px;
      font-size: 12px;
      background: rgba(0, 150, 255, 0.08);
      border: 1px solid rgba(0, 200, 255, 0.2);
      color: var(--text-secondary);
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      
      &:hover {
        background: rgba(0, 200, 255, 0.15);
        border-color: rgba(0, 230, 255, 0.4);
        color: var(--primary-cyan);
        box-shadow: 0 0 15px rgba(0, 200, 255, 0.15);
        transform: translateY(-1px);
      }
      
      &:active {
        transform: translateY(0);
      }
    }
  }
  
  .files-list {
    max-height: 520px;
    overflow-y: auto;
  }
  
  .run-group {
    margin-bottom: 14px;
    padding: 12px;
    background: rgba(6, 20, 50, 0.3);
    border: 1px solid rgba(0, 150, 255, 0.12);
    border-radius: 12px;
    transition: all 0.3s ease;
    
    &:hover {
      border-color: rgba(0, 200, 255, 0.2);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
    
    &:last-child { margin-bottom: 0; }
    
    .run-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 10px;
      padding-bottom: 8px;
      border-bottom: 1px solid rgba(0, 150, 255, 0.1);
      font-size: 12px;
      color: var(--text-secondary);
      transition: all 0.25s ease;
      
      .el-icon { 
        color: var(--text-muted);
        transition: all 0.25s ease;
      }
      
      .run-time {
        margin-left: auto;
        font-size: 11px;
        color: var(--text-muted);
      }
    }
    
    &:hover .run-header {
      border-bottom-color: rgba(0, 200, 255, 0.2);
      
      .el-icon {
        color: var(--primary-cyan);
      }
    }
    
    .file-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 8px;
    }

    .file-card {
      display: flex;
      align-items: center;
      background: rgba(6, 20, 50, 0.4);
      border: 1px solid rgba(0, 150, 255, 0.12);
      border-radius: 8px;
      color: var(--text-primary);
      cursor: pointer;
      transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
      position: relative;
      overflow: hidden;

      .file-main {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 4px;
        padding: 10px 4px;
        min-width: 0;
      }

      .file-download {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 24px;
        height: 100%;
        min-height: 60px;
        background: rgba(0, 150, 255, 0.06);
        border-left: 1px solid rgba(0, 150, 255, 0.1);
        color: var(--text-muted);
        transition: all 0.25s ease;
        cursor: pointer;

        &:hover {
          background: rgba(0, 200, 255, 0.15);
          color: var(--primary-cyan);
        }
      }

      // 左侧指示条
      &::before {
        content: '';
        position: absolute;
        left: 0;
        top: 50%;
        transform: translateY(-50%) scaleY(0);
        width: 3px;
        height: 60%;
        background: linear-gradient(180deg, #00c8ff, #00f0ff);
        border-radius: 0 2px 2px 0;
        transition: transform 0.25s ease;
      }

      // 背景光晕
      &::after {
        content: '';
        position: absolute;
        inset: 0;
        background: radial-gradient(
          circle at 50% 50%,
          rgba(0, 200, 255, 0.1) 0%,
          transparent 70%
        );
        opacity: 0;
        transition: opacity 0.25s ease;
        pointer-events: none;
      }

      &:hover {
        background: rgba(6, 20, 50, 0.6);
        border-color: rgba(0, 200, 255, 0.3);
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);

        &::before {
          transform: translateY(-50%) scaleY(1);
        }

        &::after {
          opacity: 1;
        }

        .file-main .el-icon {
          color: var(--primary-cyan);
          filter: drop-shadow(0 0 8px rgba(0, 240, 255, 0.5));
          transform: scale(1.1);
        }

        .file-name {
          color: var(--text-primary);
        }
      }

      &:active {
        transform: translateY(0);
      }

      .el-icon {
        font-size: 20px;
        color: var(--text-secondary);
        transition: all 0.25s ease;
      }

      .file-name {
        font-size: 11px;
        text-align: center;
        line-height: 1.3;
        word-break: break-all;
        max-width: 100%;
        transition: color 0.25s ease;
      }

      .file-ext {
        font-size: 9px;
        color: var(--text-muted);
        text-transform: uppercase;
      }

      // 不同类型文件的颜色主题
      &.type-complete {
        .file-main .el-icon { color: #3fb950; }
        &:hover {
          border-color: rgba(63, 185, 80, 0.4);
          &::before { background: linear-gradient(180deg, #3fb950, #56d364); }
          .file-main .el-icon { color: #56d364; filter: drop-shadow(0 0 8px rgba(63, 185, 80, 0.5)); }
        }
      }

      &.type-fixed {
        .file-main .el-icon { color: #58a6ff; }
        &:hover {
          border-color: rgba(88, 166, 255, 0.4);
          &::before { background: linear-gradient(180deg, #58a6ff, #79c0ff); }
          .file-main .el-icon { color: #79c0ff; filter: drop-shadow(0 0 8px rgba(88, 166, 255, 0.5)); }
        }
      }

      &.type-rolling {
        .file-main .el-icon { color: #a371f7; }
        &:hover {
          border-color: rgba(163, 113, 247, 0.4);
          &::before { background: linear-gradient(180deg, #a371f7, #bc8cff); }
          .file-main .el-icon { color: #bc8cff; filter: drop-shadow(0 0 8px rgba(163, 113, 247, 0.5)); }
        }
      }

      &.type-year {
        .file-main .el-icon { color: #e3b341; }
        &:hover {
          border-color: rgba(227, 179, 65, 0.4);
          &::before { background: linear-gradient(180deg, #e3b341, #f0d175); }
          .file-main .el-icon { color: #f0d175; filter: drop-shadow(0 0 8px rgba(227, 179, 65, 0.5)); }
        }
      }
    }
  }
  
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 220px;
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
}

// 减少动画偏好
@media (prefers-reduced-motion: reduce) {
  .file-management {
    .file-card,
    .run-group,
    .btn-open-dir,
    .el-icon {
      transition: none !important;
      transform: none !important;
    }
  }
}
</style>