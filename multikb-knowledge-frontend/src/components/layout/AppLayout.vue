<template>
  <div class="app-layout">
    <AppSidebar :collapsed="sidebarCollapsed" />
    <div class="app-content">
      <AppHeader @toggle-sidebar="toggleSidebar" />
      <div class="app-main">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import AppSidebar from './AppSidebar.vue'
import AppHeader from './AppHeader.vue'

const sidebarCollapsed = ref(false)

const toggleSidebar = () => {
  sidebarCollapsed.value = !sidebarCollapsed.value
}
</script>

<style lang="scss" scoped>
.app-layout {
  width: 100%;
  height: 100%;
  display: flex;
  background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #16213e 100%);
}

.app-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.app-main {
  flex: 1;
  padding: 20px;
  overflow: auto;
  position: relative;
  
  // 为内容区域添加微弱的光晕效果
  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: radial-gradient(circle at 20% 20%, rgba(64, 158, 255, 0.05) 0%, transparent 50%);
    pointer-events: none;
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

// 深色主题的卡片样式
:deep(.el-card) {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #e4e7ed;

  .el-card__header {
    background: rgba(255, 255, 255, 0.05);
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    color: #e4e7ed;
  }

  .el-card__body {
    color: #e4e7ed;
  }
}

// 深色主题的表格样式
:deep(.el-table) {
  background: transparent;
  color: #e4e7ed;

  .el-table__header {
    th {
      background: rgba(30, 35, 50, 0.8) !important;
      color: #8fa8d0 !important;
      border-bottom: 2px solid rgba(64, 158, 255, 0.3);
      font-weight: 500 !important;
      font-size: 15px !important;
      
      .cell {
        color: #b8d4f0 !important;
        font-weight: 500;
        font-size: 15px !important;
      }
    }
  }

  .el-table__body {
    tr {
      background: rgba(255, 255, 255, 0.02);
      
      &:hover {
        background: rgba(64, 158, 255, 0.15);
        cursor: pointer;
      }
    }

    td {
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
      color: #ffffff;
      
      .cell {
        color: #ffffff;
        font-weight: 400;
        font-size: 15px;
      }
    }
  }

  &::before {
    background-color: rgba(255, 255, 255, 0.2) !important;
  }

  .el-table__inner-wrapper::before {
    background-color: rgba(255, 255, 255, 0.2);
  }
}

// 深色主题的按钮
:deep(.el-button) {
  font-size: 15px;
  
  &:not(.el-button--primary) {
    background: rgba(255, 255, 255, 0.05);
    border-color: rgba(255, 255, 255, 0.2);
    color: #e4e7ed;

    &:hover {
      background: rgba(255, 255, 255, 0.1);
      border-color: #409eff;
      color: #409eff;
    }
  }
}

// 深色主题的分页
:deep(.el-pagination) {
  button {
    background: rgba(255, 255, 255, 0.05);
    color: #e4e7ed;
    border-color: rgba(255, 255, 255, 0.2);

    &:hover {
      color: #409eff;
      border-color: #409eff;
    }
  }

  .el-pagination__total,
  .el-pager li {
    color: #e4e7ed;
  }
}

// 深色主题的标签（Tag）
:deep(.el-tag) {
  background: rgba(64, 158, 255, 0.2) !important;
  border-color: rgba(64, 158, 255, 0.5) !important;
  color: #66b1ff !important;
  font-weight: 500;
  font-size: 14px;

  &.el-tag--success {
    background: rgba(103, 194, 58, 0.2) !important;
    border-color: rgba(103, 194, 58, 0.5) !important;
    color: #85ce61 !important;
  }

  &.el-tag--warning {
    background: rgba(230, 162, 60, 0.2) !important;
    border-color: rgba(230, 162, 60, 0.5) !important;
    color: #ebb563 !important;
  }

  &.el-tag--danger {
    background: rgba(245, 108, 108, 0.2) !important;
    border-color: rgba(245, 108, 108, 0.5) !important;
    color: #f78989 !important;
  }

  &.el-tag--info {
    background: rgba(144, 147, 153, 0.2) !important;
    border-color: rgba(144, 147, 153, 0.5) !important;
    color: #a8abb2 !important;
  }
}

// 深色主题的链接
:deep(.el-link) {
  color: #66b1ff;

  &:hover {
    color: #85c4ff;
  }
}

// 深色主题的空状态
:deep(.el-empty) {
  .el-empty__description p {
    color: rgba(255, 255, 255, 0.5) !important;
  }
}
</style>
