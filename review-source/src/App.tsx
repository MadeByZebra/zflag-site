import { useEffect, useMemo, useRef, useState } from "react"
import type * as React from "react"
import { createPortal } from "react-dom"
import { Command as ShellCommand } from "@tauri-apps/plugin-shell"
import { invoke } from "@tauri-apps/api/core"
import { listen } from "@tauri-apps/api/event"
import { EditorView } from "codemirror"
import { CodeMirrorJsonEditor } from "./CodeMirrorJsonEditor"
import {
  Activity,
  Braces,
  Check,
  ChevronDown,
  ChevronLeft,
  CircleAlert,
  Clipboard,
  Cpu,
  Download,
  Bot,
  MessageSquare,
  Send,
  User,
  ShieldCheck,
  KeyRound,
  BrainCircuit,
  Ellipsis,
  FileJson,
  FilePlus2,
  FolderOpen,
  Gauge,
  Globe2,
  Home,
  Layers3,
  LoaderCircle,
  Minus,
  Monitor,
  Maximize2,
  Minimize2,
  Copy,
  ListFilter,
  RotateCcw,
  Shield,
  GitCompareArrows,
  ScanSearch,
  Star,
  MoreHorizontal,
  PanelLeftClose,
  PanelLeftOpen,
  Play,
  Plus,
  RefreshCw,
  PencilLine,
  Rocket,
  Save,
  Search,
  Square,
  Settings,
  SlidersHorizontal,
  Sparkles,
  SquareTerminal,
  Trash2,
  Upload,
  WandSparkles,
  X,
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import logoMark from "./assets/zflag-logo.svg"

const DEFAULT_API = "http://127.0.0.1:18765"
let desktopSidecarStarted = false

const DEFAULT_JSON = `{
  "DFIntTaskSchedulerTargetFps": "9999"
}`

const PERFORMANCE_PRESET = {
  DFIntTaskSchedulerTargetFps: "9999",
  DFIntCSGLevelOfDetailSwitchingDistance: "250",
  DFIntCSGLevelOfDetailSwitchingDistanceL12: "500",
  DFIntCSGLevelOfDetailSwitchingDistanceL23: "1250",
  DFIntCSGLevelOfDetailSwitchingDistanceL34: "3000",
  DFIntTextureCompositorActiveJobs: "2",
  FFlagDebugGraphicsDisableDirect3D11: "false",
}

const FPS_PRESET = { DFIntTaskSchedulerTargetFps: "9999" }
const TEXTURE_PRESET = { FIntDebugTextureManagerSkipMips: "8" }

type View = "home" | "editor" | "presets" | "activity" | "agent" | "settings"
type ToastTone = "success" | "warning" | "error" | "info"

type LogEntry = {
  id: number
  time: string
  level: "info" | "success" | "warning" | "error" | string
  message: string
}

type Status = {
  connected: boolean
  pid: number | null
  base: string | null
  ready: boolean
  fetching: boolean
  flagsLoaded: number
  clientVersion: string | null
  offsetSource?: string | null
  offsetSourceHost?: string | null
  offsetFetchedAt?: number | null
  offsetBytes?: number
  offsetValidation?: string | null
  backendPid?: number | null
  backendUptimeSec?: number
  rollbackDepth?: number
  backendVersion?: string | null
  browserUiBundled?: boolean
  browserUrl?: string | null
  logs: LogEntry[]
}

type ThemeMode = "dark" | "light"
type AccentPreset = "default" | "emerald" | "violet" | "rose" | "cyan" | "amber"
type BackgroundMode = "default" | "glass" | "image" | "video"
type SettingsSection = "general" | "appearance" | "connection" | "behavior" | "editor" | "notifications" | "keybinds"

type SettingsState = {
  apiUrl: string
  autoRefresh: boolean
  pollMs: number
  animations: boolean
  themeMode: ThemeMode
  accentPreset: AccentPreset
  backgroundMode: BackgroundMode
  backgroundData: string
  backgroundOpacity: number
  notificationDuration: number
  notificationPosition: "bottom-right" | "bottom-left" | "top-right"
  compactNotifications: boolean
  editorFontSize: number
  editorWordWrap: boolean
  autoApplyEnabled: boolean
  autoApplyConfigId: string
}

type AgentProvider = "ollama" | "openai" | "anthropic" | "gemini" | "openrouter" | "compatible"

type AgentSettingsState = {
  provider: AgentProvider
  baseUrl: string
  model: string
  confirmApply: boolean
}

const AGENT_PROVIDER_DEFAULTS: Record<AgentProvider, { label: string; baseUrl: string; model: string; needsKey: boolean }> = {
  ollama: { label: "Ollama (local)", baseUrl: "http://127.0.0.1:11434", model: "llama3.2:3b", needsKey: false },
  openai: { label: "OpenAI / Codex API", baseUrl: "https://api.openai.com/v1", model: "gpt-5.6-luna", needsKey: true },
  anthropic: { label: "Anthropic Claude", baseUrl: "https://api.anthropic.com", model: "claude-sonnet-4-6", needsKey: true },
  gemini: { label: "Google Gemini", baseUrl: "https://generativelanguage.googleapis.com/v1beta", model: "gemini-3.8-flash", needsKey: true },
  openrouter: { label: "OpenRouter", baseUrl: "https://openrouter.ai/api/v1", model: "", needsKey: true },
  compatible: { label: "Custom OpenAI-compatible", baseUrl: "http://127.0.0.1:1234/v1", model: "", needsKey: false },
}

type AgentMessage = {
  id: string
  role: "user" | "assistant"
  content: string
  time: number
  actionSummary?: string[]
}

type AgentAction = {
  type: string
  [key: string]: unknown
}

type SavedConfig = {
  id: string
  name: string
  content: string
  updatedAt: number
}

type EditorTab = {
  id: string
  configId: string | null
  name: string
  content: string
  dirty: boolean
}

type CustomPreset = {
  id: string
  name: string
  content: string
}

type ApplyResultEntry = {
  name: string
  ok: boolean
  message: string
  value?: unknown
}

type ApplySnapshot = {
  id: string
  tabId?: string
  name: string
  content: string
  appliedAt: number
  applied: number
  errors: number
  source?: string
  rollbackId?: string | null
  results?: ApplyResultEntry[]
}

type PreflightEntry = {
  name: string
  value?: unknown
  normalized?: string
  type: string
  supported: boolean
  valid: boolean
  status: "supported" | "unsupported" | "invalid" | string
  message: string
  offset?: string | null
}

type PreflightResult = {
  ok: boolean
  total: number
  supported: number
  unsupported: number
  invalid: number
  entries: PreflightEntry[]
  source?: string | null
  clientVersion?: string | null
}

type EditorBottomTab = "activity" | "failures" | "validation" | "diagnostics"
type ActivityFilter = "all" | "success" | "warning" | "error"

const emptyStatus: Status = {
  connected: false,
  pid: null,
  base: null,
  ready: false,
  fetching: false,
  flagsLoaded: 0,
  clientVersion: null,
  offsetSource: null,
  offsetSourceHost: null,
  offsetFetchedAt: null,
  offsetBytes: 0,
  offsetValidation: null,
  backendPid: null,
  backendUptimeSec: 0,
  rollbackDepth: 0,
  logs: [],
}


function statusUiSignature(value: Status) {
  const logs = value.logs || []
  const last = logs.length ? logs[logs.length - 1] : undefined
  return [
    value.connected ? 1 : 0,
    value.pid ?? "",
    value.base ?? "",
    value.ready ? 1 : 0,
    value.fetching ? 1 : 0,
    value.flagsLoaded,
    value.clientVersion ?? "",
    value.offsetSource ?? "",
    value.offsetFetchedAt ?? "",
    value.offsetBytes ?? "",
    value.offsetValidation ?? "",
    value.backendPid ?? "",
    value.rollbackDepth ?? 0,
    value.backendVersion ?? "",
    value.browserUiBundled ? 1 : 0,
    logs.length,
    last?.id ?? "",
    last?.level ?? "",
    last?.message ?? "",
  ].join("|")
}

const builtInPresets = [
  { id: "fps", name: "FPS", description: "Minimal frame-rate preset.", value: FPS_PRESET },
  { id: "performance", name: "Performance", description: "Balanced performance profile from the original app.", value: PERFORMANCE_PRESET },
  { id: "texture", name: "Texture Skip Mips", description: "Sets FIntDebugTextureManagerSkipMips to 8.", value: TEXTURE_PRESET },
]

const accentOptions: Array<{ id: AccentPreset; label: string; color: string }> = [
  { id: "default", label: "Neutral", color: "#e8e8e8" },
  { id: "emerald", label: "Emerald", color: "#42d99a" },
  { id: "violet", label: "Violet", color: "#9f7aea" },
  { id: "rose", label: "Rose", color: "#ef7ca9" },
  { id: "cyan", label: "Cyan", color: "#46cbe6" },
  { id: "amber", label: "Amber", color: "#e9b949" },
]

const backgroundOptions: Array<{ id: BackgroundMode; label: string; detail: string }> = [
  { id: "default", label: "Default", detail: "Clean solid surface" },
  { id: "glass", label: "Glass", detail: "Layered translucent panels" },
  { id: "image", label: "Image / GIF", detail: "Use custom visual media" },
  { id: "video", label: "Video", detail: "Loop MP4 / WebM media" },
]

function uid(prefix: string) {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`
}

function safeParse<T>(raw: string | null, fallback: T): T {
  if (!raw) return fallback
  try {
    return JSON.parse(raw) as T
  } catch {
    return fallback
  }
}

function loadSettings(): SettingsState {
  const parsed = safeParse<Partial<SettingsState>>(localStorage.getItem("fflag-studio-settings"), {})
  const savedApi = typeof parsed.apiUrl === "string" ? parsed.apiUrl.trim().replace(/\/$/, "") : ""
  const migratedApi = !savedApi || savedApi === "http://127.0.0.1:8765" || savedApi === "http://localhost:8765"
    ? DEFAULT_API
    : savedApi
  const savedPoll = typeof parsed.pollMs === "number" ? parsed.pollMs : 3000
  return {
    apiUrl: migratedApi,
    autoRefresh: typeof parsed.autoRefresh === "boolean" ? parsed.autoRefresh : true,
    // 1–1.8 second full-status polling caused unnecessary whole-app React
    // renders on large 1,000+ flag configs. Keep the minimum at 3 seconds.
    pollMs: Math.max(3000, savedPoll),
    animations: typeof parsed.animations === "boolean" ? parsed.animations : true,
    themeMode: parsed.themeMode === "light" ? "light" : "dark",
    accentPreset: ["default", "emerald", "violet", "rose", "cyan", "amber"].includes(String(parsed.accentPreset)) ? parsed.accentPreset as AccentPreset : "default",
    backgroundMode: ["default", "glass", "image", "video"].includes(String(parsed.backgroundMode)) ? parsed.backgroundMode as BackgroundMode : "default",
    backgroundData: typeof parsed.backgroundData === "string" ? parsed.backgroundData : "",
    backgroundOpacity: typeof parsed.backgroundOpacity === "number" ? parsed.backgroundOpacity : 0.32,
    notificationDuration: typeof parsed.notificationDuration === "number" ? parsed.notificationDuration : 2600,
    notificationPosition: parsed.notificationPosition === "bottom-left" || parsed.notificationPosition === "top-right" ? parsed.notificationPosition : "bottom-right",
    compactNotifications: typeof parsed.compactNotifications === "boolean" ? parsed.compactNotifications : true,
    editorFontSize: typeof parsed.editorFontSize === "number" ? parsed.editorFontSize : 12.5,
    editorWordWrap: typeof parsed.editorWordWrap === "boolean" ? parsed.editorWordWrap : false,
    autoApplyEnabled: typeof parsed.autoApplyEnabled === "boolean" ? parsed.autoApplyEnabled : false,
    autoApplyConfigId: typeof parsed.autoApplyConfigId === "string" ? parsed.autoApplyConfigId : "",
  }
}

const MEDIA_DB_NAME = "zflag-media-v1"
const MEDIA_STORE = "assets"
const MEDIA_BACKGROUND_KEY = "background"

const DATA_DB_NAME = "zflag-workspace-v2"
const DATA_STORE = "state"

function openDataDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DATA_DB_NAME, 1)
    request.onupgradeneeded = () => {
      const db = request.result
      if (!db.objectStoreNames.contains(DATA_STORE)) db.createObjectStore(DATA_STORE)
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

async function dataGet<T>(key: string): Promise<T | undefined> {
  const db = await openDataDb()
  return await new Promise((resolve, reject) => {
    const tx = db.transaction(DATA_STORE, "readonly")
    const req = tx.objectStore(DATA_STORE).get(key)
    req.onsuccess = () => resolve(req.result as T | undefined)
    req.onerror = () => reject(req.error)
  })
}

async function dataPut(key: string, value: unknown): Promise<void> {
  const db = await openDataDb()
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(DATA_STORE, "readwrite")
    tx.objectStore(DATA_STORE).put(value, key)
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

function validConfigs(value: unknown): value is SavedConfig[] {
  return Array.isArray(value) && value.every((v) => v && typeof v === "object" && typeof (v as SavedConfig).id === "string" && typeof (v as SavedConfig).name === "string" && typeof (v as SavedConfig).content === "string")
}
function validTabs(value: unknown): value is EditorTab[] {
  return Array.isArray(value) && value.length > 0 && value.every((v) => v && typeof v === "object" && typeof (v as EditorTab).id === "string" && typeof (v as EditorTab).name === "string" && typeof (v as EditorTab).content === "string")
}

function openMediaDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(MEDIA_DB_NAME, 1)
    request.onupgradeneeded = () => {
      const db = request.result
      if (!db.objectStoreNames.contains(MEDIA_STORE)) db.createObjectStore(MEDIA_STORE)
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

async function loadBackgroundFromDb(): Promise<string> {
  const db = await openMediaDb()
  return await new Promise((resolve, reject) => {
    const tx = db.transaction(MEDIA_STORE, "readonly")
    const req = tx.objectStore(MEDIA_STORE).get(MEDIA_BACKGROUND_KEY)
    req.onsuccess = () => resolve(typeof req.result === "string" ? req.result : "")
    req.onerror = () => reject(req.error)
  })
}

async function saveBackgroundToDb(value: string): Promise<void> {
  const db = await openMediaDb()
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(MEDIA_STORE, "readwrite")
    const store = tx.objectStore(MEDIA_STORE)
    if (value) store.put(value, MEDIA_BACKGROUND_KEY)
    else store.delete(MEDIA_BACKGROUND_KEY)
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

function loadAgentSettings(): AgentSettingsState {
  const parsed = safeParse<Partial<AgentSettingsState>>(localStorage.getItem("fflag-studio-agent-settings"), {})
  const validProviders: AgentProvider[] = ["ollama", "openai", "anthropic", "gemini", "openrouter", "compatible"]
  const provider = validProviders.includes(parsed.provider as AgentProvider) ? parsed.provider as AgentProvider : "ollama"
  const defaults = AGENT_PROVIDER_DEFAULTS[provider]
  return {
    provider,
    baseUrl: typeof parsed.baseUrl === "string" && parsed.baseUrl.trim() ? parsed.baseUrl : defaults.baseUrl,
    model: typeof parsed.model === "string" && parsed.model.trim() ? parsed.model : defaults.model,
    confirmApply: typeof parsed.confirmApply === "boolean" ? parsed.confirmApply : true,
  }
}

function loadAgentMessages(): AgentMessage[] {
  const value = safeParse<unknown>(localStorage.getItem("fflag-studio-agent-messages"), [])
  return Array.isArray(value) ? value.filter((v): v is AgentMessage => !!v && typeof v === "object" && typeof (v as AgentMessage).content === "string") : []
}

function loadConfigs(): SavedConfig[] {
  const value = safeParse<unknown>(localStorage.getItem("fflag-studio-configs"), [])
  return validConfigs(value) ? value : []
}

function loadPresets(): CustomPreset[] {
  const value = safeParse<unknown>(localStorage.getItem("fflag-studio-custom-presets"), [])
  return Array.isArray(value) ? value.filter((v): v is CustomPreset => !!v && typeof v === "object" && typeof (v as CustomPreset).id === "string" && typeof (v as CustomPreset).content === "string") : []
}

function loadTabs(): EditorTab[] {
  const tabs = safeParse<unknown>(localStorage.getItem("fflag-studio-tabs"), [])
  if (validTabs(tabs)) return tabs
  const previous = localStorage.getItem("fflag-studio-editor") ?? DEFAULT_JSON
  return [{ id: uid("tab"), configId: null, name: "Untitled.json", content: previous, dirty: false }]
}

function loadApplyHistory(): ApplySnapshot[] {
  const value = safeParse<unknown>(localStorage.getItem("fflag-studio-apply-history"), [])
  return Array.isArray(value) ? value.filter((v): v is ApplySnapshot => !!v && typeof v === "object" && typeof (v as ApplySnapshot).id === "string" && typeof (v as ApplySnapshot).content === "string") : []
}

function loadFavoriteFlags(): string[] {
  const value = safeParse<unknown>(localStorage.getItem("zflag-favorite-flags"), [])
  return Array.isArray(value) ? value.filter((v): v is string => typeof v === "string") : []
}

function IconTip({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <span className="tooltip-wrap">
      {children}
      <span className="tooltip-bubble">{label}</span>
    </span>
  )
}

function TopIcon({ active, label, children, onClick }: { active: boolean; label: string; children: React.ReactNode; onClick: () => void }) {
  return (
    <button className={cn("top-icon nav-reveal", active && "is-active")} onClick={onClick} type="button" aria-label={label}>
      <span className="top-icon-glyph">{children}</span>
      <span className="top-icon-label">{label}</span>
    </button>
  )
}

function SidebarButton({ active, icon, children, onClick, danger = false }: { active?: boolean; icon: React.ReactNode; children: React.ReactNode; onClick: () => void; danger?: boolean }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn("sidebar-row group", active && "is-active", danger && "danger")}
    >
      <span className="sidebar-row-icon">{icon}</span>
      <span className="sidebar-row-text">{children}</span>
    </button>
  )
}

function Toggle({ checked, onChange }: { checked: boolean; onChange: (value: boolean) => void }) {
  return (
    <button type="button" className={cn("toggle", checked && "is-on")} onClick={() => onChange(!checked)} aria-pressed={checked}>
      <span />
    </button>
  )
}

export default function App() {
  const [view, setView] = useState<View>("home")
  const [status, setStatus] = useState<Status>(emptyStatus)
  const [busy, setBusy] = useState(false)
  const [nativeFeedback, setNativeFeedback] = useState<string | null>(null)
  const [saveFeedback, setSaveFeedback] = useState<string | null>(null)
  const [backendReachable, setBackendReachable] = useState(false)
  const [settings, setSettings] = useState<SettingsState>(loadSettings)
  const [draftSettings, setDraftSettings] = useState<SettingsState>(settings)
  const [settingsSection, setSettingsSection] = useState<SettingsSection>("general")
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [savedConfigs, setSavedConfigs] = useState<SavedConfig[]>(loadConfigs)
  const [customPresets, setCustomPresets] = useState<CustomPreset[]>(loadPresets)
  const [tabs, setTabs] = useState<EditorTab[]>(() => loadTabs())
  const [activeTabId, setActiveTabId] = useState(() => localStorage.getItem("fflag-studio-active-tab") || tabs[0]?.id || "")
  const [configSearch, setConfigSearch] = useState("")
  const [openMenu, setOpenMenu] = useState<string | null>(null)
  const [clearDialog, setClearDialog] = useState<"object" | "blank" | "saved" | null>(null)
  const [clearMenuOpen, setClearMenuOpen] = useState(false)
  const [browserModeBusy, setBrowserModeBusy] = useState(false)
  const [clearMenuPosition, setClearMenuPosition] = useState({ top: 0, left: 0 })
  const clearMenuAnchorRef = useRef<HTMLButtonElement>(null)
  const [clearUndo, setClearUndo] = useState<{ tabId: string; content: string; dirty: boolean } | null>(null)
  const [workspaceHydrated, setWorkspaceHydrated] = useState(false)
  const [preflight, setPreflight] = useState<PreflightResult | null>(null)
  const [preflightBusy, setPreflightBusy] = useState(false)
  const [preflightOpen, setPreflightOpen] = useState(false)
  const [preflightPrefix, setPreflightPrefix] = useState("all")
  const [inspectedFlag, setInspectedFlag] = useState<string | null>(null)
  const [favoriteFlags, setFavoriteFlags] = useState<string[]>(loadFavoriteFlags)
  const [compareOpen, setCompareOpen] = useState(false)
  const [compareLeftId, setCompareLeftId] = useState("")
  const [compareRightId, setCompareRightId] = useState("")
  const [storageEstimate, setStorageEstimate] = useState<{ usage: number; quota: number } | null>(null)
  const [toast, setToast] = useState<{ id: number; title: string; detail?: string; tone: ToastTone } | null>(null)
  const [saveDialog, setSaveDialog] = useState<{ mode: "config" | "preset" | "rename"; value: string; targetId?: string } | null>(null)
  const [agentSettings, setAgentSettings] = useState<AgentSettingsState>(loadAgentSettings)
  const [draftAgentSettings, setDraftAgentSettings] = useState<AgentSettingsState>(agentSettings)
  const [agentApiKey, setAgentApiKey] = useState("")
  const [agentModels, setAgentModels] = useState<string[]>([])
  const [agentModelBusy, setAgentModelBusy] = useState(false)
  const [agentMessages, setAgentMessages] = useState<AgentMessage[]>(loadAgentMessages)
  const [agentInput, setAgentInput] = useState("")
  const [agentBusy, setAgentBusy] = useState(false)
  const [pendingAgentApply, setPendingAgentApply] = useState(false)
  const [pageKey, setPageKey] = useState(0)
  const [commandOpen, setCommandOpen] = useState(false)
  const [commandQuery, setCommandQuery] = useState("")
  const [applyHistory, setApplyHistory] = useState<ApplySnapshot[]>(loadApplyHistory)
  const [editorBottomTab, setEditorBottomTab] = useState<EditorBottomTab>("activity")
  const [bottomPanelOpen, setBottomPanelOpen] = useState(true)
  const [bottomPanelMaximized, setBottomPanelMaximized] = useState(false)
  const [bottomPanelHeight, setBottomPanelHeight] = useState(() => {
    const saved = Number(localStorage.getItem("fflag-studio-bottom-panel-height") || 170)
    return Number.isFinite(saved) ? Math.min(420, Math.max(72, saved)) : 170
  })
  const [agentHealth, setAgentHealth] = useState<"unknown" | "checking" | "online" | "offline">("unknown")
  const [agentHealthMessage, setAgentHealthMessage] = useState("Not tested yet")
  const [activityFilter, setActivityFilter] = useState<ActivityFilter>("all")
  const [activitySearch, setActivitySearch] = useState("")
  const [expandedLogGroups, setExpandedLogGroups] = useState<Record<string, boolean>>({})
  const [showUnsupportedOnly, setShowUnsupportedOnly] = useState(false)
  const [sidebarWidth, setSidebarWidth] = useState(() => {
    const saved = Number(localStorage.getItem("fflag-studio-sidebar-width") || 246)
    return Number.isFinite(saved) ? Math.min(380, Math.max(190, saved)) : 246
  })
  const [generatorName, setGeneratorName] = useState("")
  const [generatorValue, setGeneratorValue] = useState("")
  const [generatorType, setGeneratorType] = useState<"string" | "int" | "bool">("string")
  const lastConnectedRef = useRef(false)
  const fileInput = useRef<HTMLInputElement>(null)
  const mediaInput = useRef<HTMLInputElement>(null)
  const mainScrollRef = useRef<HTMLElement>(null)
  const agentBottomRef = useRef<HTMLDivElement>(null)
  const codeMirrorRef = useRef<EditorView | null>(null)
  const backendChildRef = useRef<{ kill?: () => Promise<void> } | null>(null)
  const backendStartingRef = useRef(false)
  const backendMissesRef = useRef(0)
  const statusRefreshingRef = useRef(false)
  const trayActionRef = useRef<(action: string) => void>(() => {})
  const hotkeyActionRef = useRef<{ save: () => void; apply: () => void; newTab: () => void; format: () => void; agent: () => void }>({ save: () => {}, apply: () => {}, newTab: () => {}, format: () => {}, agent: () => {} })

  const isDesktop = "__TAURI_INTERNALS__" in window
  const activeTab = tabs.find((tab) => tab.id === activeTabId) ?? tabs[0]
  const activeSavedConfig = activeTab?.configId ? savedConfigs.find((config) => config.id === activeTab.configId) : undefined
  const text = activeTab?.content ?? DEFAULT_JSON
  const visualSettings = view === "settings" && settingsSection === "appearance" ? draftSettings : settings

  const parsed = useMemo(() => {
    try {
      const value = JSON.parse(text)
      if (!value || Array.isArray(value) || typeof value !== "object") throw new Error("Top level must be an object")
      return { ok: true as const, value: value as Record<string, unknown>, error: "" }
    } catch (error) {
      return { ok: false as const, value: {}, error: error instanceof Error ? error.message : "Invalid JSON" }
    }
  }, [text])

  const lastApplied = applyHistory[0]
  const lastApplyStats = useMemo(() => {
    const success = lastApplied?.applied ?? 0
    const failed = lastApplied?.errors ?? 0
    const total = success + failed
    const rate = total ? Math.round((success / total) * 100) : 0
    return { success, failed, total, rate }
  }, [lastApplied?.id, lastApplied?.applied, lastApplied?.errors])
  const failedResults = useMemo(() => (lastApplied?.results ?? []).filter((entry) => !entry.ok), [lastApplied?.id])
  const visibleFailedResults = useMemo(() => showUnsupportedOnly ? failedResults.filter((entry) => /not in offset file|not on roblox|not allowlist|unsupported/i.test(entry.message)) : failedResults, [failedResults, showUnsupportedOnly])
  const preflightMap = useMemo(() => new Map((preflight?.entries ?? []).map((entry) => [entry.name, entry])), [preflight])
  const filteredPreflightEntries = useMemo(() => {
    const entries = preflight?.entries ?? []
    if (preflightPrefix === "all") return entries
    if (preflightPrefix === "favorites") return entries.filter((entry) => favoriteFlags.includes(entry.name))
    return entries.filter((entry) => entry.name.startsWith(preflightPrefix))
  }, [preflight, preflightPrefix, favoriteFlags])
  const inspectedEntry = inspectedFlag ? preflightMap.get(inspectedFlag) : undefined
  const inspectedLastResult = inspectedFlag ? lastApplied?.results?.find((entry) => entry.name === inspectedFlag) : undefined
  const compareResult = useMemo(() => {
    const left = compareLeftId === "current" ? text : savedConfigs.find((c) => c.id === compareLeftId)?.content
    const right = compareRightId === "current" ? text : savedConfigs.find((c) => c.id === compareRightId)?.content
    if (!left || !right) return null
    const a = safeParse<Record<string, unknown>>(left, {})
    const b = safeParse<Record<string, unknown>>(right, {})
    const keys = new Set([...Object.keys(a), ...Object.keys(b)])
    const added: string[] = [], removed: string[] = [], changed: string[] = []
    for (const key of keys) {
      if (!(key in a)) added.push(key)
      else if (!(key in b)) removed.push(key)
      else if (JSON.stringify(a[key]) !== JSON.stringify(b[key])) changed.push(key)
    }
    return { added, removed, changed, left: a, right: b }
  }, [compareLeftId, compareRightId, savedConfigs, text])
  const sessionComparison = useMemo(() => {
    const current = applyHistory[0]?.results ?? []
    const previous = applyHistory[1]?.results ?? []
    const previousMap = new Map(previous.map((entry) => [entry.name, entry.ok]))
    let newlySuccessful = 0
    let newlyFailing = 0
    let recovered = 0
    for (const entry of current) {
      const before = previousMap.get(entry.name)
      if (entry.ok && before !== true) newlySuccessful += 1
      if (!entry.ok && before !== false) newlyFailing += 1
      if (entry.ok && before === false) recovered += 1
    }
    return { newlySuccessful, newlyFailing, recovered }
  }, [applyHistory])
  const tabApplyStats = useMemo(() => {
    const map = new Map<string, { applied: number; errors: number }>()
    for (const snapshot of applyHistory) {
      if (snapshot.tabId && !map.has(snapshot.tabId)) map.set(snapshot.tabId, { applied: snapshot.applied, errors: snapshot.errors })
    }
    return map
  }, [applyHistory])

  const groupedActivity = useMemo(() => {
    const query = activitySearch.trim().toLowerCase()
    const filtered = status.logs.filter((entry) => {
      if (activityFilter !== "all" && entry.level !== activityFilter) return false
      return !query || `${entry.level} ${entry.message} ${entry.time}`.toLowerCase().includes(query)
    })
    const groups: Array<{ key: string; level: string; reason: string; entries: LogEntry[]; grouped: boolean }> = []
    const byKey = new Map<string, { key: string; level: string; reason: string; entries: LogEntry[]; grouped: boolean }>()
    for (const entry of filtered.slice().reverse()) {
      const match = entry.message.match(/^([^:]+):\s*(.+)$/)
      const shouldGroup = (entry.level === "error" || entry.level === "warning") && !!match
      const reason = shouldGroup ? match![2].trim() : entry.message
      const key = shouldGroup ? `${entry.level}:${reason}` : `entry:${entry.id}`
      if (shouldGroup) {
        const existing = byKey.get(key)
        if (existing) { existing.entries.push(entry); continue }
      }
      const group = { key, level: entry.level, reason, entries: [entry], grouped: shouldGroup }
      groups.push(group)
      if (shouldGroup) byKey.set(key, group)
    }
    return groups
  }, [status.logs, activityFilter, activitySearch])

  const lastAppliedParsed = useMemo(() => safeParse<Record<string, unknown>>(lastApplied?.content ?? null, {}), [lastApplied?.id])
  const diffSummary = useMemo(() => {
    if (!parsed.ok) return { added: 0, changed: 0, removed: 0, rows: [] as Array<{ key: string; kind: "added" | "changed" | "removed"; before?: unknown; after?: unknown }> }
    const rows: Array<{ key: string; kind: "added" | "changed" | "removed"; before?: unknown; after?: unknown }> = []
    const current = parsed.value
    for (const [key, value] of Object.entries(current)) {
      if (!(key in lastAppliedParsed)) rows.push({ key, kind: "added", after: value })
      else if (JSON.stringify(lastAppliedParsed[key]) !== JSON.stringify(value)) rows.push({ key, kind: "changed", before: lastAppliedParsed[key], after: value })
    }
    for (const [key, value] of Object.entries(lastAppliedParsed)) if (!(key in current)) rows.push({ key, kind: "removed", before: value })
    return { added: rows.filter((r) => r.kind === "added").length, changed: rows.filter((r) => r.kind === "changed").length, removed: rows.filter((r) => r.kind === "removed").length, rows }
  }, [parsed, lastAppliedParsed])

  const filteredConfigs = useMemo(() => {
    const q = configSearch.trim().toLowerCase()
    if (!q) return savedConfigs
    return savedConfigs.filter((item) => item.name.toLowerCase().includes(q))
  }, [savedConfigs, configSearch])

  const commandItems = useMemo(() => {
    const base = [
      { id: "home", label: "Open Overview", hint: "Navigate", run: () => changeView("home") },
      { id: "editor", label: "Open Editor", hint: "Navigate", run: () => changeView("editor") },
      { id: "presets", label: "Open Presets", hint: "Navigate", run: () => changeView("presets") },
      { id: "agent", label: "Open AI Agent", hint: "Navigate", run: () => changeView("agent") },
      { id: "settings", label: "Open Settings", hint: "Navigate", run: () => changeView("settings") },
      { id: "new", label: "New configuration", hint: "Create", run: () => newTab() },
      { id: "import", label: "Import JSON file", hint: "File", run: () => fileInput.current?.click() },
      { id: "refresh", label: "Refresh allowlist", hint: "Runtime", run: () => void refreshOffsets() },
      { id: "preflight", label: "Run Preflight", hint: "Validate current config", run: () => { changeView("editor"); void runPreflight() } },
      { id: "compare", label: "Compare configurations", hint: "Diff", run: () => { setCompareLeftId("current"); setCompareRightId(savedConfigs[0]?.id ?? "current"); setCompareOpen(true) } },
      { id: "rollback", label: "Rollback last Apply", hint: "Restore captured values", run: () => void rollbackLastApply() },
      { id: "diagnostic-report", label: "Export diagnostic report", hint: "Diagnostics", run: () => void exportDiagnosticReport() },
      { id: "generator", label: "Open FFlag Generator", hint: "Tools", run: () => changeView("presets") },
      { id: "history", label: "Open Apply History", hint: "Activity", run: () => changeView("activity") },
      { id: "notifications", label: "Notification Settings", hint: "Settings", run: () => { changeView("settings"); setSettingsSection("notifications") } },
      { id: "keybinds", label: "Keybind Settings", hint: "Settings", run: () => { changeView("settings"); setSettingsSection("keybinds") } },
      { id: "failures", label: "Show failed flags", hint: "Editor output", run: () => { changeView("editor"); setBottomPanelOpen(true); setEditorBottomTab("failures") } },
      { id: "maximize-output", label: "Maximize output panel", hint: "Editor output", run: () => { changeView("editor"); setBottomPanelOpen(true); setBottomPanelMaximized(true) } },
      { id: "analyze-errors", label: "Analyze last errors with AI", hint: "AI Agent", run: () => analyzeFailedFlagsWithAi() },
    ]
    const files = savedConfigs.slice(0, 12).map((config) => ({ id: `config-${config.id}`, label: config.name, hint: "Saved config", run: () => openConfig(config) }))
    const q = commandQuery.trim().toLowerCase()
    return [...base, ...files].filter((item) => !q || `${item.label} ${item.hint}`.toLowerCase().includes(q)).slice(0, 14)
  }, [commandQuery, savedConfigs, parsed.ok, text, status.rollbackDepth, isDesktop])

  function showToast(title: string, detail?: string, tone: ToastTone = "success") {
    setToast({ id: Date.now(), title, detail, tone })
  }

  function changeView(next: View) {
    setOpenMenu(null)
    setView(next)
    setPageKey((key) => key + 1)
    mainScrollRef.current?.scrollTo({ top: 0, behavior: settings.animations ? "smooth" : "auto" })
  }

  function updateActiveText(next: string, preserveClearUndo = false, dirty = true) {
    if (!preserveClearUndo) {
      setClearUndo((current) => current?.tabId === activeTabId ? null : current)
    }
    setTabs((current) => current.map((tab) => tab.id === activeTabId ? { ...tab, content: next, dirty } : tab))
  }

  function requestClearEditor(mode: "object" | "blank" | "saved") {
    setOpenMenu(null)
    setClearMenuOpen(false)
    if (mode === "saved" && !activeSavedConfig) {
      showToast("Nothing to restore", "Save this configuration first, then Reset to last saved will become available.", "info")
      return
    }
    setClearDialog(mode)
  }

  function toggleClearMenu(event: React.MouseEvent<HTMLButtonElement>) {
    event.preventDefault()
    event.stopPropagation()

    if (clearMenuOpen) {
      setClearMenuOpen(false)
      return
    }

    const rect = clearMenuAnchorRef.current?.getBoundingClientRect()
    if (rect) {
      const menuWidth = 272
      const preferredLeft = rect.right - menuWidth
      const left = Math.max(10, Math.min(window.innerWidth - menuWidth - 10, preferredLeft))
      setClearMenuPosition({
        top: Math.min(window.innerHeight - 190, rect.bottom + 6),
        left,
      })
    }

    setClearMenuOpen(true)
  }

  function confirmClearEditor() {
    if (!clearDialog || !activeTab) return

    const previous = {
      tabId: activeTab.id,
      content: activeTab.content,
      dirty: activeTab.dirty,
    }

    let next = "{}\n"
    let title = "JSON cleared"
    let detail = "Replaced the editor with an empty JSON object. Press Ctrl+Z to undo."
    let dirty = true

    if (clearDialog === "blank") {
      next = ""
      detail = "Removed all editor text. Press Ctrl+Z to undo."
    } else if (clearDialog === "saved") {
      if (!activeSavedConfig) {
        setClearDialog(null)
        showToast("Nothing to restore", "No saved version exists for this tab.", "info")
        return
      }
      next = activeSavedConfig.content
      dirty = false
      title = "Restored saved JSON"
      detail = "Restored the last saved version. Press Ctrl+Z to undo."
    }

    setClearUndo(previous)
    updateActiveText(next, true, dirty)
    setClearDialog(null)

    requestAnimationFrame(() => {
      const editor = codeMirrorRef.current
      if (!editor) return
      editor.focus()
      editor.dispatch({ selection: { anchor: 0 }, effects: EditorView.scrollIntoView(0, { y: "start" }) })
    })

    showToast(title, detail, "info")
  }

  function undoLastClear() {
    if (!clearUndo || clearUndo.tabId !== activeTabId) return false
    const snapshot = clearUndo
    setClearUndo(null)
    updateActiveText(snapshot.content, true, snapshot.dirty)
    requestAnimationFrame(() => codeMirrorRef.current?.focus())
    showToast("Clear undone", "Previous JSON restored.", "success")
    return true
  }

  function newTab(content = "{}\n", name?: string, configId: string | null = null) {
    const next: EditorTab = {
      id: uid("tab"),
      configId,
      name: name ?? `Untitled ${tabs.length + 1}.json`,
      content,
      dirty: false,
    }
    setTabs((current) => [...current, next])
    setActiveTabId(next.id)
    changeView("editor")
  }

  function closeTab(id: string) {
    setTabs((current) => {
      if (current.length === 1) {
        const replacement: EditorTab = { id: uid("tab"), configId: null, name: "Untitled.json", content: "{}\n", dirty: false }
        setActiveTabId(replacement.id)
        return [replacement]
      }
      const index = current.findIndex((tab) => tab.id === id)
      const next = current.filter((tab) => tab.id !== id)
      if (id === activeTabId) setActiveTabId(next[Math.max(0, index - 1)]?.id ?? next[0].id)
      return next
    })
  }

  function openConfig(config: SavedConfig) {
    const existing = tabs.find((tab) => tab.configId === config.id)
    if (existing) {
      setActiveTabId(existing.id)
      changeView("editor")
      return
    }
    newTab(config.content, config.name, config.id)
  }

  function saveCurrentConfig() {
    if (!activeTab) return
    if (activeTab.configId) {
      setSavedConfigs((current) => current.map((config) => config.id === activeTab.configId ? { ...config, content: activeTab.content, name: activeTab.name, updatedAt: Date.now() } : config))
      setTabs((current) => current.map((tab) => tab.id === activeTab.id ? { ...tab, dirty: false } : tab))
      showToast("Saved", activeTab.name)
      return
    }
    setSaveDialog({ mode: "config", value: activeTab.name.replace(/\.json$/i, "") })
  }

  function finishDialog() {
    if (!saveDialog || !activeTab) return
    const cleaned = saveDialog.value.trim()
    if (!cleaned) return

    if (saveDialog.mode === "config") {
      const name = cleaned.toLowerCase().endsWith(".json") ? cleaned : `${cleaned}.json`
      const config: SavedConfig = { id: uid("config"), name, content: activeTab.content, updatedAt: Date.now() }
      setSavedConfigs((current) => [config, ...current])
      setTabs((current) => current.map((tab) => tab.id === activeTab.id ? { ...tab, configId: config.id, name, dirty: false } : tab))
      showToast("Saved to library", name)
    } else if (saveDialog.mode === "preset") {
      const preset: CustomPreset = { id: uid("preset"), name: cleaned, content: activeTab.content }
      setCustomPresets((current) => [preset, ...current])
      showToast("Preset created", cleaned)
    } else if (saveDialog.mode === "rename" && saveDialog.targetId) {
      const name = cleaned.toLowerCase().endsWith(".json") ? cleaned : `${cleaned}.json`
      setSavedConfigs((current) => current.map((config) => config.id === saveDialog.targetId ? { ...config, name, updatedAt: Date.now() } : config))
      setTabs((current) => current.map((tab) => tab.configId === saveDialog.targetId ? { ...tab, name } : tab))
      showToast("Renamed", name)
    }
    setSaveDialog(null)
  }

  function deleteConfig(id: string) {
    const target = savedConfigs.find((config) => config.id === id)
    setSavedConfigs((current) => current.filter((config) => config.id !== id))
    setTabs((current) => current.map((tab) => tab.configId === id ? { ...tab, configId: null, dirty: true } : tab))
    setOpenMenu(null)
    showToast("Removed from library", target?.name, "info")
  }

  function loadPreset(value: Record<string, string> | string, label: string) {
    const content = typeof value === "string" ? value : JSON.stringify(value, null, 2)
    newTab(content, `${label}.json`)
    showToast("Preset loaded", label)
  }

  function importFile(file?: File) {
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => {
      newTab(String(reader.result ?? "{}\n"), file.name)
      showToast("File loaded", file.name)
    }
    reader.onerror = () => showToast("Could not read file", file.name, "error")
    reader.readAsText(file)
  }

  function exportText(content: string, filename: string) {
    const blob = new Blob([content], { type: "application/json" })
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
    showToast("Exported", filename)
  }

  function importBackgroundFile(file?: File) {
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => {
      const result = String(reader.result ?? "")
      const mode: BackgroundMode = file.type.startsWith("video/") ? "video" : "image"
      setDraftSettings((current) => ({ ...current, backgroundMode: mode, backgroundData: result }))
      showToast("Background loaded", file.name)
    }
    reader.onerror = () => showToast("Could not read background", file.name, "error")
    reader.readAsDataURL(file)
  }

  function clearBackgroundMedia() {
    setDraftSettings((current) => ({ ...current, backgroundMode: current.backgroundMode === "glass" ? "glass" : "default", backgroundData: "" }))
    showToast("Background cleared", undefined, "info")
  }

  function renderBackgroundLayer() {
    const opacity = Math.min(0.9, Math.max(0.05, visualSettings.backgroundOpacity || 0.32))
    if (visualSettings.backgroundMode === "video" && visualSettings.backgroundData) {
      return (
        <div className="media-background media-video" style={{ opacity }}>
          <video src={visualSettings.backgroundData} autoPlay muted loop playsInline />
        </div>
      )
    }
    if (visualSettings.backgroundMode === "image" && visualSettings.backgroundData) {
      return (
        <div className="media-background media-image" style={{ opacity, backgroundImage: `url(${visualSettings.backgroundData})` }} />
      )
    }
    if (visualSettings.backgroundMode === "glass") {
      return <div className="media-background media-glass" style={{ opacity: Math.max(0.14, opacity) }} />
    }
    return null
  }

  function formatJson() {
    if (!parsed.ok) {
      showToast("Invalid JSON", parsed.error, "error")
      return
    }
    updateActiveText(JSON.stringify(parsed.value, null, 2))
    showToast("Formatted JSON")
  }

  async function startOrRestartDesktopBackend(reason = "startup") {
    if (!isDesktop || backendStartingRef.current) return false
    backendStartingRef.current = true
    const bridgeUrl = reason.startsWith("browser-mode") ? DEFAULT_API : settings.apiUrl.replace(/\/$/, "")
    try {
      if (reason !== "startup") {
        try {
          await fetch(`${bridgeUrl}/shutdown`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: "{}",
          })
        } catch { /* already offline */ }

        // Give the previous bridge time to actually release port 18765 before
        // spawning the bundled sidecar. This avoids a stale process winning the race.
        for (let attempt = 0; attempt < 12; attempt += 1) {
          try {
            const health = await fetch(`${bridgeUrl}/health`, { cache: "no-store" })
            if (!health.ok) break
          } catch {
            break
          }
          await new Promise((resolve) => window.setTimeout(resolve, 150))
        }
      }

      try { await backendChildRef.current?.kill?.() } catch { /* previous child already stopped */ }

      const command = ShellCommand.sidecar("binaries/fflag-backend")
      const child = await command.spawn()
      backendChildRef.current = child as unknown as { kill?: () => Promise<void> }
      desktopSidecarStarted = true
      backendMissesRef.current = 0

      window.setTimeout(() => void refreshStatus(bridgeUrl, true), 450)
      window.setTimeout(() => void refreshStatus(bridgeUrl, true), 1100)

      if (reason !== "startup") showToast("Backend restarted", "Local bridge recovery completed.", "success")
      return true
    } catch (error) {
      if (reason !== "startup") showToast("Backend restart failed", error instanceof Error ? error.message : String(error), "error")
      return false
    } finally {
      backendStartingRef.current = false
    }
  }

  async function refreshStatus(apiUrl = settings.apiUrl, quiet = false) {
    if (statusRefreshingRef.current) return true
    statusRefreshingRef.current = true

    try {
      const response = await fetch(`${apiUrl}/status`, { cache: "no-store" })
      if (!response.ok) throw new Error("Backend unavailable")
      const next = (await response.json()) as Status

      setStatus((current) => (
        statusUiSignature(current) === statusUiSignature(next)
          ? current
          : next
      ))
      setBackendReachable((current) => current ? current : true)
      backendMissesRef.current = 0
      if (!quiet) showToast("Status refreshed")
      return true
    } catch {
      setStatus((current) => current.connected || current.logs.length ? emptyStatus : current)
      setBackendReachable((current) => current ? false : current)
      backendMissesRef.current += 1
      if (isDesktop && backendMissesRef.current >= 3 && !backendStartingRef.current) {
        backendMissesRef.current = 0
        void startOrRestartDesktopBackend("watchdog")
      }
      if (!quiet) showToast("Local backend unavailable", isDesktop ? "ZFLAG will try to restart the local bridge automatically." : "Start the desktop app or browser bridge.", "warning")
      return false
    } finally {
      statusRefreshingRef.current = false
    }
  }

  async function runPreflight(flags: Record<string, unknown> = parsed.ok ? parsed.value : {}, openPanel = true) {
    if (!Object.keys(flags).length) {
      showToast("Nothing to check", "The current JSON has no flags.", "info")
      return null
    }
    setPreflightBusy(true)
    try {
      const response = await fetch(`${settings.apiUrl}/preflight`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ flags }),
      })
      const result = await response.json() as PreflightResult & { error?: string }
      if (!response.ok || !result.ok) throw new Error(result.error || "Preflight failed")
      setPreflight(result)
      if (openPanel) setPreflightOpen(true)
      setEditorBottomTab("validation")
      setBottomPanelOpen(true)
      return result
    } catch (error) {
      showToast("Preflight failed", error instanceof Error ? error.message : "Backend unavailable", "error")
      return null
    } finally {
      setPreflightBusy(false)
    }
  }

  async function applyFlags(source = "manual", flagsOverride?: Record<string, unknown>, labelOverride?: string) {
    const flags = flagsOverride ?? (parsed.ok ? parsed.value : null)
    if (!flags) {
      showToast("Invalid JSON", parsed.error, "error")
      changeView("editor")
      return false
    }
    if (!Object.keys(flags).length) {
      showToast("Nothing to apply", "The configuration is empty.", "info")
      return false
    }
    if (source === "native") setNativeFeedback("Checking Roblox process and applying flags…")
    else setSaveFeedback(null)
    setBusy(true)
    try {
      const endpoint = source === "native" ? "/native-apply" : "/apply"
      const response = await fetch(`${settings.apiUrl}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ flags, source }),
      })
      const raw = await response.text()
      let result: { ok?: boolean; applied?: number; errors?: number; error?: string | null; unsupported?: number; invalid?: number; message?: string; rollbackId?: string | null; results?: Array<{ name?: string; ok?: boolean; message?: string; value?: unknown }> } = {}
      try { result = raw ? JSON.parse(raw) : {} } catch { /* handled below */ }
      const successfulResults = Array.isArray(result.results) ? result.results.filter((entry) => entry?.ok === true).length : 0
      const applied = Math.max(Number(result.applied ?? 0) || 0, successfulResults)
      const errors = Math.max(Number(result.errors ?? 0) || 0, 0)
      const normalizedResults: ApplyResultEntry[] = Array.isArray(result.results) ? result.results.slice(0, 1200).map((entry) => ({
        name: String(entry.name || "UnknownFlag"),
        ok: entry.ok === true,
        message: String(entry.message || (entry.ok ? "applied" : "failed")),
        value: entry.value ?? flags[String(entry.name || "")],
      })) : []
      const snapshot: ApplySnapshot = {
        id: uid("apply"), tabId: activeTab?.id, name: labelOverride ?? activeTab?.name ?? "Untitled.json",
        content: Object.keys(flags).length > 3000 ? JSON.stringify({ _zflag_notice: "Full large profile is stored in the saved configuration, not history" }) : JSON.stringify(flags, null, 2), appliedAt: Date.now(), applied, errors, source,
        rollbackId: result.rollbackId ?? null, results: normalizedResults,
      }
      setApplyHistory((current) => [snapshot, ...current].slice(0, Object.keys(flags).length > 3000 ? 8 : 50))
      if (applied > 0) {
        if (source === "native") setNativeFeedback(`${applied.toLocaleString()} written to Roblox memory · ${errors.toLocaleString()} failed. ${errors ? "See injection results for individual failures." : "Verify the changed behavior in Roblox."}`)
        if (source !== "native") setSaveFeedback(`${applied.toLocaleString()} saved to local settings · ${Number(result.unsupported ?? 0).toLocaleString()} unsupported · ${Number(result.invalid ?? 0).toLocaleString()} invalid. Only allowlisted flags are saved, and Roblox must restart. This is not a live injection.`)
        if (source !== "native" && errors) {
          setEditorBottomTab("failures")
          setBottomPanelOpen(true)
        }
        showToast(
          source === "native" ? (errors ? "Injection partially succeeded" : "Injection completed") : (errors ? "Only allowed flags saved" : "Allowed settings saved"),
          source === "native" ? `${applied.toLocaleString()} reported written · ${errors.toLocaleString()} failed` :
            (errors ? `${applied.toLocaleString()} saved · ${Number(result.unsupported ?? errors).toLocaleString()} not allowlisted · ${Number(result.invalid ?? 0).toLocaleString()} invalid. Open Skipped flags below; restart Roblox.` : `${applied.toLocaleString()} allowed flags saved; restart Roblox`),
          errors ? "warning" : "success",
        )
        await refreshStatus(settings.apiUrl, true)
        return true
      }
      throw new Error(result.error || (response.ok ? (source === "native" ? "Native engine did not write any flags" : "No allowed flags could be saved") : `Apply request failed (HTTP ${response.status})`))
    } catch (error) {
      if (source === "native") setNativeFeedback(error instanceof Error ? error.message : "Could not reach local backend")
      else setSaveFeedback(error instanceof Error ? error.message : "Failed to write local settings")
      showToast(source === "native" ? "Inject failed" : "Save failed", error instanceof Error ? error.message : "Could not reach local backend", "error")
      return false
    } finally {
      setBusy(false)
    }
  }

  async function applySupportedFromPreflight() {
    const check = preflight ?? await runPreflight(parsed.ok ? parsed.value : {}, false)
    if (!check?.ok) return
    const supported = Object.fromEntries(check.entries.filter((entry) => entry.supported && entry.valid).map((entry) => [entry.name, parsed.ok ? parsed.value[entry.name] : entry.value]))
    if (!Object.keys(supported).length) {
      showToast("No supported flags", "Preflight did not find any valid supported entries.", "warning")
      return
    }
    setPreflightOpen(false)
    await applyFlags("preflight-supported", supported, `${activeTab?.name ?? "Config"} · supported only`)
  }

  function cleanUnsupportedIntoNewConfig() {
    if (!preflight?.ok || !parsed.ok) return
    const clean = Object.fromEntries(preflight.entries.filter((entry) => entry.supported && entry.valid).map((entry) => [entry.name, parsed.value[entry.name]]))
    newTab(JSON.stringify(clean, null, 2), `${(activeTab?.name ?? "config").replace(/\.json$/i, "")}-clean.json`)
    setPreflightOpen(false)
    showToast("Clean config created", `${Object.keys(clean).length} supported flags kept.`, "success")
  }

  async function rollbackLastApply() {
    try {
      const response = await fetch(`${settings.apiUrl}/rollback-last`, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" })
      const result = await response.json()
      if (!response.ok || !result.ok) throw new Error(result.error || "Rollback failed")
      showToast("Rollback complete", `${Number(result.restored ?? 0)} previous value${Number(result.restored ?? 0) === 1 ? "" : "s"} restored.`, Number(result.errors ?? 0) ? "warning" : "success")
      await refreshStatus(settings.apiUrl, true)
    } catch (error) {
      showToast("Rollback unavailable", error instanceof Error ? error.message : "Could not restore previous values", "warning")
    }
  }

  async function exportDiagnosticReport() {
    let backend: unknown = status
    try {
      const response = await fetch(`${settings.apiUrl}/diagnostics`, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" })
      backend = await response.json()
    } catch { /* keep current cached status */ }
    let estimate: StorageEstimate | undefined
    try { estimate = await navigator.storage?.estimate?.() } catch { /* unavailable */ }
    const report = {
      generatedAt: new Date().toISOString(), appVersion: "2.0.9", desktop: isDesktop,
      currentFile: activeTab?.name, tabCount: tabs.length, savedConfigCount: savedConfigs.length,
      applyHistoryCount: applyHistory.length, storage: estimate, backend,
      agent: { provider: agentSettings.provider, model: agentSettings.model, health: agentHealth, message: agentHealthMessage },
    }
    exportText(JSON.stringify(report, null, 2), `zflag-diagnostics-${Date.now()}.json`)
  }

  async function refreshOffsets() {
    try {
      const response = await fetch(`${settings.apiUrl}/refresh-offsets`, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" })
      const result = await response.json()
      if (!response.ok) throw new Error(result.error ?? "Refresh failed")
      showToast("Refreshing offsets", "The backend is updating its local offset table.", "info")
      window.setTimeout(() => void refreshStatus(settings.apiUrl, true), 850)
    } catch (error) {
      showToast("Refresh failed", error instanceof Error ? error.message : "Backend unavailable", "error")
    }
  }

  async function clearLogs() {
    try {
      const response = await fetch(`${settings.apiUrl}/clear-logs`, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" })
      if (!response.ok) throw new Error("Could not clear activity")
      await refreshStatus(settings.apiUrl, true)
      showToast("Activity cleared")
    } catch (error) {
      showToast("Could not clear activity", error instanceof Error ? error.message : undefined, "error")
    }
  }

  async function copyLogs() {
    try {
      await navigator.clipboard.writeText(status.logs.map((entry) => `[${entry.time}] ${entry.level.toUpperCase()} ${entry.message}`).join("\n"))
      showToast("Activity copied")
    } catch {
      showToast("Clipboard access blocked", undefined, "error")
    }
  }

  async function saveSettings() {
    const next = { ...draftSettings, apiUrl: draftSettings.apiUrl.trim().replace(/\/$/, "") || DEFAULT_API }
    try {
      await saveBackgroundToDb(next.backgroundData)
      const persisted = { ...next, backgroundData: "" }
      localStorage.setItem("fflag-studio-settings", JSON.stringify(persisted))
      setSettings(next)
      setDraftSettings(next)
      showToast("Settings saved")
    } catch (error) {
      showToast("Could not save settings", error instanceof Error ? error.message : String(error), "error")
    }
  }

  function saveAgentSettings() {
    const next: AgentSettingsState = {
      ...draftAgentSettings,
      baseUrl: draftAgentSettings.baseUrl.trim().replace(/\/$/, ""),
      model: draftAgentSettings.model.trim(),
    }
    setAgentSettings(next)
    setDraftAgentSettings(next)
    localStorage.setItem("fflag-studio-agent-settings", JSON.stringify(next))
    showToast("Agent settings saved", `${AGENT_PROVIDER_DEFAULTS[next.provider].label} · ${next.model || "choose a model"}`)
  }

  function changeAgentProvider(provider: AgentProvider) {
    const defaults = AGENT_PROVIDER_DEFAULTS[provider]
    setAgentModels([])
    setAgentHealth("unknown")
    setAgentHealthMessage("Not tested yet")
    setDraftAgentSettings((current) => ({
      ...current,
      provider,
      baseUrl: defaults.baseUrl,
      model: defaults.model,
    }))
  }

  async function refreshAgentModels(useDraft = true, quiet = false) {
    const source = useDraft ? draftAgentSettings : agentSettings
    setAgentModelBusy(true)
    try {
      const response = await fetch(`${settings.apiUrl}/agent/models`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider: source.provider, baseUrl: source.baseUrl, apiKey: agentApiKey }),
      })
      const result = await response.json()
      if (!response.ok || !result.ok) throw new Error(result.error || "Could not load models")
      const models = Array.isArray(result.models) ? result.models.map(String) : []
      setAgentModels(models)
      if (models.length && !models.includes(source.model)) {
        setDraftAgentSettings((current) => ({ ...current, model: models[0] }))
        if (!useDraft) {
          const next = { ...agentSettings, model: models[0] }
          setAgentSettings(next)
          localStorage.setItem("fflag-studio-agent-settings", JSON.stringify(next))
        }
      }
      if (!quiet) showToast(models.length ? "Models detected" : "No models found", models.length ? `${models.length} available` : undefined, models.length ? "success" : "warning")
      return models
    } catch (error) {
      if (!quiet) showToast("AI connection failed", error instanceof Error ? error.message : String(error), "error")
      return [] as string[]
    } finally {
      setAgentModelBusy(false)
    }
  }

  async function readBrowserHealth(baseUrl: string) {
    try {
      const response = await fetch(`${baseUrl}/health`, { cache: "no-store" })
      if (!response.ok) return { online: false, browserUi: false, backendVersion: "", error: `HTTP ${response.status}` }
      const result = await response.json().catch(() => ({})) as { ok?: boolean; browserUi?: boolean; backendVersion?: string }
      return {
        online: result.ok !== false,
        browserUi: result.browserUi === true,
        backendVersion: String(result.backendVersion || ""),
        error: "",
      }
    } catch (error) {
      return {
        online: false,
        browserUi: false,
        backendVersion: "",
        error: error instanceof Error ? error.message : String(error),
      }
    }
  }

  async function waitForBrowserBridge(baseUrl: string, timeoutMs = 12000) {
    const startedAt = Date.now()
    let lastError = "Backend did not respond"

    while (Date.now() - startedAt < timeoutMs) {
      const health = await readBrowserHealth(baseUrl)
      if (health.online && health.browserUi) return health

      if (health.online && !health.browserUi) {
        lastError = health.backendVersion
          ? `Backend ${health.backendVersion} is running but its browser UI is not bundled`
          : "A stale local backend is running without the browser UI"
      } else if (health.error) {
        lastError = health.error
      }

      await new Promise((resolve) => window.setTimeout(resolve, 250))
    }

    throw new Error(`Browser bridge did not become ready: ${lastError}`)
  }

  async function verifyBrowserUi(baseUrl: string) {
    const response = await fetch(`${baseUrl}/browser-check`, { cache: "no-store" })
    const result = await response.json().catch(() => ({})) as {
      ok?: boolean
      browserUi?: boolean
      browserUrl?: string
      error?: string | null
      missingAssets?: string[]
    }

    if (!response.ok || !result.ok || !result.browserUi) {
      const missing = Array.isArray(result.missingAssets) && result.missingAssets.length
        ? ` Missing: ${result.missingAssets.slice(0, 3).join(", ")}`
        : ""
      throw new Error((result.error || `Browser bundle check failed (HTTP ${response.status})`) + missing)
    }

    return result.browserUrl || `${baseUrl}/app/`
  }

  async function openBrowserViaBackend(baseUrl: string) {
    try {
      const response = await fetch(`${baseUrl}/open-browser`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      })
      const result = await response.json().catch(() => ({})) as { ok?: boolean; error?: string }
      if (!response.ok || !result.ok) throw new Error(result.error || `HTTP ${response.status}`)
      return true
    } catch {
      return false
    }
  }

  async function openBrowserMode() {
    if (browserModeBusy) return
    setBrowserModeBusy(true)

    // The bundled desktop sidecar always owns 127.0.0.1:18765. Do not let a
    // custom API URL in Settings accidentally break the Browser button.
    const baseUrl = (isDesktop ? DEFAULT_API : settings.apiUrl).replace(/\/$/, "") || DEFAULT_API
    const browserUrl = `${baseUrl}/app/`

    try {
      let health = await readBrowserHealth(baseUrl)

      // Offline OR stale bridge: repair it automatically in desktop mode.
      if (isDesktop && (!health.online || !health.browserUi)) {
        await startOrRestartDesktopBackend(health.online ? "browser-mode-repair" : "browser-mode")
        health = await waitForBrowserBridge(baseUrl)
      }

      if (!health.online) {
        throw new Error("The local ZFLAG bridge is offline. Run RUN_BROWSER_APP.bat or restart the desktop backend.")
      }

      if (!health.browserUi) {
        throw new Error(
          health.backendVersion
            ? `Backend ${health.backendVersion} is running, but this copy does not contain the Browser UI. Restart ZFLAG using this build.`
            : "A stale ZFLAG backend is occupying port 18765. Close old ZFLAG copies and try again.",
        )
      }

      // Validate the embedded bundle through a JSON endpoint. The previous build
      // fetched /app/ directly from the Tauri webview; that cross-origin HTML
      // request was missing CORS headers and caused the "Backend restarted" ->
      // "Could not open browser mode" sequence.
      let verifiedBrowserUrl = browserUrl
      try {
        verifiedBrowserUrl = await verifyBrowserUi(baseUrl)
      } catch (firstError) {
        if (!isDesktop) throw firstError
        await startOrRestartDesktopBackend("browser-mode-repair")
        await waitForBrowserBridge(baseUrl)
        verifiedBrowserUrl = await verifyBrowserUi(baseUrl)
      }

      if (isDesktop) {
        // The verified backend is already running on Windows. Let Python use
        // os.startfile() first; native ShellExecuteW is the fallback.
        let opened = await openBrowserViaBackend(baseUrl)
        let invokeError = ""

        if (!opened) {
          try {
            await invoke("open_default_browser", { url: verifiedBrowserUrl })
            opened = true
          } catch (error) {
            invokeError = error instanceof Error ? error.message : String(error)
          }
        }

        if (!opened) {
          throw new Error(
            invokeError
              ? `Browser UI is ready, but Windows could not open it automatically: ${invokeError}`
              : "Browser UI is ready, but Windows could not open the default browser.",
          )
        }
      } else {
        const popup = window.open(verifiedBrowserUrl, "_blank", "noopener,noreferrer")
        if (!popup) throw new Error("Your browser blocked the new tab. Allow pop-ups for ZFLAG and try again.")
      }

      showToast("Browser mode opened", verifiedBrowserUrl, "success")
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      console.error("Browser mode error:", error)
      showToast("Could not open browser mode", message, "error")
    } finally {
      setBrowserModeBusy(false)
    }
  }

  function clearAgentChat() {
    setAgentMessages([])
    localStorage.removeItem("fflag-studio-agent-messages")
    void dataPut("agentMessages", []).catch(() => {})
    showToast("Agent chat cleared", undefined, "info")
  }

  function mergeFlagsIntoEditor(flags: Record<string, unknown>) {
    const base = parsed.ok ? parsed.value : {}
    const merged = { ...base, ...flags }
    updateActiveText(JSON.stringify(merged, null, 2))
    changeView("editor")
  }

  function replaceEditorJson(value: unknown, name?: string) {
    let next: Record<string, unknown>
    if (typeof value === "string") {
      try {
        const parsedValue = JSON.parse(value)
        if (!parsedValue || Array.isArray(parsedValue) || typeof parsedValue !== "object") throw new Error("JSON must be an object")
        next = parsedValue as Record<string, unknown>
      } catch {
        showToast("Agent returned invalid JSON", undefined, "error")
        return false
      }
    } else if (value && !Array.isArray(value) && typeof value === "object") {
      next = value as Record<string, unknown>
    } else {
      showToast("Agent action ignored", "replace_json needs a JSON object", "warning")
      return false
    }
    updateActiveText(JSON.stringify(next, null, 2))
    if (name && activeTab) {
      const normalized = name.toLowerCase().endsWith(".json") ? name : `${name}.json`
      setTabs((current) => current.map((tab) => tab.id === activeTab.id ? { ...tab, name: normalized } : tab))
    }
    changeView("editor")
    return true
  }

  function saveAgentConfig(name?: string) {
    if (!activeTab) return "No active editor tab"
    const cleaned = (name || activeTab.name || "Agent config.json").trim()
    const normalized = cleaned.toLowerCase().endsWith(".json") ? cleaned : `${cleaned}.json`
    if (activeTab.configId) {
      setSavedConfigs((current) => current.map((config) => config.id === activeTab.configId ? { ...config, content: activeTab.content, name: normalized, updatedAt: Date.now() } : config))
      setTabs((current) => current.map((tab) => tab.id === activeTab.id ? { ...tab, name: normalized, dirty: false } : tab))
      return `Saved ${normalized}`
    }
    const config: SavedConfig = { id: uid("config"), name: normalized, content: activeTab.content, updatedAt: Date.now() }
    setSavedConfigs((current) => [config, ...current])
    setTabs((current) => current.map((tab) => tab.id === activeTab.id ? { ...tab, configId: config.id, name: normalized, dirty: false } : tab))
    return `Saved ${normalized}`
  }

  function saveAgentPreset(name?: string) {
    if (!activeTab) return "No active editor tab"
    const cleaned = (name || activeTab.name.replace(/\.json$/i, "") || "Agent preset").trim()
    const preset: CustomPreset = { id: uid("preset"), name: cleaned, content: activeTab.content }
    setCustomPresets((current) => [preset, ...current])
    return `Created preset ${cleaned}`
  }

  function parseAgentEnvelope(raw: string): { reply: string; actions: AgentAction[] } {
    const trimmed = raw.trim()
    const fenced = trimmed.match(/```(?:json)?\s*([\s\S]*?)```/i)?.[1]?.trim()
    const candidates = [fenced, trimmed].filter(Boolean) as string[]
    for (const candidate of candidates) {
      try {
        const value = JSON.parse(candidate)
        if (value && typeof value === "object") {
          const obj = value as { reply?: unknown; actions?: unknown }
          return {
            reply: typeof obj.reply === "string" ? obj.reply : "Done.",
            actions: Array.isArray(obj.actions) ? obj.actions.filter((item): item is AgentAction => !!item && typeof item === "object" && typeof (item as AgentAction).type === "string") : [],
          }
        }
      } catch { /* try next shape */ }
    }
    return { reply: trimmed || "I couldn't produce a response.", actions: [] }
  }

  function fallbackAgentCommand(input: string): { reply: string; actions: AgentAction[] } | null {
    const lower = input.toLowerCase().trim()
    if (/^(open|go to|show)\s+(the\s+)?editor/.test(lower)) return { reply: "Opening the editor.", actions: [{ type: "navigate", view: "editor" }] }
    if (/^(open|go to|show)\s+(the\s+)?presets/.test(lower)) return { reply: "Opening presets.", actions: [{ type: "navigate", view: "presets" }] }
    if (/^(open|go to|show)\s+(the\s+)?activity/.test(lower)) return { reply: "Opening activity.", actions: [{ type: "navigate", view: "activity" }] }
    if (/^(open|go to|show)\s+(the\s+)?settings/.test(lower)) return { reply: "Opening settings.", actions: [{ type: "navigate", view: "settings" }] }
    if (/\b(new|create)\b.*\b(file|config|configuration|tab)\b/.test(lower)) return { reply: "Creating a new configuration.", actions: [{ type: "new_config" }] }
    if (/\bformat\b.*\b(json|file|config|configuration)?\b/.test(lower)) return { reply: "Formatting the current JSON.", actions: [{ type: "format_json" }] }
    if (/\brefresh\b.*\b(offset|offsets)\b/.test(lower)) return { reply: "Refreshing offsets.", actions: [{ type: "refresh_offsets" }] }
    if (/\brefresh\b.*\b(status|roblox|runtime)\b/.test(lower)) return { reply: "Refreshing runtime status.", actions: [{ type: "refresh_status" }] }
    if (/\bapply\b/.test(lower)) return { reply: "I can apply the current configuration after confirmation.", actions: [{ type: "apply_current" }] }
    const match = input.match(/(?:set|add)\s+([A-Za-z][A-Za-z0-9_]*)\s+(?:to|=)\s+["']?([^"'\n]+)["']?/i)
    if (match) {
      const [, name, rawValue] = match
      const value = rawValue.trim()
      return { reply: `Adding ${name} = ${value} to the current configuration.`, actions: [{ type: "merge_flags", flags: { [name]: value } }] }
    }
    return null
  }

  async function executeAgentActions(actions: AgentAction[]) {
    const summaries: string[] = []
    for (const action of actions.slice(0, 12)) {
      const type = String(action.type || "")
      if (type === "navigate") {
        const target = String(action.view || "") as View
        if (["home", "editor", "presets", "activity", "agent", "settings"].includes(target)) {
          changeView(target)
          summaries.push(`Opened ${target}`)
        }
      } else if (type === "new_config") {
        const name = typeof action.name === "string" ? action.name : undefined
        const contentValue = action.json ?? {}
        let content = "{}\n"
        try { content = typeof contentValue === "string" ? JSON.stringify(JSON.parse(contentValue), null, 2) : JSON.stringify(contentValue, null, 2) } catch { /* keep empty */ }
        newTab(content, name)
        summaries.push(`Created ${name || "a new configuration"}`)
      } else if (type === "replace_json") {
        if (replaceEditorJson(action.json, typeof action.name === "string" ? action.name : undefined)) summaries.push("Replaced editor JSON")
      } else if (type === "merge_flags") {
        if (action.flags && typeof action.flags === "object" && !Array.isArray(action.flags)) {
          mergeFlagsIntoEditor(action.flags as Record<string, unknown>)
          summaries.push(`Updated ${Object.keys(action.flags as Record<string, unknown>).length} flag(s)`)
        }
      } else if (type === "format_json") {
        formatJson()
        summaries.push("Formatted JSON")
      } else if (type === "save_config") {
        summaries.push(saveAgentConfig(typeof action.name === "string" ? action.name : undefined))
      } else if (type === "create_preset") {
        summaries.push(saveAgentPreset(typeof action.name === "string" ? action.name : undefined))
      } else if (type === "load_preset") {
        const id = String(action.id || "")
        const preset = builtInPresets.find((item) => item.id === id)
        if (preset) {
          loadPreset(preset.value, preset.name)
          summaries.push(`Loaded ${preset.name} preset`)
        }
      } else if (type === "refresh_status") {
        await refreshStatus(settings.apiUrl, true)
        summaries.push("Refreshed runtime status")
      } else if (type === "refresh_offsets") {
        await refreshOffsets()
        summaries.push("Started offset refresh")
      } else if (type === "apply_current") {
        if (agentSettings.confirmApply) {
          setPendingAgentApply(true)
          summaries.push("Apply is waiting for your confirmation")
        } else {
          await applyFlags("agent")
          summaries.push("Requested apply")
        }
      }
    }
    return summaries
  }

  function buildAgentSystemPrompt() {
    const currentJson = text.length > 22000 ? `${text.slice(0, 22000)}\n/* truncated */` : text
    return `You are the built-in FFlag Studio assistant. You can answer normal general questions and you can control features of this app through actions.\n\nReturn ONLY valid JSON in this exact shape:\n{"reply":"natural language answer","actions":[]}\n\nAvailable actions:\n- {"type":"navigate","view":"home|editor|presets|activity|agent|settings"}\n- {"type":"new_config","name":"optional.json","json":{}}\n- {"type":"replace_json","name":"optional.json","json":{}}\n- {"type":"merge_flags","flags":{"FlagName":"value"}}\n- {"type":"format_json"}\n- {"type":"save_config","name":"optional.json"}\n- {"type":"create_preset","name":"Preset name"}\n- {"type":"load_preset","id":"fps|performance|texture"}\n- {"type":"refresh_status"}\n- {"type":"refresh_offsets"}\n- {"type":"apply_current"}\n\nNever invent an action outside this list. Do not claim an app action happened unless you include it in actions. Keep destructive or apply-like actions explicit. If you create or modify editor JSON, do not also save or apply it in the same response; let the UI update first and do that on the next turn. You do not have arbitrary shell or unrestricted computer access. For ordinary questions, use an empty actions array.\n\nCurrent app state:\n- view: ${view}\n- desktop mode: ${isDesktop}\n- Roblox connected: ${status.connected}\n- PID: ${status.pid ?? "none"}\n- offsets ready: ${status.ready}\n- flags loaded: ${status.flagsLoaded}\n- current file: ${activeTab?.name ?? "none"}\n- saved files: ${savedConfigs.map((item) => item.name).slice(0, 30).join(", ") || "none"}\n- custom presets: ${customPresets.map((item) => item.name).slice(0, 30).join(", ") || "none"}\nCurrent editor JSON:\n${currentJson}`
  }

  function startBottomPanelResize(event: React.PointerEvent<HTMLDivElement>) {
    event.preventDefault()
    const startY = event.clientY
    const startHeight = bottomPanelHeight
    document.body.classList.add("panel-resizing")
    const onMove = (moveEvent: PointerEvent) => {
      const delta = startY - moveEvent.clientY
      setBottomPanelHeight(Math.min(420, Math.max(72, startHeight + delta)))
    }
    const onUp = () => {
      document.body.classList.remove("panel-resizing")
      window.removeEventListener("pointermove", onMove)
      window.removeEventListener("pointerup", onUp)
    }
    window.addEventListener("pointermove", onMove)
    window.addEventListener("pointerup", onUp)
  }

  function startSidebarResize(event: React.PointerEvent<HTMLDivElement>) {
    if (sidebarCollapsed) return
    event.preventDefault()
    const startX = event.clientX
    const startWidth = sidebarWidth
    document.body.classList.add("sidebar-resizing")
    const onMove = (moveEvent: PointerEvent) => {
      const delta = moveEvent.clientX - startX
      setSidebarWidth(Math.min(380, Math.max(190, startWidth + delta)))
    }
    const onUp = () => {
      document.body.classList.remove("sidebar-resizing")
      window.removeEventListener("pointermove", onMove)
      window.removeEventListener("pointerup", onUp)
    }
    window.addEventListener("pointermove", onMove)
    window.addEventListener("pointerup", onUp)
  }

  function jumpToFlag(flagName: string) {
    setInspectedFlag(flagName)
    changeView("editor")
    window.setTimeout(() => {
      const editor = codeMirrorRef.current
      if (!editor) return
      const matchIndex = text.indexOf(`"${flagName}"`) >= 0 ? text.indexOf(`"${flagName}"`) : text.indexOf(flagName)
      if (matchIndex < 0) return
      const end = Math.min(text.length, matchIndex + flagName.length + (text.slice(matchIndex, matchIndex + 1) === '"' ? 2 : 0))
      editor.focus()
      editor.dispatch({
        selection: { anchor: matchIndex, head: end },
        effects: EditorView.scrollIntoView(matchIndex, { y: "center" }),
      })
    }, 140)
  }

  async function copyFailedFlags() {
    if (!visibleFailedResults.length) { showToast("No failed flags", undefined, "info"); return }
    try {
      await navigator.clipboard.writeText(visibleFailedResults.map((entry) => entry.name).join("\n"))
      showToast("Failed flag names copied", `${visibleFailedResults.length} flag${visibleFailedResults.length === 1 ? "" : "s"}`)
    } catch { showToast("Clipboard access blocked", undefined, "error") }
  }

  function exportFailedFlags() {
    if (!lastApplied || !visibleFailedResults.length) { showToast("No failed flags", undefined, "info"); return }
    const source = safeParse<Record<string, unknown>>(lastApplied.content, {})
    const failedObject = Object.fromEntries(visibleFailedResults.map((entry) => [entry.name, source[entry.name] ?? entry.value ?? ""]))
    exportText(JSON.stringify(failedObject, null, 2), `${lastApplied.name.replace(/\.json$/i, "")}-failed.json`)
  }

  async function exportCompleteSkippedReport() {
    if (!parsed.ok) {
      showToast("Cannot export", "The editor JSON is invalid.", "error")
      return
    }
    const all = await runPreflight(parsed.value, false)
    if (!all?.ok) return
    const skipped = all.entries.filter((entry) => !entry.supported || !entry.valid)
    exportText(JSON.stringify({
      type: "ZFLAG local compatibility report",
      note: "This report describes local ClientAppSettings allowlist compatibility, not live injection results.",
      total: all.total, savedEligible: all.supported, unsupported: all.unsupported, invalid: all.invalid,
      skipped,
    }, null, 2), `${(activeTab?.name ?? "profile").replace(/\.json$/i, "")}-all-skipped.json`)
    showToast("Complete report exported", `${skipped.length.toLocaleString()} skipped local flags, including reasons. Nothing was changed in Roblox.`, "info")
  }

  function analyzeFailedFlagsWithAi() {
    if (!failedResults.length) { showToast("No failed flags", "Apply a profile first, then analyze the failures.", "info"); return }
    const summary = failedResults.slice(0, 120).map((entry) => `${entry.name}: ${entry.message}`).join("\n")
    const prompt = `Analyze these failed FFlag apply results. Explain the main failure patterns, point out unsupported/not-in-offset flags, and suggest a cleaner version of the current config. If it makes sense, create a NEW config with unsupported flags removed. Do not apply anything automatically.\n\n${summary}`
    changeView("agent")
    window.setTimeout(() => void sendAgentMessage(prompt), 160)
  }

  function renderActivityGroups(limit?: number) {
    const groups = typeof limit === "number" ? groupedActivity.slice(0, limit) : groupedActivity
    if (!groups.length) return <div className="empty-center">No matching activity.</div>
    return groups.map((group) => {
      const expanded = !!expandedLogGroups[group.key]
      const first = group.entries[0]
      const flagName = first.message.match(/^([^:]+):/)?.[1] || first.message.match(/^([^ =]+)\s*=/)?.[1]
      return <div className="grouped-log-wrap" key={group.key}>
        <div className={cn("mini-log grouped-log", group.grouped && group.entries.length > 1 && "has-children")}>
          <span>{first.time}</span>
          <b className={group.level}>{String(group.level).toUpperCase()}</b>
          <button className="grouped-log-message" type="button" onClick={() => flagName && jumpToFlag(flagName)} title={flagName ? `Jump to ${flagName}` : undefined}>{group.grouped && group.entries.length > 1 ? group.reason : first.message}</button>
          {group.grouped && group.entries.length > 1 && <button className="group-count" type="button" onClick={() => setExpandedLogGroups((current) => ({ ...current, [group.key]: !current[group.key] }))}>×{group.entries.length} {expanded ? "▴" : "▾"}</button>}
        </div>
        {expanded && group.entries.length > 1 && <div className="grouped-log-children">{group.entries.map((entry) => {
          const childFlag = entry.message.match(/^([^:]+):/)?.[1] || entry.message.match(/^([^ =]+)\s*=/)?.[1]
          return <button key={entry.id} type="button" onClick={() => childFlag && jumpToFlag(childFlag)}><span>{childFlag || entry.message}</span><small>{entry.message.split(":").slice(1).join(":").trim() || entry.level}</small></button>
        })}</div>}
      </div>
    })
  }

  async function testAgentConnection(useDraft = false, quiet = false) {
    const source = useDraft ? draftAgentSettings : agentSettings
    setAgentHealth("checking")
    setAgentHealthMessage("Checking provider…")
    try {
      const response = await fetch(`${settings.apiUrl}/agent/test`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          provider: source.provider,
          baseUrl: source.baseUrl,
          model: source.model,
          apiKey: agentApiKey,
        }),
      })
      const result = await response.json()
      if (!response.ok || !result.ok) throw new Error(result.error || "Connection test failed")
      if (typeof result.model === "string" && result.model) {
        setDraftAgentSettings((current) => ({ ...current, model: result.model }))
        if (!useDraft) {
          const next = { ...agentSettings, model: result.model }
          setAgentSettings(next)
          localStorage.setItem("fflag-studio-agent-settings", JSON.stringify(next))
        }
      }
      setAgentHealth("online")
      setAgentHealthMessage(`Connected${result.model ? ` · ${result.model}` : ""}`)
      if (!quiet) showToast("AI connected", result.model || AGENT_PROVIDER_DEFAULTS[source.provider].label, "success")
      return true
    } catch (error) {
      const message = error instanceof Error ? error.message : "AI provider unavailable"
      setAgentHealth("offline")
      setAgentHealthMessage(message)
      if (!quiet) showToast("AI connection failed", message, "error")
      return false
    }
  }

  async function sendAgentMessage(explicit?: string) {
    const input = (explicit ?? agentInput).trim()
    if (!input || agentBusy) return
    const userMessage: AgentMessage = { id: uid("msg"), role: "user", content: input, time: Date.now() }
    const nextHistory = [...agentMessages, userMessage]
    setAgentMessages(nextHistory)
    setAgentInput("")
    setAgentBusy(true)
    try {
      let envelope: { reply: string; actions: AgentAction[] } | null = null
      if (agentHealth !== "online") {
        await testAgentConnection(false, true)
      }
      try {
        const response = await fetch(`${settings.apiUrl}/agent/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            provider: agentSettings.provider,
            baseUrl: agentSettings.baseUrl,
            model: agentSettings.model,
            apiKey: agentApiKey,
            system: buildAgentSystemPrompt(),
            messages: nextHistory.slice(-14).map((message) => ({ role: message.role, content: message.content })),
          }),
        })
        const result = await response.json()
        if (!response.ok || !result.ok) throw new Error(result.error || "AI provider unavailable")
        if (typeof result.model === "string" && result.model && result.model !== agentSettings.model) {
          const next = { ...agentSettings, model: result.model }
          setAgentSettings(next)
          setDraftAgentSettings(next)
          localStorage.setItem("fflag-studio-agent-settings", JSON.stringify(next))
          showToast("AI model switched", result.model, "info")
        }
        envelope = parseAgentEnvelope(String(result.content || ""))
      } catch (error) {
        const fallback = fallbackAgentCommand(input)
        if (fallback) {
          envelope = fallback
        } else {
          const message = error instanceof Error ? error.message : "AI provider unavailable"
          envelope = {
            reply: `I couldn't reach the configured AI model (${message}). I can still handle basic app commands locally. Open Connection settings to detect an installed Ollama model or connect OpenAI/Codex, Claude, Gemini, OpenRouter, or another compatible API.`,
            actions: [],
          }
        }
      }
      const summaries = await executeAgentActions(envelope.actions)
      const assistantMessage: AgentMessage = { id: uid("msg"), role: "assistant", content: envelope.reply, time: Date.now(), actionSummary: summaries }
      setAgentMessages((current) => [...current, assistantMessage])
    } finally {
      setAgentBusy(false)
    }
  }

  async function nativeWindowAction(action: "minimize" | "toggle" | "close") {
    if (!isDesktop) return
    try {
      const { getCurrentWindow } = await import("@tauri-apps/api/window")
      const current = getCurrentWindow()
      if (action === "minimize") await current.hide()
      if (action === "toggle") await current.toggleMaximize()
      if (action === "close") await current.close()
    } catch (error) {
      showToast("Window action failed", error instanceof Error ? error.message : String(error), "error")
    }
  }

  trayActionRef.current = (action: string) => {
    if (action === "editor") changeView("editor")
    else if (action === "agent") changeView("agent")
    else if (action === "refresh") void refreshStatus(settings.apiUrl, false)
    else if (action === "apply") void applyFlags("tray")
  }
  hotkeyActionRef.current = {
    save: saveCurrentConfig,
    apply: () => { void applyFlags("hotkey") },
    newTab: () => newTab(),
    format: formatJson,
    agent: () => changeView("agent"),
  }

  useEffect(() => {
    if (!isDesktop) return
    let unlisten: (() => void) | undefined
    void listen<string>("tray-action", (event) => trayActionRef.current(String(event.payload || ""))).then((stop) => { unlisten = stop }).catch(() => {})
    return () => unlisten?.()
  }, [isDesktop])

  useEffect(() => {
    let cancelled = false
    void loadBackgroundFromDb().then((savedMedia) => {
      if (cancelled || !savedMedia) return
      setSettings((current) => ({ ...current, backgroundData: savedMedia }))
      setDraftSettings((current) => ({ ...current, backgroundData: savedMedia }))
    }).catch(() => {})
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    document.documentElement.classList.toggle("native-shell", isDesktop)
    return () => document.documentElement.classList.remove("native-shell")
  }, [isDesktop])

  // Large workspace data lives in IndexedDB. On first V14 launch we migrate the
  // old localStorage copies, then remove those bulky keys after IndexedDB confirms.
  useEffect(() => {
    let cancelled = false
    async function hydrateWorkspace() {
      try {
        const [dbConfigs, dbPresets, dbTabs, dbMessages, dbHistory] = await Promise.all([
          dataGet<SavedConfig[]>("configs"), dataGet<CustomPreset[]>("presets"), dataGet<EditorTab[]>("tabs"),
          dataGet<AgentMessage[]>("agentMessages"), dataGet<ApplySnapshot[]>("applyHistory"),
        ])
        if (cancelled) return
        if (validConfigs(dbConfigs)) setSavedConfigs(dbConfigs)
        if (Array.isArray(dbPresets)) setCustomPresets(dbPresets)
        if (validTabs(dbTabs)) setTabs(dbTabs)
        if (Array.isArray(dbMessages)) setAgentMessages(dbMessages)
        if (Array.isArray(dbHistory)) setApplyHistory(dbHistory)
      } catch { /* localStorage migration remains a safe fallback */ }
      if (!cancelled) setWorkspaceHydrated(true)
    }
    void hydrateWorkspace()
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    if (!workspaceHydrated) return
    void dataPut("configs", savedConfigs).then(() => localStorage.removeItem("fflag-studio-configs")).catch(() => {})
  }, [savedConfigs, workspaceHydrated])
  useEffect(() => {
    if (!workspaceHydrated) return
    void dataPut("presets", customPresets).then(() => localStorage.removeItem("fflag-studio-custom-presets")).catch(() => {})
  }, [customPresets, workspaceHydrated])
  useEffect(() => {
    if (!workspaceHydrated) return
    void dataPut("agentMessages", agentMessages.slice(-120)).then(() => localStorage.removeItem("fflag-studio-agent-messages")).catch(() => {})
  }, [agentMessages, workspaceHydrated])
  useEffect(() => {
    if (!workspaceHydrated) return
    void dataPut("applyHistory", applyHistory.slice(0, 80)).then(() => localStorage.removeItem("fflag-studio-apply-history")).catch(() => {})
  }, [applyHistory, workspaceHydrated])
  useEffect(() => {
    if (!workspaceHydrated) return
    void dataPut("tabs", tabs).then(() => { localStorage.removeItem("fflag-studio-tabs"); localStorage.removeItem("fflag-studio-editor") }).catch(() => {})
  }, [tabs, workspaceHydrated])

  useEffect(() => {
    // Repair stale persisted tab IDs. This fixes editor actions silently targeting a
    // no-longer-existing tab after tabs were deleted or migrated.
    if (!tabs.length) return
    if (!tabs.some((tab) => tab.id === activeTabId)) setActiveTabId(tabs[0].id)
  }, [tabs, activeTabId])

  useEffect(() => localStorage.setItem("fflag-studio-active-tab", activeTabId), [activeTabId])
  useEffect(() => localStorage.setItem("zflag-favorite-flags", JSON.stringify(favoriteFlags)), [favoriteFlags])
  useEffect(() => localStorage.setItem("fflag-studio-bottom-panel-height", String(bottomPanelHeight)), [bottomPanelHeight])
  useEffect(() => localStorage.setItem("fflag-studio-sidebar-width", String(sidebarWidth)), [sidebarWidth])
  useEffect(() => { agentBottomRef.current?.scrollIntoView({ behavior: settings.animations ? "smooth" : "auto", block: "end" }) }, [agentMessages, agentBusy, settings.animations])
  useEffect(() => {
    void navigator.storage?.estimate?.().then((estimate) => setStorageEstimate({ usage: estimate.usage ?? 0, quota: estimate.quota ?? 0 })).catch(() => {})
  }, [savedConfigs.length, tabs.length, applyHistory.length])

  useEffect(() => {
    const timer = toast ? window.setTimeout(() => setToast(null), settings.notificationDuration) : undefined
    return () => { if (timer) window.clearTimeout(timer) }
  }, [toast?.id, settings.notificationDuration])

  useEffect(() => {
    if (view !== "agent") return
    if (agentSettings.provider === "ollama" && agentModels.length === 0 && !agentModelBusy) {
      void refreshAgentModels(false, true)
    }
    if (agentSettings.provider === "ollama" && agentHealth === "unknown") {
      void testAgentConnection(false, true)
    }
  }, [view, agentSettings.provider, agentSettings.baseUrl])

  useEffect(() => {
    refreshStatus(settings.apiUrl, true)
    if (!settings.autoRefresh) return
    const timer = window.setInterval(() => refreshStatus(settings.apiUrl, true), settings.pollMs)
    return () => window.clearInterval(timer)
  }, [settings.apiUrl, settings.autoRefresh, settings.pollMs])

  useEffect(() => {
    if (!isDesktop || desktopSidecarStarted) return
    void startOrRestartDesktopBackend("startup")
  }, [])

  useEffect(() => {
    if (!isDesktop) return
    let stopped = false
    const timer = window.setInterval(async () => {
      if (stopped || backendStartingRef.current) return
      try {
        const response = await fetch(`${settings.apiUrl}/health`, { cache: "no-store" })
        if (!response.ok) throw new Error("health check failed")
        backendMissesRef.current = 0
      } catch {
        backendMissesRef.current += 1
        if (backendMissesRef.current >= 3) {
          backendMissesRef.current = 0
          void startOrRestartDesktopBackend("watchdog")
        }
      }
    }, 9000)
    return () => { stopped = true; window.clearInterval(timer) }
  }, [isDesktop, settings.apiUrl])

  useEffect(() => {
    const wasConnected = lastConnectedRef.current
    lastConnectedRef.current = status.connected
    if (!wasConnected && status.connected && settings.autoApplyEnabled && settings.autoApplyConfigId) {
      const config = savedConfigs.find((item) => item.id === settings.autoApplyConfigId)
      if (config) {
        try {
          const value = JSON.parse(config.content)
          if (value && !Array.isArray(value) && typeof value === "object") {
            void applyFlags("auto-apply", value as Record<string, unknown>, config.name)
          }
        } catch { showToast("Auto Apply skipped", `${config.name} contains invalid JSON.`, "warning") }
      }
    }
  }, [status.connected, settings.autoApplyEnabled, settings.autoApplyConfigId, savedConfigs])

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") { event.preventDefault(); hotkeyActionRef.current.save() }
      if ((event.ctrlKey || event.metaKey) && event.key === "Enter") { event.preventDefault(); hotkeyActionRef.current.apply() }
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "n") { event.preventDefault(); hotkeyActionRef.current.newTab() }
      if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key.toLowerCase() === "f") { event.preventDefault(); hotkeyActionRef.current.format() }
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "l") { event.preventDefault(); hotkeyActionRef.current.agent() }
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") { event.preventDefault(); setCommandOpen((open) => !open); setCommandQuery("") }
      if (event.key === "Escape") {
        setOpenMenu(null); setClearMenuOpen(false); setClearDialog(null); setSaveDialog(null); setCommandOpen(false); setPreflightOpen(false); setCompareOpen(false)
      }
    }
    window.addEventListener("keydown", onKeyDown)
    return () => window.removeEventListener("keydown", onKeyDown)
  }, [])

  useEffect(() => {
    function closeMenus() {
      setOpenMenu(null)
      setClearMenuOpen(false)
    }
    window.addEventListener("click", closeMenus)
    return () => window.removeEventListener("click", closeMenus)
  }, [])

  function renderSidebar() {
    if (sidebarCollapsed) {
      return (
        <aside className="sidebar sidebar-collapsed">
          <button className="brand-mark compact logo-button" onClick={() => setSidebarCollapsed(false)} type="button"><img src={logoMark} alt="ZFLAG" className="brand-logo" /></button>
          <div className="collapsed-nav">
            <TopIcon active={view === "home"} label="Home" onClick={() => changeView("home")}><Home className="size-4" /></TopIcon>
            <TopIcon active={view === "editor"} label="Editor" onClick={() => changeView("editor")}><Braces className="size-4" /></TopIcon>
            <TopIcon active={view === "presets"} label="Presets" onClick={() => changeView("presets")}><Sparkles className="size-4" /></TopIcon>
            <TopIcon active={view === "agent"} label="Agent" onClick={() => changeView("agent")}><Bot className="size-4" /></TopIcon>
            <TopIcon active={view === "activity"} label="Activity" onClick={() => changeView("activity")}><Activity className="size-4" /></TopIcon>
            <TopIcon active={view === "settings"} label="Settings" onClick={() => changeView("settings")}><Settings className="size-4" /></TopIcon>
          </div>
          <button className="collapse-button" onClick={() => setSidebarCollapsed(false)} type="button"><PanelLeftOpen className="size-4" /></button>
        </aside>
      )
    }

    return (
      <aside className="sidebar">
        <div className="brand-row">
          <div className="brand-mark"><img src={logoMark} alt="ZFLAG" className="brand-logo" /></div>
          <div className="min-w-0">
            <div className="brand-name">ZFLAG</div>
            <div className="brand-sub">FFLAG STUDIO • BY ZEBRA</div>
          </div>
        </div>

        <div className="sidebar-heading-row">
          <h2>{view === "home" ? "Home" : view === "editor" ? "Explorer" : view === "presets" ? "Presets" : view === "agent" ? "Agent" : view === "activity" ? "Activity" : "Settings"}</h2>
          <button className="icon-button" onClick={() => setSidebarCollapsed(true)} type="button"><PanelLeftClose className="size-4" /></button>
        </div>

        {view === "editor" ? (
          <>
            <div className="search-box"><Search className="size-3.5" /><input value={configSearch} onChange={(e) => setConfigSearch(e.target.value)} placeholder="Search files..." /></div>
            <div className="sidebar-section-label">LOCAL FILES</div>
            <div className="config-list smooth-scroll">
              {filteredConfigs.length === 0 && <div className="sidebar-empty">No saved FFlag files yet.</div>}
              {filteredConfigs.map((config) => (
                <div key={config.id} className={cn("file-row", activeTab?.configId === config.id && "is-active")}>
                  <button className="file-main" onClick={() => openConfig(config)} type="button"><FileJson className="size-3.5" /><span>{config.name}</span></button>
                  <div className="relative">
                    <button className="file-more" type="button" onClick={(event) => { event.stopPropagation(); setOpenMenu(openMenu === config.id ? null : config.id) }}><Ellipsis className="size-3.5" /></button>
                    {openMenu === config.id && (
                      <div className="dropdown-menu" onClick={(event) => event.stopPropagation()}>
                        <button type="button" onClick={() => { setSaveDialog({ mode: "rename", value: config.name.replace(/\.json$/i, ""), targetId: config.id }); setOpenMenu(null) }}><PencilLine className="size-3.5" /> Rename</button>
                        <button type="button" onClick={() => exportText(config.content, config.name)}><Download className="size-3.5" /> Export</button>
                        <div className="menu-separator" />
                        <button type="button" className="danger" onClick={() => deleteConfig(config.id)}><Trash2 className="size-3.5" /> Delete</button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
            <button className="new-file-row" type="button" onClick={() => newTab()}><Plus className="size-3.5" /> New configuration</button>
          </>
        ) : view === "settings" ? (
          <div className="settings-nav-stack">
            <button type="button" className={cn("settings-nav-item", settingsSection === "general" && "is-active")} onClick={() => setSettingsSection("general")}><SlidersHorizontal className="size-4" /><div><strong>General</strong><small>Run mode & basics</small></div><ChevronLeft className="nav-chevron size-3.5 rotate-180" /></button>
            <button type="button" className={cn("settings-nav-item", settingsSection === "appearance" && "is-active")} onClick={() => setSettingsSection("appearance")}><Monitor className="size-4" /><div><strong>Appearance</strong><small>Theme & background</small></div><ChevronLeft className="nav-chevron size-3.5 rotate-180" /></button>
            <button type="button" className={cn("settings-nav-item", settingsSection === "editor" && "is-active")} onClick={() => setSettingsSection("editor")}><Braces className="size-4" /><div><strong>Editor</strong><small>Font & panels</small></div><ChevronLeft className="nav-chevron size-3.5 rotate-180" /></button>
            <button type="button" className={cn("settings-nav-item", settingsSection === "behavior" && "is-active")} onClick={() => setSettingsSection("behavior")}><Rocket className="size-4" /><div><strong>Behavior</strong><small>Auto Apply</small></div><ChevronLeft className="nav-chevron size-3.5 rotate-180" /></button>
            <button type="button" className={cn("settings-nav-item", settingsSection === "notifications" && "is-active")} onClick={() => setSettingsSection("notifications")}><Activity className="size-4" /><div><strong>Notifications</strong><small>Position & duration</small></div><ChevronLeft className="nav-chevron size-3.5 rotate-180" /></button>
            <button type="button" className={cn("settings-nav-item", settingsSection === "keybinds" && "is-active")} onClick={() => setSettingsSection("keybinds")}><SquareTerminal className="size-4" /><div><strong>Keybinds</strong><small>Keyboard shortcuts</small></div><ChevronLeft className="nav-chevron size-3.5 rotate-180" /></button>
            <button type="button" className={cn("settings-nav-item", settingsSection === "connection" && "is-active")} onClick={() => setSettingsSection("connection")}><Globe2 className="size-4" /><div><strong>Connections</strong><small>Backend & AI models</small></div><ChevronLeft className="nav-chevron size-3.5 rotate-180" /></button>
          </div>
        ) : (
          <div className="sidebar-nav-stack">
            <SidebarButton active={view === "home"} icon={<Home className="size-4" />} onClick={() => changeView("home")}>Overview</SidebarButton>
            <SidebarButton active={false} icon={<Braces className="size-4" />} onClick={() => changeView("editor")}>Editor</SidebarButton>
            <SidebarButton active={view === "presets"} icon={<Sparkles className="size-4" />} onClick={() => changeView("presets")}>Presets</SidebarButton>
            <SidebarButton active={view === "agent"} icon={<Bot className="size-4" />} onClick={() => changeView("agent")}>AI Agent</SidebarButton>
            <SidebarButton active={view === "activity"} icon={<Activity className="size-4" />} onClick={() => changeView("activity")}>Activity</SidebarButton>
          </div>
        )}

        <div className="sidebar-bottom">
          <div className="credits-card">
            <span>Made by Zebra</span>
            <small>FFlag Studio v2.0.9</small>
          </div>
          <div className="mode-card">
            <div className="mode-icon">{isDesktop ? <Monitor className="size-4" /> : <Globe2 className="size-4" />}</div>
            <div className="min-w-0 flex-1"><div className="mode-title">{isDesktop ? "Desktop app" : "Browser mode"}</div><div className="mode-sub">{backendReachable ? "Local bridge connected" : "Local bridge offline"}</div></div>
            <span className={cn("status-dot", backendReachable && "online")} />
          </div>
          <SidebarButton icon={<Settings className="size-4" />} active={view === "settings"} onClick={() => changeView("settings")}>Settings</SidebarButton>
        </div>
      </aside>
    )
  }

  function renderTopbar() {
    function handleTopbarDoubleClick(event: React.MouseEvent<HTMLElement>) {
      const target = event.target as HTMLElement
      if (target.closest("button, nav, input, select, textarea, a, .no-drag")) return
      void nativeWindowAction("toggle")
    }
    return (
      <header className="topbar" onDoubleClick={handleTopbarDoubleClick}>
        {isDesktop && <div className="topbar-drag-fill" data-tauri-drag-region aria-hidden="true" />}
        <div className="topbar-left topbar-drag" data-tauri-drag-region>
          <div className="title-brand" data-tauri-drag-region>
            <img src={logoMark} alt="ZFLAG" className="title-logo" data-tauri-drag-region />
            <div className="title-brand-copy" data-tauri-drag-region>
              <strong data-tauri-drag-region>ZFLAG</strong>
              <span data-tauri-drag-region>FFlag Studio • By Zebra</span>
            </div>
          </div>
        </div>
        <nav className="top-nav no-drag">
          <TopIcon active={view === "home"} label="Home" onClick={() => changeView("home")}><Home className="size-4" /></TopIcon>
          <TopIcon active={view === "editor"} label="Editor" onClick={() => changeView("editor")}><Braces className="size-4" /></TopIcon>
          <TopIcon active={view === "presets"} label="Presets" onClick={() => changeView("presets")}><Sparkles className="size-4" /></TopIcon>
          <TopIcon active={view === "agent"} label="AI Agent" onClick={() => changeView("agent")}><Bot className="size-4" /></TopIcon>
          <TopIcon active={view === "activity"} label="Activity" onClick={() => changeView("activity")}><Activity className="size-4" /></TopIcon>
          <TopIcon active={view === "settings"} label="Settings" onClick={() => changeView("settings")}><Settings className="size-4" /></TopIcon>
        </nav>
        <div className="topbar-right no-drag">
          <Badge className={cn("runtime-pill", status.connected && "connected")}>
            <span className={cn("status-dot", status.connected && "online")} />
            {status.connected ? `PID ${status.pid}` : "Roblox not running"}
          </Badge>
          {isDesktop && (
            <div className="window-controls">
              <button type="button" aria-label="Minimize" onClick={() => void nativeWindowAction("minimize")}><Minus className="size-3.5" /></button>
              <button type="button" aria-label="Maximize" onClick={() => void nativeWindowAction("toggle")}><Square className="size-3" /></button>
              <button type="button" className="window-close" aria-label="Close" onClick={() => void nativeWindowAction("close")}><X className="size-3.5" /></button>
            </div>
          )}
        </div>
      </header>
    )
  }

  function renderTabs() {
    if (view !== "editor") return null
    return (
      <div className="tab-strip smooth-scroll">
        {tabs.map((tab) => {
          const stats = tabApplyStats.get(tab.id)
          return (
            <button key={tab.id} type="button" onClick={() => setActiveTabId(tab.id)} className={cn("editor-tab", activeTabId === tab.id && "is-active")}>
              <FileJson className="size-3.5 shrink-0" />
              <span className="truncate">{tab.name}</span>
              {stats && <span className="tab-apply-stats"><i>✓{stats.applied}</i><em>✕{stats.errors}</em></span>}
              {tab.dirty && <span className="dirty-dot" />}
              <button type="button" className="tab-close" aria-label={`Close ${tab.name}`} onClick={(event) => { event.stopPropagation(); closeTab(tab.id) }}><X className="size-3" /></button>
            </button>
          )
        })}
        <button className="tab-add" type="button" onClick={() => newTab()}><Plus className="size-3.5" /></button>
      </div>
    )
  }

  function addGeneratedFlag() {
    const name = generatorName.trim()
    if (!name) { showToast("Enter a flag name", undefined, "warning"); return }
    let value: unknown = generatorValue
    if (generatorType === "int") {
      const number = Number.parseInt(generatorValue, 10)
      if (!Number.isFinite(number)) { showToast("Enter a valid integer", undefined, "warning"); return }
      value = number
    } else if (generatorType === "bool") {
      value = /^(true|1|yes|on)$/i.test(generatorValue.trim())
    }
    mergeFlagsIntoEditor({ [name]: value })
    showToast("FFlag generated", `${name} = ${String(value)}`)
    setGeneratorName("")
    setGeneratorValue("")
  }

  function restoreSnapshot(snapshot: ApplySnapshot) {
    newTab(snapshot.content, `${snapshot.name.replace(/\.json$/i, "")}-restore.json`)
    showToast("Snapshot restored", snapshot.name)
  }

  function renderHome() {
    return (
      <div className="view-content">
        <div className="page-title-block"><h1>Overview</h1><p>Everything you need at a glance.</p></div>
        <div className="metric-grid">
          <div className="metric-panel"><span>Process</span><strong>{status.connected ? "Connected" : "Offline"}</strong><small>{status.pid ? `PID ${status.pid}` : "Launch Roblox to connect"}</small></div>
          <div className="metric-panel"><span>Offsets</span><strong>{status.flagsLoaded.toLocaleString()}</strong><small>{status.ready ? "Ready" : status.fetching ? "Refreshing…" : "Unavailable"}</small></div>
          <div className="metric-panel"><span>Client</span><strong className="truncate">{status.clientVersion ?? "Unknown"}</strong><small>{backendReachable ? "Backend online" : "Backend offline"}</small></div>
        </div>
        <div className="section-label-row"><span>GET STARTED</span></div>
        <div className="action-stack">
          <button type="button" onClick={() => newTab()}><Braces className="size-4" /><div><strong>New configuration</strong><small>Open a clean FFlag JSON tab</small></div><ChevronLeft className="ml-auto size-4 rotate-180 opacity-40" /></button>
          <button type="button" onClick={() => fileInput.current?.click()}><FolderOpen className="size-4" /><div><strong>Open JSON file</strong><small>Import an existing configuration</small></div><ChevronLeft className="ml-auto size-4 rotate-180 opacity-40" /></button>
          <button type="button" onClick={() => changeView("presets")}><Sparkles className="size-4" /><div><strong>Browse presets</strong><small>Load built-in or saved profiles</small></div><ChevronLeft className="ml-auto size-4 rotate-180 opacity-40" /></button>
          <button type="button" onClick={() => changeView("agent")}><Bot className="size-4" /><div><strong>Ask the AI agent</strong><small>Answer questions or control FFlag Studio with chat</small></div><ChevronLeft className="ml-auto size-4 rotate-180 opacity-40" /></button>
          <button type="button" onClick={() => void refreshOffsets()}><RefreshCw className={cn("size-4", status.fetching && "animate-spin")} /><div><strong>Refresh offsets</strong><small>Update the local offset table</small></div><ChevronLeft className="ml-auto size-4 rotate-180 opacity-40" /></button>
        </div>
        {savedConfigs.length > 0 && <>
          <div className="section-label-row"><span>RECENT CONFIGURATIONS</span><button type="button" onClick={() => changeView("editor")}>Open Explorer</button></div>
          <div className="recent-config-grid">
            {savedConfigs.slice(0, 4).map((config) => <button key={config.id} type="button" className="recent-config-card" onClick={() => openConfig(config)}><FileJson className="size-4" /><div className="min-w-0"><strong>{config.name}</strong><small>{Object.keys(safeParse<Record<string, unknown>>(config.content, {})).length} flags</small></div><ChevronLeft className="size-3.5 rotate-180" /></button>)}
          </div>
        </>}
        <div className="section-label-row"><span>RECENT ACTIVITY</span><button type="button" onClick={() => changeView("activity")}>View all</button></div>
        <div className="activity-panel">
          {status.logs.length === 0 ? <div className="empty-center">No activity yet.</div> : status.logs.slice(-6).reverse().map((entry) => (
            <div key={entry.id} className="activity-row"><span className={cn("activity-dot", entry.level)} /><span className="activity-time">{entry.time}</span><span className="activity-message">{entry.message}</span></div>
          ))}
        </div>
        <div className="section-label-row"><span>LAST APPLY</span><button type="button" onClick={() => changeView("activity")}>History</button></div>
        <div className="history-preview-card">
          {lastApplied ? <><div><strong>{lastApplied.name}</strong><small>{new Date(lastApplied.appliedAt).toLocaleString()} · {lastApplied.applied} applied · {lastApplied.errors} errors · {lastApplied.source ?? "manual"}</small></div><button type="button" onClick={() => restoreSnapshot(lastApplied)}>Restore snapshot</button></> : <div className="empty-center">No apply history yet.</div>}
        </div>
        <div className="section-label-row"><span>WHAT'S NEW</span></div>
        <div className="update-log-card"><strong>v2.0.9 Browser CORS Fix</strong><p>Fixed the exact Browser button failure after backend restart: Browser verification now uses a CORS-safe JSON bundle check, static browser files include CORS headers, and Windows launch uses backend os.startfile first.</p></div><div className="update-log-card"><strong>v2.0.8 Browser + Performance Fix</strong><p>Moved the local bridge to port 18765 to bypass stale old backends, added root redirects, reduced status polling/render churn, and removed expensive always-on blur effects.</p></div><div className="update-log-card"><strong>v2.0.7 Preset + Browser Fix</strong><p>Centered preset/save dialogs through body portals, hardened Browser Mode recovery, fixed stale bridge handling, and added native + backend browser-launch fallbacks.</p></div><div className="update-log-card"><strong>v2.0.4 Friend Package</strong><p>Added a one-click release packager that creates a clean friend-ready installer ZIP.</p></div><div className="update-log-card"><strong>v2.0.3 UI Stability Pass</strong><p>Button reliability pass, safe titlebar clicks, repeated-file imports, browser-mode click locking, build preflight, and no silent invalid-JSON export.</p></div><div className="update-log-card"><strong>v2.0.2 Tauri Config Fix</strong><p>Removed the invalid useHttpsScheme window property so Tauri 2.0.0 can validate the native window configuration and continue the Windows build.</p></div><div className="update-log-card"><strong>v2.0.1 Browser Mode Fix</strong><p>One-click browser mode now verifies/restarts the local bridge, validates the bundled web UI, and opens it in the Windows default browser without relying on the old /open-browser route.</p></div><div className="update-log-card"><strong>v2.0.0 Reliability Suite</strong><p>CodeMirror 6, preflight, rollback, backend recovery, offset validation, IndexedDB workspace storage, inspector, compare tools, and diagnostics.</p></div>
      </div>
    )
  }


  function renderEditor() {
    return (
      <div className={cn("editor-layout", bottomPanelMaximized && "bottom-maximized")}>
        <div className="editor-toolbar">
          <div className="toolbar-left">
            <button type="button" onClick={() => newTab()}><FilePlus2 className="size-3.5" /> New</button>
            <button type="button" onClick={() => fileInput.current?.click()}><FolderOpen className="size-3.5" /> Open</button>
            <button type="button" onClick={saveCurrentConfig}><Save className="size-3.5" /> Save</button>
            <button type="button" onClick={() => parsed.ok ? exportText(JSON.stringify(parsed.value, null, 2), activeTab?.name ?? "fflags.json") : showToast("Cannot export invalid JSON", parsed.error, "error")}><Download className="size-3.5" /> Export</button>
            <button type="button" onClick={formatJson}><Braces className="size-3.5" /> Format</button>
            <div className="editor-clear-split" onClick={(event) => event.stopPropagation()}>
              <button
                type="button"
                className="editor-clear-main"
                onClick={() => requestClearEditor("object")}
                title="Clear the current editor to an empty JSON object"
              >
                <Trash2 className="size-3.5" /> Clear
              </button>
              <button
                ref={clearMenuAnchorRef}
                type="button"
                className="editor-clear-more"
                onClick={toggleClearMenu}
                aria-label="More clear options"
                aria-expanded={clearMenuOpen}
                title="More clear options"
              >
                <ChevronDown className={cn("size-3 clear-chevron", clearMenuOpen && "is-open")} />
              </button>
            </div>
          </div>
          <div className="toolbar-right">
            <button type="button" onClick={() => { setCompareLeftId("current"); setCompareRightId(savedConfigs[0]?.id ?? "current"); setCompareOpen(true) }}><GitCompareArrows className="size-3.5" /> Compare</button>
            <button type="button" disabled={preflightBusy || !parsed.ok || !status.ready} title={!parsed.ok ? "Fix invalid JSON first" : !status.ready ? "Local allowlist is not ready yet" : "Check Roblox local allowlist before saving"} onClick={() => void runPreflight()}><ScanSearch className="size-3.5" /> {preflightBusy ? "Checking…" : "Preflight"}</button>
            <button type="button" disabled={!status.rollbackDepth} onClick={() => void rollbackLastApply()} title={status.rollbackDepth ? "Restore values captured before the last successful Apply" : "No config backup is available yet"}><RotateCcw className="size-3.5" /> Rollback</button>
            <button type="button" onClick={() => setSaveDialog({ mode: "preset", value: activeTab?.name.replace(/\.json$/i, "") ?? "My preset" })}><WandSparkles className="size-3.5" /> Preset</button>
            <Button className="zflag-action zflag-action-primary" size="sm" disabled={busy || !parsed.ok} variant="outline" title="INJECT • Attempts to apply FastFlags to the running Roblox process using the original C++ native engine. Experimental; no memory rollback." onClick={() => void applyFlags("native")}>
              {busy ? <LoaderCircle className="size-3.5 animate-spin" /> : <Play className="size-3.5" />} {busy ? "Injecting…" : "Inject"}
            </Button>
            <Button className="zflag-action zflag-action-secondary" size="sm" disabled={busy || !parsed.ok || !status.ready} variant="outline" title="SAVE ALLOWED • Writes only Roblox-allowlisted flags to the local settings file. Restart Roblox to load them." onClick={() => void applyFlags("manual")}>
              {busy ? <LoaderCircle className="size-3.5 animate-spin" /> : <Save className="size-3.5" />} {busy ? "Saving…" : "Save Allowed"}
            </Button>
          </div>
        </div>
        {nativeFeedback && <div role="status" className="native-inject-feedback"><span>LIVE INJECT</span><p>{nativeFeedback}</p><button type="button" title="Dismiss inject result" onClick={() => setNativeFeedback(null)}>×</button></div>}
        {saveFeedback && <div role="status" className="native-inject-feedback zflag-save-feedback"><span>LOCAL SAVE</span><p>{saveFeedback}</p><button type="button" onClick={() => { setEditorBottomTab("failures"); setBottomPanelOpen(true) }}>Skipped details</button><button type="button" aria-label="Dismiss save result" onClick={() => setSaveFeedback(null)}>×</button></div>
        <div className="diff-strip">
          <div className="diff-left"><span>Changes vs last apply</span><b className="diff-add">+{diffSummary.added}</b><b className="diff-change">~{diffSummary.changed}</b><b className="diff-remove">-{diffSummary.removed}</b></div>
          <div className="apply-result-summary">
            <span className="session-up">+{sessionComparison.newlySuccessful} newly successful</span>
            <span className="session-down">{sessionComparison.newlyFailing} newly failing</span>
          </div>
          <button type="button" onClick={() => setBottomPanelOpen((value) => !value)}>{bottomPanelOpen ? "Hide details" : "Show details"}</button>
        </div>
        {lastApplyStats.total > 0 && <div className="apply-progress-row">
          <div className="apply-progress-track"><span style={{ width: `${lastApplyStats.rate}%` }} /></div>
          <div className="apply-progress-labels"><b>{lastApplyStats.rate}% {lastApplied?.source === "native" ? "reported written" : "saved"}</b><span>{lastApplyStats.success} {lastApplied?.source === "native" ? "reported written" : "saved"}</span><span>{lastApplyStats.failed} {lastApplied?.source === "native" ? "failed" : "skipped"}</span></div>
        </div>}
        <div className="editor-surface" key={activeTab?.id} style={{ ['--editor-font-size' as string]: `${settings.editorFontSize}px` }}>
          <div className="editor-meta">
            <div className="flex min-w-0 items-center gap-2"><FileJson className="size-4" /><span className="truncate">{activeTab?.name}</span>{activeTab?.dirty && <span className="unsaved-label">UNSAVED</span>}</div>
            <div className={cn("validation-chip", parsed.ok ? "valid" : "invalid")}>{parsed.ok ? <Check className="size-3" /> : <CircleAlert className="size-3" />}{parsed.ok ? `${Object.keys(parsed.value).length} entries` : "Invalid JSON"}</div>
          </div>
          <div className="code-editor-shell codemirror-shell">
            <CodeMirrorJsonEditor
              viewRef={codeMirrorRef}
              value={text}
              onChange={(next) => updateActiveText(next)}
              onFlagFocus={setInspectedFlag}
              fontSize={settings.editorFontSize}
              wordWrap={settings.editorWordWrap}
              themeMode={visualSettings.themeMode}
            />
          </div>
          <div className="editor-statusbar"><span>{parsed.ok ? "JSON valid" : parsed.error}</span><span>CodeMirror 6 · Ctrl+F search · Ctrl+H replace · Ctrl+Z undo · Ctrl+S save · Ctrl+Enter apply</span></div>
        </div>
        {inspectedFlag && <aside className="flag-inspector">
          <div className="flag-inspector-head"><div><span>FLAG INSPECTOR</span><strong>{inspectedFlag}</strong></div><div className="flag-inspector-actions"><button type="button" className={cn(favoriteFlags.includes(inspectedFlag) && "active")} onClick={() => setFavoriteFlags((current) => current.includes(inspectedFlag) ? current.filter((name) => name !== inspectedFlag) : [inspectedFlag, ...current])} title="Favorite flag"><Star className="size-3.5" /></button><button type="button" onClick={() => setInspectedFlag(null)}><X className="size-3.5" /></button></div></div>
          <div className="flag-inspector-grid">
            <div><span>Value</span><strong>{parsed.ok && inspectedFlag in parsed.value ? String(parsed.value[inspectedFlag]) : "—"}</strong></div>
            <div><span>Type</span><strong>{inspectedEntry?.type ?? "Run Preflight"}</strong></div>
            <div><span>Support</span><strong className={cn(inspectedEntry?.supported ? "ok" : inspectedEntry ? "bad" : "")}>{inspectedEntry ? (inspectedEntry.supported ? "Supported" : "Unsupported") : "Unknown"}</strong></div>
            <div><span>Offset</span><strong>{inspectedEntry?.offset ?? "—"}</strong></div>
            <div><span>Offset source</span><strong title={status.offsetSource ?? undefined}>{status.offsetSourceHost ?? "—"}</strong></div>
            <div><span>Last apply</span><strong className={cn(inspectedLastResult?.ok ? "ok" : inspectedLastResult ? "bad" : "")}>{inspectedLastResult ? (inspectedLastResult.ok ? "Applied" : inspectedLastResult.message) : "No result"}</strong></div>
            <div className="wide"><span>Last check</span><strong>{inspectedEntry?.message ?? "Run Preflight to inspect this flag against the current offset table."}</strong></div>
          </div>
          <div className="flag-inspector-footer"><button type="button" onClick={() => void runPreflight()}><ScanSearch className="size-3.5" /> Refresh inspector</button><button type="button" onClick={() => void navigator.clipboard.writeText(inspectedFlag).then(() => showToast("Flag name copied", inspectedFlag, "success")).catch(() => showToast("Clipboard access blocked", undefined, "error"))}><Copy className="size-3.5" /> Copy name</button></div>
        </aside>}
        {bottomPanelOpen && <>
          {!bottomPanelMaximized && <div className="editor-panel-resizer" onPointerDown={startBottomPanelResize} title="Drag this divider up or down to resize the entire output panel"><span /></div>}
          <div className="editor-bottom-panel" style={bottomPanelMaximized ? undefined : { height: `${bottomPanelHeight}px` }}>
            <div className="editor-bottom-tabs">
              <div className="editor-bottom-tab-buttons">
                <button type="button" className={cn(editorBottomTab === "activity" && "active")} onClick={() => setEditorBottomTab("activity")}>Activity</button>
                <button type="button" className={cn(editorBottomTab === "failures" && "active")} onClick={() => setEditorBottomTab("failures")}>{lastApplied?.source === "native" ? "Failed writes" : "Skipped flags"} <span className="tab-count">{lastApplied?.errors ?? 0}</span></button>
                <button type="button" className={cn(editorBottomTab === "validation" && "active")} onClick={() => setEditorBottomTab("validation")}>Validation</button>
                <button type="button" className={cn(editorBottomTab === "diagnostics" && "active")} onClick={() => setEditorBottomTab("diagnostics")}>Diagnostics</button>
              </div>
              <div className="apply-stat-strip">
                <span className="stat-success"><b>{lastApplyStats.success}</b> success</span>
                <span className="stat-error"><b>{lastApplyStats.failed}</b> {lastApplied?.source === "native" ? "failed" : "skipped"}</span>
                <span><b>{lastApplyStats.total}</b> total</span>
                <span className="stat-rate"><b>{lastApplyStats.rate}%</b> rate</span>
                <button className="panel-max-button" type="button" onClick={() => setBottomPanelMaximized((value) => !value)} title={bottomPanelMaximized ? "Restore panel" : "Maximize panel"}>{bottomPanelMaximized ? <Minimize2 className="size-3.5" /> : <Maximize2 className="size-3.5" />}</button>
              </div>
            </div>
            <div className="editor-bottom-content smooth-scroll">
              {editorBottomTab === "activity" && <>
                <div className="activity-tools compact-tools">
                  <div className="activity-search"><Search className="size-3.5" /><input value={activitySearch} onChange={(event) => setActivitySearch(event.target.value)} placeholder="Search output…" /></div>
                  <div className="activity-filter-buttons">
                    {(["all", "success", "warning", "error"] as ActivityFilter[]).map((filter) => <button type="button" key={filter} className={cn(activityFilter === filter && "active", `filter-${filter}`)} onClick={() => setActivityFilter(filter)}>{filter === "all" ? "All" : filter === "success" ? "Success" : filter === "warning" ? "Warnings" : "Errors"}</button>)}
                  </div>
                  <span className="activity-result-count">{groupedActivity.length} groups</span>
                </div>
                <div className="grouped-log-list">{renderActivityGroups()}</div>
              </>}
              {editorBottomTab === "failures" && <div className="failed-flags-panel">
                <div className="failed-flags-toolbar">
                  <button className={cn(showUnsupportedOnly && "active")} type="button" onClick={() => setShowUnsupportedOnly((value) => !value)}><ListFilter className="size-3.5" /> Unsupported only</button>
                  <button type="button" onClick={() => void copyFailedFlags()}><Copy className="size-3.5" /> Copy names</button>
                  <button type="button" onClick={exportFailedFlags}><Download className="size-3.5" /> Export failed</button>
                  {lastApplied?.source !== "native" && <button type="button" disabled={preflightBusy || !parsed.ok} onClick={() => void exportCompleteSkippedReport()}><Download className="size-3.5" /> Full skip report</button>}
                  <button type="button" onClick={analyzeFailedFlagsWithAi}><Bot className="size-3.5" /> Analyze with AI</button>
                </div>
                {visibleFailedResults.length === 0 ? <div className="empty-center">No failed flags in the current filter.</div> : <div className="failed-flags-list">{visibleFailedResults.map((entry) => <button type="button" key={`${entry.name}-${entry.message}`} onClick={() => jumpToFlag(entry.name)}><span className="failure-name">{entry.name}</span><span className="failure-reason">{entry.message}</span><span className="failure-jump">Jump ↗</span></button>)}</div>}
              </div>}
              {editorBottomTab === "validation" && <div className="validation-panel validation-v14">
                {parsed.ok ? <><Check className="size-4" /><div className="validation-main"><strong>Valid JSON</strong><span>{Object.keys(parsed.value).length} FFlag entries in the editor.</span>{preflight?.ok && <div className="preflight-inline-stats"><b className="ok">{preflight.supported} supported</b><b className="warn">{preflight.unsupported} unsupported</b><b className="bad">{preflight.invalid} invalid</b></div>}<div className="validation-actions"><button type="button" onClick={() => void runPreflight()}><ScanSearch className="size-3.5" /> Run Preflight</button>{preflight?.ok && <><button type="button" onClick={() => void applySupportedFromPreflight()}><Play className="size-3.5" /> Apply supported only</button><button type="button" onClick={cleanUnsupportedIntoNewConfig}><Shield className="size-3.5" /> Create clean config</button><button type="button" onClick={() => setPreflightOpen(true)}>View details</button></>}</div></div></> : <><CircleAlert className="size-4" /><div><strong>JSON error</strong><span>{parsed.error}</span></div></>}
              </div>}
              {editorBottomTab === "diagnostics" && <div className="diagnostics-v14">
                <div className="diagnostic-grid">
                  <div><span>Backend</span><strong>{backendReachable ? `Online · PID ${status.backendPid ?? "?"}` : "Offline"}</strong></div>
                  <div><span>Backend uptime</span><strong>{Math.floor((status.backendUptimeSec ?? 0) / 60)}m {(status.backendUptimeSec ?? 0) % 60}s</strong></div>
                  <div><span>Backend version</span><strong>{status.backendVersion ?? "Unknown"}</strong></div>
                  <div><span>Browser UI</span><strong>{status.browserUiBundled === false ? "Missing" : status.browserUiBundled ? "Bundled" : "Unknown"}</strong></div>
                  <div><span>Roblox</span><strong>{status.connected ? `PID ${status.pid}` : "Offline"}</strong></div>
                  <div><span>Module base</span><strong>{status.base ?? "—"}</strong></div>
                  <div><span>Offsets</span><strong>{status.flagsLoaded.toLocaleString()} · {status.offsetValidation ?? (status.ready ? "ready" : "not ready")}</strong></div>
                  <div><span>Offset source</span><strong title={status.offsetSource ?? undefined}>{status.offsetSourceHost ?? "Unknown"}</strong></div>
                  <div><span>Offset fetched</span><strong>{status.offsetFetchedAt ? new Date(status.offsetFetchedAt * 1000).toLocaleTimeString() : "—"}</strong></div>
                  <div><span>Offset payload</span><strong>{status.offsetBytes ? `${(status.offsetBytes / 1024).toFixed(0)} KB` : "—"}</strong></div>
                  <div><span>Client</span><strong>{status.clientVersion ?? "Unknown"}</strong></div>
                  <div><span>Rollback snapshots</span><strong>{status.rollbackDepth ?? 0}</strong></div>
                  <div><span>Workspace storage</span><strong>{storageEstimate ? `${(storageEstimate.usage / 1048576).toFixed(1)} / ${(storageEstimate.quota / 1048576).toFixed(0)} MB` : "Unknown"}</strong></div>
                  <div><span>AI</span><strong>{agentHealth} · {agentSettings.model || "no model"}</strong></div>
                  <div><span>Last apply</span><strong>{lastApplyStats.success} / {lastApplyStats.total}</strong></div>
                  <div><span>Success rate</span><strong>{lastApplyStats.rate}%</strong></div>
                </div>
                <div className="diagnostic-actions"><button type="button" onClick={() => void refreshStatus(settings.apiUrl, false)}><RefreshCw className="size-3.5" /> Refresh</button>{isDesktop && <button type="button" onClick={() => void startOrRestartDesktopBackend("manual")}><RotateCcw className="size-3.5" /> Restart backend</button>}<button type="button" onClick={() => void exportDiagnosticReport()}><Download className="size-3.5" /> Export report</button></div>
              </div>}
            </div>
          </div>
        </>}
      </div>
    )
  }


  function renderPresets() {
    return (
      <div className="view-content">
        <div className="page-title-block"><h1>Presets & Generator</h1><p>Reusable profiles plus a guided FFlag builder.</p></div>
        <div className="fflag-generator-card"><div><strong>FFlag Generator</strong><p>Add a flag without hand-editing JSON.</p></div><div className="generator-grid"><input value={generatorName} onChange={(e) => setGeneratorName(e.target.value)} placeholder="FFlagName" /><select value={generatorType} onChange={(e) => setGeneratorType(e.target.value as "string" | "int" | "bool")}><option value="string">String</option><option value="int">Integer</option><option value="bool">Boolean</option></select><input value={generatorValue} onChange={(e) => setGeneratorValue(e.target.value)} placeholder={generatorType === "bool" ? "true / false" : "Value"} /><Button size="sm" onClick={addGeneratedFlag}>Add to editor</Button></div></div>
        <div className="section-label-row"><span>BUILT IN</span></div>
        <div className="preset-grid">
          {builtInPresets.map((preset) => (
            <button type="button" key={preset.id} className="preset-card" onClick={() => loadPreset(preset.value, preset.name)}>
              <div className="preset-icon"><Sparkles className="size-4" /></div><strong>{preset.name}</strong><p>{preset.description}</p><span>Load preset <ChevronLeft className="size-3 rotate-180" /></span>
            </button>
          ))}
        </div>
        <div className="section-label-row"><span>MY PRESETS</span><button type="button" onClick={() => { changeView("editor"); setSaveDialog({ mode: "preset", value: "My preset" }) }}>Create from editor</button></div>
        <div className="saved-preset-list">
          {customPresets.length === 0 && <div className="empty-card">No custom presets yet. Open a configuration in the editor and choose <b>Save as preset</b>.</div>}
          {customPresets.map((preset) => (
            <div key={preset.id} className="saved-preset-row"><div className="preset-icon small"><FileJson className="size-3.5" /></div><div className="min-w-0 flex-1"><strong>{preset.name}</strong><small>{Object.keys(safeParse<Record<string, unknown>>(preset.content, {})).length} entries</small></div><button type="button" onClick={() => loadPreset(preset.content, preset.name)}>Load</button><button className="icon-button" onClick={() => setCustomPresets((current) => current.filter((item) => item.id !== preset.id))}><Trash2 className="size-3.5" /></button></div>
          ))}
        </div>
      </div>
    )
  }

  function renderAgent() {
    const providerLabel = AGENT_PROVIDER_DEFAULTS[agentSettings.provider].label
    return (
      <div className="agent-layout">
        <div className="agent-header">
          <div>
            <div className="agent-title-row"><div className="agent-orb"><BrainCircuit className="size-4" /></div><div><h1>AI Agent</h1><p>Ask questions or tell it to work inside FFlag Studio.</p></div></div>
          </div>
          <div className="agent-header-actions">
            <span className={cn("agent-provider-pill", `health-${agentHealth}`)} title={agentHealthMessage}>
              <span className={cn("status-dot", agentHealth === "online" && "online", agentHealth === "checking" && "checking")} />
              {providerLabel} · {agentSettings.model || "model not set"}
            </span>
            <button className="agent-ghost-button" type="button" onClick={() => void testAgentConnection(false, false)}>{agentHealth === "checking" ? <LoaderCircle className="size-3.5 animate-spin" /> : <RefreshCw className="size-3.5" />} Test</button>
            <button className="agent-ghost-button" type="button" onClick={clearAgentChat}><Trash2 className="size-3.5" /> Clear</button>
          </div>
        </div>

        <div className="agent-body smooth-scroll">
          {agentMessages.length === 0 ? (
            <div className="agent-empty">
              <div className="agent-empty-icon"><Bot className="size-6" /></div>
              <h2>What do you want to do?</h2>
              <p>The agent can answer general questions through your configured model and can operate FFlag Studio features without needing you to hunt through menus.</p>
              <div className="agent-suggestions">
                {["Create a new config and set FIntDebugTextureManagerSkipMips to 8", "Open my presets", "Explain what the JSON in my editor contains", "Refresh Roblox status"].map((suggestion) => (
                  <button type="button" key={suggestion} onClick={() => void sendAgentMessage(suggestion)}>{suggestion}</button>
                ))}
              </div>
            </div>
          ) : (
            <div className="agent-messages">
              {agentMessages.map((message) => (
                <div key={message.id} className={cn("agent-message-row", message.role)}>
                  <div className="agent-avatar">{message.role === "assistant" ? <Sparkles className="size-3.5" /> : <User className="size-3.5" />}</div>
                  <div className="agent-message-card">
                    <div className="agent-message-meta">{message.role === "assistant" ? "FFlag Agent" : "You"}</div>
                    <div className="agent-message-text">{message.content}</div>
                    {!!message.actionSummary?.length && <div className="agent-action-summary">{message.actionSummary.map((summary) => <span key={summary}><Check className="size-3" />{summary}</span>)}</div>}
                  </div>
                </div>
              ))}
              {agentBusy && <div className="agent-message-row assistant"><div className="agent-avatar"><Sparkles className="size-3.5" /></div><div className="agent-message-card thinking"><LoaderCircle className="size-3.5 animate-spin" /> Thinking…</div></div>}
              <div ref={agentBottomRef} />
            </div>
          )}
        </div>

        {pendingAgentApply && (
          <div className="agent-confirm-bar">
            <ShieldCheck className="size-4" />
            <div><strong>Agent wants to apply the current configuration</strong><span>Review the editor first if you want. This action is waiting for your confirmation.</span></div>
            <button type="button" onClick={() => setPendingAgentApply(false)}>Cancel</button>
            <Button size="sm" onClick={async () => { setPendingAgentApply(false); await applyFlags("agent-confirmed") }}>Confirm apply</Button>
          </div>
        )}

        <div className="agent-composer-wrap">
          <div className="agent-composer">
            <textarea
              value={agentInput}
              onChange={(event) => setAgentInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault()
                  void sendAgentMessage()
                }
              }}
              placeholder="Ask anything, or tell the agent what to do in FFlag Studio…"
            />
            <div className="agent-composer-bottom">
              <div className="agent-capabilities"><span><MessageSquare className="size-3" /> General Q&A</span><span><WandSparkles className="size-3" /> App actions</span></div>
              <button className="agent-send" type="button" disabled={!agentInput.trim() || agentBusy} onClick={() => void sendAgentMessage()}>{agentBusy ? <LoaderCircle className="size-4 animate-spin" /> : <Send className="size-4" />}</button>
            </div>
          </div>
        </div>

        <div className="agent-settings-panel">
          <div className="agent-settings-heading"><div><strong>Agent connection</strong><span>Connect Ollama, OpenAI/Codex API, Claude, Gemini, OpenRouter, or a compatible endpoint.</span></div><KeyRound className="size-4" /></div>
          <div className="agent-settings-grid">
            <label><span>Provider</span><select value={draftAgentSettings.provider} onChange={(e) => changeAgentProvider(e.target.value as AgentProvider)}>{Object.entries(AGENT_PROVIDER_DEFAULTS).map(([id, meta]) => <option key={id} value={id}>{meta.label}</option>)}</select></label>
            <label><span>Model</span>{agentModels.length ? <select value={draftAgentSettings.model} onChange={(e) => setDraftAgentSettings((current) => ({ ...current, model: e.target.value }))}>{agentModels.map((model) => <option key={model} value={model}>{model}</option>)}</select> : <input value={draftAgentSettings.model} onChange={(e) => setDraftAgentSettings((current) => ({ ...current, model: e.target.value }))} placeholder="Model ID" />}</label>
            <label className="agent-url-field"><span>Base URL</span><input value={draftAgentSettings.baseUrl} onChange={(e) => setDraftAgentSettings((current) => ({ ...current, baseUrl: e.target.value }))} placeholder={AGENT_PROVIDER_DEFAULTS[draftAgentSettings.provider].baseUrl} /></label>
            {draftAgentSettings.provider !== "ollama" && <label className="agent-key-field"><span>API key (session only)</span><input type="password" value={agentApiKey} onChange={(e) => setAgentApiKey(e.target.value)} placeholder="Paste your provider API key" /></label>}
          </div>
          <div className={cn("agent-health-card", `health-${agentHealth}`)}>
            <span className={cn("status-dot", agentHealth === "online" && "online", agentHealth === "checking" && "checking")} />
            <div><strong>{agentHealth === "online" ? "AI connection ready" : agentHealth === "checking" ? "Checking AI connection…" : agentHealth === "offline" ? "AI connection needs attention" : "AI connection not tested"}</strong><span>{agentHealthMessage}</span></div>
            <Button variant="outline" size="sm" onClick={() => void testAgentConnection(true, false)}>Test</Button>
          </div>
          <div className="agent-setting-row"><div><strong>Confirm before Apply</strong><span>Recommended. The agent can prepare changes, but you approve before applying them.</span></div><Toggle checked={draftAgentSettings.confirmApply} onChange={(value) => setDraftAgentSettings((current) => ({ ...current, confirmApply: value }))} /></div>
          <div className="agent-settings-footer"><span>{draftAgentSettings.provider === "ollama" ? "Ollama stays local. Detect models if the selected model says Not found." : "API keys are kept in memory for this app session and sent only to the provider you selected."}</span><div className="flex gap-2"><Button variant="outline" size="sm" disabled={agentModelBusy} onClick={() => void refreshAgentModels(true)}>{agentModelBusy ? <LoaderCircle className="size-3.5 animate-spin" /> : <RefreshCw className="size-3.5" />} Detect</Button><Button size="sm" onClick={saveAgentSettings}>Save agent settings</Button></div></div>
        </div>
      </div>
    )
  }

  function renderActivity() {
    return (
      <div className="view-content">
        <div className="page-title-row"><div className="page-title-block"><h1>Activity</h1><p>Local backend events, grouped errors, apply history, and restore points.</p></div><div className="flex gap-2"><Button variant="outline" size="sm" onClick={copyLogs}><Clipboard className="size-3.5" /> Copy</Button><Button variant="outline" size="sm" onClick={() => void clearLogs()}><Trash2 className="size-3.5" /> Clear</Button></div></div>
        <div className="apply-overview-grid">
          <div><span>Success</span><strong className="success">{lastApplyStats.success}</strong><small>Last apply</small></div>
          <div><span>{lastApplied?.source === "native" ? "Failed writes" : "Skipped"}</span><strong className="error">{lastApplyStats.failed}</strong><small>{lastApplied?.source === "native" ? "Native results" : "Unsupported or invalid"}</small></div>
          <div><span>Success rate</span><strong>{lastApplyStats.rate}%</strong><small>{lastApplyStats.total} attempted</small></div>
          <div><span>Session change</span><strong>+{sessionComparison.newlySuccessful} / -{sessionComparison.newlyFailing}</strong><small>{sessionComparison.recovered} recovered</small></div>
        </div>
        <div className="section-label-row"><span>APPLY HISTORY</span><button type="button" onClick={() => { setApplyHistory([]); showToast("Apply history cleared", undefined, "info") }}>Clear history</button></div>
        <div className="apply-history-list">{applyHistory.length === 0 ? <div className="empty-card">No saved apply snapshots yet.</div> : applyHistory.slice(0, 12).map((item) => <div className="apply-history-row" key={item.id}><div><strong>{item.name}</strong><small>{new Date(item.appliedAt).toLocaleString()} · {item.applied} {item.source === "native" ? "reported written" : "saved"} · {item.errors} {item.source === "native" ? "failed" : "skipped"} · {item.source ?? "manual"}{item.rollbackId ? " · rollback captured" : ""}</small></div><div className="history-row-actions"><button type="button" onClick={() => restoreSnapshot(item)}>Restore JSON</button>{item === applyHistory[0] && item.rollbackId && <button onClick={() => void rollbackLastApply()}>Rollback local file</button>}{item.results?.some((entry) => !entry.ok) && <button onClick={() => { const source = safeParse<Record<string, unknown>>(item.content, {}); const failed = Object.fromEntries((item.results ?? []).filter((entry) => !entry.ok).map((entry) => [entry.name, source[entry.name] ?? entry.value ?? ""])); exportText(JSON.stringify(failed, null, 2), `${item.name.replace(/\.json$/i, "")}-failed.json`) }}>Export failed</button>}</div></div>)}</div>
        <div className="section-label-row"><span>BACKEND LOG</span></div>
        <div className="activity-tools">
          <div className="activity-search"><Search className="size-3.5" /><input value={activitySearch} onChange={(event) => setActivitySearch(event.target.value)} placeholder="Search activity…" /></div>
          <div className="activity-filter-buttons">{(["all", "success", "warning", "error"] as ActivityFilter[]).map((filter) => <button type="button" key={filter} className={cn(activityFilter === filter && "active", `filter-${filter}`)} onClick={() => setActivityFilter(filter)}>{filter === "all" ? "All" : filter === "success" ? "Success" : filter === "warning" ? "Warnings" : "Errors"}</button>)}</div>
        </div>
        <div className="terminal-panel grouped-terminal smooth-scroll">{renderActivityGroups()}</div>
      </div>
    )
  }


  function renderSettings() {
    const settingsMeta: Record<SettingsSection, { title: string; subtitle: string }> = {
      general: { title: "General", subtitle: "Runtime basics and desktop/browser mode." },
      appearance: { title: "Appearance", subtitle: "Theme, accent, glass, image, GIF, and video backgrounds." },
      editor: { title: "Editor", subtitle: "Editor font, word wrap, and utility panels." },
      behavior: { title: "Behavior", subtitle: "Automation and Auto Apply profiles." },
      notifications: { title: "Notifications", subtitle: "Toast position, duration, and size." },
      keybinds: { title: "Keybinds", subtitle: "Keyboard shortcuts available throughout ZFLAG." },
      connection: { title: "Connections", subtitle: "Local backend plus AI providers and API credentials." },
    }
    const settingsMetaItem = settingsMeta[settingsSection]

    return (
      <div className="view-content narrow settings-layout">
        <div className="page-title-block"><h1>{settingsMetaItem.title}</h1><p>{settingsMetaItem.subtitle}</p></div>
        <div key={settingsSection} className="settings-subpage">
          {settingsSection === "general" && (
            <>
              <div className="settings-section"><div className="settings-title">APPLICATION</div>
                <div className="setting-row"><div><strong>Interface animations</strong><p>Smooth hover states, page fades, menus, tabs, and toast motion.</p></div><Toggle checked={draftSettings.animations} onChange={(value) => setDraftSettings((current) => ({ ...current, animations: value }))} /></div>
                <div className="setting-row"><div><strong>Auto-refresh runtime</strong><p>Poll the local backend for Roblox and offset status.</p></div><Toggle checked={draftSettings.autoRefresh} onChange={(value) => setDraftSettings((current) => ({ ...current, autoRefresh: value }))} /></div>
              </div>
              <div className="settings-section"><div className="settings-title">RUN MODE</div>
                <div className="mode-choice-grid">
                  <button type="button" className={cn("mode-choice mode-choice-button", isDesktop && "selected")}><Monitor className="size-5" /><strong>Desktop app</strong><p>Tauri window with the bundled local backend.</p></button>
                  <button type="button" disabled={browserModeBusy} className={cn("mode-choice mode-choice-button", !isDesktop && "selected", browserModeBusy && "is-busy")} onClick={() => void openBrowserMode()}>{browserModeBusy ? <LoaderCircle className="size-5 animate-spin" /> : <Globe2 className="size-5" />}<strong>{browserModeBusy ? "Opening…" : "Browser"}</strong><p>Open the same FFlag Studio UI in your default browser.</p><span>{browserModeBusy ? "Starting local bridge…" : "Open browser →"}</span></button>
                </div>
              </div>
            </>
          )}

          {settingsSection === "appearance" && (
            <>
              <div className="settings-section"><div className="settings-title">THEME</div>
                <div className="appearance-segmented">
                  <button type="button" className={cn(draftSettings.themeMode === "dark" && "selected")} onClick={() => setDraftSettings((current) => ({ ...current, themeMode: "dark" }))}><span className="theme-thumb dark" /><div><strong>Dark</strong><small>Deep black surfaces</small></div></button>
                  <button type="button" className={cn(draftSettings.themeMode === "light" && "selected")} onClick={() => setDraftSettings((current) => ({ ...current, themeMode: "light" }))}><span className="theme-thumb light" /><div><strong>Light</strong><small>Clean bright surfaces</small></div></button>
                </div>
                <div className="appearance-label">ACCENT COLOR</div>
                <div className="accent-swatch-grid">
                  {accentOptions.map((option) => <button key={option.id} type="button" className={cn("accent-swatch", draftSettings.accentPreset === option.id && "selected")} onClick={() => setDraftSettings((current) => ({ ...current, accentPreset: option.id }))}><span style={{ background: option.color }} /><small>{option.label}</small><Check className="size-3" /></button>)}
                </div>
              </div>
              <div className="settings-section"><div className="settings-title">BACKGROUND</div>
                <div className="background-mode-grid">
                  {backgroundOptions.map((option) => <button key={option.id} type="button" className={cn("background-mode-card", draftSettings.backgroundMode === option.id && "selected")} onClick={() => setDraftSettings((current) => ({ ...current, backgroundMode: option.id }))}><span className={cn("background-mode-preview", `preview-${option.id}`)} /><strong>{option.label}</strong><small>{option.detail}</small></button>)}
                </div>
                <div className="setting-field range-field"><label>Background intensity</label><input type="range" min="0.08" max="0.9" step="0.02" value={draftSettings.backgroundOpacity} onChange={(e) => setDraftSettings((current) => ({ ...current, backgroundOpacity: Number(e.target.value) }))} /></div>
                <div className="setting-row"><div><strong>Custom media</strong><p>Choose an image, GIF, MP4, or WebM. It stays behind the translucent app surfaces.</p></div><div className="settings-inline-actions"><Button variant="outline" size="sm" onClick={() => mediaInput.current?.click()}>Choose file</Button><Button variant="outline" size="sm" onClick={clearBackgroundMedia}>Clear</Button></div></div>
                {draftSettings.backgroundData && <div className="background-preview-note">Custom media is ready. Save settings to apply the preview everywhere.</div>}
              </div>
            </>
          )}

          {settingsSection === "editor" && (
          <><div className="settings-section"><div className="settings-title">EDITOR</div>
            <div className="setting-field"><label>Font size</label><input type="range" min="10" max="18" step="0.5" value={draftSettings.editorFontSize} onChange={(e) => setDraftSettings((current) => ({ ...current, editorFontSize: Number(e.target.value) }))} /></div>
            <div className="setting-row"><div><strong>Word wrap</strong><p>Wrap long JSON lines inside the editor.</p></div><Toggle checked={draftSettings.editorWordWrap} onChange={(value) => setDraftSettings((current) => ({ ...current, editorWordWrap: value }))} /></div>
            <div className="setting-row"><div><strong>Bottom diagnostics panel</strong><p>Activity, validation, and runtime details are available below the editor.</p></div><Toggle checked={bottomPanelOpen} onChange={setBottomPanelOpen} /></div>
            <div className="setting-row"><div><strong>Explorer width</strong><p>Drag the Explorer divider in the editor. Current width: {Math.round(sidebarWidth)}px.</p></div><Button variant="outline" size="sm" onClick={() => setSidebarWidth(246)}>Reset width</Button></div>
          </div></>
        )}

        {settingsSection === "behavior" && (
          <><div className="settings-section"><div className="settings-title">AUTO APPLY</div>
            <div className="setting-row"><div><strong>Apply profile when Roblox connects</strong><p>Runs only after you explicitly enable it and choose a saved profile.</p></div><Toggle checked={draftSettings.autoApplyEnabled} onChange={(value) => setDraftSettings((current) => ({ ...current, autoApplyEnabled: value }))} /></div>
            <div className="setting-field"><label>Auto Apply profile</label><select value={draftSettings.autoApplyConfigId} onChange={(e) => setDraftSettings((current) => ({ ...current, autoApplyConfigId: e.target.value }))}><option value="">None</option>{savedConfigs.map((config) => <option key={config.id} value={config.id}>{config.name}</option>)}</select></div>
          </div></>
        )}

        {settingsSection === "notifications" && (
          <><div className="settings-section"><div className="settings-title">NOTIFICATIONS</div>
            <div className="setting-field"><label>Position</label><select value={draftSettings.notificationPosition} onChange={(e) => setDraftSettings((current) => ({ ...current, notificationPosition: e.target.value as SettingsState["notificationPosition"] }))}><option value="bottom-right">Bottom right</option><option value="bottom-left">Bottom left</option><option value="top-right">Top right</option></select></div>
            <div className="setting-field"><label>Duration</label><select value={draftSettings.notificationDuration} onChange={(e) => setDraftSettings((current) => ({ ...current, notificationDuration: Number(e.target.value) }))}><option value={1600}>1.6 seconds</option><option value={2600}>2.6 seconds</option><option value={4000}>4 seconds</option><option value={6000}>6 seconds</option></select></div>
            <div className="setting-row"><div><strong>Compact notifications</strong><p>Use smaller desktop-style toasts.</p></div><Toggle checked={draftSettings.compactNotifications} onChange={(value) => setDraftSettings((current) => ({ ...current, compactNotifications: value }))} /></div>
            <Button variant="outline" size="sm" onClick={() => showToast("Notification preview", "This is how alerts will look.")}>Preview notification</Button>
          </div></>
        )}

        {settingsSection === "keybinds" && (
          <><div className="settings-section"><div className="settings-title">KEYBINDS</div><div className="keybind-list">
            {[ ["Command palette","Ctrl + K"], ["Save configuration","Ctrl + S"], ["Save allowed flags from current profile","Ctrl + Enter"], ["New configuration","Ctrl + N"], ["Format JSON","Ctrl + Shift + F"], ["Open AI Agent","Ctrl + L"] ].map(([label, shortcut]) => <div className="keybind-row" key={label}><span>{label}</span><kbd>{shortcut}</kbd></div>)}
          </div></div></>
        )}

        {settingsSection === "connection" && (
            <>
              <div className="settings-section"><div className="settings-title">LOCAL BACKEND</div>
                <div className="setting-field"><label>Local backend URL</label><input value={draftSettings.apiUrl} onChange={(e) => setDraftSettings((current) => ({ ...current, apiUrl: e.target.value }))} /></div>
                <div className="setting-field"><label>Refresh interval</label><select value={draftSettings.pollMs} onChange={(e) => setDraftSettings((current) => ({ ...current, pollMs: Number(e.target.value) }))}><option value={3000}>3 seconds</option><option value={5000}>5 seconds</option><option value={8000}>8 seconds</option></select></div>
                <div className="connection-card"><span className={cn("status-dot", backendReachable && "online")} /><div><strong>{backendReachable ? "Local bridge connected" : "Local bridge offline"}</strong><p>{isDesktop ? "Desktop mode watches the bundled backend and attempts recovery after repeated failures." : "Browser mode uses the same localhost bridge."}</p></div><Button variant="outline" size="sm" onClick={() => void refreshStatus(draftSettings.apiUrl, false)}>Test</Button></div>
                <div className="settings-inline-actions">{isDesktop && <Button variant="outline" size="sm" onClick={() => void startOrRestartDesktopBackend("manual")}><RotateCcw className="size-3.5" /> Restart backend</Button>}<Button variant="outline" size="sm" onClick={() => void exportDiagnosticReport()}><Download className="size-3.5" /> Export diagnostics</Button></div>
              </div>
              <div className="settings-section"><div className="settings-title">AI PROVIDER</div>
                <div className="setting-field"><label>Provider</label><select value={draftAgentSettings.provider} onChange={(e) => changeAgentProvider(e.target.value as AgentProvider)}>{Object.entries(AGENT_PROVIDER_DEFAULTS).map(([id, meta]) => <option key={id} value={id}>{meta.label}</option>)}</select></div>
                <div className="setting-field"><label>Base URL</label><input value={draftAgentSettings.baseUrl} onChange={(e) => setDraftAgentSettings((current) => ({ ...current, baseUrl: e.target.value }))} /></div>
                <div className="setting-field"><label>Model</label>{agentModels.length ? <select value={draftAgentSettings.model} onChange={(e) => setDraftAgentSettings((current) => ({ ...current, model: e.target.value }))}>{agentModels.map((model) => <option key={model} value={model}>{model}</option>)}</select> : <input value={draftAgentSettings.model} onChange={(e) => setDraftAgentSettings((current) => ({ ...current, model: e.target.value }))} placeholder="Model ID" />}</div>
                {draftAgentSettings.provider !== "ollama" && <div className="setting-field"><label>API key</label><input type="password" value={agentApiKey} onChange={(e) => setAgentApiKey(e.target.value)} placeholder="Stored for this app session only" /></div>}
                <div className="setting-row"><div><strong>Detect available models</strong><p>Checks the selected provider. For Ollama, this also fixes a missing model by selecting one you actually have installed.</p></div><Button variant="outline" size="sm" disabled={agentModelBusy} onClick={() => void refreshAgentModels(true)}>{agentModelBusy ? <LoaderCircle className="size-3.5 animate-spin" /> : <RefreshCw className="size-3.5" />} Detect</Button></div>
                <div className={cn("agent-health-card", `health-${agentHealth}`)}><span className={cn("status-dot", agentHealth === "online" && "online", agentHealth === "checking" && "checking")} /><div><strong>{agentHealth === "online" ? "AI provider connected" : agentHealth === "checking" ? "Testing AI provider…" : agentHealth === "offline" ? "AI provider unavailable" : "AI provider not tested"}</strong><span>{agentHealthMessage}</span></div><Button variant="outline" size="sm" onClick={() => void testAgentConnection(true, false)}>Test connection</Button></div>
                <div className="setting-row"><div><strong>Confirm before Apply</strong><p>The AI can prepare edits, but you approve before applying them.</p></div><Toggle checked={draftAgentSettings.confirmApply} onChange={(value) => setDraftAgentSettings((current) => ({ ...current, confirmApply: value }))} /></div>
                {draftAgentSettings.provider === "ollama" && <div className="provider-tip"><strong>Ollama tip</strong><span>If no models are detected, install one first, for example: <code>ollama pull llama3.2:3b</code>.</span></div>}
                <div className="flex justify-end"><Button size="sm" onClick={saveAgentSettings}>Save AI connection</Button></div>
              </div>
            </>
          )}
        </div>

        <div className="settings-footer-actions"><Button variant="outline" onClick={() => { setDraftSettings(loadSettings()); setDraftAgentSettings(loadAgentSettings()); setAgentModels([]) }}>Reset unsaved</Button><Button onClick={() => void saveSettings()}>Save settings</Button></div>
      </div>
    )
  }


  return (
    <div className={cn("app-shell", `theme-${visualSettings.themeMode}`, `accent-${visualSettings.accentPreset}`, `bg-${visualSettings.backgroundMode}`, !settings.animations && "reduce-motion") } style={{ ['--sidebar-width' as string]: `${sidebarWidth}px` }}>
      {renderBackgroundLayer()}
      <input ref={fileInput} className="hidden" type="file" accept=".json,application/json" onChange={(e) => { importFile(e.target.files?.[0]); e.currentTarget.value = "" }} />
      <input ref={mediaInput} className="hidden" type="file" accept="image/*,image/gif,video/mp4,video/webm" onChange={(e) => { importBackgroundFile(e.target.files?.[0]); e.currentTarget.value = "" }} />
      {renderSidebar()}
      {!sidebarCollapsed && <div className="sidebar-resizer" onPointerDown={startSidebarResize} title="Drag to resize Explorer"><span /></div>}
      <div className="app-main">
        {renderTopbar()}
        {renderTabs()}
        <main ref={mainScrollRef} className="main-scroll smooth-scroll">
          <div key={`${view}-${pageKey}`} className="page-transition">
            {view === "home" && renderHome()}
            {view === "editor" && renderEditor()}
            {view === "presets" && renderPresets()}
            {view === "agent" && renderAgent()}
            {view === "activity" && renderActivity()}
            {view === "settings" && renderSettings()}
          </div>
        </main>
      </div>

      {toast && createPortal(
        <div key={toast.id} className={cn("toast", `tone-${toast.tone}`, `position-${settings.notificationPosition}`, settings.compactNotifications && "compact")}>
          <div className="toast-icon">{toast.tone === "error" ? <CircleAlert className="size-4" /> : toast.tone === "warning" ? <CircleAlert className="size-4" /> : <Check className="size-4" />}</div>
          <div><strong>{toast.title}</strong>{toast.detail && <span>{toast.detail}</span>}</div>
        </div>,
        document.body,
      )}

      {preflightOpen && preflight && createPortal(
        <div className="modal-backdrop" onMouseDown={() => setPreflightOpen(false)}>
          <div className="modal-card v14-preflight-modal" onMouseDown={(event) => event.stopPropagation()}>
            <div className="v14-modal-head"><div><span>DRY RUN</span><h2>Preflight results</h2><p>{preflight.total} entries checked against {preflight.clientVersion ?? "the current offset table"}.</p></div><button type="button" onClick={() => setPreflightOpen(false)}><X className="size-4" /></button></div>
            <div className="preflight-stat-grid"><div className="ok"><strong>{preflight.supported}</strong><span>Supported</span></div><div className="warn"><strong>{preflight.unsupported}</strong><span>Unsupported</span></div><div className="bad"><strong>{preflight.invalid}</strong><span>Invalid</span></div><div><strong>{preflight.total}</strong><span>Total</span></div></div>
            <div className="preflight-filterbar"><span>Filter flags</span><select value={preflightPrefix} onChange={(e) => setPreflightPrefix(e.target.value)}><option value="all">All prefixes</option><option value="favorites">★ Favorites</option><option value="FFlag">FFlag</option><option value="DFFlag">DFFlag</option><option value="FInt">FInt</option><option value="DFInt">DFInt</option><option value="FString">FString</option><option value="DFString">DFString</option></select><small>{filteredPreflightEntries.length} shown</small></div>
            <div className="preflight-list smooth-scroll">{filteredPreflightEntries.slice(0, 350).map((entry) => <button type="button" key={entry.name} className={cn("preflight-row", `status-${entry.status}`)} onClick={() => { setPreflightOpen(false); jumpToFlag(entry.name) }}><span className="preflight-dot" /><strong>{favoriteFlags.includes(entry.name) ? `★ ${entry.name}` : entry.name}</strong><span>{entry.type}</span><span>{entry.offset ?? "—"}</span><small>{entry.message}</small></button>)}</div>
            <div className="modal-actions v14-modal-actions"><Button variant="outline" onClick={() => setPreflightOpen(false)}>Close</Button><Button variant="outline" onClick={cleanUnsupportedIntoNewConfig}><Shield className="size-3.5" /> Create clean config</Button><Button onClick={() => void applySupportedFromPreflight()}><Play className="size-3.5" /> Apply supported only</Button></div>
          </div>
        </div>,
        document.body,
      )}

      {compareOpen && createPortal(
        <div className="modal-backdrop" onMouseDown={() => setCompareOpen(false)}>
          <div className="modal-card v14-compare-modal" onMouseDown={(event) => event.stopPropagation()}>
            <div className="v14-modal-head"><div><span>CONFIG DIFF</span><h2>Compare configurations</h2><p>See added, removed, and changed flags before you merge or export.</p></div><button type="button" onClick={() => setCompareOpen(false)}><X className="size-4" /></button></div>
            <div className="compare-selectors"><label>Left<select value={compareLeftId} onChange={(e) => setCompareLeftId(e.target.value)}><option value="current">Current editor</option>{savedConfigs.map((config) => <option key={config.id} value={config.id}>{config.name}</option>)}</select></label><span>↔</span><label>Right<select value={compareRightId} onChange={(e) => setCompareRightId(e.target.value)}><option value="current">Current editor</option>{savedConfigs.map((config) => <option key={config.id} value={config.id}>{config.name}</option>)}</select></label></div>
            {compareResult ? <><div className="preflight-stat-grid compare-stats"><div className="ok"><strong>{compareResult.added.length}</strong><span>Added</span></div><div className="warn"><strong>{compareResult.changed.length}</strong><span>Changed</span></div><div className="bad"><strong>{compareResult.removed.length}</strong><span>Removed</span></div><div><strong>{compareResult.added.length + compareResult.changed.length + compareResult.removed.length}</strong><span>Total diff</span></div></div><div className="compare-lists smooth-scroll">{compareResult.added.map((name) => <button type="button" key={`a-${name}`} onClick={() => jumpToFlag(name)}><b className="diff-add">+</b><strong>{name}</strong><small>Added on right</small></button>)}{compareResult.changed.map((name) => <button type="button" key={`c-${name}`} onClick={() => jumpToFlag(name)}><b className="diff-change">~</b><strong>{name}</strong><small>{String(compareResult.left[name])} → {String(compareResult.right[name])}</small></button>)}{compareResult.removed.map((name) => <button type="button" key={`r-${name}`} onClick={() => jumpToFlag(name)}><b className="diff-remove">−</b><strong>{name}</strong><small>Removed on right</small></button>)}</div><div className="modal-actions v14-modal-actions"><Button variant="outline" onClick={() => navigator.clipboard.writeText(JSON.stringify({ added: compareResult.added, changed: compareResult.changed, removed: compareResult.removed }, null, 2))}><Copy className="size-3.5" /> Copy diff</Button><Button variant="outline" onClick={() => { newTab(JSON.stringify(compareResult.right, null, 2), "Merged comparison.json"); setCompareOpen(false) }}>Create config from right</Button><Button onClick={() => setCompareOpen(false)}>Done</Button></div></> : <div className="empty-center">Choose two configurations to compare.</div>}
          </div>
        </div>,
        document.body,
      )}

      {clearMenuOpen && createPortal(
        <div
          className="clear-options-popover"
          style={{ top: clearMenuPosition.top, left: clearMenuPosition.left }}
          onClick={(event) => event.stopPropagation()}
          onMouseDown={(event) => event.stopPropagation()}
        >
          <button type="button" onClick={() => requestClearEditor("object")}>
            <Braces className="size-3.5" />
            <span><b>Clear to {"{}"}</b><small>Replace everything with an empty JSON object</small></span>
          </button>
          <button type="button" className="danger" onClick={() => requestClearEditor("blank")}>
            <Trash2 className="size-3.5" />
            <span><b>Clear completely</b><small>Remove all text from this tab</small></span>
          </button>
          <div className="menu-separator" />
          <button type="button" disabled={!activeSavedConfig} onClick={() => requestClearEditor("saved")}>
            <RefreshCw className="size-3.5" />
            <span><b>Reset to last saved</b><small>{activeSavedConfig ? activeSavedConfig.name : "Save this tab first"}</small></span>
          </button>
        </div>,
        document.body,
      )}

      {commandOpen && createPortal(
        <div className="command-backdrop" onMouseDown={() => setCommandOpen(false)}>
          <div className="command-palette" onMouseDown={(event) => event.stopPropagation()}>
            <div className="command-search"><Search className="size-4" /><input autoFocus value={commandQuery} onChange={(event) => setCommandQuery(event.target.value)} placeholder="Search pages, actions, and saved configurations…" /><kbd>ESC</kbd></div>
            <div className="command-results smooth-scroll">
              {commandItems.length === 0 ? <div className="command-empty">No matching actions.</div> : commandItems.map((item) => <button key={item.id} type="button" onClick={() => { item.run(); setCommandOpen(false); setCommandQuery("") }}><span className="command-dot" /><div><strong>{item.label}</strong><small>{item.hint}</small></div><span className="command-arrow">↵</span></button>)}
            </div>
            <div className="command-footer"><span>Quick command</span><kbd>Ctrl K</kbd></div>
          </div>
        </div>,
        document.body,
      )}

      {clearDialog && createPortal(
        <div className="modal-backdrop" onMouseDown={() => setClearDialog(null)}>
          <div className="modal-card clear-json-modal" onMouseDown={(event) => event.stopPropagation()}>
            <div className="clear-json-icon"><Trash2 className="size-4" /></div>
            <div className="modal-title">
              {clearDialog === "object" ? "Clear JSON to {}?" : clearDialog === "blank" ? "Clear all JSON text?" : "Reset to last saved?"}
            </div>
            <div className="modal-sub">
              {clearDialog === "object"
                ? "This replaces the current editor contents with an empty JSON object."
                : clearDialog === "blank"
                  ? "This removes every character from the current editor tab."
                  : `This replaces the current editor contents with ${activeSavedConfig?.name ?? "the last saved version"}.`}
              <br />You can press <b>Ctrl+Z</b> immediately afterward to restore what was here.
            </div>
            <div className="modal-actions">
              <Button variant="outline" onClick={() => setClearDialog(null)}>Cancel</Button>
              <Button className={cn(clearDialog === "blank" && "clear-danger-button")} onClick={confirmClearEditor}>
                {clearDialog === "saved" ? "Reset" : "Clear"}
              </Button>
            </div>
          </div>
        </div>,
        document.body,
      )}

      {saveDialog && createPortal(
        <div className="modal-backdrop" onMouseDown={() => setSaveDialog(null)}>
          <div className="modal-card save-dialog-card" role="dialog" aria-modal="true" aria-label={saveDialog.mode === "preset" ? "Save as preset" : saveDialog.mode === "rename" ? "Rename configuration" : "Save configuration"} onMouseDown={(event) => event.stopPropagation()}>
            <div className="modal-title">{saveDialog.mode === "preset" ? "Save as preset" : saveDialog.mode === "rename" ? "Rename configuration" : "Save configuration"}</div>
            <div className="modal-sub">{saveDialog.mode === "preset" ? "This preset stays inside FFlag Studio on this device." : "Saved configurations appear in the Explorer sidebar."}</div>
            <input
              autoFocus
              value={saveDialog.value}
              onFocus={(event) => event.currentTarget.select()}
              onChange={(e) => setSaveDialog((current) => current ? { ...current, value: e.target.value } : current)}
              onKeyDown={(e) => {
                if (e.key === "Enter") finishDialog()
                if (e.key === "Escape") setSaveDialog(null)
              }}
            />
            <div className="modal-actions"><Button variant="outline" onClick={() => setSaveDialog(null)}>Cancel</Button><Button disabled={!saveDialog.value.trim()} onClick={finishDialog}>{saveDialog.mode === "rename" ? "Rename" : "Save"}</Button></div>
          </div>
        </div>,
        document.body,
      )}
    </div>
  )
}
