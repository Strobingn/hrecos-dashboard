import AsyncStorage from '@react-native-async-storage/async-storage';
import { API_BASE_URL, API_STORAGE_KEY } from '../config/api';
import { setBaseUrl } from '../api/hrecosApi';

export async function ensureApiConfigured() {
  try {
    const existing = await AsyncStorage.getItem(API_STORAGE_KEY);
    if (existing !== API_BASE_URL) {
      await setBaseUrl(API_BASE_URL);
      console.log(`HRECOS API configured: ${API_BASE_URL}`);
    }
  } catch (e) {
    console.warn('API init failed:', e.message);
  }
}