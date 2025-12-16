<template>
  <header class="app-header">
    <div class="header-left">
      <el-icon :size="20" @click="handleToggleSidebar">
        <Menu />
      </el-icon>
      <h1 class="app-title">{{ appTitle }}</h1>
    </div>
    <div class="header-right">
      <el-dropdown v-if="userStore.user" @command="handleCommand">
        <span class="user-info">
          <el-avatar :size="32" :src="userStore.user.avatar_url">
            {{ userStore.user.nickname || userStore.user.username?.charAt(0).toUpperCase() }}
          </el-avatar>
          <span class="username">{{ userStore.user.nickname || userStore.user.username }}</span>
          <el-icon><ArrowDown /></el-icon>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item disabled>
              <div class="user-detail">
                <div class="user-name">{{ userStore.user.nickname || userStore.user.username }}</div>
                <div class="user-email">{{ userStore.user.email }}</div>
              </div>
            </el-dropdown-item>
            <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAppStore } from '@/stores/modules/app'
import { useUserStore } from '@/stores/modules/user'
import { Menu, ArrowDown } from '@element-plus/icons-vue'

const emit = defineEmits(['toggle-sidebar'])

const appStore = useAppStore()
const userStore = useUserStore()
const appTitle = computed(() => appStore.appTitle)

const handleToggleSidebar = () => {
  emit('toggle-sidebar')
}

const handleCommand = async (command: string) => {
  if (command === 'logout') {
    await userStore.userLogout()
  }
}
</script>

<style lang="scss" scoped>
.app-header {
  height: 60px;
  padding: 0 20px;
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #e4e7ed;

  .header-left {
    display: flex;
    align-items: center;
    gap: 12px;

    .el-icon {
      cursor: pointer;
      transition: all 0.3s ease;
      padding: 8px;
      border-radius: 8px;

      &:hover {
        background: rgba(64, 158, 255, 0.2);
        color: #409eff;
      }
    }

    .app-title {
      font-size: 18px;
      font-weight: 600;
      margin: 0;
      background: linear-gradient(135deg, #409eff 0%, #67c23a 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }
  }

  .header-right {
    display: flex;
    align-items: center;
    color: rgba(255, 255, 255, 0.7);

    .user-info {
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      padding: 4px 12px;
      border-radius: 8px;
      transition: all 0.3s ease;

      &:hover {
        background: rgba(64, 158, 255, 0.2);
      }

      .username {
        font-size: 14px;
        max-width: 100px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }
  }
}

.user-detail {
  padding: 4px 0;

  .user-name {
    font-weight: 600;
    margin-bottom: 4px;
  }

  .user-email {
    font-size: 12px;
    color: #909399;
  }
}
</style>
