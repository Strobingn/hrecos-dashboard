/**
 * HRECOS RiverWatch API Client
 *
 * Axios-based API client for the HRECOS (Hudson River Environmental Conditions
 * Observing System) monitoring service. Supports configurable base URL via
 * AsyncStorage, request/response interceptors, offline detection, and
 * comprehensive error handling.
 */

import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import NetInfo from '@react-native-community/netinfo';
import { API_BASE_URL, API_STORAGE_KEY, API_REGION } from '../config/api';

// ── Constants ────────────────────────────────────────────────────────────────

const DEFAULT_BASE_URL = API_BASE_URL;
const REQUEST_TIMEOUT = 15000; // 15 seconds
const BASE_URL_KEY = API_STORAGE_KEY;

// ── Axios Instance ───────────────────────────────────────────────────────────

const apiClient = axios.create({
  baseURL: DEFAULT_BASE_URL,
  timeout: REQUEST_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
});

// ── Request Interceptor ──────────────────────────────────────────────────────

/**
 * Request interceptor that reads the base URL from AsyncStorage.
 * Falls back to the default HRECOS API endpoint if none is configured.
 */
apiClient.interceptors.request.use(
  async (config) => {
    // Check network connectivity before making the request
    const netInfo = await NetInfo.fetch();
    if (!netInfo.isConnected) {
      const error = new Error(
        'No internet connection. Please check your network and try again.'
      );
      error.name = 'NetworkError';
      error.isOffline = true;
      throw error;
    }

    try {
      const storedBaseUrl = await AsyncStorage.getItem(BASE_URL_KEY);
      if (storedBaseUrl) {
        config.baseURL = storedBaseUrl;
      } else {
        config.baseURL = DEFAULT_BASE_URL;
      }
    } catch (storageError) {
      // If AsyncStorage fails, use the default base URL
      config.baseURL = DEFAULT_BASE_URL;
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// ── Response Interceptor ─────────────────────────────────────────────────────

/**
 * Response interceptor for global error handling.
 * Handles 401 (Unauthorized), 500 (Server Error), and network failures gracefully.
 */
apiClient.interceptors.response.use(
  (response) => {
    // Return successful responses as-is
    return response;
  },
  async (error) => {
    // Handle cases where the error was thrown before the request was made
    if (!error.response) {
      if (error.name === 'NetworkError' && error.isOffline) {
        return Promise.reject(error);
      }

      if (error.code === 'ECONNABORTED' || error.code === 'ETIMEDOUT') {
        const timeoutError = new Error(
          'Request timed out. The server is taking too long to respond. Please try again later.'
        );
        timeoutError.name = 'TimeoutError';
        timeoutError.status = 408;
        return Promise.reject(timeoutError);
      }

      if (error.code === 'ECONNREFUSED' || error.code === 'ERR_NETWORK') {
        const networkError = new Error(
          'Unable to connect to the HRECOS server. Please check your internet connection or try again later.'
        );
        networkError.name = 'ConnectionError';
        networkError.status = 0;
        return Promise.reject(networkError);
      }

      return Promise.reject(error);
    }

    const { status, config } = error.response;
    const endpoint = config?.url || 'unknown endpoint';

    switch (status) {
      case 400: {
        const badRequestError = new Error(
          `Invalid request to ${endpoint}. Please check your parameters and try again.`
        );
        badRequestError.name = 'BadRequestError';
        badRequestError.status = 400;
        badRequestError.response = error.response.data;
        return Promise.reject(badRequestError);
      }

      case 401: {
        const authError = new Error(
          'Authentication required. Please log in to access this resource.'
        );
        authError.name = 'AuthenticationError';
        authError.status = 401;
        return Promise.reject(authError);
      }

      case 403: {
        const forbiddenError = new Error(
          'You do not have permission to access this resource.'
        );
        forbiddenError.name = 'ForbiddenError';
        forbiddenError.status = 403;
        return Promise.reject(forbiddenError);
      }

      case 404: {
        const notFoundError = new Error(
          `The requested resource at ${endpoint} was not found.`
        );
        notFoundError.name = 'NotFoundError';
        notFoundError.status = 404;
        return Promise.reject(notFoundError);
      }

      case 429: {
        const rateLimitError = new Error(
          'Too many requests. Please wait a moment before trying again.'
        );
        rateLimitError.name = 'RateLimitError';
        rateLimitError.status = 429;
        return Promise.reject(rateLimitError);
      }

      case 500:
      case 502:
      case 503:
      case 504: {
        const serverError = new Error(
          `HRECOS server error (${status}). The monitoring service is temporarily unavailable. Please try again later.`
        );
        serverError.name = 'ServerError';
        serverError.status = status;
        return Promise.reject(serverError);
      }

      default: {
        const genericError = new Error(
          `An unexpected error occurred (${status}). Please try again.`
        );
        genericError.name = 'ApiError';
        genericError.status = status;
        genericError.response = error.response.data;
        return Promise.reject(genericError);
      }
    }
  }
);

// ── Utility Functions ────────────────────────────────────────────────────────

/**
 * Check if the device is currently online.
 * @returns {Promise<boolean>}
 */
export const isOnline = async () => {
  const netInfo = await NetInfo.fetch();
  return netInfo.isConnected === true;
};

/**
 * Get the currently configured base URL.
 * @returns {Promise<string>}
 */
export const getBaseUrl = async () => {
  try {
    const stored = await AsyncStorage.getItem(BASE_URL_KEY);
    return stored || DEFAULT_BASE_URL;
  } catch {
    return DEFAULT_BASE_URL;
  }
};

/**
 * Set a custom base URL for the API.
 * @param {string} url - The new base URL.
 */
export const setBaseUrl = async (url) => {
  try {
    if (url && url.trim().length > 0) {
      await AsyncStorage.setItem(BASE_URL_KEY, url.trim());
    } else {
      await AsyncStorage.removeItem(BASE_URL_KEY);
    }
  } catch (error) {
    throw new Error(`Failed to save base URL: ${error.message}`);
  }
};

/**
 * Reset the base URL to the default HRECOS endpoint.
 */
export const resetBaseUrl = async () => {
  try {
    await AsyncStorage.removeItem(BASE_URL_KEY);
  } catch (error) {
    throw new Error(`Failed to reset base URL: ${error.message}`);
  }
};

// ── API Functions ────────────────────────────────────────────────────────────

/**
 * Fetch all monitoring stations in the HRECOS network.
 * @returns {Promise<Array>} List of station objects.
 */
export const getStations = async () => {
  try {
    const response = await apiClient.get('/api/stations', {
      params: { region: API_REGION },
    });
    return response.data;
  } catch (error) {
    throw error;
  }
};

/**
 * Fetch the latest environmental data for a specific station.
 * @param {string} station - The station identifier.
 * @returns {Promise<Object>} Latest sensor readings.
 */
export const getLatestData = async (station) => {
  try {
    const response = await apiClient.get('/api/data', {
      params: { station, region: API_REGION },
    });
    return response.data;
  } catch (error) {
    throw error;
  }
};

/**
 * Fetch the latest environmental data from all stations.
 * @returns {Promise<Array>} Latest readings from all stations.
 */
export const getAllData = async () => {
  try {
    const response = await apiClient.get('/api/data', {
      params: { region: API_REGION },
    });
    return response.data;
  } catch (error) {
    throw error;
  }
};

/**
 * Fetch historical data for a specific station.
 * @param {string} station - The station identifier.
 * @param {number} hours - Number of hours of history to fetch (default: 24).
 * @returns {Promise<Array>} Historical sensor readings.
 */
export const getHistorical = async (station, hours = 24) => {
  try {
    const response = await apiClient.get(`/api/historical/${station}`, {
      params: { hours },
    });
    return response.data;
  } catch (error) {
    throw error;
  }
};

/**
 * Fetch statistical summaries for a specific station.
 * @param {string} station - The station identifier.
 * @param {number} hours - Number of hours to summarize (default: 24).
 * @returns {Promise<Object>} Statistical summary (min, max, avg).
 */
export const getStats = async (station, hours = 24) => {
  try {
    const response = await apiClient.get(`/api/stats/${station}`, {
      params: { hours },
    });
    return response.data;
  } catch (error) {
    throw error;
  }
};

/**
 * Fetch tide predictions for the Hudson River.
 * @param {number} hours - Number of hours of tide data (default: 48).
 * @returns {Promise<Array>} Tide level predictions.
 */
export const getTides = async (hours = 48) => {
  try {
    const response = await apiClient.get('/api/tides', {
      params: { hours, region: API_REGION },
    });
    return response.data;
  } catch (error) {
    throw error;
  }
};

/**
 * Fetch the current tide status.
 * @returns {Promise<Object>} Current tide level and trend.
 */
export const getCurrentTide = async () => {
  try {
    const response = await apiClient.get('/api/tides/current', {
      params: { region: API_REGION },
    });
    return response.data;
  } catch (error) {
    throw error;
  }
};

/**
 * Fetch the dashboard overview with key metrics and summaries.
 * @returns {Promise<Object>} Dashboard data including recent readings and alerts.
 */
export const getDashboard = async () => {
  try {
    const response = await apiClient.get('/api/dashboard');
    return response.data;
  } catch (error) {
    throw error;
  }
};

/**
 * Fetch detected environmental anomalies across all stations.
 * @returns {Promise<Array>} List of anomaly events.
 */
export const getAnomalies = async () => {
  try {
    const response = await apiClient.get('/api/anomalies');
    return response.data;
  } catch (error) {
    throw error;
  }
};

// ── Default Export ───────────────────────────────────────────────────────────

export default apiClient;
