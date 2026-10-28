/**
 * ZFLAG Smooth Scroll v2 — desktop wheel and precision trackpad easing.
 * All vertical wheel deltas animate, including small trackpad deltas.
 * Mouse-wheel scrolling must NOT depend on pointer/hover device detection.
 * Touch, keyboard, nested scroll panes, reduced motion, and zoom stay native.
 */
(() => {
  "use strict";

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const root = document.scrollingElement || document.documentElement;
  if (typeof window.requestAnimationFrame !== "function") return;

  let goal = window.scrollY;
  let frame = null;
  let lastTime = 0;
  let easingMs = 115;

  const scrollLimit = () => Math.max(0, root.scrollHeight - window.innerHeight);
  const limitToPage = y => Math.max(0, Math.min(scrollLimit(), y));

  function cancel() {
    if (frame !== null) cancelAnimationFrame(frame);
    frame = null;
    lastTime = 0;
    goal = window.scrollY;
  }

  function tick(now) {
    // Time-corrected easing: consistent on 60/120/144Hz monitors.
    const dt = lastTime ? Math.min(64, Math.max(1, now - lastTime)) : 16.67;
    lastTime = now;
    goal = limitToPage(goal);
    const current = window.scrollY;
    const difference = goal - current;
    if (Math.abs(difference) < 0.6) {
      window.scrollTo({ top: goal, behavior: "instant" });
      frame = null;
      lastTime = 0;
      return;
    }
    const progress = 1 - Math.exp(-dt / easingMs);
    window.scrollTo({ top: current + difference * progress, behavior: "instant" });
    frame = requestAnimationFrame(tick);
  }

  function nestedScrollTarget(target) {
    if (!(target instanceof Element)) return false;
    // Complex controls retain their expected native interactions.
    if (target.closest(
      "[data-native-scroll], [contenteditable], textarea, select, " +
      "input[type='number'], input[type='range'], [role='dialog']"
    )) return true;
    if (document.querySelector(".modal.open, [aria-modal='true'].open")) return true;

    let node = target;
    while (node && node !== document.documentElement && node !== document.body) {
      if (node instanceof HTMLElement) {
        const style = getComputedStyle(node);
        const vertical = style.overflowY;
        if (
          /^(auto|scroll|overlay)$/.test(vertical) &&
          node.scrollHeight > node.clientHeight + 2
        ) return true;
      }
      node = node.parentElement;
    }
    return false;
  }

  window.addEventListener("wheel", event => {
    if (
      reducedMotion.matches ||
      event.defaultPrevented ||
      !event.cancelable ||
      event.ctrlKey || event.metaKey || event.shiftKey || event.altKey ||
      Math.abs(event.deltaX) > Math.abs(event.deltaY) ||
      nestedScrollTarget(event.target)
    ) {
      cancel();
      return;
    }

    let delta = event.deltaY;
    if (event.deltaMode === 1) delta *= 20;
    else if (event.deltaMode === 2) delta *= window.innerHeight * 0.9;
    if (!Number.isFinite(delta) || delta === 0 || !scrollLimit()) return;

    // No first-frame jump; inputs accumulate toward a target rather than
    // rendering an entire wheel notch instantly.
    if (frame === null) goal = window.scrollY;
    const precision = event.deltaMode === 0 && Math.abs(event.deltaY) < 48;
    easingMs = precision ? 75 : 150;
    goal = limitToPage(goal + Math.max(-680, Math.min(680, delta)));
    event.preventDefault();
    if (frame === null) frame = requestAnimationFrame(tick);
  }, { passive: false });

  // Release control immediately for native gestures, links, keyboard,
  // manual dragging of the scrollbar, navigation, and reduced motion.
  document.addEventListener("pointerdown", event => {
    if (event.target instanceof Element &&
        event.target.closest("a, button, input, [role='button']")) cancel();
  }, { capture: true });
  window.addEventListener("keydown", cancel, { capture: true });
  window.addEventListener("touchstart", cancel, { passive: true });
  window.addEventListener("popstate", cancel);
  window.addEventListener("hashchange", cancel);
  window.addEventListener("scroll", () => {
    if (frame === null) goal = window.scrollY;
  }, { passive: true });
  reducedMotion.addEventListener?.("change", cancel);

  // Exposes diagnostics to real-browser regression tests (read-only).
  Object.defineProperty(window, "__zflagScrollV2", {
    configurable: false,
    value: Object.freeze({
      version: "2.0",
      isReducedMotion: () => reducedMotion.matches,
      isAnimating: () => frame !== null
    })
  });
})();
