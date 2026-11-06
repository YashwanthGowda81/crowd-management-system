/**
 * CROWD-AI Parallel Video Processing & Batched YOLO Diagnostics Logger
 * 
 * Provides verifiable evidence of concurrent video capture and batched YOLO inference
 * through the browser DevTools console with the strict namespace:
 * [ CROWD-AI | PARALLEL-DIAG ]
 * 
 * Opt-in control:
 * localStorage.setItem("crowdAiDiagnostics", "true")
 */

const STORAGE_KEY = 'crowdAiDiagnostics';
const LOG_PREFIX = '[ CROWD-AI | PARALLEL-DIAG ]';

let lastLoggedEventId = 0;
let isInitialized = false;

/**
 * Returns true only when the operator has explicitly opted into detailed diagnostic logging.
 */
export const isDiagnosticsEnabled = (): boolean => {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'true';
  } catch {
    return false;
  }
};

/**
 * Programmatically enables or disables diagnostics logging in localStorage.
 */
export const setDiagnosticsEnabled = (enabled: boolean): void => {
  try {
    if (enabled) {
      localStorage.setItem(STORAGE_KEY, 'true');
      console.log(
        `%c${LOG_PREFIX} Diagnostic logging ENABLED. Detailed pipeline telemetry will output to console.`,
        'color: #06b6d4; font-weight: bold;'
      );
    } else {
      localStorage.removeItem(STORAGE_KEY);
      console.log(
        `%c${LOG_PREFIX} Diagnostic logging DISABLED. Detailed telemetry stopped.`,
        'color: #94a3b8; font-weight: bold;'
      );
    }
  } catch (err) {
    console.warn(`${LOG_PREFIX} Could not update localStorage:`, err);
  }
};

/**
 * Emits a namespaced diagnostic message if opt-in is enabled.
 */
export const logDiagnostic = (eventType: string, details: string): void => {
  if (!isDiagnosticsEnabled()) return;
  console.log(`${LOG_PREFIX} ${eventType} ${details}`);
};

/**
 * Processes incoming diagnostic event records from the backend and emits them to console.
 */
export const processDiagnosticEvents = (events: Array<{ id: number; formatted: string; type: string }>): void => {
  if (!isDiagnosticsEnabled() || !Array.isArray(events) || events.length === 0) return;

  for (const ev of events) {
    if (ev.id > lastLoggedEventId) {
      lastLoggedEventId = ev.id;
      if (ev.formatted) {
        console.log(ev.formatted);
      }
    }
  }
};

/**
 * Initializes console environment and registers global helper shortcuts for DevTools operators.
 */
export const initDiagnosticsConsole = (): void => {
  if (isInitialized) return;
  isInitialized = true;

  // Expose convenient DevTools shortcuts
  if (typeof window !== 'undefined') {
    (window as any).enableCrowdAiDiagnostics = () => {
      setDiagnosticsEnabled(true);
      return 'Diagnostics ENABLED. Real-time capture & batched inference logs active.';
    };
    (window as any).disableCrowdAiDiagnostics = () => {
      setDiagnosticsEnabled(false);
      return 'Diagnostics DISABLED. Real-time telemetry logs stopped.';
    };
  }

  if (isDiagnosticsEnabled()) {
    console.log(
      `%c${LOG_PREFIX} Diagnostic logger active (opt-in verified). Ready for parallel capture & batched inference events.`,
      'color: #22d3ee; font-weight: bold; background: #082f49; padding: 3px 6px; border-radius: 4px;'
    );
  }
};
