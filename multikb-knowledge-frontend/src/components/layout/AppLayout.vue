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
  background: linear-gradient(135deg, #f5f7fa 0%, #e8eef5 50%, #dfe6f0 100%);
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
    background: radial-gradient(circle at 20% 20%, rgba(64, 158, 255, 0.03) 0%, transparent 50%);
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

// 浅色主题的卡片样式
:deep(.el-card) {
  background: #ffffff;
  backdrop-filter: blur(10px);
  border: 1px solid #e4e7ed;
  color: #303133;

  .el-card__header {
    background: #f5f7fa;
    border-bottom: 1px solid #e4e7ed;
    color: #303133;
  }

  .el-card__body {
    color: #606266;
  }
}

// 浅色主题的表格样式
:deep(.el-table) {
  background: #ffffff;
  color: #303133;

  .el-table__header {
    th {
      background: #f5f7fa !important;
      color: #606266 !important;
      border-bottom: 2px solid #e4e7ed;
      font-weight: 500 !important;
      font-size: 15px !important;
      
      .cell {
        color: #303133 !important;
        font-weight: 500;
        font-size: 15px !important;
      }
    }
  }

  .el-table__body {
    tr {
      background: #ffffff;
      
      &:hover {
        background: #f0f9ff;
        cursor: pointer;
      }
    }

    td {
      border-bottom: 1px solid #ebeef5;
      color: #606266;
      
      .cell {
        color: #606266;
        font-weight: 400;
        font-size: 15px;
      }
    }
  }

  &::before {
    background-color: #ebeef5 !important;
  }

  .el-table__inner-wrapper::before {
    background-color: #ebeef5;
  }
}

// 浅色主题的按钮
:deep(.el-button) {
  font-size: 15px;
  
  &:not(.el-button--primary) {
    background: #ffffff;
    border-color: #dcdfe6;
    color: #606266;

    &:hover {
      background: #f0f9ff;
      border-color: #409eff;
      color: #409eff;
    }
  }
}

// 浅色主题的分页
:deep(.el-pagination) {
  button {
    background: #ffffff;
    color: #606266;
    border-color: #dcdfe6;

    &:hover {
      color: #409eff;
      border-color: #409eff;
    }
  }

  .el-pagination__total,
  .el-pager li {
    color: #606266;
  }
}

// 浅色主题的标签（Tag）
:deep(.el-tag) {
  background: #ecf5ff !important;
  border-color: #d9ecff !important;
  color: #409eff !important;
  font-weight: 500;
  font-size: 14px;

  &.el-tag--success {
    background: #f0f9ff !important;
    border-color: #c2e7b0 !important;
    color: #67c23a !important;
  }

  &.el-tag--warning {
    background: #fdf6ec !important;
    border-color: #f5dab1 !important;
    color: #e6a23c !important;
  }

  &.el-tag--danger {
    background: #fef0f0 !important;
    border-color: #fbc4c4 !important;
    color: #f56c6c !important;
  }

  &.el-tag--info {
    background: #f4f4f5 !important;
    border-color: #e9e9eb !important;
    color: #909399 !important;
  }
}

// 浅色主题的链接
:deep(.el-link) {
  color: #409eff;

  &:hover {
    color: #66b1ff;
  }
}

// 浅色主题的空状态
:deep(.el-empty) {
  .el-empty__description p {
    color: #909399 !important;
  }
}
</style>
