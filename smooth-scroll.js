/**
 * ZFLAG Smooth Scroll · Website only
 * Keeps native trackpad/touch/keyboard behavior and preserves nested scrolling.
 * Coarse mouse-wheel easing is intentionally modest and runs only while needed.
 */
(() => {
  "use strict";

  const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const finePointer = window.matchMedia("(pointer: fine)");
  const hover = window.matchMedia("(hover: hover)");
  if (!("requestAnimationFrame" in window)) return;

  let destination = window.scrollY;
  let frame = 0;

  function stop() {
    if (frame) window.cancelAnimationFrame(frame);
    frame = 0;
    destination = window.scrollY;
  }

  function frameStep() {
    frame = 0;
    const position = window.scrollY;
    const gap = destination - position;

    if (Math.abs(gap) < 0.7) {
      window.scrollTo({ top: destination, behavior: "instant" });
      destination = window.scrollY;
      return;
    }

    window.scrollTo({ top: position + gap * 0.22, behavior: "instant" });
    frame = window.requestAnimationFrame(frameStep);
  }

  function shouldUseNativeScroll(target) {
    if (!(target instanceof Element)) return false;

    // Legal dialogs, the language dropdown, UI mockups, and custom overflow
    // containers must keep their own scrolling and never move the whole page.
    if (document.querySelector(".modal.open, [aria-modal='true'].open")) return true;
    if (target.closest(
      "[data-native-scroll], [contenteditable], textarea, select, " +
      "input[type='number'], input[type='range'], [role='dialog']"
    )) return true;

    let node = target;
    while (node && node !== document.documentElement && node !== document.body) {
      if (node instanceof HTMLElement) {
        const css = window.getComputedStyle(node);
        if (
          /^(auto|scroll|overlay)$/.test(css.overflowY) &&
          node.scrollHeight > node.clientHeight + 2
        ) return true;
      }
      node = node.parentElement;
    }
    return false;
  }

  window.addEventListener("wheel", (event) => {
    if (
      event.defaultPrevented ||
      !event.cancelable ||
      motion.matches ||
      !finePointer.matches ||
      !hover.matches ||
      event.ctrlKey || event.metaKey || event.altKey || event.shiftKey ||
      Math.abs(event.deltaX) > Math.abs(event.deltaY)
    ) {
      stop();
      return;
    }

    // Precision trackpads provide small pixel deltas and already feel fluid.
    // Let the browser handle these naturally to preserve native gestures.
    if (event.deltaMode === 0 && Math.abs(event.deltaY) < 48) {
      stop();
      return;
    }
    if (shouldUseNativeScroll(event.target)) {
      stop();
      return;
    }

    const delta = event.deltaMode === 1
      ? event.deltaY * 18
      : event.deltaMode === 2
        ? event.deltaY * window.innerHeight
        : event.deltaY;

    const limit = Math.max(0,
      document.documentElement.scrollHeight - window.innerHeight
    );

    if (!limit) return;
    if (!frame) destination = window.scrollY;
    destination = Math.max(0, Math.min(limit,
      destination + Math.max(-420, Math.min(420, delta))
    ));

    event.preventDefault();
    if (!frame) frame = window.requestAnimationFrame(frameStep);
  }, { passive: false });

  // A nav click, pager click, touch, or keyboard action immediately returns
  // control to the browser. Hash links use native CSS smooth scrolling.
  document.addEventListener("click", (event) => {
    if (event.target instanceof Element &&
        event.target.closest("a[href*='#'], button, [role='button']")) stop();
  }, { capture: true });
  window.addEventListener("keydown", stop, { capture: true });
  window.addEventListener("touchstart", stop, { passive: true });
  window.addEventListener("popstate", stop);
  window.addEventListener("hashchange", stop);
  window.addEventListener("scroll", () => {
    if (!frame) destination = window.scrollY;
  }, { passive: true });
  motion.addEventListener?.("change", stop);
})();
