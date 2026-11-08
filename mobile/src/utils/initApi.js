import AsyncStorage from '@react-native-async-storage/async-storage';
import { API_BASE_URL, API_STORAGE_KEY, isIgnoredApiOverride, resolveApiBaseUrl } from '../config/api';

export async function ensureApiConfigured() {
  try {
    const existing = await AsyncStorage.getItem(API_STORAGE_KEY);
    if (existing && isIgnoredApiOverride(existing)) {
      await AsyncStorage.removeItem(API_STORAGE_KEY);
      console.log(`Ignoring stale API override ${existing}; using ${API_BASE_URL}`);
      return;
    }
    console.log(`HRECOS API configured: ${resolveApiBaseUrl(existing)}`);
  } catch (e) {
    console.warn('API init failed:', e.message);
  }
}