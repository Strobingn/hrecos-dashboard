/**
 * Release tags are `v` plus versionName (`v1.0.1` for versionName 1.0.1).
 * Comparison is semver on that version, and prereleases stay eligible.
 */

const SEMVER = /^v?(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?$/;

function parseVersion(input) {
  if (input == null) return null;
  const match = String(input).trim().match(SEMVER);
  if (!match) return null;
  return {
    major: Number(match[1]),
    minor: Number(match[2]),
    patch: Number(match[3]),
    prerelease: match[4] || null,
    raw: `${match[1]}.${match[2]}.${match[3]}${match[4] ? `-${match[4]}` : ''}`,
  };
}

/** 1 if a is newer, -1 if b is newer, 0 if equal, null if either side is not a version. */
function compareVersions(a, b) {
  const left = typeof a === 'string' ? parseVersion(a) : a;
  const right = typeof b === 'string' ? parseVersion(b) : b;
  if (!left || !right) return null;
  if (left.major !== right.major) return left.major > right.major ? 1 : -1;
  if (left.minor !== right.minor) return left.minor > right.minor ? 1 : -1;
  if (left.patch !== right.patch) return left.patch > right.patch ? 1 : -1;
  if (left.prerelease === right.prerelease) return 0;
  if (left.prerelease && !right.prerelease) return -1;
  if (!left.prerelease && right.prerelease) return 1;
  return left.prerelease > right.prerelease ? 1 : -1;
}

function apkAsset(release) {
  const assets = Array.isArray(release?.assets) ? release.assets : [];
  return assets.find(
    (asset) =>
      asset &&
      typeof asset.name === 'string' &&
      asset.name.toLowerCase().endsWith('.apk') &&
      typeof asset.browser_download_url === 'string' &&
      asset.browser_download_url.length > 0
  );
}

/**
 * Newest GitHub release, including prereleases, that is newer than the
 * installed versionName and has an .apk attached. Drafts are ignored.
 */
function pickUpdate(releases, installedVersion) {
  const installed = parseVersion(installedVersion);
  if (!installed || !Array.isArray(releases)) return null;

  let best = null;
  for (const release of releases) {
    if (!release || release.draft) continue;
    const parsed = parseVersion(release.tag_name);
    if (!parsed) continue;
    const apk = apkAsset(release);
    if (!apk) continue;
    if (compareVersions(parsed, installed) <= 0) continue;
    if (!best || compareVersions(parsed, best.parsed) > 0) {
      best = {
        parsed,
        version: parsed.raw,
        tag: release.tag_name,
        notes: typeof release.body === 'string' ? release.body.trim() : '',
        apkUrl: apk.browser_download_url,
        apkName: apk.name,
        prerelease: !!release.prerelease,
      };
    }
  }
  return best;
}

module.exports = { parseVersion, compareVersions, pickUpdate };
