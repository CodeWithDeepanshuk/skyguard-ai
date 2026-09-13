/**
 * SkyGuard AI - Scientific and Temporal Formatters
 * Strict UTC/IST conversions, elevation-invariant pressure formatting, robust residuals
 */

export function formatTime(isoString: string | null | undefined, mode: 'UTC' | 'IST' = 'UTC', includeSeconds = false): string {
  if (!isoString) return '—';
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return '—';

    if (mode === 'UTC') {
      const year = d.getUTCFullYear();
      const month = d.toLocaleString('en-US', { month: 'short', timeZone: 'UTC' });
      const day = String(d.getUTCDate()).padStart(2, '0');
      const hours = String(d.getUTCHours()).padStart(2, '0');
      const minutes = String(d.getUTCMinutes()).padStart(2, '0');
      const seconds = includeSeconds ? `:${String(d.getUTCSeconds()).padStart(2, '0')}` : '';
      return `${day} ${month} ${year} · ${hours}:${minutes}${seconds} UTC`;
    } else {
      // Indian Standard Time is UTC + 5:30
      const options: Intl.DateTimeFormatOptions = {
        timeZone: 'Asia/Kolkata',
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: includeSeconds ? '2-digit' : undefined,
        hour12: false,
      };
      return `${new Intl.DateTimeFormat('en-IN', options).format(d)} IST`;
    }
  } catch {
    return '—';
  }
}

export function formatAge(minutes: number | null | undefined): string {
  if (minutes === null || minutes === undefined || isNaN(minutes)) return 'Age unknown';
  if (minutes < 1) return '< 1 min ago';
  if (minutes < 60) return `${Math.round(minutes)}m ago`;
  const hours = Math.floor(minutes / 60);
  const remainingMins = Math.round(minutes % 60);
  if (hours < 24) return `${hours}h ${remainingMins}m ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function formatTemp(value: number | null | undefined): string {
  if (value === null || value === undefined || isNaN(value)) return '—';
  return `${value > 0 ? '' : ''}${value.toFixed(1)}°C`;
}

export function formatPressure(value: number | null | undefined): string {
  if (value === null || value === undefined || isNaN(value)) return '—';
  return `${value.toFixed(1)} hPa`;
}

export function formatHumidity(value: number | null | undefined): string {
  if (value === null || value === undefined || isNaN(value)) return '—';
  return `${value.toFixed(1)}%`;
}

export function formatResidual(val: number | null | undefined, unit: string): string {
  if (val === null || val === undefined || isNaN(val)) return '—';
  const sign = val > 0 ? '+' : '';
  return `${sign}${val.toFixed(2)} ${unit}`;
}

export function formatCoord(lat: number, lon: number): string {
  const latStr = `${Math.abs(lat).toFixed(3)}°${lat >= 0 ? 'N' : 'S'}`;
  const lonStr = `${Math.abs(lon).toFixed(3)}°${lon >= 0 ? 'E' : 'W'}`;
  return `${latStr}, ${lonStr}`;
}
