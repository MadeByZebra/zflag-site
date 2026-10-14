import { useEffect, useRef } from "react"
import type { MutableRefObject } from "react"
import { basicSetup, EditorView } from "codemirror"
import { json } from "@codemirror/lang-json"

type Props = {
  value: string
  onChange: (value: string) => void
  onFlagFocus?: (flagName: string | null) => void
  fontSize: number
  wordWrap: boolean
  themeMode: "dark" | "light"
  viewRef: MutableRefObject<EditorView | null>
}

export function CodeMirrorJsonEditor({ value, onChange, onFlagFocus, fontSize, wordWrap, themeMode, viewRef }: Props) {
  const hostRef = useRef<HTMLDivElement>(null)
  const onChangeRef = useRef(onChange)
  const onFlagFocusRef = useRef(onFlagFocus)

  onChangeRef.current = onChange
  onFlagFocusRef.current = onFlagFocus

  useEffect(() => {
    if (!hostRef.current) return

    const dark = themeMode === "dark"
    const editorTheme = EditorView.theme({
      "&": {
        height: "100%",
        backgroundColor: dark ? "#080808" : "#ffffff",
        color: dark ? "#e7e7e7" : "#202124",
        fontSize: `${fontSize}px`,
      },
      ".cm-scroller": {
        overflow: "auto",
        fontFamily: '"Cascadia Code", "SFMono-Regular", Consolas, monospace',
        lineHeight: "1.65",
      },
      ".cm-content": { padding: "10px 14px 40px" },
      ".cm-gutters": {
        backgroundColor: dark ? "#090909" : "#fafafa",
        color: dark ? "#555" : "#9aa0a6",
        borderRight: dark ? "1px solid rgba(255,255,255,.045)" : "1px solid rgba(0,0,0,.07)",
      },
      ".cm-activeLine": { backgroundColor: dark ? "rgba(255,255,255,.022)" : "rgba(0,0,0,.025)" },
      ".cm-activeLineGutter": { backgroundColor: dark ? "rgba(255,255,255,.028)" : "rgba(0,0,0,.03)" },
      ".cm-selectionBackground, ::selection": {
        backgroundColor: dark ? "rgba(110,150,210,.28) !important" : "rgba(75,120,200,.20) !important",
      },
      ".cm-cursor": { borderLeftColor: dark ? "#fff" : "#111" },
      ".cm-foldPlaceholder": {
        backgroundColor: dark ? "#151515" : "#f3f4f6",
        border: "0",
        color: dark ? "#888" : "#666",
      },
      ".cm-tooltip": {
        backgroundColor: dark ? "#151515" : "#fff",
        color: dark ? "#ddd" : "#222",
        border: dark ? "1px solid #2c2c2c" : "1px solid #ddd",
      },
    }, { dark })

    const view = new EditorView({
      doc: value,
      parent: hostRef.current,
      extensions: [
        basicSetup,
        json(),
        editorTheme,
        wordWrap ? EditorView.lineWrapping : [],
        EditorView.updateListener.of((update) => {
          if (update.docChanged) onChangeRef.current(update.state.doc.toString())
          if (update.selectionSet || update.docChanged) {
            const pos = update.state.selection.main.head
            const line = update.state.doc.lineAt(Math.min(pos, update.state.doc.length)).text
            const match = line.match(/^\s*"([^"]+)"\s*:/)
            onFlagFocusRef.current?.(match?.[1] ?? null)
          }
        }),
      ],
    })

    viewRef.current = view
    return () => {
      if (viewRef.current === view) viewRef.current = null
      view.destroy()
    }
  }, [fontSize, wordWrap, themeMode, viewRef])

  useEffect(() => {
    const view = viewRef.current
    if (!view) return
    const current = view.state.doc.toString()
    if (current === value) return
    const selection = view.state.selection.main
    view.dispatch({
      changes: { from: 0, to: current.length, insert: value },
      selection: { anchor: Math.min(selection.anchor, value.length), head: Math.min(selection.head, value.length) },
    })
  }, [value, viewRef])

  return <div ref={hostRef} className="codemirror-json-editor" />
}
