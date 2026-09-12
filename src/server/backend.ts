// Server-only endpoint; never expose deployment secrets to the browser.
export const LIVE_CONTRACT = 'observed_metar_only_v2';
export async function backendJSON(endpoint: string, init: RequestInit = {}) {
  const configured = process.env.SKYGUARD_API_URL;
  if (!configured) throw new Error('The online ML backend has not been configured.');
  const base = new URL(configured);
  if (!['http:', 'https:'].includes(base.protocol) || base.username || base.password)
    throw new Error('Invalid ML service configuration.');
  const response = await fetch(new URL(endpoint, base), {
    ...init, cache: 'no-store', signal: AbortSignal.timeout(15000),
  });
  if (!response.ok) throw new Error(`ML service unavailable (HTTP ${response.status}).`);
  return response.json();
}
export async function observedFeedStatus() {
  const status = await backendJSON('/api/live/status');
  if (status.presentation_contract !== LIVE_CONTRACT || status.simulation_active !== false)
    throw new Error('An observed-only source refresh is required before displaying live evidence.');
  return status;
}
