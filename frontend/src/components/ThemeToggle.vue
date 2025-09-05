<template>
  <el-dropdown @command="handleThemeChange" trigger="click">
    <el-button type="text" class="theme-toggle-button">
      <el-icon v-if="isDarkMode" class="theme-icon">
        <Moon />
      </el-icon>
      <el-icon v-else class="theme-icon">
        <Sunny />
      </el-icon>
    </el-button>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item 
          command="light" 
          :class="{ 'is-active': theme === 'light' }"
        >
          <el-icon><Sunny /></el-icon>
          Light
        </el-dropdown-item>
        <el-dropdown-item 
          command="dark" 
          :class="{ 'is-active': theme === 'dark' }"
        >
          <el-icon><Moon /></el-icon>
          Dark
        </el-dropdown-item>
        <el-dropdown-item 
          command="auto" 
          :class="{ 'is-active': theme === 'auto' }"
        >
          <el-icon><Monitor /></el-icon>
          Auto
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useThemeStore } from '@/stores/theme'
import { Sunny, Moon, Monitor } from '@element-plus/icons-vue'

const themeStore = useThemeStore()

const isDarkMode = computed(() => themeStore.isDarkMode)
const theme = computed(() => themeStore.theme)

const handleThemeChange = (command: string) => {
  themeStore.setTheme(command as 'light' | 'dark' | 'auto')
}
</script>

<style scoped>
.theme-toggle-button {
  padding: 8px;
  color: #606266;
  transition: color 0.2s;
}

.theme-toggle-button:hover {
  color: #409eff;
}

.theme-icon {
  font-size: 18px;
}

:deep(.el-dropdown-menu__item.is-active) {
  background-color: #f0f9ff;
  color: #409eff;
  font-weight: 600;
}

:deep(.el-dropdown-menu__item.is-active .el-icon) {
  color: #409eff;
}
</style>
