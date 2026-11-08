import AsyncStorage from '@react-native-async-storage/async-storage';
import { API_BASE_URL } from '../config/api';

const LEGACY_API_STORAGE_KEY = '@hrecos_api_base_url';

/** Drop any previously saved server address and log the baked-in API. */
export async function ensureApiConfigured() {
  try {
    await AsyncStorage.removeItem(LEGACY_API_STORAGE_KEY);
  } catch (e) {
    console.warn('API init failed:', e.message);
  }
  console.log(`HRECOS API configured: ${API_BASE_URL}`);
}
