// Server-only endpoints; never expose deployment secrets to the browser.
export const LIVE_CONTRACT = 'observed_metar_only_v2';
export const CANONICAL_SKYGUARD_API_URL = 'https://skyguard-ai-wbm9.onrender.com';

export interface LiveBackendStatus {
  presentation_contract?: string;
  simulation_active?: boolean;
  is_cached?: boolean;
  fetched_at_utc?: string | null;
}

const LEGACY_BACKEND_HOSTS = new Set(['skyguard-ai.onrender.com']);
const DEFAULT_TIMEOUT_MS = 55_000;

function normalizedBackend(value: string): URL {
  const base = new URL(value);
  if (!['http:', 'https:'].includes(base.protocol) || base.username || base.password)
    throw new Error('Invalid ML service configuration.');
  base.pathname = base.pathname.replace(/\/$/, '') || '/';
  base.search = '';
  base.hash = '';
  return base;
}

/**
 * Return trusted backend candidates without leaking environment values to the client.
 *
 * The first Vercel setup guide used the non-existent skyguard-ai.onrender.com example
 * hostname.  Treat that known legacy value as invalid and always retain the verified
 * public Render service as a recovery target.  A future custom backend remains the
 * preferred target and races the canonical service, so one dead origin cannot consume
 * the complete Vercel function duration.
 */
export function backendCandidates(): URL[] {
  const candidates: URL[] = [];
  const configured = process.env.SKYGUARD_API_URL?.trim();
  if (configured) {
    try {
      const parsed = normalizedBackend(configured);
      if (!LEGACY_BACKEND_HOSTS.has(parsed.hostname)) candidates.push(parsed);
    } catch {
      // A malformed deployment variable must not disable the verified fallback.
    }
  }
  candidates.push(normalizedBackend(CANONICAL_SKYGUARD_API_URL));
  return candidates.filter((candidate, index, all) =>
    all.findIndex(other => other.origin === candidate.origin && other.pathname === candidate.pathname) === index
  );
}

function backendTimeoutMs(): number {
  const value = Number(process.env.SKYGUARD_API_TIMEOUT_MS || DEFAULT_TIMEOUT_MS);
  if (!Number.isFinite(value)) return DEFAULT_TIMEOUT_MS;
  return Math.max(5_000, Math.min(55_000, Math.trunc(value)));
}

async function fetchBackendJSON<T>(base: URL, endpoint: string, init: RequestInit): Promise<T> {
  const response = await fetch(new URL(endpoint, base), {
    ...init,
    cache: 'no-store',
    signal: AbortSignal.timeout(backendTimeoutMs()),
  });
  if (!response.ok) throw new Error(`ML service unavailable (HTTP ${response.status}).`);
  const contentType = response.headers.get('content-type')?.toLowerCase() || '';
  if (!contentType.includes('application/json')) {
    throw new Error('ML service is warming up and has not returned JSON yet.');
  }
  return response.json() as Promise<T>;
}

export async function backendJSON<T = unknown>(endpoint: string, init: RequestInit = {}): Promise<T> {
  if (!endpoint.startsWith('/')) throw new Error('Backend endpoint must be an absolute path.');
  try {
    return await Promise.any(
      backendCandidates().map(base => fetchBackendJSON<T>(base, endpoint, init))
    );
  } catch {
    throw new Error('ML service is unavailable or still waking. Retry shortly.');
  }
}
export async function observedFeedStatus() {
  const status = await backendJSON<LiveBackendStatus>('/api/live/status');
  if (status.presentation_contract !== LIVE_CONTRACT || status.simulation_active !== false)
    throw new Error('An observed-only source refresh is required before displaying live evidence.');
  return status;
}
