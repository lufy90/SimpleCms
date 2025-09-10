import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/files',
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/LoginView.vue'),
      meta: { requiresAuth: false },
    },
    {
      path: '/register',
      name: 'Register',
      component: () => import('@/views/RegisterView.vue'),
      meta: { requiresAuth: false },
    },
    {
      path: '/view/:id',
      name: 'FileViewer',
      component: () => import('@/views/FileViewerView.vue'),
      meta: { requiresAuth: true, title: 'File Viewer' },
    },
    {
      path: '/test-onlyoffice',
      name: 'OnlyOfficeTest',
      component: () => import('@/components/OnlyOfficeTest.vue'),
      meta: { requiresAuth: false, title: 'OnlyOffice Test' },
    },
    {
      path: '/',
      component: () => import('@/layouts/MainLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: 'files',
          name: 'Files',
          component: () => import('@/views/FilesView.vue'),
          meta: { title: 'Files' },
          props: (route) => ({ parentId: route.query.parent_id }),
        },
        {
          path: 'files/:id',
          name: 'FileDetails',
          component: () => import('@/views/FileDetailsView.vue'),
          meta: { title: 'File Details' },
          props: (route) => ({ fileId: route.params.id }),
        },
        {
          path: 'upload',
          name: 'Upload',
          component: () => import('@/views/UploadView.vue'),
          meta: { title: 'Upload Files' },
        },
        {
          path: 'search',
          name: 'Search',
          component: () => import('@/views/SearchView.vue'),
          meta: { title: 'Search Files' },
        },
        {
          path: 'permissions',
          name: 'Permissions',
          component: () => import('@/views/PermissionsView.vue'),
          meta: { title: 'Permissions' },
        },
        {
          path: 'permission-requests',
          name: 'PermissionRequests',
          component: () => import('@/views/PermissionRequestsView.vue'),
          meta: { title: 'Permission Requests' },
        },
        {
          path: 'tags',
          name: 'Tags',
          component: () => import('@/views/TagsView.vue'),
          meta: { title: 'File Tags' },
        },
        {
          path: 'access-logs',
          name: 'AccessLogs',
          component: () => import('@/views/AccessLogsView.vue'),
          meta: { title: 'Access Logs' },
        },
        {
          path: 'deleted-files',
          name: 'DeletedFiles',
          component: () => import('@/views/DeletedFilesView.vue'),
          meta: { title: 'Dustbin' },
        },

        {
          path: 'profile',
          name: 'Profile',
          component: () => import('@/views/ProfileView.vue'),
          meta: { title: 'User Profile' },
        },
        {
          path: 'settings',
          name: 'Settings',
          component: () => import('@/views/SettingsView.vue'),
          meta: { title: 'Settings' },
        },
      ],
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'NotFound',
      component: () => import('@/views/NotFoundView.vue'),
    },
  ],
})

// Navigation guard
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  // Initialize auth state if not already done
  if (!authStore.isAuthenticated && authStore.user === null) {
    await authStore.init()
  }

  if (to.meta.requiresAuth === false) {
    // Public routes (login, register)
    if (authStore.isAuthenticated) {
      next('/files')
    } else {
      next()
    }
  } else {
    // Protected routes
    if (authStore.isAuthenticated) {
      next()
    } else {
      next('/login')
    }
  }
})

export default router
