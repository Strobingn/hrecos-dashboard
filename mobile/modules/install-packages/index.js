import { requireNativeModule } from 'expo-modules-core';

const InstallPackages = requireNativeModule('InstallPackages');

/** True when Android will allow this app to start the package installer. */
export function canRequestPackageInstalls() {
  return InstallPackages.canRequestPackageInstalls() !== false;
}
