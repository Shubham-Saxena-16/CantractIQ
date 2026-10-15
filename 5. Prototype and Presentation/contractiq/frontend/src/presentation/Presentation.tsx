import { useCallback, useEffect, useRef, useState } from 'react'
import { SLIDES } from './slides'
import './presentation.css'

/** Interactive slide deck at #/presentation[/n]. Text-only design: no images, illustrations or diagrams. */
export default function Presentation({ initial }: { initial?: string }) {
  const clamp = (n: number) => Math.max(0, Math.min(SLIDES.length - 1, n))
  const [idx, setIdx] = useState(() => clamp((parseInt(initial || '1', 10) || 1) - 1))
  const [dir, setDir] = useState<'next' | 'prev'>('next')
  const [notes, setNotes] = useState(false)
  const [overview, setOverview] = useState(false)
  const [full, setFull] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const touch = useRef<{ x: number; y: number } | null>(null)

  const idxRef = useRef(idx)
  idxRef.current = idx
  const go = useCallback((n: number) => {
    const cur = idxRef.current, t = clamp(n)
    setOverview(false)
    if (t === cur) return
    setDir(t > cur ? 'next' : 'prev')
    setIdx(t)
  }, [])
  const next = useCallback(() => go(idxRef.current + 1), [go])
  const prev = useCallback(() => go(idxRef.current - 1), [go])

  // Keep the slide number in the URL (without triggering the app router) so a refresh stays on the same slide.
  useEffect(() => {
    history.replaceState(null, '', `#/presentation/${idx + 1}`)
    scrollRef.current?.scrollTo({ top: 0 })
    document.title = `${SLIDES[idx].title} · ContractIQ presentation`
  }, [idx])
  useEffect(() => () => { document.title = 'AtliQ ContractIQ' }, [])

  const toggleFull = useCallback(async () => {
    try {
      if (!document.fullscreenElement) await rootRef.current?.requestFullscreen()
      else await document.exitFullscreen()
    } catch { /* fullscreen not allowed (e.g. embedded preview): ignore */ }
  }, [])
  useEffect(() => {
    const on = () => setFull(!!document.fullscreenElement)
    document.addEventListener('fullscreenchange', on)
    return () => document.removeEventListener('fullscreenchange', on)
  }, [])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.altKey || e.ctrlKey || e.metaKey) return
      const t = e.target as HTMLElement
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT' || t.isContentEditable)) return
      const onButton = t && (t.tagName === 'BUTTON' || t.tagName === 'A')
      switch (e.key) {
        case 'ArrowRight': case 'PageDown': e.preventDefault(); next(); break
        case 'ArrowLeft': case 'PageUp': e.preventDefault(); prev(); break
        case ' ': if (!onButton) { e.preventDefault(); e.shiftKey ? prev() : next() } break
        case 'Home': e.preventDefault(); go(0); break
        case 'End': e.preventDefault(); go(SLIDES.length - 1); break
        case 'f': case 'F': toggleFull(); break
        case 'n': case 'N': setNotes(v => !v); break
        case 'o': case 'O': setOverview(v => !v); break
        case 'Escape': setOverview(false); setNotes(false); break
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [next, prev, go, toggleFull])

  const s = SLIDES[idx]
  const pct = ((idx + 1) / SLIDES.length) * 100
  return (
    <div className="deck" ref={rootRef}
      onTouchStart={e => { touch.current = { x: e.touches[0].clientX, y: e.touches[0].clientY } }}
      onTouchEnd={e => {
        const st = touch.current; touch.current = null
        if (!st) return
        const dx = e.changedTouches[0].clientX - st.x, dy = e.changedTouches[0].clientY - st.y
        if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy) * 1.5) { if (dx < 0) next(); else prev() }
      }}>
      <div className="deck-progress" role="progressbar" aria-label="Presentation progress" aria-valuemin={1} aria-valuemax={SLIDES.length} aria-valuenow={idx + 1}>
        <div style={{ width: `${pct}%` }} />
      </div>
      <header className="deck-top">
        <div className="deck-brand">AtliQ ContractIQ<span>Project presentation</span></div>
        <div className="spacer" />
        <button className="deck-tbtn" aria-pressed={overview} onClick={() => setOverview(v => !v)}>All slides<kbd>O</kbd></button>
        <button className="deck-tbtn" aria-pressed={notes} onClick={() => setNotes(v => !v)}>Speaker notes<kbd>N</kbd></button>
        <button className="deck-tbtn" aria-pressed={full} onClick={toggleFull}>{full ? 'Exit full screen' : 'Full screen'}<kbd>F</kbd></button>
        <a className="deck-tbtn" href="#/">Back to app</a>
      </header>

      <main className="deck-stage" aria-roledescription="slide deck">
        <div className="deck-scroll" ref={scrollRef}>
          <section key={s.id} className={`slide enter-${dir}`} aria-roledescription="slide" aria-label={`Slide ${idx + 1} of ${SLIDES.length}: ${s.title}`}>
            {s.render()}
          </section>
        </div>
        {notes && (
          <aside className="notes" aria-label="Speaker notes">
            <h4>Speaker notes · slide {idx + 1}</h4>
            <ul>{s.notes.map(n => <li key={n}>{n}</li>)}</ul>
          </aside>)}
        {overview && (
          <nav className="overview" aria-label="All slides">
            <ol>{SLIDES.map((x, i) => (
              <li key={x.id}><button aria-current={i === idx} onClick={() => go(i)}>
                <span className="on">{String(i + 1).padStart(2, '0')}</span><span className="ot">{x.title}</span></button></li>))}</ol>
          </nav>)}
      </main>

      <footer className="deck-bottom">
        <button className="deck-nav" onClick={prev} disabled={idx === 0} aria-label="Previous slide">← Previous</button>
        <span className="deck-count" aria-live="polite">{idx + 1} / {SLIDES.length}</span>
        <div className="dots" role="group" aria-label="Go to slide">
          {SLIDES.map((x, i) => <button key={x.id} aria-label={`Slide ${i + 1}: ${x.title}`} aria-current={i === idx ? 'step' : undefined} onClick={() => go(i)} />)}
        </div>
        <span className="deck-title-mini">{s.title}</span>
        <button className="deck-nav primary" onClick={next} disabled={idx === SLIDES.length - 1} aria-label="Next slide">Next →</button>
      </footer>
    </div>
  )
}
