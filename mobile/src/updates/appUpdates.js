import { File, Paths } from 'expo-file-system';
import * as IntentLauncher from 'expo-intent-launcher';
import * as Application from 'expo-application';
import Constants from 'expo-constants';
import { pickUpdate } from './version';

const RELEASES_URL =
  'https://api.github.com/repos/Strobingn/hrecos-dashboard/releases?per_page=30';
const PACKAGE_NAME = 'com.hrecos.riverwatch';
const APK_TYPE = 'application/vnd.android.package-archive';

export function getInstalledVersion() {
  return (
    Application.nativeApplicationVersion ||
    Constants.expoConfig?.version ||
    Constants.manifest?.version ||
    '0.0.0'
  );
}

export async function findUpdate() {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(RELEASES_URL, {
      signal: controller.signal,
      headers: {
        Accept: 'application/vnd.github+json',
        'User-Agent': 'hrecos-riverwatch',
      },
    });
    if (!response.ok) {
      throw new Error(`GitHub releases responded ${response.status}`);
    }
    const releases = await response.json();
    return pickUpdate(releases, getInstalledVersion());
  } finally {
    clearTimeout(timer);
  }
}

function canRequestPackageInstalls() {
  try {
    const { canRequestPackageInstalls: check } = require('hrecos-install-packages');
    return check();
  } catch {
    return null;
  }
}

export async function openInstallPermissionSettings() {
  await IntentLauncher.startActivityAsync(
    'android.settings.MANAGE_UNKNOWN_APP_SOURCES',
    { data: `package:${Application.applicationId || PACKAGE_NAME}` }
  );
}

export async function downloadAndInstall(update, onProgress) {
  const allowed = canRequestPackageInstalls();
  if (allowed === false) {
    await openInstallPermissionSettings();
    const error = new Error('Allow installs from this app, then tap Update again.');
    error.code = 'INSTALL_PERMISSION';
    throw error;
  }

  const destination = new File(Paths.cache, 'hrecos-update.apk');
  if (destination.exists) destination.delete();

  const task = File.createDownloadTask(update.apkUrl, destination, {
    onProgress({ bytesWritten, totalBytes }) {
      if (typeof onProgress === 'function' && totalBytes > 0) {
        onProgress(Math.max(0, Math.min(1, bytesWritten / totalBytes)));
      }
    },
  });

  const file = await task.downloadAsync();
  if (!file) {
    throw new Error('Download did not finish');
  }

  const contentUri = file.contentUri;
  if (!contentUri) {
    throw new Error('Could not share the downloaded APK with the installer');
  }

  try {
    await IntentLauncher.startActivityAsync('android.intent.action.VIEW', {
      data: contentUri,
      flags: 1,
      type: APK_TYPE,
    });
  } catch (error) {
    await openInstallPermissionSettings();
    const wrapped = new Error('Allow installs from this app, then tap Update again.');
    wrapped.code = 'INSTALL_PERMISSION';
    wrapped.cause = error;
    throw wrapped;
  }
}
