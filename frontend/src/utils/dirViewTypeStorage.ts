const STORAGE_KEY = 'simplecms:dir-view-types'
const DEFAULT_VIEW_TYPE = 'list'
const MAX_ENTRIES = 100
const MAX_AGE_MS = 30 * 24 * 60 * 60 * 1000

export type DirViewType = 'grid' | 'large' | 'picture' | 'list'

interface DirViewTypeEntry {
  viewType: DirViewType
  lastVisited: number
}

type DirViewTypeMap = Record<string, DirViewTypeEntry>

const VALID_VIEW_TYPES: readonly DirViewType[] = ['grid', 'large', 'picture', 'list']

function isValidViewType(value: unknown): value is DirViewType {
  return typeof value === 'string' && (VALID_VIEW_TYPES as readonly string[]).includes(value)
}

function readMap(): DirViewTypeMap {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return {}
    const parsed = JSON.parse(raw)
    if (!parsed || typeof parsed !== 'object') return {}
    return parsed as DirViewTypeMap
  } catch (error) {
    console.error('[dirViewTypeStorage] Failed to read localStorage:', error)
    return {}
  }
}

function writeMap(map: DirViewTypeMap): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(map))
  } catch (error) {
    console.error('[dirViewTypeStorage] Failed to write localStorage:', error)
  }
}

function pruneMap(map: DirViewTypeMap): DirViewTypeMap {
  const now = Date.now()
  const pruned: DirViewTypeMap = {}

  for (const [key, entry] of Object.entries(map)) {
    if (!entry || !isValidViewType(entry.viewType)) continue
    if (entry.viewType === DEFAULT_VIEW_TYPE) continue
    if (typeof entry.lastVisited !== 'number') continue
    if (now - entry.lastVisited > MAX_AGE_MS) continue
    pruned[key] = entry
  }

  const keys = Object.keys(pruned)
  if (keys.length <= MAX_ENTRIES) {
    return pruned
  }

  keys
    .sort((a, b) => pruned[a].lastVisited - pruned[b].lastVisited)
    .slice(0, keys.length - MAX_ENTRIES)
    .forEach((key) => {
      delete pruned[key]
    })

  return pruned
}

export function getDirViewType(dirKey: string): DirViewType | null {
  if (!dirKey) return null

  const map = pruneMap(readMap())
  const entry = map[dirKey]
  if (!entry || !isValidViewType(entry.viewType) || entry.viewType === DEFAULT_VIEW_TYPE) {
    writeMap(map)
    return null
  }

  // Refresh lastVisited so actively used directories are not evicted by age
  map[dirKey] = {
    ...entry,
    lastVisited: Date.now(),
  }
  writeMap(pruneMap(map))

  return entry.viewType
}

export function setDirViewType(dirKey: string, viewType: DirViewType): void {
  if (!dirKey || !isValidViewType(viewType)) return

  const map = pruneMap(readMap())

  if (viewType === DEFAULT_VIEW_TYPE) {
    delete map[dirKey]
  } else {
    map[dirKey] = {
      viewType,
      lastVisited: Date.now(),
    }
  }

  writeMap(pruneMap(map))
}

export function resolveDirViewTypeKey(options: {
  directoryId?: string | null
  space?: string | null
}): string {
  if (options.directoryId) {
    return options.directoryId
  }

  if (options.space === 'shared_to_me') {
    return 'space:shared_to_me'
  }

  if (options.space === 'group_spaces') {
    return 'space:group_spaces'
  }

  return 'space:home'
}

export const DEFAULT_DIR_VIEW_TYPE: DirViewType = DEFAULT_VIEW_TYPE
