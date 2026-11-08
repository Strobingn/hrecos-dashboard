const test = require('node:test');
const assert = require('node:assert/strict');
const { parseVersion, compareVersions, pickUpdate } = require('./version.js');

test('tag v1.0.1 matches versionName 1.0.1', () => {
  assert.equal(compareVersions('v1.0.1', '1.0.1'), 0);
  assert.equal(parseVersion('v1.0.1').raw, '1.0.1');
});

test('1.0.1 is newer than the installed 1.0.0 and the old v0.3.0-live tag', () => {
  assert.equal(compareVersions('1.0.1', '1.0.0'), 1);
  assert.equal(compareVersions('v0.3.0-live', '1.0.1'), -1);
  assert.equal(compareVersions('1.0.1', '1.0.1-live'), 1);
});

test('pickUpdate skips drafts, tags without an apk, and versions that are not newer', () => {
  const releases = [
    {
      tag_name: 'v1.0.2',
      draft: true,
      prerelease: false,
      body: 'draft',
      assets: [{ name: 'app.apk', browser_download_url: 'https://example.test/draft.apk' }],
    },
    {
      tag_name: 'bass',
      draft: false,
      prerelease: false,
      body: 'not a version',
      assets: [{ name: 'app.apk', browser_download_url: 'https://example.test/bass.apk' }],
    },
    {
      tag_name: 'v1.0.0',
      draft: false,
      prerelease: false,
      body: 'same as installed',
      assets: [{ name: 'app.apk', browser_download_url: 'https://example.test/100.apk' }],
    },
    {
      tag_name: 'v0.3.0-live',
      draft: false,
      prerelease: true,
      body: 'older prerelease',
      assets: [{ name: 'old.apk', browser_download_url: 'https://example.test/old.apk' }],
    },
    {
      tag_name: 'v1.0.2',
      draft: false,
      prerelease: false,
      body: 'notes',
      assets: [{ name: 'notes.txt', browser_download_url: 'https://example.test/notes.txt' }],
    },
    {
      tag_name: 'v1.0.1',
      draft: false,
      prerelease: false,
      body: 'Fixed launch crash.',
      assets: [{ name: 'hrecos.apk', browser_download_url: 'https://example.test/hrecos.apk' }],
    },
  ];

  const update = pickUpdate(releases, '1.0.0');
  assert.equal(update.tag, 'v1.0.1');
  assert.equal(update.version, '1.0.1');
  assert.equal(update.apkName, 'hrecos.apk');
  assert.equal(update.notes, 'Fixed launch crash.');
  assert.equal(pickUpdate(releases, '1.0.1'), null);
  assert.equal(pickUpdate(releases, '9.0.0'), null);
});

test('live GitHub releases offer the newest tagged apk and skip the installed version', async () => {
  const response = await fetch(
    'https://api.github.com/repos/Strobingn/hrecos-dashboard/releases?per_page=20',
    {
      headers: {
        Accept: 'application/vnd.github+json',
        'User-Agent': 'hrecos-riverwatch',
      },
    }
  );
  assert.equal(response.status, 200);
  const releases = await response.json();
  const older = pickUpdate(releases, '0.1.0');
  assert.ok(older);
  assert.ok(older.apkUrl.endsWith('.apk'));
  assert.ok(compareVersions(older.version, '1.0.1') >= 0);
  assert.equal(pickUpdate(releases, older.version), null);
});
