<template>
  <el-dropdown @command="handleLanguageChange" trigger="click">
    <el-button type="text" size="large" class="language-switcher">
      <GlobeIcon :size="16" class="language-icon" />
      <span class="language-text">{{ currentLanguageName }}</span>
      <el-icon class="el-icon--right"><ArrowDown /></el-icon>
    </el-button>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item
          v-for="lang in languages"
          :key="lang.code"
          :command="lang.code"
          :class="{ 'is-active': currentLocale === lang.code }"
        >
          <component :is="lang.flag" :size="16" class="language-icon-small" />
          <span class="language-name">{{ lang.name }}</span>
          <el-icon v-if="currentLocale === lang.code" class="check-icon">
            <Check />
          </el-icon>
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ArrowDown, Check } from '@element-plus/icons-vue'
import { GlobeIcon, FlagChina, FlagUS } from '@/assets/icons'

const { locale } = useI18n()

const languages = [
  { code: 'en', name: 'English', flag: FlagUS },
  { code: 'zh', name: '中文', flag: FlagChina },
]

const currentLocale = computed(() => locale.value)

const currentLanguageName = computed(() => {
  const lang = languages.find((l) => l.code === currentLocale.value)
  return lang ? lang.name : 'English'
})

const handleLanguageChange = (langCode: string) => {
  locale.value = langCode
  // Save language preference to localStorage
  localStorage.setItem('preferred-language', langCode)
}

// Initialize language from localStorage on component mount
const savedLanguage = localStorage.getItem('preferred-language')
if (savedLanguage && languages.some((l) => l.code === savedLanguage)) {
  locale.value = savedLanguage
}
</script>

<style scoped>
.language-switcher {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 6px;
  transition: all 0.2s ease;
}

.language-switcher:hover {
  background-color: rgba(64, 158, 255, 0.1);
}

.language-text {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.language-icon {
  color: #606266;
  margin-right: 8px;
  flex-shrink: 0;
}

.language-icon-small {
  color: #606266;
  margin-right: 8px;
  flex-shrink: 0;
}

.language-name {
  font-size: 14px;
  color: #303133;
}

.is-active {
  background-color: #f0f9ff;
  color: #409eff;
}

.check-icon {
  margin-left: auto;
  color: #409eff;
}

/* Dark mode styles */
.dark .language-text,
.dark .language-name {
  color: #e5e5e5;
}

.dark .language-icon,
.dark .language-icon-small {
  color: #a8a8a8;
}

.dark .language-switcher:hover {
  background-color: rgba(64, 158, 255, 0.2);
}

.dark .is-active {
  background-color: rgba(64, 158, 255, 0.2);
}

.dark .is-active .language-icon-small {
  color: #409eff;
}
</style>
