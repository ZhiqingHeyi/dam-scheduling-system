<template>
  <div class="tech-panel database-config">
    <div class="panel-header">
      <el-icon><Connection /></el-icon>
      <span>浇筑进度同步</span>
    </div>

    <div class="sync-main">
      <!-- 第一行：状态 + 配置按钮左右布局 -->
      <div class="sync-top-row">
        <div class="sync-status">
          <div class="status-indicator" :class="connectionStatus">
            <div class="status-dot"></div>
            <span class="status-text">{{ statusText }}</span>
          </div>
          <div class="status-detail" v-if="config.database">
            {{ config.host }}:{{ config.port }} / {{ config.database }}
          </div>
        </div>

        <el-button
          class="btn-config"
          @click="showConfigDialog = true"
        >
          <el-icon><Setting /></el-icon>
          配置
        </el-button>
      </div>

      <!-- 第二行：同步按钮 -->
      <el-button
        type="primary"
        @click="handleSync"
        class="btn-sync-main"
        :loading="syncing"
      >
        <el-icon><Refresh /></el-icon>
        同步大坝浇筑进度
      </el-button>
    </div>

    <el-dialog
      v-model="showConfigDialog"
      width="520px"
      :close-on-click-modal="false"
      class="config-dialog"
      destroy-on-close
      append-to-body
      :show-close="false"
    >
      <template #header>
        <div class="dialog-header">
          <div class="dialog-header-icon">
            <el-icon><Setting /></el-icon>
          </div>
          <span class="dialog-header-title">数据库配置</span>
          <div class="dialog-header-line"></div>
        </div>
      </template>

      <div class="dialog-body">
        <div class="form-grid">
          <div class="form-item">
            <label class="form-label">HOST</label>
            <el-input v-model="config.host" placeholder="数据库地址" class="input-tech" />
          </div>

          <div class="form-row">
            <div class="form-item">
              <label class="form-label">PORT</label>
              <el-input v-model="config.port" placeholder="端口" class="input-tech" />
            </div>
            <div class="form-item">
              <label class="form-label">USER</label>
              <el-input v-model="config.user" placeholder="用户名" class="input-tech" />
            </div>
          </div>

          <div class="form-row">
            <div class="form-item">
              <label class="form-label">PASSWORD</label>
              <el-input v-model="config.password" type="password" placeholder="密码" show-password class="input-tech" />
            </div>
            <div class="form-item">
              <label class="form-label">DATABASE</label>
              <el-input v-model="config.database" placeholder="数据库名" class="input-tech" />
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showConfigDialog = false" class="btn-dialog-cancel">
            取消
          </el-button>
          <el-button
            type="primary"
            @click="handleSave"
            class="btn-dialog-save"
            :loading="testing"
          >
            <el-icon><CircleCheck /></el-icon>
            验证连接并保存
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Connection, CircleCheck, Refresh, Setting } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import api from '@/utils/api'

const emit = defineEmits(['config-saved', 'sync-database'])

const showConfigDialog = ref(false)
const testing = ref(false)
const syncing = ref(false)
const connectionStatus = ref<'unknown' | 'connected' | 'disconnected'>('unknown')

const config = ref({
  host: '192.168.1.88',
  port: '3306',
  user: 'root',
  password: '!Tmhc20170717',
  database: 'qbt'
})

const statusText = computed(() => {
  switch (connectionStatus.value) {
    case 'connected': return '数据库已连接'
    case 'disconnected': return '数据库未连接'
    default: return '连接状态未知'
  }
})

onMounted(() => {
  const saved = localStorage.getItem('dbConfig')
  if (saved) {
    try {
      config.value = JSON.parse(saved)
    } catch {}
  }
})

const handleSave = async () => {
  testing.value = true
  try {
    await api.testDatabaseConnection(config.value)
    connectionStatus.value = 'connected'
    localStorage.setItem('dbConfig', JSON.stringify(config.value))
    emit('config-saved', config.value)
    ElMessage.success('数据库连接验证成功，配置已保存')
    showConfigDialog.value = false
  } catch (error: any) {
    connectionStatus.value = 'disconnected'
    ElMessage.error(`连接验证失败：${error.response?.data?.detail || error.message}`)
  } finally {
    testing.value = false
  }
}

const handleSync = async () => {
  syncing.value = true
  try {
    emit('sync-database')
  } finally {
    setTimeout(() => {
      syncing.value = false
    }, 1000)
  }
}
</script>

