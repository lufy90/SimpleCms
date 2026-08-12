import { watch, onUnmounted, type Ref } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessageBox } from 'element-plus'

/**
 * Warn when the user tries to leave while an upload is in progress.
 * - In-app navigation: Element Plus confirm dialog
 * - Tab close / refresh: browser native beforeunload prompt
 */
export function useUploadLeaveGuard(isUploading: Ref<boolean>) {
  const { t } = useI18n()

  const handleBeforeUnload = (event: BeforeUnloadEvent) => {
    if (!isUploading.value) return
    event.preventDefault()
    event.returnValue = ''
  }

  watch(
    isUploading,
    (uploading) => {
      if (uploading) {
        window.addEventListener('beforeunload', handleBeforeUnload)
      } else {
        window.removeEventListener('beforeunload', handleBeforeUnload)
      }
    },
    { immediate: true },
  )

  onUnmounted(() => {
    window.removeEventListener('beforeunload', handleBeforeUnload)
  })

  onBeforeRouteLeave(async () => {
    if (!isUploading.value) return true

    try {
      await ElMessageBox.confirm(
        t('upload.messages.leaveWhileUploading'),
        t('upload.messages.leaveWhileUploadingTitle'),
        {
          type: 'warning',
          confirmButtonText: t('upload.messages.leaveAnyway'),
          cancelButtonText: t('common.cancel'),
          distinguishCancelAndClose: true,
        },
      )
      return true
    } catch {
      return false
    }
  })
}
