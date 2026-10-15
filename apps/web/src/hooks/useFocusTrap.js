import { useEffect } from "react";

const FOCUSABLE =
  'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])';

export function useFocusTrap(containerRef, active) {
  useEffect(() => {
    if (!active || !containerRef.current) {
      return undefined;
    }
    const root = containerRef.current;
    const previouslyFocused = document.activeElement;

    const focusables = () => Array.from(root.querySelectorAll(FOCUSABLE));
    const initial = root.querySelector("[data-modal-initial-focus]");
    if (initial instanceof HTMLElement) {
      initial.focus();
    } else {
      focusables()[0]?.focus();
    }

    function onKeyDown(event) {
      if (event.key !== "Tab") {
        return;
      }
      const items = focusables();
      if (items.length === 0) {
        return;
      }
      const firstEl = items[0];
      const lastEl = items[items.length - 1];
      if (event.shiftKey && document.activeElement === firstEl) {
        event.preventDefault();
        lastEl.focus();
      } else if (!event.shiftKey && document.activeElement === lastEl) {
        event.preventDefault();
        firstEl.focus();
      }
    }

    root.addEventListener("keydown", onKeyDown);
    return () => {
      root.removeEventListener("keydown", onKeyDown);
      if (previouslyFocused instanceof HTMLElement) {
        previouslyFocused.focus();
      }
    };
  }, [active, containerRef]);
}
