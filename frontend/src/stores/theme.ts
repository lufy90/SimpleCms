import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export const useThemeStore = defineStore('theme', () => {
  // Theme state
  const isDarkMode = ref(false)
  const theme = ref<'light' | 'dark' | 'auto'>('auto')

  // Initialize theme from localStorage or system preference
  const initializeTheme = () => {
    const savedTheme = localStorage.getItem('theme')
    if (savedTheme && ['light', 'dark', 'auto'].includes(savedTheme)) {
      theme.value = savedTheme as 'light' | 'dark' | 'auto'
    }

    updateTheme()
  }

  // Update theme based on current setting
  const updateTheme = () => {
    let shouldBeDark = false

    if (theme.value === 'dark') {
      shouldBeDark = true
    } else if (theme.value === 'light') {
      shouldBeDark = false
    } else if (theme.value === 'auto') {
      // Check system preference
      shouldBeDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    }

    isDarkMode.value = shouldBeDark
    applyTheme(shouldBeDark)
  }

  // Apply theme to DOM
  const applyTheme = (dark: boolean) => {
    const html = document.documentElement
    if (dark) {
      html.classList.add('dark')
    } else {
      html.classList.remove('dark')
    }
  }

  // Set theme
  const setTheme = (newTheme: 'light' | 'dark' | 'auto') => {
    theme.value = newTheme
    localStorage.setItem('theme', newTheme)
    updateTheme()
  }

  // Toggle between light and dark (ignores auto)
  const toggleTheme = () => {
    if (theme.value === 'auto') {
      // If currently auto, switch to opposite of system preference
      const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
      setTheme(systemPrefersDark ? 'light' : 'dark')
    } else {
      // Toggle between light and dark
      setTheme(theme.value === 'light' ? 'dark' : 'light')
    }
  }

  // Watch for system theme changes when in auto mode
  if (typeof window !== 'undefined') {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    mediaQuery.addEventListener('change', () => {
      if (theme.value === 'auto') {
        updateTheme()
      }
    })
  }

  return {
    isDarkMode,
    theme,
    initializeTheme,
    setTheme,
    toggleTheme,
    updateTheme,
  }
})