<style scoped lang="scss">
.database-config {
  padding: 16px;

  .panel-header {
    margin-bottom: 12px;
    padding-bottom: 10px;
  }

  .sync-main {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  // 第一行：状态 + 配置按钮左右布局
  .sync-top-row {
    display: flex;
    align-items: stretch;
    gap: 10px;

    .sync-status {
      flex: 1;
      min-width: 0;
    }

    .btn-config {
      flex-shrink: 0;
      height: auto;
      min-height: 32px;
      padding: 0 12px;
      align-self: stretch;
    }
  }

  .sync-status {
    padding: 10px 12px;
    background: rgba(0, 150, 255, 0.06);
    border: 1px solid rgba(0, 200, 255, 0.12);
    border-radius: 10px;
    margin-bottom: 0;

    .status-indicator {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 6px;

      .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        transition: all 0.3s ease;
      }

      .status-text {
        font-size: 13px;
        font-weight: 600;
      }

      &.unknown {
        .status-dot {
          background: rgba(150, 150, 150, 0.6);
          box-shadow: 0 0 6px rgba(150, 150, 150, 0.3);
        }
        .status-text { color: var(--text-secondary); }
      }

      &.connected {
        .status-dot {
          background: rgba(0, 230, 118, 0.9);
          box-shadow: 0 0 8px rgba(0, 230, 118, 0.5);
          animation: pulse-green 2s ease-in-out infinite;
        }
        .status-text { color: rgba(0, 230, 118, 0.9); }
      }

      &.disconnected {
        .status-dot {
          background: rgba(255, 82, 82, 0.9);
          box-shadow: 0 0 8px rgba(255, 82, 82, 0.5);
        }
        .status-text { color: rgba(255, 82, 82, 0.9); }
      }
    }

    .status-detail {
      font-size: 11px;
      color: var(--text-muted);
      padding-left: 16px;
      font-family: 'Courier New', monospace;
      letter-spacing: 0.3px;
    }
  }

  // 配置按钮（在 sync-top-row 中的）
  .sync-top-row .btn-config {
    font-size: 12px;
    font-weight: 600;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
    border-radius: 8px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    background: rgba(0, 150, 255, 0.06);
    border: 1px solid rgba(0, 200, 255, 0.15);
    color: var(--text-secondary);
    backdrop-filter: blur(10px);
    margin: 0;

    .el-icon {
      font-size: 14px;
      transition: transform 0.3s ease;
    }

    &:hover {
      background: rgba(0, 150, 255, 0.12);
      border-color: rgba(0, 200, 255, 0.3);
      color: var(--text-primary);
      transform: translateY(-1px);

      .el-icon {
        transform: rotate(90deg);
      }
    }

    &:active {
      transform: translateY(0);
    }
  }

  .btn-sync-main {
    width: 100%;
    height: 38px;
    font-size: 13px;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    border-radius: 10px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
    background: linear-gradient(135deg, rgba(0, 180, 255, 0.15) 0%, rgba(0, 120, 255, 0.12) 100%);
    border: 1px solid rgba(0, 200, 255, 0.35);
    color: var(--text-primary);
    backdrop-filter: blur(10px);

    .el-icon {
      font-size: 16px;
      transition: transform 0.3s ease;
    }

    &::before {
      content: '';
      position: absolute;
      inset: 0;
      background: linear-gradient(
        135deg,
        rgba(0, 200, 255, 0.12) 0%,
        transparent 50%,
        rgba(0, 240, 255, 0.12) 100%
      );
      opacity: 0;
      transition: opacity 0.3s ease;
    }

    &:hover {
      background: linear-gradient(135deg, rgba(0, 200, 255, 0.22) 0%, rgba(0, 150, 255, 0.18) 100%);
      border-color: var(--primary-cyan);
      color: var(--primary-cyan);
      box-shadow: 0 0 24px rgba(0, 200, 255, 0.25), 0 4px 16px rgba(0, 0, 0, 0.2);
      transform: translateY(-1px);

      &::before {
        opacity: 1;
      }

      .el-icon {
        transform: rotate(180deg);
      }
    }

    &:active {
      transform: translateY(0);
    }
  }
}

@keyframes pulse-green {
  0%, 100% {
    box-shadow: 0 0 6px rgba(0, 230, 118, 0.4);
  }
  50% {
    box-shadow: 0 0 12px rgba(0, 230, 118, 0.7);
  }
}
</style>
