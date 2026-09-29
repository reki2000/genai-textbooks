// プレビュー上の推敲 UI。dev_server.py だけが配信し、本番には入らない。
//
// 本文をなぞって選ぶ → アクションを押す（数字キー）→ 候補が逐次届く →
// 選ぶ（数字キー）と dev_server が本文へ適用する。LLM は本文を直接編集しない。
// 選択とアンカーの組み立ては dev_comment_ui.js の window.__devSelection を使う。
// 仕様は REVISE.md。

(function () {
  'use strict'

  var API = '/__dev/revise'
  var PREFS_KEY = 'devRevisePrefs'
  var REASONS = [
    { key: '1', id: 'verbose', label: '冗長' },
    { key: '2', id: 'character', label: 'キャラが崩れた' },
    { key: '3', id: 'meaning', label: '意味が変わった' },
    { key: '4', id: 'stiff', label: '硬い' },
    { key: '5', id: 'other', label: 'その他' },
  ]

  var state = {
    config: null,
    book: null,
    prefs: { backend: '', tier: 'auto' },
    selection: null, // window.__devSelection() の結果
    request: null, // 生成中・生成済みの依頼
    rejecting: false,
    freeText: '',
    toast: null,
  }

  try {
    var saved = JSON.parse(localStorage.getItem(PREFS_KEY) || 'null')
    if (saved) {
      state.prefs.backend = saved.backend || ''
      state.prefs.tier = saved.tier || 'auto'
    }
  } catch (error) { /* private mode */ }

  function savePrefs() {
    try { localStorage.setItem(PREFS_KEY, JSON.stringify(state.prefs)) } catch (error) { /* noop */ }
  }

  // ------------------------------------------------------------------ 通信

  function postJson(path, body) {
    return fetch(API + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {}),
    }).then(function (response) {
      if (!response.ok) {
        return response.text().then(function (text) { throw new Error(text || ('HTTP ' + response.status)) })
      }
      return response.json()
    })
  }

  function loadConfig(book) {
    var backend = state.prefs.backend
    var query = '?book=' + encodeURIComponent(book) + (backend ? '&backend=' + encodeURIComponent(backend) : '')
    return fetch(API + '/config' + query, { cache: 'no-store' })
      .then(function (response) { return response.ok ? response.json() : null })
      .then(function (config) {
        if (!config) return
        state.config = config
        if (!state.prefs.backend || !(state.prefs.backend in config.backends)) {
          state.prefs.backend = config.default_backend
        }
        render()
      })
      .catch(function () {})
  }

  // 依頼を1件送り、Server-Sent Events を読みながら候補を積む。
  function startRequest(actionId, options) {
    options = options || {}
    var base = options.base || state.selection
    if (!base) return
    abortRequest()
    var controller = new AbortController()
    var request = {
      action: actionId,
      instruction: options.instruction || '',
      base: base,
      controller: controller,
      id: null,
      meta: null,
      candidates: [],
      raw: '',
      streaming: true,
      error: '',
      done: null,
      started: Date.now(),
    }
    state.request = request
    state.rejecting = false
    render()

    fetch(API, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      body: JSON.stringify({
        book: base.book,
        unit: base.unit,
        anchor: base.anchor,
        action: actionId,
        instruction: request.instruction,
        backend: state.prefs.backend,
        tier: options.tier || state.prefs.tier,
        parent: options.parent || '',
        escalate: !!options.escalate,
      }),
    })
      .then(function (response) {
        if (!response.ok) {
          return response.text().then(function (text) { throw new Error(text || ('HTTP ' + response.status)) })
        }
        return readEvents(response, function (event) { onEvent(request, event) })
      })
      .then(function () {
        request.streaming = false
        if (state.request === request) render()
      })
      .catch(function (error) {
        if (error.name === 'AbortError') return
        request.streaming = false
        request.error = error.message
        if (state.request === request) render()
      })
  }

  function readEvents(response, handle) {
    var reader = response.body.getReader()
    var decoder = new TextDecoder()
    var buffer = ''
    function pump() {
      return reader.read().then(function (chunk) {
        if (chunk.done) return
        buffer += decoder.decode(chunk.value, { stream: true })
        var cut
        while ((cut = buffer.indexOf('\n\n')) >= 0) {
          var block = buffer.slice(0, cut)
          buffer = buffer.slice(cut + 2)
          block.split('\n').forEach(function (line) {
            if (line.indexOf('data: ') === 0) {
              try { handle(JSON.parse(line.slice(6))) } catch (error) { /* 壊れた行は捨てる */ }
            }
          })
        }
        return pump()
      })
    }
    return pump()
  }

  function onEvent(request, event) {
    if (event.event === 'meta') {
      request.id = event.id
      request.meta = event
    } else if (event.event === 'delta') {
      request.raw += event.text
    } else if (event.event === 'candidate') {
      request.candidates.push(event)
      // 完成した行の分は生の表示から落とす（次の案の書きかけだけを見せる）。
      var cut = request.raw.lastIndexOf('\n')
      request.raw = cut >= 0 ? request.raw.slice(cut + 1) : ''
    } else if (event.event === 'error') {
      request.error = event.message
    } else if (event.event === 'done') {
      request.done = event
      request.streaming = false
    }
    if (state.request === request) render()
  }

  function abortRequest() {
    if (state.request && state.request.streaming && state.request.controller) {
      state.request.controller.abort()
    }
  }

  function adopt(index) {
    var request = state.request
    if (!request || !request.id) return
    var candidate = request.candidates[index]
    if (!candidate || !candidate.ok) return
    abortRequest()
    postJson('/' + request.id + '/adopt', { index: index })
      .then(function () {
        state.request = null
        // 本文が書き換わったので、古い選択のアンカーでは次の依頼を出さない。
        state.selection = null
        showToast('採用した（z で取り消し）')
        render()
      })
      .catch(function (error) {
        request.error = error.message
        render()
      })
  }

  function reject(reasonId) {
    var request = state.request
    abortRequest()
    state.request = null
    state.rejecting = false
    if (request && request.id) {
      postJson('/' + request.id + '/reject', { reason: reasonId || '' }).catch(function () {})
    }
    render()
  }

  function regenerate(escalate) {
    var request = state.request
    if (!request) return
    startRequest(request.action, {
      base: request.base,
      instruction: request.instruction,
      parent: request.id || '',
      escalate: escalate,
      tier: escalate ? 'heavy' : '',
    })
  }

  function undo() {
    if (!state.book) return
    postJson('/undo', { book: state.book })
      .then(function () { showToast('取り消した') })
      .catch(function (error) { showToast(error.message) })
  }

  // ------------------------------------------------------------------ 差分

  // 文字単位の最長共通部分列。候補は段落程度なので O(nm) で足りる。大きすぎる
  // ときは差分を諦めて新しい本文だけ見せる。
  function diff(a, b) {
    if (a.length * b.length > 2000000) return [{ op: 'ins', text: b }]
    var n = a.length
    var m = b.length
    var table = []
    for (var i = 0; i <= n; i++) table.push(new Uint16Array(m + 1))
    for (i = n - 1; i >= 0; i--) {
      for (var j = m - 1; j >= 0; j--) {
        table[i][j] = a[i] === b[j] ? table[i + 1][j + 1] + 1 : Math.max(table[i + 1][j], table[i][j + 1])
      }
    }
    var out = []
    function push(op, ch) {
      var last = out[out.length - 1]
      if (last && last.op === op) last.text += ch
      else out.push({ op: op, text: ch })
    }
    i = 0
    j = 0
    while (i < n && j < m) {
      if (a[i] === b[j]) { push('eq', a[i]); i++; j++ }
      else if (table[i + 1][j] >= table[i][j + 1]) { push('del', a[i]); i++ }
      else { push('ins', b[j]); j++ }
    }
    while (i < n) { push('del', a[i]); i++ }
    while (j < m) { push('ins', b[j]); j++ }
    return out
  }

  function renderDiff(oldText, newText) {
    return diff(oldText.replace(/\n$/, ''), newText.replace(/\n$/, '')).map(function (part) {
      var text = escapeHtml(part.text)
      if (part.op === 'del') return '<del>' + text + '</del>'
      if (part.op === 'ins') return '<ins>' + text + '</ins>'
      return '<span>' + text + '</span>'
    }).join('')
  }

  // ------------------------------------------------------------------ 画面

  function popover() {
    var element = document.getElementById('dev-revise-pop')
    if (!element) {
      element = document.createElement('div')
      element.id = 'dev-revise-pop'
      document.body.appendChild(element)
      element.addEventListener('mousedown', function (event) {
        // ボタンを押しても本文の選択が消えないようにする（入力欄は除く）。
        if (!event.target.closest('input, textarea')) event.preventDefault()
      })
    }
    return element
  }

  function render() {
    var element = popover()
    var base = state.request ? state.request.base : state.selection
    if (!state.book || !state.config || !base) {
      element.style.display = 'none'
      renderToast()
      return
    }
    element.style.display = 'block'
    element.innerHTML = state.request ? renderRequest(state.request) : renderActions()
    bind(element)
    place(element, base.rect)
    renderToast()
  }

  function place(element, rect) {
    var panelWidth = document.body.classList.contains('dev-comment-mode') ? 340 : 0
    var width = Math.min(560, window.innerWidth - panelWidth - 24)
    element.style.width = width + 'px'
    var left = Math.max(12 + window.scrollX,
      Math.min(rect.left, window.scrollX + window.innerWidth - panelWidth - width - 12))
    var top = rect.bottom + 8
    element.style.left = left + 'px'
    element.style.top = top + 'px'
  }

  function renderActions() {
    var actions = state.config.actions.map(function (action) {
      return '<button type="button" class="dev-revise-action" data-action="' + action.id + '">' +
        (action.key ? '<kbd>' + escapeHtml(action.key) + '</kbd>' : '') + escapeHtml(action.label) +
        '<small>' + (action.tier === 'heavy' ? '重' : '軽') + '</small></button>'
    }).join('')
    return (
      '<div class="dev-revise-row">' + actions + '</div>' +
      '<form class="dev-revise-free"><kbd>0</kbd>' +
      '<input type="text" placeholder="自由指示（Enter で候補を作る）" value="' + escapeHtml(state.freeText) + '">' +
      '</form>' +
      renderSettings()
    )
  }

  function renderSettings() {
    var backends = Object.keys(state.config.backends).filter(function (name) {
      return state.config.backends[name] || name === state.prefs.backend
    })
    return (
      '<div class="dev-revise-settings">' +
      backends.map(function (name) {
        return '<button type="button" data-backend="' + name + '" class="' +
          (name === state.prefs.backend ? 'is-on' : '') + '">' + name + '</button>'
      }).join('') +
      '<span class="dev-revise-sep"></span>' +
      ['auto', 'light', 'heavy'].map(function (tier) {
        return '<button type="button" data-tier="' + tier + '" class="' +
          (tier === state.prefs.tier ? 'is-on' : '') + '">' + tier + '</button>'
      }).join('') +
      '<span class="dev-revise-hint">z 取り消し · Esc 閉じる</span>' +
      '</div>'
    )
  }

  function renderRequest(request) {
    var meta = request.meta
    var head = meta
      ? escapeHtml(meta.tier + ' · ' + meta.backend + ' ' + meta.model + (meta.effort ? ' · ' + meta.effort : ''))
      : '依頼中…'
    var timing = ''
    if (request.done) {
      var usage = request.done.usage || {}
      var cached = usage.cache_read_input_tokens
      timing = ' · ' + (request.done.ms / 1000).toFixed(1) + 's' +
        (request.done.ttft_ms != null ? '（初字 ' + (request.done.ttft_ms / 1000).toFixed(1) + 's）' : '') +
        (cached != null ? ' · cache ' + Math.round(cached / 100) / 10 + 'k' : '')
    } else if (request.streaming) {
      timing = ' · <span class="dev-revise-spin"></span>'
    }
    var cards = request.candidates.map(function (candidate) {
      return renderCandidate(request, candidate)
    }).join('')
    var partial = request.streaming && request.raw.trim()
      ? '<div class="dev-revise-partial">' + escapeHtml(request.raw.slice(-120)) + '</div>'
      : ''
    var empty = !request.streaming && !request.error && !request.candidates.length
      ? '<div class="dev-revise-error">候補を読み取れなかった。r で作り直す</div>'
      : ''
    var error = request.error ? '<div class="dev-revise-error">' + escapeHtml(request.error) + '</div>' : ''
    var footer = state.rejecting
      ? '<div class="dev-revise-foot">却下の理由：' + REASONS.map(function (reason) {
        return '<button type="button" data-reason="' + reason.id + '"><kbd>' + reason.key + '</kbd>' +
          reason.label + '</button>'
      }).join('') + '<button type="button" data-reason=""><kbd>Esc</kbd>理由なし</button></div>'
      : '<div class="dev-revise-foot">' +
        '<button type="button" data-command="regenerate"><kbd>r</kbd>作り直す</button>' +
        '<button type="button" data-command="escalate"><kbd>h</kbd>もっと考えて</button>' +
        '<button type="button" data-command="reject"><kbd>Esc</kbd>却下</button></div>'
    return (
      '<div class="dev-revise-head">' + head + timing + '</div>' +
      cards + partial + empty + error + footer
    )
  }

  function renderCandidate(request, candidate) {
    var old = candidate.old || (request.meta && request.meta.old) || ''
    var usable = candidate.ok
    var body = candidate.new == null
      ? '<i>直す必要なし</i>'
      : '<div class="dev-revise-diff">' + renderDiff(old, candidate.new) + '</div>'
    var notes = ''
    if (candidate.problems && candidate.problems.length) {
      notes += '<div class="dev-revise-note is-bad">' + escapeHtml(candidate.problems.join('、')) + '</div>'
    }
    if (candidate.lint && candidate.lint.length) {
      notes += '<div class="dev-revise-note">lint: ' + escapeHtml(candidate.lint.join(' / ')) + '</div>'
    }
    return (
      '<div class="dev-revise-card' + (usable ? '' : ' is-disabled') + '" data-adopt="' + candidate.index + '">' +
      '<div class="dev-revise-why"><kbd>' + (candidate.index + 1) + '</kbd>' + escapeHtml(candidate.why) + '</div>' +
      body + notes + '</div>'
    )
  }

  function bind(element) {
    each(element, '[data-action]', function (button) {
      button.addEventListener('click', function () { startRequest(button.getAttribute('data-action')) })
    })
    each(element, '[data-backend]', function (button) {
      button.addEventListener('click', function () {
        state.prefs.backend = button.getAttribute('data-backend')
        savePrefs()
        loadConfig(state.book)
      })
    })
    each(element, '[data-tier]', function (button) {
      button.addEventListener('click', function () {
        state.prefs.tier = button.getAttribute('data-tier')
        savePrefs()
        render()
      })
    })
    each(element, '[data-adopt]', function (card) {
      card.addEventListener('click', function () { adopt(parseInt(card.getAttribute('data-adopt'), 10)) })
    })
    each(element, '[data-command]', function (button) {
      button.addEventListener('click', function () { command(button.getAttribute('data-command')) })
    })
    each(element, '[data-reason]', function (button) {
      button.addEventListener('click', function () { reject(button.getAttribute('data-reason')) })
    })
    var form = element.querySelector('.dev-revise-free')
    if (form) {
      var input = form.querySelector('input')
      input.addEventListener('input', function () { state.freeText = input.value })
      form.addEventListener('submit', function (event) {
        event.preventDefault()
        var text = input.value.trim()
        if (!text) return
        startRequest('free', { instruction: text })
      })
      input.addEventListener('keydown', function (event) {
        if (event.key === 'Escape') {
          input.blur()
          event.stopPropagation()
        }
      })
    }
  }

  function command(name) {
    if (name === 'regenerate') regenerate(false)
    else if (name === 'escalate') regenerate(true)
    else if (name === 'reject') {
      if (state.request && state.request.id && state.request.candidates.length) {
        state.rejecting = true
        render()
      } else {
        reject('')
      }
    }
  }

  function showToast(message) {
    state.toast = { message: message, until: Date.now() + 2500 }
    renderToast()
    window.setTimeout(renderToast, 2600)
  }

  function renderToast() {
    var element = document.getElementById('dev-revise-toast')
    if (!element) {
      element = document.createElement('div')
      element.id = 'dev-revise-toast'
      document.body.appendChild(element)
    }
    var visible = state.toast && state.toast.until > Date.now()
    element.style.display = visible ? 'block' : 'none'
    element.textContent = visible ? state.toast.message : ''
  }

  // ------------------------------------------------------------ キー操作

  function typing(event) {
    var target = event.target
    return target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)
  }

  document.addEventListener('keydown', function (event) {
    if (!state.book || !state.config || event.ctrlKey || event.metaKey || event.altKey) return
    if (typing(event)) return
    var key = event.key

    if (state.request) {
      if (state.rejecting) {
        var reason = REASONS.filter(function (item) { return item.key === key })[0]
        if (reason) { reject(reason.id); event.preventDefault() }
        else if (key === 'Escape' || key === 'Enter') { reject(''); event.preventDefault() }
        event.stopPropagation()
        return
      }
      if (/^[1-9]$/.test(key)) { adopt(parseInt(key, 10) - 1); event.preventDefault() }
      else if (key === 'r') { regenerate(false); event.preventDefault() }
      else if (key === 'h') { regenerate(true); event.preventDefault() }
      else if (key === 'Escape') { command('reject'); event.preventDefault(); event.stopPropagation() }
      return
    }

    if (state.selection) {
      var action = state.config.actions.filter(function (item) { return item.key === key })[0]
      if (action) { startRequest(action.id); event.preventDefault(); return }
      if (key === '0') {
        var input = document.querySelector('#dev-revise-pop .dev-revise-free input')
        if (input) { input.focus(); event.preventDefault() }
        return
      }
    }
    if (key === 'z') { undo(); event.preventDefault() }
  }, true)

  document.addEventListener('dev-selection-change', function () {
    var selection = window.__devSelection ? window.__devSelection() : null
    if (selection) {
      // 位置はページ座標で持つ（選んだ後にスクロールしてもずれないように）。
      selection.rect = {
        left: selection.rect.left + window.scrollX,
        bottom: selection.rect.bottom + window.scrollY,
      }
    }
    state.selection = selection
    render()
  })

  window.addEventListener('resize', render)

  // ------------------------------------------------------------ ルート

  function routeBook() {
    var match = window.location.pathname.match(/\/books\/([a-z0-9-]+)\//)
    return match ? match[1] : null
  }

  function onRoute() {
    var book = routeBook()
    if (book === state.book) return
    state.book = book
    abortRequest()
    state.request = null
    state.selection = null
    if (book) loadConfig(book)
    render()
  }

  window.setInterval(onRoute, 1000)
  onRoute()

  function each(root, selector, fn) {
    Array.prototype.forEach.call(root.querySelectorAll(selector), fn)
  }

  function escapeHtml(text) {
    return String(text == null ? '' : text).replace(/[&<>"]/g, function (ch) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch]
    })
  }

  // ------------------------------------------------------------------ 見た目

  var STYLE = [
    '#dev-revise-pop{display:none;position:absolute;z-index:30;box-sizing:border-box;padding:8px;',
    'background:var(--background,#fff);color:var(--textColor,#34495e);font-size:13px;line-height:1.6;',
    'border:1px solid var(--borderColor,rgba(0,0,0,.15));border-radius:8px;',
    'box-shadow:0 6px 24px rgba(0,0,0,.18);max-height:70vh;overflow:auto}',
    '#dev-revise-pop kbd{display:inline-block;min-width:1.4em;margin-right:4px;padding:0 3px;',
    'border:1px solid var(--borderColor,rgba(0,0,0,.2));border-radius:3px;font-size:11px;',
    'text-align:center;opacity:.75;font-family:inherit}',
    '#dev-revise-pop button{font:inherit;color:inherit;background:transparent;cursor:pointer;',
    'border:1px solid var(--borderColor,rgba(0,0,0,.15));border-radius:5px;padding:2px 8px}',
    '#dev-revise-pop button:hover{border-color:var(--accent,#42b983)}',
    '.dev-revise-row{display:flex;flex-wrap:wrap;gap:6px}',
    '.dev-revise-action small{margin-left:4px;opacity:.55;font-size:10px}',
    '.dev-revise-free{display:flex;align-items:center;margin:8px 0 0}',
    '.dev-revise-free input{flex:1;font:inherit;color:inherit;background:transparent;padding:3px 6px;',
    'border:1px solid var(--borderColor,rgba(0,0,0,.15));border-radius:5px}',
    '.dev-revise-settings{display:flex;flex-wrap:wrap;align-items:center;gap:4px;margin-top:8px;font-size:11px}',
    '.dev-revise-settings button{padding:0 6px!important;opacity:.6}',
    '.dev-revise-settings button.is-on{opacity:1;border-color:var(--accent,#42b983)!important}',
    '.dev-revise-sep{width:8px}',
    '.dev-revise-hint{margin-left:auto;opacity:.55}',
    '.dev-revise-head{font-size:11px;opacity:.7;margin-bottom:6px}',
    '.dev-revise-card{padding:6px 8px;margin-bottom:6px;border-radius:6px;cursor:pointer;',
    'border:1px solid var(--borderColor,rgba(0,0,0,.12))}',
    '.dev-revise-card:hover{border-color:var(--accent,#42b983)}',
    '.dev-revise-card.is-disabled{opacity:.5;cursor:default}',
    '.dev-revise-why{font-size:12px;opacity:.8;margin-bottom:2px}',
    '.dev-revise-diff{white-space:pre-wrap;word-break:break-all}',
    '.dev-revise-diff del{background:rgba(210,39,60,.18);text-decoration:line-through}',
    '.dev-revise-diff ins{background:rgba(66,185,131,.28);text-decoration:none}',
    '.dev-revise-note{font-size:11px;color:#b7791f;margin-top:2px}',
    '.dev-revise-note.is-bad{color:#c53030}',
    '.dev-revise-partial{white-space:pre-wrap;opacity:.45;font-size:12px;margin-bottom:6px}',
    '.dev-revise-error{color:#c53030;white-space:pre-wrap;margin-bottom:6px}',
    '.dev-revise-foot{display:flex;flex-wrap:wrap;gap:6px;font-size:12px}',
    '.dev-revise-spin{display:inline-block;width:8px;height:8px;border-radius:50%;',
    'background:var(--accent,#42b983);animation:dev-revise-pulse 1s ease-in-out infinite}',
    '@keyframes dev-revise-pulse{0%,100%{opacity:.2}50%{opacity:1}}',
    '#dev-revise-toast{display:none;position:fixed;left:50%;bottom:24px;transform:translateX(-50%);',
    'z-index:40;padding:6px 14px;border-radius:6px;background:rgba(40,40,40,.9);color:#fff;font-size:13px}',
  ].join('')

  var style = document.createElement('style')
  style.textContent = STYLE
  document.head.appendChild(style)
})()
