/* Browser-only Google Drive appDataFolder sync. No tokens are persisted. */
(function () {
  'use strict';
  var oauthClientId = window.genaiDriveClientId || '';
  var scope = 'https://www.googleapis.com/auth/drive.appdata';
  var requiredScopes = 'openid email ' + scope;
  var filePrefix = 'genai-textbooks-progress-v1-';
  var loginStateKey = 'genai-drive-last-sub-v1';
  var token = null; // Never store in localStorage, cookies, sessionStorage or IndexedDB.
  var expiresAt = 0;
  var profile = null;
  var tokenClient = null;
  var ownFileId = null;
  var ownFilename = null;
  var generation = 0;
  var busy = false;
  var dirty = false;
  var flushTimer = null;
  var lastSync = 0;
  var errorText = '';
  var progress = window.genaiReadingProgress;
  if (!progress) return;

  var shell = document.createElement('div');
  shell.id = 'drive-account';
  var button = document.createElement('button');
  button.id = 'drive-account-button';
  button.type = 'button';
  shell.appendChild(button);
  document.body.appendChild(shell);
  document.body.classList.add('drive-sync-enabled');

  function saved(key) {
    try { return localStorage.getItem(key); } catch (error) { return null; }
  }
  function remember(key, value) {
    try {
      if (value === null) localStorage.removeItem(key);
      else localStorage.setItem(key, value);
    } catch (error) {}
  }

  // A stable per-browser file avoids overwriting another device's progress.
  function deviceFile(sub) {
    var key = 'genai-drive-device-v1:' + sub;
    var device = saved(key);
    if (!device || !/^[a-f0-9-]{32,36}$/.test(device)) {
      device = crypto.randomUUID();
      remember(key, device);
    }
    return filePrefix + device + '.json';
  }

  function hasToken() {
    return !!token && Date.now() < expiresAt;
  }
  function display() {
    var label;
    if (profile && hasToken()) label = (profile.email || profile.name || 'Google') + ' · 同期';
    else if (profile) label = (profile.email || 'Google') + ' · 再接続';
    else if (saved(loginStateKey)) label = 'Google Driveに再接続';
    else label = 'Google Driveに接続';
    button.textContent = label;
    button.title = errorText || label;
  }

  function element(name, content, parent, className) {
    var el = document.createElement(name);
    if (content) el.textContent = content;
    if (className) el.className = className;
    parent.appendChild(el);
    return el;
  }
  function action(parent, label, handler, primary, disabled) {
    var el = element('button', label, parent, primary ? 'drive-primary' : '');
    el.type = 'button';
    el.disabled = !!disabled;
    el.addEventListener('click', handler);
    return el;
  }

  function closeDialog() {
    var overlay = document.getElementById('drive-dialog-overlay');
    if (overlay) overlay.remove();
  }
  function dialog() {
    closeDialog();
    var overlay = element('div', '', document.body);
    overlay.id = 'drive-dialog-overlay';
    var panel = element('div', '', overlay);
    panel.id = 'drive-dialog';
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-modal', 'true');
    panel.setAttribute('aria-labelledby', 'drive-dialog-title');
    var heading = element('h2', profile ? 'Google Drive 同期' : 'Google Driveで読書記録を同期', panel);
    heading.id = 'drive-dialog-title';

    if (!profile || !hasToken()) {
      element('p', 'Googleアカウントを接続すると、読書位置・読了率を端末間で同期できます。', panel);
      element('p', '記録はご自身のGoogle Driveの非公開アプリデータ領域（appDataFolder）に小さなJSONとして保存します。', panel);
      element('p', '権限はこのアプリの専用データ領域のみです。ほかのGoogle Drive文書・写真・スプレッドシートは表示も読み取りもできません。アカウント表示のためメールアドレスも取得します。', panel);
      element('p', 'アクセストークンはページのメモリ内だけで保持し、保存しません。ページ再読み込みや期限切れでは再接続が必要です。', panel, 'drive-small');
      if (!oauthClientId) element('p', '現在はサイト管理者によるGoogle OAuth設定待ちです。', panel, 'drive-error');
      if (errorText) element('p', errorText, panel, 'drive-error');
      var row = element('div', '', panel, 'drive-actions');
      action(row, 'Googleで接続', function () {
        closeDialog();
        beginAuthorization();
      }, true, !oauthClientId);
      if (saved(loginStateKey)) action(row, 'この端末からログアウト', signOut, false);
      action(row, '閉じる', closeDialog);
    } else {
      element('p', profile.email || 'Googleアカウント', panel);
      element('p', busy ? '同期しています…' : errorText ? errorText : '読書記録の同期が有効です。', panel, errorText ? 'drive-error' : '');
      element('p', '記録はアプリ専用領域にのみ保存されます。', panel, 'drive-small');
      var actions = element('div', '', panel, 'drive-actions');
      action(actions, '今すぐ同期', function () { closeDialog(); syncNow(); }, true, busy);
      action(actions, 'ログアウト', signOut);
      action(actions, '閉じる', closeDialog);
    }
    action(overlay, '', function () {}, false).remove(); // Prevent click-through only; no visible control.
    overlay.addEventListener('click', function (event) { if (event.target === overlay) closeDialog(); });
    document.addEventListener('keydown', function escape(event) {
      if (event.key === 'Escape' && overlay.isConnected) {
        closeDialog();
        document.removeEventListener('keydown', escape);
      }
    });
    var firstButton = panel.querySelector('button');
    if (firstButton) firstButton.focus();
  }

  function beginAuthorization() {
    if (!oauthClientId) { dialog(); return; }
    if (!window.google || !google.accounts || !google.accounts.oauth2) {
      errorText = 'Google認証ライブラリが読み込めません。通信状況を確認してください。';
      dialog();
      return;
    }
    if (!tokenClient) {
      tokenClient = google.accounts.oauth2.initTokenClient({
        client_id: oauthClientId,
        scope: requiredScopes,
        callback: function (response) {
          if (!response || response.error || !response.access_token ||
              !google.accounts.oauth2.hasGrantedAllScopes(response, scope)) {
            errorText = 'Googleへの接続が許可されませんでした。';
            dialog();
            return;
          }
          token = response.access_token;
          expiresAt = Date.now() + Math.max(0, Number(response.expires_in || 300) - 30) * 1000;
          errorText = '';
          connect().catch(handleFailure);
        },
        error_callback: function () {
          errorText = 'Google認証を完了できませんでした。';
          dialog();
        }
      });
    }
    // This call must occur directly from a user click for popup access.
    tokenClient.requestAccessToken({ prompt: 'select_account' });
  }

  async function api(url, init) {
    if (!hasToken()) throw new Error('認証の期限が切れました。再接続してください。');
    var headers = Object.assign({ Authorization: 'Bearer ' + token }, init && init.headers || {});
    var response = await fetch(url, Object.assign({}, init || {}, { headers: headers, cache: 'no-store' }));
    if (response.status === 401) {
      token = null;
      expiresAt = 0;
      throw new Error('認証の期限が切れました。再接続してください。');
    }
    if (!response.ok) throw new Error('Google API error: HTTP ' + response.status);
    return response;
  }
  async function jsonApi(url, init) {
    var response = await api(url, init);
    return response.json();
  }
  function fileListUrl() {
    var params = new URLSearchParams({
      spaces: 'appDataFolder',
      q: "name contains '" + filePrefix + "' and trashed = false",
      fields: 'nextPageToken,files(id,name)',
      pageSize: '100'
    });
    return 'https://www.googleapis.com/drive/v3/files?' + params;
  }

  async function readDriveFiles() {
    var id = 0;
    var url = fileListUrl();
    ownFileId = null;
    while (url && id++ < 5) {
      var listed = await jsonApi(url);
      var files = Array.isArray(listed.files) ? listed.files : [];
      for (var i = 0; i < files.length; i++) {
        var file = files[i];
        if (file.name === ownFilename) ownFileId = file.id;
        if (!file.name || !file.name.startsWith(filePrefix) || !file.name.endsWith('.json')) continue;
        var response = await api('https://www.googleapis.com/drive/v3/files/' + encodeURIComponent(file.id) + '?alt=media');
        var raw = await response.text();
        if (raw.length > 500000) continue;
        try {
          var data = JSON.parse(raw);
          if (data && data.schema === 1 && data.records) progress.merge(data.records);
        } catch (error) { /* Ignore malformed obsolete app data, never execute it. */ }
      }
      url = listed.nextPageToken
        ? 'https://www.googleapis.com/drive/v3/files?' + new URLSearchParams({
            spaces: 'appDataFolder', q: "name contains '" + filePrefix + "' and trashed = false",
            fields: 'nextPageToken,files(id,name)', pageSize: '100', pageToken: listed.nextPageToken
          })
        : null;
    }
  }

  async function writeOwnFile() {
    var body = JSON.stringify({ schema: 1, records: progress.snapshot() });
    if (body.length > 500000) throw new Error('読書記録の容量が上限を超えました。');
    if (ownFileId) {
      await api('https://www.googleapis.com/upload/drive/v3/files/' +
        encodeURIComponent(ownFileId) + '?uploadType=media', {
          method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: body
        });
      return;
    }
    var boundary = 'progress_' + crypto.randomUUID().replace(/-/g, '');
    var multipart = new Blob([
      '--' + boundary + '\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n',
      JSON.stringify({ name: ownFilename, parents: ['appDataFolder'], mimeType: 'application/json' }),
      '\r\n--' + boundary + '\r\nContent-Type: application/json\r\n\r\n',
      body, '\r\n--' + boundary + '--\r\n'
    ]);
    var uploaded = await jsonApi('https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id', {
      method: 'POST', headers: { 'Content-Type': 'multipart/related; boundary=' + boundary }, body: multipart
    });
    ownFileId = uploaded.id;
  }

  async function syncNow() {
    if (!hasToken() || busy || !profile) { display(); return; }
    var epoch = generation;
    busy = true;
    dirty = false;
    try {
      await readDriveFiles();
      if (epoch !== generation) return;
      await writeOwnFile();
      if (epoch !== generation) return;
      lastSync = Date.now();
      errorText = '';
    } catch (error) {
      dirty = true;
      handleFailure(error);
    } finally {
      busy = false;
      display();
      if (dirty && hasToken()) queueSync();
    }
  }
  function queueSync() {
    if (!hasToken() || flushTimer) return;
    flushTimer = setTimeout(function () {
      flushTimer = null;
      if (busy) { queueSync(); return; }
      syncNow();
    }, Math.max(5000, 30000 - (Date.now() - lastSync)));
  }
  function handleFailure(error) {
    errorText = error && error.message ? error.message : '同期に失敗しました。';
    display();
  }

  async function connect() {
    var epoch = ++generation;
    var info = await jsonApi('https://openidconnect.googleapis.com/v1/userinfo');
    if (epoch !== generation) return;
    if (!info.sub) throw new Error('Googleアカウント情報を取得できませんでした。');
    if (!profile || profile.sub !== info.sub) {
      progress.switchAccount(info.sub);
      ownFileId = null;
    }
    profile = { sub: info.sub, name: info.name || '', email: info.email || '' };
    ownFilename = deviceFile(info.sub);
    remember(loginStateKey, info.sub); // Account ID only, never a credential.
    errorText = '';
    display();
    await syncNow();
  }

  function signOut() {
    closeDialog();
    ++generation;
    clearTimeout(flushTimer);
    flushTimer = null;
    var oldToken = token;
    token = null;
    expiresAt = 0;
    profile = null;
    ownFilename = null;
    ownFileId = null;
    errorText = '';
    remember(loginStateKey, null);
    progress.switchAccount(null);
    display();
    // Revokes this app's Google grant. Does not sign the user out of Google itself.
    if (oldToken && window.google && google.accounts && google.accounts.oauth2) {
      google.accounts.oauth2.revoke(oldToken, function () {});
    }
  }

  button.addEventListener('click', dialog);
  window.addEventListener('genai-reading-progress-changed', function () {
    if (hasToken()) { dirty = true; queueSync(); }
  });
  document.addEventListener('visibilitychange', function () {
    if (document.hidden && hasToken() && dirty && !busy) syncNow();
  });
  window.addEventListener('online', function () { if (hasToken()) syncNow(); });
  setInterval(function () { if (hasToken()) syncNow(); }, 120000);
  var lastSub = saved(loginStateKey);
  if (lastSub && /^[0-9]{1,50}$/.test(lastSub)) progress.switchAccount(lastSub);
  display();
})();
