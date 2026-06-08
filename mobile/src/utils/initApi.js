import AsyncStorage from '@react-native-async-storage/async-storage';
import { API_BASE_URL, API_STORAGE_KEY } from '../config/api';
import { setBaseUrl } from '../api/hrecosApi';

export async function ensureApiConfigured() {
  try {
    const existing = await AsyncStorage.getItem(API_STORAGE_KEY);
    // Only set default if nothing is stored yet (respect user customization)
    if (existing === null) {
      await setBaseUrl(API_BASE_URL);
      console.log(`HRECOS API configured: ${API_BASE_URL}`);
    } else {
      console.log(`HRECOS API using stored URL: ${existing}`);
    }
  } catch (e) {
    console.warn('API init failed:', e.message);
  }
}