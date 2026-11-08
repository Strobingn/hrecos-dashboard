/**
 * HRECOS API configuration
 *
 * The default is the live Oracle Always Free server. Settings can still
 * override it (AsyncStorage key @hrecos_api_base_url). Stored localhost and
 * 192.168.x values are ignored so existing installs pick up the live server.
 */
export const API_BASE_URL = 'https://129-213-163-221.sslip.io';
export const API_STORAGE_KEY = '@hrecos_api_base_url';
export const API_REGION = 'cornwall_on_hudson';

function hostnameOf(url) {
  const trimmed = String(url || '').trim();
  if (!trimmed) return '';
  try {
    return new URL(trimmed.includes('://') ? trimmed : `http://${trimmed}`).hostname;
  } catch {
    return '';
  }
}

/**
 * True when a saved override should not be used.
 * Matches http://localhost:8000 and any 192.168.x host (the old LAN placeholder).
 */
export function isIgnoredApiOverride(url) {
  if (url == null) return false;
  const trimmed = String(url).trim().replace(/\/+$/, '');
  if (!trimmed) return false;
  const lower = trimmed.toLowerCase();
  if (
    lower === 'http://localhost:8000' ||
    lower === 'https://localhost:8000' ||
    lower === 'http://127.0.0.1:8000' ||
    lower === 'https://127.0.0.1:8000'
  ) {
    return true;
  }
  return /^192\.168\.\d{1,3}\.\d{1,3}$/.test(hostnameOf(lower));
}

/** Stored custom URL, or the live default when the override is missing or stale. */
export function resolveApiBaseUrl(stored) {
  if (stored && !isIgnoredApiOverride(stored)) {
    return String(stored).trim().replace(/\/+$/, '');
  }
  return API_BASE_URL;
}
