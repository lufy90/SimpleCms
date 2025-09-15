# Custom Icons

This directory contains custom SVG icons used throughout the application.

## Structure

```
src/assets/icons/
├── GlobeIcon.vue          # Globe icon for language switching
├── FileIcon.vue           # Generic file icon
├── FolderIcon.vue         # Generic folder icon
├── FlagChina.vue          # China flag icon
├── FlagUS.vue             # US flag icon
├── index.ts              # Export all icons for easy importing
└── README.md             # This documentation file
```

## Usage

### Importing Icons

```typescript
// Import specific icons
import { GlobeIcon, FlagChina, FlagUS } from '@/assets/icons'

// Import all icons
import * as Icons from '@/assets/icons'
```

### Using Icons in Templates

```vue
<template>
  <GlobeIcon :size="16" class="my-icon" />
  <FlagChina :size="20" />
  <FlagUS :size="20" />
</template>
```

## Icon Component Props

All icon components accept the following props:

- `size`: Number or string - Size of the icon (default: 16)
- `className`: String - Additional CSS classes

## Adding New Icons

1. Create a new Vue component in this directory
2. Follow the naming convention: `IconName.vue`
3. Use the same props interface as existing icons
4. Export the component in `index.ts`
5. Update this README

## Styling

Icons use `fill: currentColor` by default, so they inherit the text color of their parent element. You can override this with CSS:

```css
.my-icon {
  color: #409eff; /* Blue color */
}
```
