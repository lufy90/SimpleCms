<template>
  <div class="files-view">
    <div class="page-header">
      <div class="header-left">
        <h1>{{ currentDirectory ? currentDirectory.name : $t('navigation.files') }}</h1>
      </div>
      <div class="header-actions">
        <!-- File input for multiple files -->
        <input
          ref="fileInputRef"
          type="file"
          multiple
          style="display: none"
          @change="handleFileSelection"
        />
        <!-- Directory input for directory structure -->
        <input
          ref="dirInputRef"
          type="file"
          webkitdirectory
          style="display: none"
          @change="handleDirectorySelection"
        />
        <el-dropdown @command="handleUploadCommand" trigger="click">
          <el-button type="primary">
            <el-icon><Upload /></el-icon>
            {{ $t('common.upload') }}
            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="files">
                <el-icon><Document /></el-icon>
                {{ $t('files.multipleFiles') }}
              </el-dropdown-item>
              <el-dropdown-item command="directory">
                <el-icon><Folder /></el-icon>
                {{ $t('files.directoryStructure') }}
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-dropdown @command="handleCreateCommand" trigger="click">
          <el-button type="success">
            <el-icon><FolderAdd /></el-icon>
            {{ $t('common.create') }}
            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="directory">
                <el-icon><FolderAdd /></el-icon>
                {{ $t('files.newFolder') }}
              </el-dropdown-item>
              <el-dropdown-item command="text">
                <el-icon><Document /></el-icon>
                {{ $t('files.textFile') }}
              </el-dropdown-item>
              <el-dropdown-item command="word" divided>
                <el-icon style="color: #409eff"><Document /></el-icon>
                {{ $t('files.wordDocument') }}
              </el-dropdown-item>
              <el-dropdown-item command="excel">
                <el-icon style="color: #67c23a"><Document /></el-icon>
                {{ $t('files.excelSpreadsheet') }}
              </el-dropdown-item>
              <el-dropdown-item command="powerpoint">
                <el-icon style="color: #f56c6c"><Document /></el-icon>
                {{ $t('files.powerPointPresentation') }}
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-button @click="refreshFiles">
          <el-icon><Refresh /></el-icon>
          {{ $t('common.refresh') }}
        </el-button>
        <!-- <el-button 
          v-if="currentDirectory" 
          @click="navigateToRoot"
          type="info"
        >
          <el-icon><Back /></el-icon>
          Back to Root
        </el-button> -->
      </div>
    </div>

    <!-- Bulk Operations Toolbar -->
    <div v-if="selectedFileIds.size > 0" class="bulk-operations-toolbar">
      <div class="bulk-info">
        <span>{{ selectedFileIds.size }} {{ $t('files.bulkOperations.itemsSelected') }}</span>
      </div>
      <div class="bulk-actions">
        <el-button @click="showCopyDialog" type="primary" size="small">
          <el-icon><CopyDocument /></el-icon>
          {{ $t('common.copy') }}
        </el-button>
        <el-button @click="showMoveDialog" type="warning" size="small">
          <el-icon><Position /></el-icon>
          {{ $t('common.move') }}
        </el-button>
        <el-button @click="bulkDownload" type="success" size="small" :disabled="!hasSelectedFiles">
          <el-icon><Download /></el-icon>
          {{ $t('common.download') }}
        </el-button>
        <el-button @click="confirmDelete" type="danger" size="small">
          <el-icon><Delete /></el-icon>
          {{ $t('common.delete') }}
        </el-button>
        <el-button @click="clearSelection" size="small">
          <el-icon><Close /></el-icon>
          {{ $t('common.clear') }}
        </el-button>
      </div>
    </div>

    <!-- Breadcrumb Navigation -->
    <div class="breadcrumb-container">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item @click="handleBreadcrumbClick({ id: null, name: 'root', path: '/' })">
          root
        </el-breadcrumb-item>
        <el-breadcrumb-item
          v-for="(item, index) in breadcrumbPath.filter((item) => item.id !== null)"
          :key="index"
          @click="handleBreadcrumbClick(item)"
        >
          {{ item.name }}
        </el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <!-- Search and Filters -->
    <div class="search-bar">
      <el-input
        v-model="searchQuery"
        :placeholder="$t('files.placeholders.searchFiles')"
        prefix-icon="Search"
        clearable
        @input="handleSearch"
        style="width: 300px"
      />
      <!-- View Type Toggle -->
      <el-button-group class="view-toggle">
        <el-button
          :type="viewType === 'grid' ? 'primary' : 'default'"
          @click="setViewType('grid')"
          size="default"
        >
          <el-icon><Grid /></el-icon>
          {{ $t('files.viewTypes.grid') }}
        </el-button>
        <el-button
          :type="viewType === 'large' ? 'primary' : 'default'"
          @click="setViewType('large')"
          size="default"
        >
          <el-icon><Menu /></el-icon>
          {{ $t('files.viewTypes.large') }}
        </el-button>
        <el-button
          :type="viewType === 'picture' ? 'primary' : 'default'"
          @click="setViewType('picture')"
          size="default"
        >
          <el-icon><Picture /></el-icon>
          {{ $t('files.viewTypes.pictures') }}
        </el-button>
        <el-button
          :type="viewType === 'list' ? 'primary' : 'default'"
          @click="setViewType('list')"
          size="default"
        >
          <el-icon><List /></el-icon>
          {{ $t('files.viewTypes.list') }}
        </el-button>
      </el-button-group>
    </div>

    <!-- File List -->
    <div class="file-list-container">
      <el-empty v-if="filteredFiles.length === 0 && !isLoading" :description="$t('files.noFilesFound')">
        <el-button type="primary" @click="triggerFileSelection"> {{ $t('files.uploadFiles') }} </el-button>
      </el-empty>

      <!-- Large View (Picture Wall) -->
      <div v-else-if="viewType === 'large'" class="large-view">
        <div v-for="file in filteredFiles" :key="file.id" class="large-file-card">
          <div class="large-file-selection">
            <el-checkbox
              :model-value="selectedFileIds.has(file.id)"
              @change="(checked: boolean) => toggleFileSelection(file.id, checked)"
              @click.stop
            />
          </div>
          <div class="large-file-content" @click="handleFileClick(file)">
            <div class="large-file-icon">
              <FileIcon :file="file" :size="80" />
            </div>
            <div class="large-file-name">{{ file.name }}</div>
            <div class="large-file-meta">
              <span v-if="file.file_info?.size">{{ formatFileSize(file.file_info.size) }}</span>
              <span>{{ formatDate(file.created_at) }}</span>
            </div>
          </div>
          <div class="large-file-actions">
            <el-dropdown
              @command="(command: string) => handleFileAction(command, file)"
              trigger="click"
            >
              <el-button type="info" size="small" title="Actions" circle @click.stop>
                <el-icon><More /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="copy">
                    <el-icon><CopyDocument /></el-icon>
                    Copy
                  </el-dropdown-item>
                  <el-dropdown-item command="move">
                    <el-icon><Position /></el-icon>
                    Move
                  </el-dropdown-item>
                  <el-dropdown-item command="download" :disabled="file.item_type !== 'file'">
                    <el-icon><Download /></el-icon>
                    Download
                  </el-dropdown-item>
                  <el-dropdown-item command="details">
                    <el-icon><Document /></el-icon>
                    Details
                  </el-dropdown-item>
                  <el-dropdown-item command="share" :disabled="!file.can_share">
                    <el-icon><Share /></el-icon>
                    Share
                  </el-dropdown-item>
                  <el-dropdown-item command="rename" :disabled="!file.can_write">
                    <el-icon><Edit /></el-icon>
                    Rename
                  </el-dropdown-item>
                  <el-dropdown-item command="delete" divided>
                    <el-icon><Delete /></el-icon>
                    Delete
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </div>

      <!-- Picture Wall View -->
      <div v-else-if="viewType === 'picture'" class="picture-wall-view">
        <div v-for="file in filteredFiles" :key="file.id" class="picture-item">
          <div class="picture-selection">
            <el-checkbox
              :model-value="selectedFileIds.has(file.id)"
              @change="(checked: boolean) => toggleFileSelection(file.id, checked)"
              @click.stop
            />
          </div>
          <div class="picture-content" @click="handleFileClick(file)">
            <div class="picture-thumbnail">
              <FileIcon :file="file" />
            </div>
            <div class="picture-overlay">
              <div class="picture-filename">{{ file.name }}</div>
              <div class="picture-meta">
                <span v-if="file.file_info?.size">{{ formatFileSize(file.file_info.size) }}</span>
                <span>{{ formatDate(file.created_at) }}</span>
              </div>
            </div>
          </div>
          <div class="picture-actions">
            <el-dropdown
              @command="(command: string) => handleFileAction(command, file)"
              trigger="click"
            >
              <el-button type="info" size="small" title="Actions" circle @click.stop>
                <el-icon><More /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="copy">
                    <el-icon><CopyDocument /></el-icon>
                    Copy
                  </el-dropdown-item>
                  <el-dropdown-item command="move">
                    <el-icon><Position /></el-icon>
                    Move
                  </el-dropdown-item>
                  <el-dropdown-item command="download" :disabled="file.item_type !== 'file'">
                    <el-icon><Download /></el-icon>
                    Download
                  </el-dropdown-item>
                  <el-dropdown-item command="details">
                    <el-icon><Document /></el-icon>
                    Details
                  </el-dropdown-item>
                  <el-dropdown-item command="share" :disabled="!file.can_share">
                    <el-icon><Share /></el-icon>
                    Share
                  </el-dropdown-item>
                  <el-dropdown-item command="rename" :disabled="!file.can_write">
                    <el-icon><Edit /></el-icon>
                    Rename
                  </el-dropdown-item>
                  <el-dropdown-item command="delete" divided>
                    <el-icon><Delete /></el-icon>
                    Delete
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </div>

      <!-- Grid View -->
      <div v-else-if="viewType === 'grid'" class="grid-view">
        <div v-for="file in filteredFiles" :key="file.id" class="file-card">
          <div class="file-selection">
            <el-checkbox
              :model-value="selectedFileIds.has(file.id)"
              @change="(checked: boolean) => toggleFileSelection(file.id, checked)"
              @click.stop
            />
          </div>
          <div class="file-card-content" @click="handleFileClick(file)">
            <div class="file-icon">
              <FileIcon :file="file" :size="48" />
            </div>
            <div class="file-name">{{ file.name }}</div>
            <div class="file-meta">
              <span v-if="file.file_info?.size">{{ formatFileSize(file.file_info.size) }}</span>
              <span>{{ formatDate(file.created_at) }}</span>
            </div>
          </div>
          <div class="file-actions">
            <el-dropdown
              @command="(command: string) => handleFileAction(command, file)"
              trigger="click"
            >
              <el-button type="info" size="small" title="Actions" circle @click.stop>
                <el-icon><More /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="copy">
                    <el-icon><CopyDocument /></el-icon>
                    Copy
                  </el-dropdown-item>
                  <el-dropdown-item command="move">
                    <el-icon><Position /></el-icon>
                    Move
                  </el-dropdown-item>
                  <el-dropdown-item command="download" :disabled="file.item_type !== 'file'">
                    <el-icon><Download /></el-icon>
                    Download
                  </el-dropdown-item>
                  <el-dropdown-item command="details">
                    <el-icon><Document /></el-icon>
                    Details
                  </el-dropdown-item>
                  <el-dropdown-item command="share" :disabled="!file.can_share">
                    <el-icon><Share /></el-icon>
                    Share
                  </el-dropdown-item>
                  <el-dropdown-item command="rename" :disabled="!file.can_write">
                    <el-icon><Edit /></el-icon>
                    Rename
                  </el-dropdown-item>
                  <el-dropdown-item command="delete" divided>
                    <el-icon><Delete /></el-icon>
                    Delete
                  </el-dropdown-item>
                  <!-- Future operations can be added here -->
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </div>

      <!-- List View -->
      <el-table
        v-else
        :data="filteredFiles"
        @row-click="handleListRowClick"
        class="list-view"
        @selection-change="handleListSelectionChange"
        @sort-change="handleSortChange"
        ref="listTableRef"
        :default-sort="{ prop: 'name', order: 'ascending' }"
      >
        <!-- Selection Column -->
        <el-table-column type="selection" width="55" />

        <el-table-column
          prop="name"
          :label="$t('files.columns.name')"
          min-width="200"
          sortable
          :sort-method="sortByName"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <div class="file-name-cell">
              <FileIcon :file="row" :size="18" />
              <span>{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="size" :label="$t('files.columns.size')" width="120" sortable :sort-method="sortBySize">
          <template #default="{ row }">
            <span v-if="row.file_info?.size">{{ formatFileSize(row.file_info.size) }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="item_type" :label="$t('files.columns.type')" width="100" sortable />
        <el-table-column prop="owner" :label="$t('files.columns.owner')" width="120" sortable>
          <template #default="{ row }">
            <div class="owner-cell">
              <el-icon v-if="row.owner" :size="14" class="owner-icon">
                <User />
              </el-icon>
              <span>{{ row.owner?.username || '-' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="visibility" :label="$t('files.columns.visibility')" width="120" sortable>
          <template #default="{ row }">
            <el-tag :type="getVisibilityTagType(row.visibility)" size="small">
              {{ $t(`files.visibility.${row.visibility}`) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          prop="created_at"
          :label="$t('files.columns.created')"
          width="180"
          sortable
          :sort-method="sortByDate"
        >
          <template #default="{ row }">
            <span>{{ formatDate(row.created_at) }}</span>
          </template>
        </el-table-column>

        <!-- Actions Column -->
        <el-table-column :label="$t('files.columns.actions')" width="200" fixed="right">
          <template #default="{ row }">
            <div class="list-actions">
              <el-button
                type="primary"
                size="small"
                @click.stop="handleFileAction('copy', row)"
                :title="$t('common.copy')"
                circle
              >
                <el-icon><CopyDocument /></el-icon>
              </el-button>
              <el-button
                type="warning"
                size="small"
                @click.stop="handleFileAction('move', row)"
                :title="$t('common.move')"
                circle
              >
                <el-icon><Position /></el-icon>
              </el-button>
              <el-button
                type="success"
                size="small"
                @click.stop="handleFileAction('download', row)"
                :title="$t('common.download')"
                :disabled="row.item_type !== 'file'"
                circle
              >
                <el-icon><Download /></el-icon>
              </el-button>
              <el-dropdown
                @command="(command: string) => handleFileAction(command, row)"
                trigger="click"
              >
                <el-button
                  type="info"
                  size="small"
                  :title="$t('files.columns.actions')"
                  circle
                  style="margin-left: 12px"
                  @click.stop
                >
                  <el-icon><More /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="details">
                      <el-icon><Document /></el-icon>
                      {{ $t('files.dialogs.fileDetails') }}
                    </el-dropdown-item>
                    <el-dropdown-item command="share" :disabled="!row.can_share">
                      <el-icon><Share /></el-icon>
                      {{ $t('common.share') }}
                    </el-dropdown-item>
                    <el-dropdown-item command="rename" :disabled="!row.can_write">
                      <el-icon><Edit /></el-icon>
                      {{ $t('common.rename') }}
                    </el-dropdown-item>
                    <el-dropdown-item command="delete" divided>
                      <el-icon><Delete /></el-icon>
                      {{ $t('common.delete') }}
                    </el-dropdown-item>
                    <!-- Future operations can be added here -->
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- List View Summary -->
      <div class="list-view-summary">
        <p class="summary-text">
          {{ $t('files.messages.totalItems', { 
            total: filteredFiles.length,
            files: filteredFiles.filter((f) => f.item_type === 'file').length,
            directories: filteredFiles.filter((f) => f.item_type === 'directory').length
          }) }}
        </p>
      </div>
    </div>

    <!-- Upload Dialog -->
    <el-dialog
      v-model="uploadDialogVisible"
      title="Upload Files"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form :model="uploadForm" label-width="120px">
        <el-form-item label="Visibility">
          <el-select v-model="uploadForm.visibility" placeholder="Select visibility">
            <el-option label="Private" value="private" />
            <el-option label="User Shared" value="user" />
            <el-option label="Group Shared" value="group" />
            <el-option label="Public" value="public" />
          </el-select>
        </el-form-item>

        <!-- File Upload Section -->
        <el-form-item label="Files">
          <el-upload
            ref="uploadRef"
            :action="uploadAction"
            :headers="uploadHeaders"
            :data="uploadData"
            :on-success="handleUploadSuccess"
            :on-error="handleUploadError"
            :before-upload="beforeUpload"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
            :on-progress="handleUploadProgress"
            :on-exceed="handleFileExceed"
            :limit="20"
            multiple
            drag
            class="upload-area"
            :auto-upload="false"
            :show-file-list="true"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">Drop files here or <em>click to upload</em></div>
            <template #tip>
              <div class="el-upload__tip">
                Support for multiple files. Drag and drop or click to select.
                <div
                  v-if="selectedFiles.length > 0"
                  style="margin-top: 8px; color: #409eff; font-weight: 500"
                >
                  {{ selectedFiles.length }} file(s) selected
                </div>
              </div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="closeUploadDialog">Cancel</el-button>
          <el-button
            type="primary"
            @click="handleUpload"
            :loading="isUploading"
            :disabled="!hasFilesToUpload"
          >
            Upload Files {{ selectedFiles.length > 0 ? `(${selectedFiles.length})` : '' }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>

  <!-- Upload Progress Display -->
  <div v-if="uploadProgress.length > 0" class="upload-progress-overlay">
    <div class="upload-progress-panel">
      <div class="progress-header">
        <h3>Upload Progress</h3>
        <el-button v-if="!isUploading" @click="uploadProgress = []" size="small" type="text">
          Close
        </el-button>
      </div>
      <div class="progress-list">
        <div v-for="(progress, index) in uploadProgress" :key="index" class="progress-item">
          <div class="progress-item-header">
            <span class="filename">{{ progress.filename }}</span>
            <span class="status" :class="progress.status">{{ progress.status }}</span>
          </div>
          <el-progress
            v-if="progress.status === 'uploading'"
            :percentage="progress.percentage"
            :status="progress.error ? 'exception' : undefined"
            :stroke-width="4"
          />
          <div v-if="progress.error" class="error-message">
            {{ progress.error }}
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Copy Dialog -->
  <el-dialog
    v-model="copyDialogVisible"
    title="Copy Files"
    width="800px"
    :close-on-click-modal="false"
    class="operation-dialog"
  >
    <el-form>
      <el-form-item label="Destination Directory" class="destination-selector">
        <el-tree-select
          v-model="operationDestination"
          :data="directoryTreeData"
          :props="treeSelectProps"
          placeholder="Select destination directory"
          class="destination-tree-select"
          clearable
          check-strictly
          :render-after-expand="false"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="copyDialogVisible = false">Cancel</el-button>
        <el-button
          type="primary"
          @click="executeOperation"
          :disabled="operationDestination === undefined"
          >Copy Files</el-button
        >
      </div>
    </template>
  </el-dialog>

  <!-- Move Dialog -->
  <el-dialog
    v-model="moveDialogVisible"
    title="Move Files"
    width="800px"
    :close-on-click-modal="false"
    class="operation-dialog"
  >
    <el-form>
      <el-form-item label="Destination Directory" class="destination-selector">
        <el-tree-select
          v-model="operationDestination"
          :data="directoryTreeData"
          :props="treeSelectProps"
          placeholder="Select destination directory"
          class="destination-tree-select"
          clearable
          check-strictly
          :render-after-expand="false"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="moveDialogVisible = false">Cancel</el-button>
        <el-button
          type="warning"
          @click="executeOperation"
          :disabled="operationDestination === undefined"
          >Move Files</el-button
        >
      </div>
    </template>
  </el-dialog>

  <!-- Share Dialog -->
  <ShareDialog
    v-model:visible="shareDialogVisible"
    :file="selectedFileForSharing"
    @permissions-updated="handlePermissionsUpdated"
  />

  <!-- Details Dialog -->
  <el-dialog
    v-model="detailsDialogVisible"
    :title="`File Details: ${selectedFileForDetails?.name}`"
    width="600px"
    :close-on-click-modal="false"
  >
    <div v-if="selectedFileForDetails" class="file-details-content">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="Name">
          {{ selectedFileForDetails.name }}
        </el-descriptions-item>
        <el-descriptions-item label="Type">
          <el-tag :type="selectedFileForDetails.item_type === 'directory' ? 'primary' : 'success'">
            {{ selectedFileForDetails.item_type }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="Size" v-if="selectedFileForDetails.size">
          {{ formatFileSize(selectedFileForDetails.size) }}
        </el-descriptions-item>
        <el-descriptions-item label="Extension" v-if="selectedFileForDetails.extension">
          {{ selectedFileForDetails.extension }}
        </el-descriptions-item>
        <el-descriptions-item label="MIME Type" v-if="selectedFileForDetails.mime_type">
          <code>{{ selectedFileForDetails.mime_type }}</code>
        </el-descriptions-item>
        <el-descriptions-item label="Visibility">
          <el-tag :type="getVisibilityTagType(selectedFileForDetails.visibility)" size="small">
            {{ selectedFileForDetails.visibility }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="Owner">
          {{ selectedFileForDetails.owner.username }}
        </el-descriptions-item>
        <el-descriptions-item label="Created">
          {{ formatDate(selectedFileForDetails.created_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="Last Modified">
          {{ formatDate(selectedFileForDetails.updated_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="Path" :span="2">
          <code>{{ getFilePath(selectedFileForDetails) }}</code>
        </el-descriptions-item>
        <el-descriptions-item label="Permissions" :span="2">
          <div class="permissions-display">
            <el-tag
              v-for="perm in selectedFileForDetails.effective_permissions"
              :key="perm"
              :type="getPermissionTagType(perm)"
              size="small"
              style="margin-right: 8px; margin-bottom: 8px"
            >
              {{ perm }}
            </el-tag>
          </div>
        </el-descriptions-item>
        <el-descriptions-item
          label="Tags"
          :span="2"
          v-if="selectedFileForDetails.tags && selectedFileForDetails.tags.length > 0"
        >
          <div class="tags-display">
            <el-tag
              v-for="tagRel in selectedFileForDetails.tags"
              :key="tagRel.id"
              :color="tagRel.tag.color"
              size="small"
              style="margin-right: 8px; margin-bottom: 8px"
            >
              {{ tagRel.tag.name }}
            </el-tag>
          </div>
        </el-descriptions-item>
      </el-descriptions>
    </div>
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="detailsDialogVisible = false">Close</el-button>
        <el-button
          type="primary"
          @click="handleFileAction('share', selectedFileForDetails)"
          :disabled="!selectedFileForDetails?.can_share"
        >
          <el-icon><Share /></el-icon>
          Share
        </el-button>
      </div>
    </template>
  </el-dialog>

  <!-- Rename Dialog -->
  <el-dialog
    v-model="renameDialogVisible"
    :title="`Rename ${selectedFileForRename?.item_type === 'directory' ? 'Folder' : 'File'}`"
    width="500px"
    :close-on-click-modal="false"
  >
    <el-form :model="renameForm" label-width="80px">
      <el-form-item label="Name">
        <el-input
          v-model="renameForm.name"
          :placeholder="`Enter new ${selectedFileForRename?.item_type === 'directory' ? 'folder' : 'file'} name`"
          @keyup.enter="handleRename"
          ref="renameInputRef"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="renameDialogVisible = false">Cancel</el-button>
        <el-button
          type="primary"
          @click="handleRename"
          :disabled="!renameForm.name.trim() || renameForm.name === selectedFileForRename?.name"
        >
          Rename
        </el-button>
      </div>
    </template>
  </el-dialog>

  <!-- Upload Conflict Dialog -->
  <el-dialog
    v-model="conflictDialogVisible"
    title="File Conflict Detected"
    width="600px"
    :close-on-click-modal="false"
  >
    <div v-if="conflictData" class="conflict-content">
      <div class="conflict-info">
        <el-alert title="File already exists" type="warning" :closable="false" show-icon>
          <template #default>
            <p>
              A file with the name <strong>{{ conflictData.fileName }}</strong> already exists in
              this location.
            </p>
            <p v-if="conflictData.relativePath">
              Path: <code>{{ conflictData.relativePath }}/{{ conflictData.fileName }}</code>
            </p>
          </template>
        </el-alert>
      </div>

      <div class="conflict-options">
        <h4>How would you like to resolve this conflict?</h4>

        <el-radio-group v-model="conflictData.resolveAction" class="conflict-radio-group">
          <el-radio value="rename" class="conflict-radio">
            <div class="radio-content">
              <div class="radio-title">Rename the uploaded file</div>
              <div class="radio-description">Keep the existing file and rename the new one</div>
              <el-input
                v-if="conflictData.resolveAction === 'rename'"
                v-model="conflictData.newName"
                placeholder="Enter new filename"
                style="margin-top: 8px; width: 300px"
                @keyup.enter="handleConflictResolve"
              />
            </div>
          </el-radio>

          <el-radio value="overwrite" class="conflict-radio">
            <div class="radio-content">
              <div class="radio-title">Overwrite the existing file</div>
              <div class="radio-description">Replace the existing file with the new one</div>
            </div>
          </el-radio>
        </el-radio-group>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleConflictSkip">Skip This File</el-button>
        <el-button
          type="primary"
          @click="handleConflictResolve"
          :disabled="
            !conflictData?.resolveAction ||
            (conflictData.resolveAction === 'rename' && !conflictData.newName.trim())
          "
        >
          Continue
        </el-button>
      </div>
    </template>
  </el-dialog>

  <!-- Image Preview -->
  <el-image-viewer
    v-if="imagePreviewVisible"
    :url-list="imagePreviewList"
    :initial-index="imagePreviewInitialIndex"
    :z-index="3000"
    @close="handleImagePreviewClose"
    @switch="handleImagePreviewChange"
  />

  <!-- Loading indicator for image preview -->
  <div
    v-if="imagePreviewVisible && imageLoadingStates.some((loading) => loading)"
    class="image-loading-overlay"
  >
    <el-icon class="is-loading">
      <Loading />
    </el-icon>
    <span>Loading image...</span>
  </div>

  <!-- Loading indicator for directory navigation -->
  <div v-if="isNavigating" class="directory-loading-overlay">
    <el-icon class="is-loading">
      <Loading />
    </el-icon>
    <span>Loading directory...</span>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useFilesStore, type FileItem } from '@/stores/files'
import { uploadAPI, filesAPI } from '@/services/api'
import { tokenStorage } from '@/utils/storage'
import { electronUtils } from '@/utils/electron'
import { config } from '@/config'
import {
  List,
  Menu,
  Picture,
  Document,
  Folder,
  Upload,
  Refresh,
  Back,
  UploadFilled,
  ArrowDown,
  CopyDocument,
  Position,
  Delete,
  Close,
  More,
  Download,
  Share,
  Edit,
  Loading,
  User,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import ShareDialog from '@/components/ShareDialog.vue'
import FileIcon from '@/components/FileIcon.vue'

// Props
interface Props {
  parentId?: string | string[]
}

const props = withDefaults(defineProps<Props>(), {
  parentId: undefined,
})

const router = useRouter()
const route = useRoute()
const filesStore = useFilesStore()
const { t } = useI18n()

// State
const viewType = ref<'grid' | 'large' | 'picture' | 'list'>('list')
const searchQuery = ref('')
const uploadDialogVisible = ref(false)
const imagePreviewVisible = ref(false)
const imagePreviewList = ref<string[]>([])
const imagePreviewInitialIndex = ref(0)
const imageObjectUrls = ref<string[]>([]) // Store object URLs for cleanup
const imageLoadingStates = ref<boolean[]>([]) // Track loading state for each image
const imageFiles = ref<any[]>([]) // Store the actual file objects for lazy loading
const uploadForm = ref({
  visibility: 'private',
})
const fileInputRef = ref<HTMLInputElement>()
const dirInputRef = ref<HTMLInputElement>()
const uploadRef = ref()
const selectedFiles = ref<Array<File>>([])
const selectedFileIds = ref<Set<number>>(new Set())
const uploadProgress = ref<
  Array<{
    filename: string
    status: 'uploading' | 'success' | 'error'
    percentage: number
    error?: string
  }>
>([])
const isUploading = ref(false)
const isNavigating = ref(false)

// Operation dialogs
const copyDialogVisible = ref(false)
const moveDialogVisible = ref(false)
const operationDestination = ref<number | undefined>(undefined)
const operationType = ref<'copy' | 'move'>('copy')

// Share dialog
const shareDialogVisible = ref(false)
const selectedFileForSharing = ref<FileItem | null>(null)

// Details dialog
const detailsDialogVisible = ref(false)
const selectedFileForDetails = ref<FileItem | null>(null)

// Rename dialog
const renameDialogVisible = ref(false)
const selectedFileForRename = ref<FileItem | null>(null)
const renameForm = ref({
  name: '',
})

// Upload conflict dialog
const conflictDialogVisible = ref(false)
const conflictData = ref<{
  fileName: string
  relativePath: string
  existingFile: FileItem | null
  newFile: File
  resolveAction: 'rename' | 'overwrite' | null
  newName: string
} | null>(null)
const pendingUploads = ref<
  Array<{
    file: File
    relativePath: string
    resolveAction: 'rename' | 'overwrite' | 'skip'
    newName?: string
  }>
>([])

// Tree selector configuration for el-tree-select
const treeSelectProps = {
  children: 'children',
  label: 'name',
  value: 'id',
}

// Directory tree data for tree-select (non-lazy)
const directoryTreeData = ref<any[]>([
  {
    id: 0,
    name: 'Root Directory (/)',
    children: [],
  },
])

// Load directory tree data for tree-select
const loadDirectoryTreeData = async () => {
  try {
    const response = await filesAPI.listChildren()
    const rootItems = response.data.children || []
    const directories = rootItems.filter((item: any) => item.item_type === 'directory')

    // Build the tree structure
    const treeData = [
      {
        id: 0,
        name: 'Root Directory (/)',
        children: await buildDirectoryTree(directories),
      },
    ]

    directoryTreeData.value = treeData
  } catch (error) {
    console.error('Failed to load directory tree data:', error)
  }
}

// Recursively build directory tree
const buildDirectoryTree = async (directories: any[]): Promise<any[]> => {
  const tree = []

  for (const dir of directories) {
    try {
      const response = await filesAPI.listChildren(dir.id)
      const children = response.data.children || []
      const childDirs = children.filter((item: any) => item.item_type === 'directory')

      const node = {
        id: dir.id,
        name: dir.name,
        children: childDirs.length > 0 ? await buildDirectoryTree(childDirs) : [],
      }

      tree.push(node)
    } catch (error) {
      console.error(`Failed to load children for directory ${dir.id}:`, error)
      // Add directory without children if loading fails
      tree.push({
        id: dir.id,
        name: dir.name,
        children: [],
      })
    }
  }

  return tree
}

// Tree refs
const listTableRef = ref()
const renameInputRef = ref()

// Upload configuration
const uploadAction = `${config.API_BASE_URL}/api/upload/`
const uploadHeaders = computed(() => {
  const token = document.cookie
    .split('; ')
    .find((row) => row.startsWith('access_token='))
    ?.split('=')[1]
  return {
    Authorization: `Bearer ${token}`,
  }
})
const uploadData = computed(() => ({
  parent_id: currentDirectory.value?.id,
  visibility: uploadForm.value.visibility,
}))

// Computed
const files = computed(() => filesStore.files)
const filteredFiles = computed(() => filesStore.filteredFiles)
const isLoading = computed(() => filesStore.isLoading)
const pagination = computed(() => filesStore.pagination)
const currentDirectory = computed(() => filesStore.currentDirectory)

// Computed for upload functionality
const hasFilesToUpload = computed(() => {
  return selectedFiles.value.length > 0
})

// Computed for bulk operations
const hasSelectedFiles = computed(() => {
  return selectedFileIds.value.size > 0
})

// Directory upload functionality removed - now handled by file upload with relative paths

// Breadcrumb state - maintains the full navigation path
const breadcrumbPath = ref<Array<{ id: number | null; name: string; path: string }>>([
  { id: null, name: 'root', path: '/' },
])

// Utility functions for path construction
const getFilePath = (file: FileItem | null): string => {
  if (!file) return ''

  // If the file has a relative_path, use it (fallback for backward compatibility)
  if (file.relative_path) {
    return file.relative_path
  }

  // Build path from parents array
  if (file.parents && file.parents.length > 0) {
    const parentNames = file.parents.map((parent) => parent.name)
    return '/' + parentNames.join('/') + '/' + file.name
  }

  // If no parents, it's a root-level file
  return '/' + file.name
}

const getDirectoryPath = (
  directory: FileItem | { id: number; name: string; relative_path?: string } | null,
): string => {
  if (!directory) return '/'

  // If the directory has a relative_path, use it (fallback for backward compatibility)
  if (directory.relative_path) {
    return directory.relative_path
  }

  // Build path from parents array (only for full FileItem objects)
  if ('parents' in directory && directory.parents && directory.parents.length > 0) {
    const parentNames = directory.parents.map((parent) => parent.name)
    return '/' + parentNames.join('/') + '/' + directory.name
  }

  // If no parents, it's a root-level directory
  return '/' + directory.name
}

// Update breadcrumb when directory changes
const updateBreadcrumb = async () => {
  console.log('updateBreadcrumb called, currentDirectory:', currentDirectory.value)

  if (!currentDirectory.value) {
    console.log('No current directory, setting root breadcrumb')
    breadcrumbPath.value = [{ id: null, name: 'root', path: '/' }]
    return
  }

  // Debug: Log the complete current directory object
  console.log('Current directory full object:', JSON.stringify(currentDirectory.value, null, 2))
  console.log('Parents attribute:', currentDirectory.value.parents)
  console.log('Parents type:', typeof currentDirectory.value.parents)
  console.log('Parents is array:', Array.isArray(currentDirectory.value.parents))

  // Build breadcrumb using the parents attribute from the API
  const newBreadcrumb = []

  // Always start with root
  newBreadcrumb.push({
    id: null,
    name: 'root',
    path: '/',
  })

  // Add all parent directories from the parents array (if available)
  if (
    currentDirectory.value.parents &&
    Array.isArray(currentDirectory.value.parents) &&
    currentDirectory.value.parents.length > 0
  ) {
    console.log('Adding parents from API:', currentDirectory.value.parents)

    currentDirectory.value.parents.forEach((parent) => {
      newBreadcrumb.push({
        id: parent.id,
        name: parent.name,
        path: parent.relative_path || getDirectoryPath(parent),
      })
    })
  } else {
    console.log(
      'No parents attribute available, breadcrumb will only show root and current directory',
    )
  }

  // Add current directory at the end
  newBreadcrumb.push({
    id: currentDirectory.value.id,
    name: currentDirectory.value.name,
    path: currentDirectory.value.relative_path || getDirectoryPath(currentDirectory.value),
  })

  console.log('Built complete breadcrumb:', newBreadcrumb)
  breadcrumbPath.value = newBreadcrumb
}

// Watch for route changes to load appropriate directory
watch(
  () => props.parentId,
  async (newParentId, oldParentId) => {
    console.log('parentId watcher triggered:', {
      old: oldParentId,
      new: newParentId,
      isImmediate: oldParentId === undefined,
    })

    // Show loading state for directory changes (but not on initial load)
    if (oldParentId !== undefined) {
      isNavigating.value = true
    }

    try {
      if (newParentId) {
        // Navigate to specific directory
        console.log('Loading directory:', newParentId)
        await filesStore.fetchChildren(Number(newParentId))
      } else {
        // Navigate to root (parent_id is undefined or was removed)
        console.log('Loading root directory')
        await filesStore.fetchChildren()
      }

      // Update breadcrumb after loading
      await updateBreadcrumb()
    } finally {
      // Hide loading state
      isNavigating.value = false
    }
  },
  { immediate: true },
)

// Watch for directory changes to update breadcrumb
watch(
  currentDirectory,
  (newDir, oldDir) => {
    console.log('currentDirectory changed:', { old: oldDir, new: newDir })
    updateBreadcrumb()
  },
  { immediate: true },
)

// Watch for selected files changes
watch(
  selectedFiles,
  (newFiles, oldFiles) => {
    console.log('selectedFiles changed:', {
      old: oldFiles?.length || 0,
      new: newFiles?.length || 0,
      files: newFiles?.map((f) => f.name) || [],
    })
  },
  { deep: true },
)

// Methods
const setViewType = (type: 'grid' | 'large' | 'picture' | 'list') => {
  viewType.value = type
}

const handleSortChange = (sortInfo: { prop: string; order: string }) => {
  console.log('Sort changed:', sortInfo)
  // The table handles sorting automatically, but we can add custom logic here if needed
}

const triggerFileSelection = () => {
  fileInputRef.value?.click()
}

const triggerDirectorySelection = () => {
  dirInputRef.value?.click()
}

const handleUploadCommand = (command: string) => {
  if (command === 'files') {
    triggerFileSelection()
  } else if (command === 'directory') {
    triggerDirectorySelection()
  }
}

const handleFileSelection = async (event: Event) => {
  const target = event.target as HTMLInputElement
  const files = Array.from(target.files || [])

  if (files.length === 0) return

  // Reset progress
  uploadProgress.value = []
  isUploading.value = true

  try {
    // Process files and create directory structure
    await processAndUploadFiles(files)
  } catch (error: any) {
    ElMessage.error(`Upload failed: ${error.message || error}`)
  } finally {
    isUploading.value = false
    // Reset file input
    if (target) target.value = ''
  }
}

const handleDirectorySelection = async (event: Event) => {
  const target = event.target as HTMLInputElement
  const files = Array.from(target.files || [])

  if (files.length === 0) return

  // Reset progress
  uploadProgress.value = []
  isUploading.value = true

  try {
    // Process directory files with relative paths
    await processAndUploadFiles(files)
  } catch (error: any) {
    ElMessage.error(`Upload failed: ${error.message || error}`)
  } finally {
    isUploading.value = false
    // Reset directory input
    if (target) target.value = ''
  }
}

const processAndUploadFiles = async (files: File[]) => {
  // Upload all files with their relative paths
  await uploadAllFiles(files)

  // Refresh file list
  await refreshFiles()
  ElMessage.success(`Upload completed: ${files.length} files processed`)
}

// Directory creation now handled by backend during file upload

const uploadAllFiles = async (files: File[]) => {
  const batchSize = 3
  let uploadedCount = 0
  let failedCount = 0
  let skippedCount = 0

  // Initialize progress for all files
  files.forEach((file) => {
    uploadProgress.value.push({
      filename: file.webkitRelativePath,
      status: 'uploading',
      percentage: 0,
    })
  })

  // Process files one by one to handle conflicts
  for (let i = 0; i < files.length; i++) {
    let file = files[i]

    try {
      // Get the relative path for this file
      const pathParts = file.webkitRelativePath.split('/')
      const fileName = pathParts.pop()! // Remove filename
      const relativePath = pathParts.join('/') // Keep directory path

      // Check for conflicts before uploading
      const conflictResult = await checkForConflict(fileName, relativePath)

      if (conflictResult.hasConflict) {
        // Show conflict dialog and wait for user decision
        const resolution = await showConflictDialog(
          file,
          fileName,
          relativePath,
          conflictResult.existingFile,
          conflictResult.existingFiles,
        )

        if (resolution.action === 'skip') {
          uploadProgress.value[i].status = 'error'
          uploadProgress.value[i].error = 'Skipped due to conflict'
          skippedCount++
          continue
        }

        // Handle overwrite action - use PATCH request to update existing file
        if (resolution.action === 'overwrite' && conflictResult.existingFile) {
          console.log('Overwriting existing file:', {
            fileId: conflictResult.existingFile.id,
            fileName: file.name,
            fileSize: file.size,
          })

          // Create progress callback for overwrite operation
          const overwriteProgressCallback = (progressEvent: any) => {
            if (progressEvent.total) {
              const percentage = Math.round((progressEvent.loaded * 100) / progressEvent.total)
              uploadProgress.value[i].percentage = percentage
            }
          }

          // Use the store's updateFileContent method which makes a PATCH request
          const success = await filesStore.updateFileContent(
            conflictResult.existingFile.id,
            file,
            overwriteProgressCallback,
          )

          if (success) {
            uploadProgress.value[i].status = 'success'
            uploadProgress.value[i].percentage = 100
            uploadedCount++
          } else {
            uploadProgress.value[i].status = 'error'
            uploadProgress.value[i].error = 'Failed to overwrite file'
            failedCount++
          }
          continue
        }

        // Update file name if renaming
        if (resolution.action === 'rename' && resolution.newName) {
          // Create a new File object with the new name
          file = new File([file], resolution.newName, { type: file.type })
        }
      }

      // Create FormData for upload (only for new files or renamed files)
      const formData = new FormData()
      formData.append('file', file)
      formData.append('visibility', uploadForm.value.visibility)
      if (currentDirectory.value?.id) {
        formData.append('parent_id', currentDirectory.value.id.toString())
      }
      if (relativePath) {
        formData.append('relative_path', relativePath)
      }

      // Upload the file - backend will handle directory creation
      console.log('Uploading new file via POST request:', {
        fileName: file.name,
        fileSize: file.size,
        relativePath,
      })

      // Create progress callback for this specific file
      const progressCallback = (progressEvent: any) => {
        if (progressEvent.total) {
          const percentage = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          uploadProgress.value[i].percentage = percentage
        }
      }

      await uploadAPI.upload(formData, progressCallback)

      // Update progress
      uploadProgress.value[i].status = 'success'
      uploadProgress.value[i].percentage = 100
      uploadedCount++
    } catch (error: any) {
      // Update progress with error
      uploadProgress.value[i].status = 'error'
      uploadProgress.value[i].error =
        error.response?.data?.error || error.message || 'Upload failed'
      failedCount++
    }

    // Small delay between uploads
    if (i < files.length - 1) {
      await new Promise((resolve) => setTimeout(resolve, 200))
    }
  }

  // Show final results
  const totalProcessed = uploadedCount + failedCount + skippedCount
  if (failedCount === 0 && skippedCount === 0) {
    ElMessage.success(`All ${files.length} files uploaded successfully!`)
  } else {
    ElMessage.warning(`${uploadedCount} uploaded, ${failedCount} failed, ${skippedCount} skipped.`)
  }
}

// Directory lookup methods removed - no longer needed with simplified backend approach

const openUpload = () => {
  uploadDialogVisible.value = true
  // Reset selected files when opening upload dialog
  selectedFiles.value = []
}

const closeUploadDialog = () => {
  uploadDialogVisible.value = false
  // Reset selected files when closing upload dialog
  selectedFiles.value = []
  // Reset upload progress
  uploadProgress.value = []
}

const showCreateDirectoryDialog = () => {
  ElMessageBox.prompt('Enter folder name:', 'Create New Folder', {
    confirmButtonText: 'Create',
    cancelButtonText: 'Cancel',
    inputPattern: /^[^\/\\]+$/,
    inputErrorMessage: 'Folder name cannot contain slashes or backslashes',
  })
    .then(async ({ value }) => {
      if (value) {
        // Create directory within current directory
        const parentId = currentDirectory.value?.id
        const newDirectory = await filesStore.createDirectory(value, parentId)
        if (newDirectory) {
          ElMessage.success('Folder created successfully')
          // Refresh the current directory contents
          await refreshFiles()
        }
      }
    })
    .catch(() => {
      // User cancelled
    })
}

const handleCreateCommand = (command: string) => {
  switch (command) {
    case 'directory':
      showCreateDirectoryDialog()
      break
    case 'text':
      showCreateTextFileDialog()
      break
    case 'word':
      showCreateWordDocumentDialog()
      break
    case 'excel':
      showCreateExcelDocumentDialog()
      break
    case 'powerpoint':
      showCreatePowerPointDocumentDialog()
      break
  }
}

const showCreateTextFileDialog = () => {
  ElMessageBox.prompt('Enter file name:', 'Create Text File', {
    confirmButtonText: 'Create',
    cancelButtonText: 'Cancel',
    inputPattern: /^[^\/\\]+$/,
    inputErrorMessage: 'File name cannot contain slashes or backslashes',
    inputPlaceholder: 'my-file.txt',
  })
    .then(async ({ value }) => {
      if (value) {
        try {
          const parentId = currentDirectory.value?.id
          const response = await filesAPI.createTextFile({
            name: value,
            content: '',
            parent_id: parentId,
            visibility: 'private',
          })

          if (response.data) {
            ElMessage.success('Text file created successfully')
            await refreshFiles()
          }
        } catch (error: any) {
          ElMessage.error(error.response?.data?.error || 'Failed to create text file')
        }
      }
    })
    .catch(() => {
      // User cancelled
    })
}

const showCreateWordDocumentDialog = () => {
  ElMessageBox.prompt('Enter document name:', 'Create Word Document', {
    confirmButtonText: 'Create',
    cancelButtonText: 'Cancel',
    inputPattern: /^[^\/\\]+$/,
    inputErrorMessage: 'Document name cannot contain slashes or backslashes',
    inputPlaceholder: 'my-document.docx',
  })
    .then(async ({ value }) => {
      if (value) {
        try {
          const parentId = currentDirectory.value?.id
          if (!value.endsWith('.docx')) {
            value += '.docx'
          }

          const response = await filesAPI.createOfficeDocument({
            name: value,
            document_type: 'docx',
            parent_id: parentId,
            visibility: 'private',
          })

          if (response.data) {
            ElMessage.success('Word document created successfully')
            await refreshFiles()
          }
        } catch (error: any) {
          ElMessage.error(error.response?.data?.error || 'Failed to create Word document')
        }
      }
    })
    .catch(() => {
      // User cancelled
    })
}

const showCreateExcelDocumentDialog = () => {
  ElMessageBox.prompt('Enter spreadsheet name:', 'Create Excel Spreadsheet', {
    confirmButtonText: 'Create',
    cancelButtonText: 'Cancel',
    inputPattern: /^[^\/\\]+$/,
    inputErrorMessage: 'Document name cannot contain slashes or backslashes',
    inputPlaceholder: 'my-spreadsheet.xlsx',
  })
    .then(async ({ value }) => {
      if (value) {
        try {
          const parentId = currentDirectory.value?.id
          if (!value.endsWith('.xlsx')) {
            value += '.xlsx'
          }

          const response = await filesAPI.createOfficeDocument({
            name: value,
            document_type: 'xlsx',
            parent_id: parentId,
            visibility: 'private',
          })

          if (response.data) {
            ElMessage.success('Excel spreadsheet created successfully')
            await refreshFiles()
          }
        } catch (error: any) {
          ElMessage.error(error.response?.data?.error || 'Failed to create Excel spreadsheet')
        }
      }
    })
    .catch(() => {
      // User cancelled
    })
}

const showCreatePowerPointDocumentDialog = () => {
  ElMessageBox.prompt('Enter presentation name:', 'Create PowerPoint Presentation', {
    confirmButtonText: 'Create',
    cancelButtonText: 'Cancel',
    inputPattern: /^[^\/\\]+$/,
    inputErrorMessage: 'Document name cannot contain slashes or backslashes',
    inputPlaceholder: 'my-presentation.pptx',
  })
    .then(async ({ value }) => {
      if (value) {
        try {
          const parentId = currentDirectory.value?.id
          if (!value.endsWith('.pptx')) {
            value += '.pptx'
          }

          const response = await filesAPI.createOfficeDocument({
            name: value,
            document_type: 'pptx',
            parent_id: parentId,
            visibility: 'private',
          })

          if (response.data) {
            ElMessage.success('PowerPoint presentation created successfully')
            await refreshFiles()
          }
        } catch (error: any) {
          ElMessage.error(error.response?.data?.error || 'Failed to create PowerPoint presentation')
        }
      }
    })
    .catch(() => {
      // User cancelled
    })
}

// Upload methods
const handleUpload = () => {
  if (uploadRef.value) {
    // Get the file list from the upload component
    const fileList = uploadRef.value.uploadFiles || []

    if (fileList.length === 0) {
      ElMessage.warning('Please select files to upload.')
      return
    }

    // Submit all files
    uploadRef.value.submit()
  }
}

const handleUploadSuccess = (response: any, file: any) => {
  ElMessage.success(`${file.name} uploaded successfully`)
  // Refresh the file list to show the new file
  refreshFiles()
}

const handleUploadComplete = () => {
  // Clear selected files after all uploads are complete
  selectedFiles.value = []
}

const handleUploadError = (error: any, file: any) => {
  ElMessage.error(`${file.name} upload failed: ${error.message || 'Unknown error'}`)
}

const beforeUpload = (file: any) => {
  return true
}

const handleFileChange = (file: any, fileList: any) => {
  console.log('File changed:', file, 'File list:', fileList)
  // Update the selected files array
  selectedFiles.value = fileList.map((f: any) => f.raw || f)
}

const handleFileRemove = (file: any, fileList: any) => {
  console.log('File removed:', file, 'File list:', fileList)
  // Update the selected files array
  selectedFiles.value = fileList.map((f: any) => f.raw || f)
}

const handleUploadProgress = (event: any, file: any) => {
  console.log(`Upload progress for ${file.name}:`, event.percent)
  // You can add progress tracking logic here if needed
}

const handleFileExceed = (files: any, fileList: any) => {
  ElMessage.warning(`Maximum ${fileList.length} files allowed. Please remove some files first.`)
}

// Directory selection method removed - now handled by file input with webkitdirectory

// Directory scanning method removed - no longer needed

// Directory upload method removed - now handled by file upload with relative paths

// handleBulkFileUpload method removed - no longer needed with simplified upload approach

// Directory handle methods removed - no longer needed

const refreshFiles = async () => {
  // Use current route parent_id to determine which directory to refresh
  const parentId = props.parentId ? Number(props.parentId) : undefined
  await filesStore.fetchChildren(parentId)
}

const handleSearch = async (value: string) => {
  searchQuery.value = value

  // If there's a search query, perform the search
  if (value.trim()) {
    // Use unified search API - pass node_id if in a directory, otherwise global search
    await filesStore.searchFiles(value, {
      node_id: currentDirectory.value?.id,
      recursive: true,
      limit: 100,
    })
  } else {
    // Clear search, refresh current directory
    await refreshFiles()
  }
}

// Image file detection
const isImageFile = (file: any): boolean => {
  const mimeType = file.mime_type || file.file_info?.mime_type || ''
  const extension = file.extension || file.file_info?.extension || ''
  const fileName = file.name.toLowerCase()

  // Check by MIME type
  if (mimeType.startsWith('image/')) {
    return true
  }

  // Check by file extension from file_info
  if (extension && /\.(jpg|jpeg|png|gif|webp|svg|bmp)$/i.test(extension)) {
    return true
  }

  // Fallback to filename extension
  return /\.(jpg|jpeg|png|gif|webp|svg|bmp)$/i.test(fileName)
}

// Get all image files in current directory
const getImageFiles = (): any[] => {
  return filteredFiles.value.filter((file) => file.item_type === 'file' && isImageFile(file))
}

// Clean up object URLs to prevent memory leaks
const cleanupImageObjectUrls = () => {
  imageObjectUrls.value.forEach((url) => {
    URL.revokeObjectURL(url)
  })
  imageObjectUrls.value = []
  imagePreviewList.value = []
  imageLoadingStates.value = []
  imageFiles.value = []
}

// Handle image preview close
const handleImagePreviewClose = () => {
  imagePreviewVisible.value = false
  cleanupImageObjectUrls()
}

// Handle image preview change (when user navigates to different image)
const handleImagePreviewChange = (index: number) => {
  // Load the image at the new index if not already loaded
  loadImageLazy(index)

  // Preload adjacent images for smoother navigation
  if (index > 0) {
    loadImageLazy(index - 1) // Previous image
  }
  if (index < imageFiles.value.length - 1) {
    loadImageLazy(index + 1) // Next image
  }
}

// Show image preview
const showImagePreview = async (clickedFile: any) => {
  const currentImageFiles = getImageFiles()

  if (currentImageFiles.length === 0) {
    ElMessage.warning('No images found in current directory')
    return
  }

  // Find the index of the clicked image
  const clickedIndex = currentImageFiles.findIndex((file) => file.id === clickedFile.id)

  if (clickedIndex === -1) {
    ElMessage.warning('Image not found in current directory')
    return
  }

  try {
    // Clean up previous object URLs
    cleanupImageObjectUrls()

    // Store the file objects for lazy loading
    imageFiles.value = currentImageFiles

    // Initialize arrays with placeholders
    const previewUrls: string[] = new Array(currentImageFiles.length).fill('')
    const loadingStates: boolean[] = new Array(currentImageFiles.length).fill(false) // Start as not loading

    // Set up the preview immediately
    imagePreviewList.value = previewUrls
    imagePreviewInitialIndex.value = clickedIndex
    imageLoadingStates.value = loadingStates
    imagePreviewVisible.value = true

    // Load only the clicked image initially
    await loadImageLazy(clickedIndex)
  } catch (error) {
    console.error('Error setting up image preview:', error)
    ElMessage.error('Failed to set up image preview')
  }
}

// Load a single image lazily (only when needed)
const loadImageLazy = async (index: number) => {
  if (!imageFiles.value[index]) {
    console.error(`No file found at index ${index}`)
    return
  }

  const file = imageFiles.value[index]

  // Check if already loaded
  if (imagePreviewList.value[index] && imagePreviewList.value[index] !== '') {
    return
  }

  // Set loading state
  const newLoadingStates = [...imageLoadingStates.value]
  newLoadingStates[index] = true
  imageLoadingStates.value = newLoadingStates

  try {
    const response = await filesAPI.download(file.id)
    const blob = new Blob([response.data])
    const objectUrl = URL.createObjectURL(blob)

    // Update the specific index
    const newPreviewUrls = [...imagePreviewList.value]
    newPreviewUrls[index] = objectUrl
    imagePreviewList.value = newPreviewUrls

    // Add to object URLs for cleanup
    imageObjectUrls.value.push(objectUrl)

    // Update loading state
    const updatedLoadingStates = [...imageLoadingStates.value]
    updatedLoadingStates[index] = false
    imageLoadingStates.value = updatedLoadingStates
  } catch (error) {
    console.error(`Error loading image ${file.name}:`, error)

    // Set error placeholder
    const newPreviewUrls = [...imagePreviewList.value]
    newPreviewUrls[index] =
      'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgZmlsbD0iI2Y1ZjVmNSIvPjx0ZXh0IHg9IjUwIiB5PSI1MCIgZm9udC1mYW1pbHk9IkFyaWFsIiBmb250LXNpemU9IjEyIiBmaWxsPSIjOTk5IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkeT0iLjNlbSI+RXJyb3I8L3RleHQ+PC9zdmc+'
    imagePreviewList.value = newPreviewUrls

    // Update loading state even on error
    const updatedLoadingStates = [...imageLoadingStates.value]
    updatedLoadingStates[index] = false
    imageLoadingStates.value = updatedLoadingStates
  }
}

const handleFileClick = async (file: any) => {
  if (file.item_type === 'directory') {
    // Navigate to directory using router
    // Loading state will be handled by the parentId watcher
    console.log('Starting directory navigation to:', file.name, file.id)
    await navigateToDirectory(file.id)
  } else {
    // Check if it's an image file
    if (isImageFile(file)) {
      // For images, show image preview with all images in current directory
      showImagePreview(file)
    } else {
      // For other files, navigate to file detail page
      await router.push({ name: 'FileDetails', params: { id: file.id.toString() } })
    }
  }
}

const openFileInBrowser = async (file: any) => {
  try {
    // Check if file type can be displayed in browser
    const mimeType = file.mime_type || file.file_info?.mime_type || ''
    const fileName = file.name.toLowerCase()

    // Define file types that can be opened in browser
    const browserSupportedTypes = [
      // Images
      'image/jpeg',
      'image/jpg',
      'image/png',
      'image/gif',
      'image/webp',
      'image/svg+xml',
      'image/bmp',
      // Documents
      'application/pdf',
      'text/plain',
      'text/html',
      'text/css',
      'text/javascript',
      'application/json',
      'text/xml',
      'application/xml',
      'text/csv',
      // Audio/Video (some browsers support these)
      'audio/mpeg',
      'audio/wav',
      'audio/ogg',
      'video/mp4',
      'video/webm',
      'video/ogg',
    ]

    // Check by MIME type or file extension
    const isSupportedByMime = browserSupportedTypes.includes(mimeType)
    const isSupportedByExtension = [
      '.jpg',
      '.jpeg',
      '.png',
      '.gif',
      '.webp',
      '.svg',
      '.bmp',
      '.pdf',
      '.txt',
      '.html',
      '.htm',
      '.css',
      '.js',
      '.json',
      '.xml',
      '.csv',
      '.mp3',
      '.wav',
      '.ogg',
      '.mp4',
      '.webm',
    ].some((ext) => fileName.endsWith(ext))

    if (isSupportedByMime || isSupportedByExtension) {
      // Open file in new tab using the dedicated file viewer route
      const fileViewerUrl = `/view/${file.id}`
      window.open(fileViewerUrl, '_blank')
    } else {
      // For unsupported files, show details or download
      ElMessage.info(`File type not supported for browser preview. Use download option.`)
      // Optionally, you could still open the details dialog here
      // showFileDetails(file)
    }
  } catch (error) {
    console.error('Error opening file in browser:', error)
    ElMessage.error('Failed to open file in browser')
  }
}

const handleListRowClick = (row: any, column: any, event: Event) => {
  // Don't navigate if clicking on selection checkbox or actions column
  if (column.type === 'selection' || column.label === 'Actions') {
    return
  }
  handleFileClick(row)
}

const navigateToDirectory = async (directoryId: number) => {
  console.log('navigateToDirectory called with ID:', directoryId)
  // Use router navigation instead of direct store calls
  await router.push({
    name: 'Files',
    query: { parent_id: directoryId.toString() },
  })
}

const navigateToRoot = async () => {
  console.log('navigateToRoot called')
  // Use router navigation to root
  await router.push({
    name: 'Files',
    query: {},
  })
}

const handleBreadcrumbClick = async (item: { id: number | null; name: string; path: string }) => {
  if (item.id === null) {
    // Clicked on root
    await navigateToRoot()
  } else {
    // Clicked on a directory in the breadcrumb
    console.log('Navigating to breadcrumb directory:', item)
    // Navigate to this directory using router
    await navigateToDirectory(item.id)
  }
  // Loading state will be handled by the parentId watcher
}

// File operation methods
const toggleFileSelection = (fileId: number, checked: boolean) => {
  if (checked) {
    selectedFileIds.value.add(fileId)
  } else {
    selectedFileIds.value.delete(fileId)
  }
}

const clearSelection = () => {
  selectedFileIds.value.clear()
  // Clear table selection if list view is active
  if (viewType.value === 'list' && listTableRef.value) {
    listTableRef.value.clearSelection()
  }
}

const showCopyDialog = () => {
  operationType.value = 'copy'
  operationDestination.value = undefined
  copyDialogVisible.value = true
  console.log('Copy dialog opened')

  // Load directory tree data when dialog opens
  loadDirectoryTreeData()
}

const showMoveDialog = () => {
  operationType.value = 'move'
  operationDestination.value = undefined
  moveDialogVisible.value = true
  console.log('Move dialog opened')

  // Load directory tree data when dialog opens
  loadDirectoryTreeData()
}

const confirmDelete = async () => {
  try {
    await ElMessageBox.confirm(
      t('files.messages.deleteConfirm', { count: selectedFileIds.value.size }),
      t('common.confirmDelete'),
      {
        confirmButtonText: t('common.delete'),
        cancelButtonText: t('common.cancel'),
        type: 'warning',
      },
    )

    const fileIds = Array.from(selectedFileIds.value)
    await filesStore.deleteFiles(fileIds)
    clearSelection()
  } catch (error) {
    // User cancelled
  }
}

const handleFileAction = async (command: string, file: any) => {
  if (command === 'copy') {
    selectedFileIds.value.clear()
    selectedFileIds.value.add(file.id)
    showCopyDialog()
  } else if (command === 'move') {
    selectedFileIds.value.clear()
    selectedFileIds.value.add(file.id)
    showMoveDialog()
  } else if (command === 'download') {
    if (file.item_type === 'file') {
      await downloadFile(file)
    }
  } else if (command === 'delete') {
    selectedFileIds.value.clear()
    selectedFileIds.value.add(file.id)
    await confirmDelete()
  } else if (command === 'share') {
    selectedFileForSharing.value = file
    shareDialogVisible.value = true
  } else if (command === 'details') {
    selectedFileForDetails.value = file
    detailsDialogVisible.value = true
  } else if (command === 'rename') {
    selectedFileForRename.value = file
    renameForm.value.name = file.name
    renameDialogVisible.value = true
    // Focus the input after dialog opens
    nextTick(() => {
      renameInputRef.value?.focus()
    })
  }
}

const handlePermissionsUpdated = () => {
  // Refresh the current directory contents to get updated permission information
  if (currentDirectory.value) {
    filesStore.fetchChildren(currentDirectory.value.id)
  } else {
    filesStore.fetchChildren()
  }
}

const handleRename = async () => {
  if (!selectedFileForRename.value || !renameForm.value.name.trim()) {
    return
  }

  const newName = renameForm.value.name.trim()
  const oldName = selectedFileForRename.value.name

  // Don't rename if the name hasn't changed
  if (newName === oldName) {
    renameDialogVisible.value = false
    return
  }

  try {
    // Call the API to rename the file
    await filesAPI.patch(selectedFileForRename.value.id, { name: newName })

    ElMessage.success(
      `${selectedFileForRename.value.item_type === 'directory' ? 'Folder' : 'File'} renamed successfully`,
    )

    // Close the dialog
    renameDialogVisible.value = false

    // Refresh the file list to show the updated name
    await refreshFiles()
  } catch (error: any) {
    console.error('Rename error:', error)
    ElMessage.error(
      `Rename failed: ${error.response?.data?.error || error.message || 'Unknown error'}`,
    )
  }
}

// Conflict detection and resolution functions
const checkForConflict = async (fileName: string, relativePath: string) => {
  try {
    // If there's a relative path, we need to navigate to that subdirectory
    let targetDirectoryId = currentDirectory.value?.id

    if (relativePath) {
      // Find or create the target directory
      targetDirectoryId = await findOrCreateDirectory(relativePath, currentDirectory.value?.id)
    }

    // Get directory contents to check for conflicts
    const response = await filesAPI.listChildren(targetDirectoryId)
    const children = response.data.children || []

    // Find existing file with the same name
    const existingFile = children.find(
      (item: any) => item.name === fileName && item.item_type === 'file',
    )

    // Get all existing files in the directory for unique name generation
    const existingFiles = children.filter((item: any) => item.item_type === 'file')

    return {
      hasConflict: !!existingFile,
      existingFile: existingFile || null,
      existingFiles: existingFiles,
    }
  } catch (error) {
    console.error('Error checking for conflicts:', error)
    return { hasConflict: false, existingFile: null, existingFiles: [] }
  }
}

const findOrCreateDirectory = async (
  relativePath: string,
  parentId?: number,
): Promise<number | undefined> => {
  try {
    const pathParts = relativePath.split('/').filter((part) => part.length > 0)
    let currentParentId = parentId

    for (const dirName of pathParts) {
      // Check if directory exists
      const response = await filesAPI.listChildren(currentParentId)
      const children = response.data.children || []

      let existingDir = children.find(
        (item: any) => item.name === dirName && item.item_type === 'directory',
      )

      if (!existingDir) {
        // Create directory if it doesn't exist
        const createResponse = await filesAPI.createDirectory({
          name: dirName,
          parent_id: currentParentId,
          visibility: uploadForm.value.visibility,
        })
        existingDir = createResponse.data
      }

      currentParentId = existingDir.id
    }

    return currentParentId
  } catch (error) {
    console.error('Error finding or creating directory:', error)
    return parentId
  }
}

const showConflictDialog = (
  file: File,
  fileName: string,
  relativePath: string,
  existingFile: any,
  existingFiles: FileItem[],
): Promise<{ action: 'rename' | 'overwrite' | 'skip'; newName?: string }> => {
  return new Promise((resolve) => {
    conflictData.value = {
      fileName,
      relativePath,
      existingFile,
      newFile: file,
      resolveAction: null,
      newName: generateUniqueFileName(fileName, existingFiles),
    }

    conflictDialogVisible.value = true

    // Store the resolve function to be called by dialog handlers
    ;(conflictData.value as any).resolve = resolve
  })
}

const generateUniqueFileName = (originalName: string, existingFiles: FileItem[]): string => {
  const lastDotIndex = originalName.lastIndexOf('.')
  let nameWithoutExt: string
  let extension: string

  if (lastDotIndex === -1) {
    nameWithoutExt = originalName
    extension = ''
  } else {
    nameWithoutExt = originalName.substring(0, lastDotIndex)
    extension = originalName.substring(lastDotIndex)
  }

  // Check if the original name is already unique
  const isOriginalUnique = !existingFiles.some(
    (file) => file.name === originalName && file.item_type === 'file',
  )

  if (isOriginalUnique) {
    return originalName
  }

  // Find the next available number
  let counter = 1
  let newName: string

  do {
    newName = `${nameWithoutExt} (${counter})${extension}`
    counter++
  } while (existingFiles.some((file) => file.name === newName && file.item_type === 'file'))

  return newName
}

const handleConflictResolve = () => {
  if (!conflictData.value) return

  const resolve = (conflictData.value as any).resolve
  if (resolve) {
    resolve({
      action: conflictData.value.resolveAction!,
      newName:
        conflictData.value.resolveAction === 'rename' ? conflictData.value.newName : undefined,
    })
  }

  conflictDialogVisible.value = false
  conflictData.value = null
}

const handleConflictSkip = () => {
  if (!conflictData.value) return

  const resolve = (conflictData.value as any).resolve
  if (resolve) {
    resolve({ action: 'skip' })
  }

  conflictDialogVisible.value = false
  conflictData.value = null
}

const downloadFile = async (file: any) => {
  try {
    // Use Electron utility for download
    await electronUtils.downloadFile(file.id, file.name, true)
    ElMessage.success(`Download started for ${file.name}`)
  } catch (error: any) {
    console.error('Download error:', error)
    ElMessage.error(
      `Download failed: ${error.response?.data?.error || error.message || 'Unknown error'}`,
    )
  }
}

const bulkDownload = async () => {
  try {
    const selectedFiles = Array.from(selectedFileIds.value)
      .map((id) => filteredFiles.value.find((file) => file.id === id))
      .filter((file) => file && file.item_type === 'file')

    if (selectedFiles.length === 0) {
      ElMessage.warning('No files selected for download')
      return
    }

    ElMessage.info(`Downloading ${selectedFiles.length} file(s)...`)

    // Download files one by one
    for (const file of selectedFiles) {
      if (file) {
        try {
          await downloadFile(file)
          // Small delay between downloads to avoid overwhelming the browser
          await new Promise((resolve) => setTimeout(resolve, 100))
        } catch (error) {
          console.error(`Failed to download ${file.name}:`, error)
          ElMessage.error(`Failed to download ${file.name}`)
        }
      }
    }

    ElMessage.success(`Bulk download completed`)
  } catch (error: any) {
    console.error('Bulk download error:', error)
    ElMessage.error(`Bulk download failed: ${error.message || 'Unknown error'}`)
  }
}

const handleListSelectionChange = (selection: any[]) => {
  // Update selectedFileIds based on table selection
  selectedFileIds.value.clear()
  selection.forEach((item) => {
    selectedFileIds.value.add(item.id)
  })
}

const executeOperation = async () => {
  if (operationDestination.value === undefined) {
    ElMessage.warning('Please select a destination directory')
    return
  }

  try {
    const fileIds = Array.from(selectedFileIds.value)

    if (operationType.value === 'copy') {
      await filesStore.copyFiles(fileIds, operationDestination.value)
      copyDialogVisible.value = false
    } else if (operationType.value === 'move') {
      await filesStore.moveFiles(fileIds, operationDestination.value)
      moveDialogVisible.value = false
    }

    operationDestination.value = undefined
    clearSelection()
  } catch (error: any) {
    ElMessage.error(`Operation failed: ${error.message || error}`)
  }
}

// Utility methods
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatDate = (dateString: string | null): string => {
  if (!dateString) return '-'
  try {
    const date = new Date(dateString)
    return (
      date.toLocaleDateString() +
      ' ' +
      date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    )
  } catch {
    return '-'
  }
}

// Sorting methods for table columns
const sortByName = (a: any, b: any): number => {
  const nameA = a.name.toLowerCase()
  const nameB = b.name.toLowerCase()

  // Directories first, then files
  if (a.item_type === 'directory' && b.item_type !== 'directory') return -1
  if (a.item_type !== 'directory' && b.item_type === 'directory') return 1

  return nameA.localeCompare(nameB)
}

const sortBySize = (a: any, b: any): number => {
  // Directories first (no size)
  if (a.item_type === 'directory' && b.item_type !== 'directory') return -1
  if (a.item_type !== 'directory' && b.item_type === 'directory') return 1

  const sizeA = a.file_info?.size || 0
  const sizeB = b.file_info?.size || 0

  return sizeA - sizeB
}

const sortByDate = (a: any, b: any): number => {
  const dateA = a.created_at ? new Date(a.created_at).getTime() : 0
  const dateB = b.created_at ? new Date(b.created_at).getTime() : 0

  return dateA - dateB
}

const getVisibilityTagType = (visibility: string): string => {
  switch (visibility) {
    case 'public':
      return 'success'
    case 'group':
      return 'warning'
    case 'user':
      return 'info'
    case 'private':
      return 'danger'
    default:
      return 'info'
  }
}

const getPermissionTagType = (permission: string): string => {
  switch (permission) {
    case 'read':
      return 'info'
    case 'write':
      return 'warning'
    case 'delete':
      return 'danger'
    case 'share':
      return 'success'
    case 'admin':
      return 'danger'
    default:
      return 'info'
  }
}

// Lifecycle
onMounted(async () => {
  await filesStore.fetchDirectoryTree()
  // Directory loading is handled by the parentId watcher with immediate: true
})

// Cleanup on unmount
onUnmounted(() => {
  cleanupImageObjectUrls()
})
</script>

<style scoped>
.files-view {
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.page-header h1 {
  margin: 0;
  font-size: 28px;
  font-weight: 600;
  color: #303133;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.header-actions .el-dropdown {
  margin-right: 0;
}

.bulk-operations-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding: 12px 24px;
  background-color: #f5f7fa;
  border: 1px solid #ebeef5;
  border-radius: 8px;
}

.bulk-info {
  font-size: 16px;
  color: #303133;
  font-weight: 500;
}

.bulk-actions {
  display: flex;
  gap: 12px;
}

.breadcrumb-container {
  margin-bottom: 24px;
}

.breadcrumb-container .el-breadcrumb {
  font-size: 16px;
}

.breadcrumb-container .el-breadcrumb__item {
  cursor: pointer;
  transition: color 0.2s ease;
}

.breadcrumb-container .el-breadcrumb__item:hover {
  color: #409eff;
}

.breadcrumb-container .el-breadcrumb__item:last-child {
  color: #409eff;
  font-weight: 600;
}

.search-bar {
  margin-bottom: 24px;
  display: flex;
  align-items: center;
  gap: 16px;
  justify-content: space-between;
}

.view-toggle {
  flex-shrink: 0;
}

/* Responsive adjustments for search bar */
@media (max-width: 768px) {
  .search-bar {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }

  .search-bar .el-input {
    width: 100% !important;
  }

  .view-toggle {
    align-self: center;
  }
}

.file-list-container {
  margin-bottom: 24px;
}

/* Grid View */
.grid-view {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  padding: 8px;
}

.file-card {
  background: #fff;
  border: 1px solid transparent;
  border-radius: 6px;
  padding: 12px;
  transition: all 0.2s ease;
  text-align: center;
  position: relative;
  min-height: 120px;
  width: 180px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.file-card-content {
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  width: 100%;
  flex: 1;
  justify-content: center;
}

.file-card:hover {
  background: #f8f9fa;
  border-color: #e1e5e9;
}

.file-card:hover .file-selection,
.file-card:hover .file-actions {
  opacity: 1;
  visibility: visible;
}

.file-selection {
  position: absolute;
  top: 6px;
  left: 6px;
  z-index: 2;
  opacity: 0;
  visibility: hidden;
  transition: all 0.2s ease;
}

.file-actions {
  position: absolute;
  top: 6px;
  right: 6px;
  z-index: 2;
  opacity: 0;
  visibility: hidden;
  transition: all 0.2s ease;
}

.file-icon {
  margin-bottom: 4px;
}

.file-name {
  font-size: 13px;
  font-weight: 500;
  color: #333;
  word-break: break-word;
  line-height: 1.3;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
}

.file-meta {
  font-size: 11px;
  color: #666;
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-top: 4px;
}

/* Large View (Picture Wall) */
.large-view {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  padding: 16px;
  justify-content: flex-start;
}

.large-file-card {
  background: #fff;
  border: 1px solid transparent;
  border-radius: 8px;
  padding: 16px;
  transition: all 0.2s ease;
  text-align: center;
  position: relative;
  min-height: 200px;
  width: 200px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.large-file-content {
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  width: 100%;
  flex: 1;
  justify-content: center;
}

.large-file-card:hover {
  background: #f8f9fa;
  border-color: #e1e5e9;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}

.large-file-card:hover .large-file-selection,
.large-file-card:hover .large-file-actions {
  opacity: 1;
  visibility: visible;
}

.large-file-selection {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 2;
  opacity: 0;
  visibility: hidden;
  transition: all 0.2s ease;
}

.large-file-actions {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 2;
  opacity: 0;
  visibility: hidden;
  transition: all 0.2s ease;
}

.large-file-icon {
  margin-bottom: 8px;
}

.large-file-name {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  word-break: break-word;
  line-height: 1.4;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  text-align: center;
}

.large-file-meta {
  font-size: 12px;
  color: #666;
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 8px;
  text-align: center;
}

/* Responsive design for large view */
@media (max-width: 1200px) {
  .large-file-card {
    width: 180px;
    min-height: 180px;
  }
}

@media (max-width: 768px) {
  .large-view {
    gap: 16px;
    padding: 12px;
  }

  .large-file-card {
    width: 160px;
    min-height: 160px;
    padding: 12px;
  }

  .large-file-name {
    font-size: 13px;
  }

  .large-file-meta {
    font-size: 11px;
  }
}

@media (max-width: 480px) {
  .large-view {
    gap: 12px;
    padding: 8px;
  }

  .large-file-card {
    width: 140px;
    min-height: 140px;
    padding: 10px;
  }
}

/* Picture Wall View */
.picture-wall-view {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
  padding: 16px;
  justify-items: center;
}

.picture-item {
  position: relative;
  width: 200px;
  height: 200px;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
  cursor: pointer;
}

.picture-content {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.picture-thumbnail {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f8f9fa;
}

.picture-thumbnail .file-icon {
  width: 100% !important;
  height: 100% !important;
  aspect-ratio: unset !important;
  border-radius: 0 !important;
}

.picture-thumbnail .thumbnail-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 0;
}

.picture-thumbnail .fallback-icon {
  width: 100%;
  height: 100%;
  font-size: 80px;
}

.picture-thumbnail .fallback-icon .el-icon {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.picture-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: linear-gradient(transparent, rgba(0, 0, 0, 0.8));
  color: white;
  padding: 20px 12px 12px;
  transform: translateY(100%);
  transition: transform 0.3s ease;
  opacity: 0;
}

.picture-item:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
}

.picture-item:hover .picture-overlay {
  transform: translateY(0);
  opacity: 1;
}

.picture-item:hover .picture-selection,
.picture-item:hover .picture-actions {
  opacity: 1;
  visibility: visible;
}

.picture-selection {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 3;
  opacity: 0;
  visibility: hidden;
  transition: all 0.2s ease;
}

.picture-actions {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 3;
  opacity: 0;
  visibility: hidden;
  transition: all 0.2s ease;
}

.picture-filename {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.picture-meta {
  font-size: 11px;
  opacity: 0.9;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

/* Responsive design for picture wall */
@media (max-width: 1200px) {
  .picture-wall-view {
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 14px;
  }

  .picture-item {
    width: 180px;
    height: 180px;
  }
}

@media (max-width: 768px) {
  .picture-wall-view {
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 12px;
    padding: 12px;
  }

  .picture-item {
    width: 160px;
    height: 160px;
  }

  .picture-filename {
    font-size: 13px;
  }

  .picture-meta {
    font-size: 10px;
  }
}

@media (max-width: 480px) {
  .picture-wall-view {
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 10px;
    padding: 10px;
  }

  .picture-item {
    width: 140px;
    height: 140px;
  }
}

.custom-tree-node {
  display: flex;
  align-items: center;
  width: 100%;
}

.custom-tree-node .el-icon {
  color: #409eff;
}

.file-name {
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-meta {
  font-size: 12px;
  color: #909399;
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
}

/* List View */
.list-view {
  width: 100%;
}

.list-view-summary {
  background: #f8f9fa;
}

.list-view-summary .summary-text {
  margin: 4px;
  font-size: 14px;
  color: #606266;
  line-height: 1.5;
}

.list-view-summary .summary-text strong {
  color: #303133;
  font-weight: 600;
}

.file-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.owner-cell {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #606266;
}

.owner-icon {
  color: #67c23a;
}

/* List view table styling */
:deep(.el-table) {
  border-radius: 8px;
  overflow: hidden;
}

/* Sortable column styling */
:deep(.el-table .sortable) {
  cursor: pointer;
}

:deep(.el-table .sortable:hover) {
  background-color: #f0f9ff;
}

:deep(.el-table .sortable .cell) {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

:deep(.el-table .sortable .cell::after) {
  content: '';
  width: 0;
  height: 0;
  border-left: 4px solid transparent;
  border-right: 4px solid transparent;
  margin-left: 8px;
  opacity: 0.3;
}

:deep(.el-table .sortable.ascending .cell::after) {
  border-bottom: 4px solid #409eff;
  opacity: 1;
}

:deep(.el-table .sortable.descending .cell::after) {
  border-top: 4px solid #409eff;
  opacity: 1;
}

:deep(.el-table th) {
  background-color: #f5f7fa;
  color: #606266;
  font-weight: 600;
}

:deep(.el-table td) {
  padding: 12px 0;
}

:deep(.el-table .el-table__row:hover) {
  background-color: #f5f7fa;
}

/* List actions styling */
.list-actions {
  display: flex;
  gap: 6px;
  align-items: center;
}

.list-actions .el-button {
  padding: 8px;
  font-size: 14px;
  min-width: 32px;
  height: 32px;
}

.list-actions .el-button .el-icon {
  margin: 0;
  font-size: 16px;
}

/* Upload Dialog Styles */
.upload-area {
  width: 100%;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

:deep(.el-upload-dragger) {
  width: 100%;
  height: 120px;
}

/* Directory upload styles */
.directory-upload-area {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.directory-input {
  width: 100%;
}

.directory-preview {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 10px;
  background-color: #f9fafc;
}

.directory-preview h4 {
  margin-top: 0;
  margin-bottom: 10px;
  color: #303133;
}

.item-breakdown {
  font-size: 14px;
  font-weight: 400;
  color: #909399;
  margin-left: 8px;
}

.total-size {
  color: #409eff;
  font-weight: 500;
}

.directory-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px dashed #ebeef5;
}

.directory-item:last-child {
  border-bottom: none;
}

.item-name {
  flex-grow: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 600;
  color: #303133;
}

.item-size {
  font-size: 12px;
  color: #909399;
}

.directory-placeholder {
  text-align: center;
  padding: 40px 20px;
  color: #c0c4cc;
}

.directory-placeholder p {
  margin: 16px 0 0 0;
  font-size: 14px;
}

.upload-progress-section {
  margin-top: 20px;
  border-top: 1px solid #e4e7ed;
  padding-top: 20px;
}

.upload-progress-section h4 {
  margin-top: 0;
  margin-bottom: 16px;
  color: #303133;
}

.upload-progress-list {
  max-height: 300px;
  overflow-y: auto;
}

.progress-item {
  margin-bottom: 16px;
  padding: 12px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  background-color: #fafafa;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.filename {
  font-weight: 600;
  color: #303133;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-right: 12px;
}

.status {
  font-size: 12px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 12px;
  text-transform: capitalize;
}

.status.uploading {
  color: #409eff;
  background-color: #ecf5ff;
}

.status.success {
  color: #67c23a;
  background-color: #f0f9ff;
}

.status.error {
  color: #f56c6c;
  background-color: #fef0f0;
}

.error-message {
  color: #f56c6c;
  font-size: 12px;
  margin-top: 8px;
  padding: 8px;
  background-color: #fef0f0;
  border-radius: 4px;
}

/* Operation Dialog Styling */
.operation-dialog {
  border-radius: 12px;
}

.operation-dialog :deep(.el-dialog__header) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 12px 12px 0 0;
  padding: 20px 24px;
}

.operation-dialog :deep(.el-dialog__title) {
  color: white;
  font-size: 18px;
  font-weight: 600;
}

.operation-dialog :deep(.el-dialog__headerbtn .el-dialog__close) {
  color: white;
  font-size: 18px;
}

.operation-dialog :deep(.el-dialog__body) {
  padding: 24px;
}

.operation-dialog :deep(.el-dialog__footer) {
  padding: 16px 24px;
  border-top: 1px solid #e4e7ed;
  background-color: #fafafa;
}

/* Destination Selector Styling */
.destination-selector {
  margin-bottom: 0;
}

.destination-selector :deep(.el-form-item__label) {
  font-weight: 600;
  color: #303133;
  font-size: 16px;
  margin-bottom: 16px;
  display: block;
}

.destination-tree-select {
  width: 100%;
}

.destination-tree-select :deep(.el-tree-select) {
  width: 100%;
}

.destination-tree-select :deep(.el-input__wrapper) {
  border: 2px solid #e4e7ed;
  border-radius: 8px;
  background-color: #fafafa;
  transition: all 0.3s ease;
}

.destination-tree-select :deep(.el-input__wrapper:hover) {
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.1);
}

.destination-tree-select :deep(.el-input__wrapper.is-focus) {
  border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
}

/* Conflict Dialog Styles */
.conflict-content {
  padding: 16px 0;
}

.conflict-info {
  margin-bottom: 24px;
}

.conflict-options h4 {
  margin: 0 0 16px 0;
  color: #303133;
  font-size: 16px;
  font-weight: 600;
}

.conflict-radio-group {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.conflict-radio {
  width: 100%;
  margin: 0;
  padding: 16px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  transition: all 0.2s ease;
}

.conflict-radio:hover {
  border-color: #409eff;
  background-color: #f0f9ff;
}

.conflict-radio.is-checked {
  border-color: #409eff;
  background-color: #f0f9ff;
}

.radio-content {
  width: 100%;
}

.radio-title {
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}

.radio-description {
  font-size: 14px;
  color: #606266;
  line-height: 1.4;
}

/* Loading overlay for image preview */
.image-loading-overlay {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: rgba(0, 0, 0, 0.8);
  color: white;
  padding: 20px 30px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 10px;
  z-index: 3001;
  font-size: 14px;
}

.image-loading-overlay .el-icon {
  font-size: 18px;
}

.directory-loading-overlay {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: rgba(0, 0, 0, 0.8);
  color: white;
  padding: 20px 30px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 12px;
  z-index: 2000;
  font-size: 16px;
  font-weight: 500;
}

.directory-loading-overlay .el-icon {
  font-size: 18px;
}

/* Dark mode styles */
.dark .files-view {
  background: #141414;
}

.dark .page-header h1 {
  color: #e5e5e5;
}

.dark .files-grid {
  background: #1f1f1f;
}

.dark .file-item {
  background: #2a2a2a;
  border-color: #3c3c3c;
}

.dark .file-item:hover {
  background: #333;
  border-color: #409eff;
}

.dark .file-name {
  color: #e5e5e5;
}

.dark .file-size {
  color: #a8a8a8;
}

.dark .file-date {
  color: #a8a8a8;
}

.dark .directory-item {
  border-bottom-color: #3c3c3c;
}

.dark .item-name {
  color: #e5e5e5;
}

.dark .item-size {
  color: #a8a8a8;
}

.dark .directory-placeholder {
  color: #666;
}

.dark .directory-placeholder p {
  color: #a8a8a8;
}

.dark .upload-progress-section {
  border-top-color: #3c3c3c;
}

.dark .upload-progress-section h4 {
  color: #e5e5e5;
}

.dark .progress-item {
  background-color: #2a2a2a;
  border-color: #3c3c3c;
}

.dark .filename {
  color: #e5e5e5;
}

.dark .conflict-radio {
  border-color: #3c3c3c;
  background-color: #2a2a2a;
}

.dark .conflict-radio:hover {
  border-color: #409eff;
  background-color: #1a1a1a;
}

.dark .conflict-radio.is-checked {
  border-color: #409eff;
  background-color: #1a1a1a;
}

.dark .radio-title {
  color: #e5e5e5;
}

.dark .radio-description {
  color: #a8a8a8;
}

.dark .image-loading-overlay {
  background: rgba(0, 0, 0, 0.9);
}

.dark .directory-loading-overlay {
  background: rgba(0, 0, 0, 0.9);
}
</style>
