<template>
  <div class="markdown-viewer">
    <div class="markdown-toolbar">
      <el-radio-group v-model="viewMode" size="small">
        <el-radio-button value="preview">Preview</el-radio-button>
        <el-radio-button value="code">Code</el-radio-button>
      </el-radio-group>
      <el-button v-if="viewMode === 'preview'" @click="copyToClipboard" size="small">
        <el-icon><CopyDocument /></el-icon>
        Copy
      </el-button>
    </div>

    <div v-if="viewMode === 'preview'" class="markdown-preview">
      <div class="markdown-body" v-html="renderedHtml" />
    </div>

    <div v-else class="markdown-code">
      <CodeViewer
        :content="localContent"
        :filename="filename"
        language="markdown"
        :file-id="fileId"
        @content-updated="handleContentUpdated"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { CopyDocument } from '@element-plus/icons-vue'
import { toast } from 'vue3-toastify'
import { copyTextToClipboard } from '@/utils/clipboard'
import CodeViewer from './CodeViewer.vue'

interface Props {
  content: string
  filename: string
  fileId?: string
}

const props = defineProps<Props>()

const emit = defineEmits<{
  contentUpdated: [content: string]
}>()

const viewMode = ref<'preview' | 'code'>('preview')
const localContent = ref(props.content)

watch(
  () => props.content,
  (value) => {
    localContent.value = value
  },
)

marked.setOptions({
  gfm: true,
  breaks: true,
})

const renderedHtml = computed(() => {
  const raw = marked.parse(localContent.value || '') as string
  return DOMPurify.sanitize(raw)
})

const copyToClipboard = async () => {
  try {
    await copyTextToClipboard(localContent.value)
    toast.success('Copied to clipboard')
  } catch {
    toast.error('Failed to copy')
  }
}

const handleContentUpdated = (content: string) => {
  localContent.value = content
  emit('contentUpdated', content)
  viewMode.value = 'preview'
}
</script>

<style scoped>
.markdown-viewer {
  width: 100%;
  height: 100%;
  min-height: 400px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.markdown-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
  gap: 8px;
}

.markdown-preview {
  flex: 1;
  overflow: auto;
  padding: 24px;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
}

.markdown-code {
  flex: 1;
  min-height: 0;
}

.markdown-body {
  max-width: 920px;
  margin: 0 auto;
  color: #303133;
  line-height: 1.7;
  font-size: 15px;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4),
.markdown-body :deep(h5),
.markdown-body :deep(h6) {
  margin: 1.4em 0 0.6em;
  font-weight: 600;
  line-height: 1.3;
}

.markdown-body :deep(h1) {
  font-size: 1.8em;
  border-bottom: 1px solid #ebeef5;
  padding-bottom: 0.3em;
}

.markdown-body :deep(h2) {
  font-size: 1.45em;
  border-bottom: 1px solid #ebeef5;
  padding-bottom: 0.25em;
}

.markdown-body :deep(p) {
  margin: 0.8em 0;
}

.markdown-body :deep(a) {
  color: #409eff;
  text-decoration: none;
}

.markdown-body :deep(a:hover) {
  text-decoration: underline;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 1.6em;
  margin: 0.8em 0;
}

.markdown-body :deep(blockquote) {
  margin: 1em 0;
  padding: 0.2em 1em;
  border-left: 4px solid #dcdfe6;
  color: #606266;
  background: #f5f7fa;
}

.markdown-body :deep(code) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.9em;
  background: #f5f7fa;
  padding: 0.15em 0.4em;
  border-radius: 4px;
}

.markdown-body :deep(pre) {
  overflow: auto;
  padding: 12px 14px;
  margin: 1em 0;
  background: #f5f7fa;
  border-radius: 6px;
  border: 1px solid #ebeef5;
}

.markdown-body :deep(pre code) {
  padding: 0;
  background: transparent;
}

.markdown-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 1em 0;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid #e4e7ed;
  padding: 8px 10px;
  text-align: left;
}

.markdown-body :deep(th) {
  background: #f5f7fa;
}

.markdown-body :deep(img) {
  max-width: 100%;
  height: auto;
}

.markdown-body :deep(hr) {
  border: none;
  border-top: 1px solid #e4e7ed;
  margin: 1.5em 0;
}

.dark .markdown-preview {
  background: #1e1e1e;
  border-color: #3c3c3c;
}

.dark .markdown-body {
  color: #e5e5e5;
}

.dark .markdown-body :deep(h1),
.dark .markdown-body :deep(h2) {
  border-bottom-color: #3c3c3c;
}

.dark .markdown-body :deep(blockquote) {
  border-left-color: #5c5c5c;
  color: #a8a8a8;
  background: #2a2a2a;
}

.dark .markdown-body :deep(code),
.dark .markdown-body :deep(pre) {
  background: #2a2a2a;
}

.dark .markdown-body :deep(pre) {
  border-color: #3c3c3c;
}

.dark .markdown-body :deep(th),
.dark .markdown-body :deep(td) {
  border-color: #3c3c3c;
}

.dark .markdown-body :deep(th) {
  background: #2a2a2a;
}

.dark .markdown-body :deep(hr) {
  border-top-color: #3c3c3c;
}

.dark .markdown-body :deep(a) {
  color: #79bbff;
}
</style>
