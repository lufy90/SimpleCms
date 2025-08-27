# File Manager Frontend

A modern Vue.js frontend for the Django-based file management system.

## Features

- **Multiple View Types**: Grid, List, and Details views for files
- **Sidebar Navigation**: Directory tree navigation
- **Authentication**: JWT-based login/registration system
- **File Operations**: Upload, download, search, and manage files
- **Permission Management**: View and manage file permissions
- **Responsive Design**: Mobile-friendly interface
- **Modern UI**: Built with Element Plus components

## Tech Stack

- **Vue 3** - Progressive JavaScript framework
- **TypeScript** - Type-safe JavaScript
- **Vue Router** - Official router for Vue.js
- **Pinia** - State management for Vue
- **Element Plus** - Vue 3 UI component library
- **Axios** - HTTP client for API communication
- **Vite** - Fast build tool and dev server

## Setup Instructions

### 1. Install Dependencies

```bash
npm install
```

### 2. Environment Configuration

Create a `.env` file in the frontend directory:

```env
VITE_API_BASE_URL=http://localhost:8002
```

### 3. Start Development Server

```bash
npm run dev
```

The application will be available at `http://localhost:5173`

### 4. Build for Production

```bash
npm run build
```

## Project Structure

```
src/
├── components/          # Reusable Vue components
├── layouts/            # Layout components (MainLayout)
├── router/             # Vue Router configuration
├── services/           # API services and HTTP client
├── stores/             # Pinia stores (auth, files)
├── views/              # Page components
│   ├── LoginView.vue
│   ├── RegisterView.vue
│   ├── FilesView.vue
│   ├── UploadView.vue
│   ├── SearchView.vue
│   ├── ProfileView.vue
│   └── ... (other views)
├── App.vue             # Root component
└── main.ts             # Application entry point
```

## API Integration

The frontend communicates with the Django backend through RESTful APIs:

- **Authentication**: `/api/auth/*` - Login, registration, profile
- **Files**: `/api/files/*` - File management operations
- **Upload**: `/api/upload/` - File upload
- **Permissions**: `/api/permissions/*` - Access control
- **Search**: `/api/files/search/` - File search

## Key Components

### MainLayout.vue
- Sidebar with directory tree navigation
- Top navigation bar with search and user menu
- Responsive design with collapsible sidebar

### FilesView.vue
- Multiple view types (Grid, List)
- File search and filtering
- Pagination support
- File operations (click to navigate)

### Authentication
- JWT token management
- Automatic token refresh
- Protected routes
- User profile management

## Development

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run type-check` - TypeScript type checking
- `npm run lint` - ESLint linting
- `npm run format` - Prettier code formatting

### Code Style

- TypeScript for type safety
- Vue 3 Composition API
- Element Plus for UI components
- Responsive design principles
- Accessibility considerations

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Contributing

1. Follow Vue.js style guide
2. Use TypeScript for all new code
3. Maintain responsive design
4. Test on multiple devices
5. Follow accessibility guidelines

## License

This project is part of the File Manager CMS system.
