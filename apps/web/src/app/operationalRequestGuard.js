/**
 * Generación + AbortController para descartar respuestas operativas obsoletas (H3-C.1.1).
 */

export function createOperationalRequestGuard() {
  let generation = 0;
  /** @type {AbortController | null} */
  let controller = null;

  function ensureController() {
    if (!controller) {
      controller = new AbortController();
    }
    return controller;
  }

  return {
    getGeneration() {
      return generation;
    },
    getSignal() {
      return ensureController().signal;
    },
    isStale(requestGeneration) {
      return requestGeneration !== generation;
    },
    /** Cancela solicitudes en vuelo e incrementa la generación. */
    invalidate() {
      generation += 1;
      if (controller) {
        controller.abort();
        controller = null;
      }
      return { generation, signal: ensureController().signal };
    },
  };
}
