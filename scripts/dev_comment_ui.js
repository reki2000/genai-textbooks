// プレビュー上でコメントを付ける UI。dev_server.py だけが配信し、本番の
// site_template.html には一切入らない。
//
// 設計の要点：
//
// - 対象はユーザーが引いた選択範囲そのもの。位置の確定はサーバ側でやり、
//   ブラウザは「見出し・引用文字列・節内の何番目か」だけを送って行番号は送らない。
//   行番号は編集のたびに陳腐化するので、サーバが毎回引き直す（scripts/comments.py）。
// - 引用の突き合わせは正規形で行う。ルビの読み（rt/rp）、脚注番号、KaTeX の
//   描画結果、空白を落とす。落とし方は comments.py の normalize() と対で保つ。
// - 反映はページ全体のリロードではなく docsify の再取得で行い、スクロール位置を
//   保ったまま該当段落を光らせる。コメントを書きながら直っていく体験のため。

(function () {
  'use strict'

  var API = '/__dev/comments'
  var STORAGE_KEY = 'devCommentDraft'
  var STATUS_LABEL = {
    open: '処理中',
    answered: '対応済み',
    resolved: '確認済み',
    stale: '位置不明',
  }
  var STATUS_ICON = {
    open: '⏳',
    answered: '✔',
    resolved: '☑',
    stale: '⚠',
  }
  var STATUS_ORDER = ['open', 'answered', 'stale', 'resolved']

  var AGENT_LABEL = {
    loading: '確認中',
    waiting: '待機中',
    initializing: '初期化中',
    working: '対応中',
    disconnected: '未接続',
  }

  var state = {
    // 初回の一覧 API が返すサーバ側の在席情報を正本にする。応答前に未接続と
    // 決めつけると、画面リロードのたびに担当が消えたように見えてしまう。
    agent: { state: 'loading' },
    book: null,
    part: 1,
    vm: null,
    index: null,
    selection: null, // { range, unit, block }
    comments: [],
    markers: null,
    markdown: '',
    markdownPath: null,
    flash: null,
    revision: null,
    expanded: {}, // コメント id → 全文を開いているか
    followupDrafts: {}, // コメント id → 対応結果への追加コメント
    // 見出しのアイコンで切り替える表示フィルタ。確認済みは既定で畳んでおく。
    filters: { open: true, answered: true, stale: true, resolved: false },
    draft: '',
    kind: 'wording',
  }

  // ---------------------------------------------------------------- 正規化

  var STRIP_SELECTORS = 'rt, rp, sup, .katex, .katex-display, .footnotes, .anchor > span.sr-only'

  function normalizeChar(ch) {
    if (/[\s　]/.test(ch)) return ''
    // <ruby> の両脇に置かれるゼロ幅非結合子（generate_site.py の RUBY_GUARD）は
    // 描画結果にしか無い。ソース側の正規形と揃うように落とす。
    if (ch === '‌' || ch === '​') return ''
    return ch.normalize('NFKC')
  }

  function normalizeText(text) {
    var out = ''
    for (var i = 0; i < text.length; i++) out += normalizeChar(text[i])
    return out
  }

  // ------------------------------------------------------------ 文字索引
  //
  // 描画結果を1文字ずつ走査し、正規化した文字列と「その文字がどのテキスト
  // ノードの何文字目か」を並べて持つ。保存済みコメントの引用を本文から探して
  // 目印を置くために使う（選択そのものはブラウザの選択機能に任せる）。

  function buildIndex(root) {
    var chars = []
    var text = ''
    var skip = root.querySelectorAll ? Array.prototype.slice.call(root.querySelectorAll(STRIP_SELECTORS)) : []

    function isSkipped(node) {
      for (var i = 0; i < skip.length; i++) {
        if (skip[i].contains(node)) return true
      }
      return false
    }

    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT, null)
    var node
    var lastWasBoundary = true
    while ((node = walker.nextNode())) {
      if (node.nodeType === Node.ELEMENT_NODE) {
        var tag = node.tagName
        if (tag === 'BR' || /^(P|DIV|LI|TR|H[1-6]|BLOCKQUOTE|PRE|TABLE|HR)$/.test(tag)) {
          if (!lastWasBoundary) {
            chars.push({ node: null, offset: 0, boundary: true })
            text += '\n'
            lastWasBoundary = true
          }
        }
        continue
      }
      if (isSkipped(node)) continue
      var value = node.nodeValue
      for (var i = 0; i < value.length; i++) {
        var normalized = normalizeChar(value[i])
        for (var j = 0; j < normalized.length; j++) {
          chars.push({ node: node, offset: i, boundary: false })
          text += normalized[j]
          lastWasBoundary = false
        }
      }
    }
    // 引用の検索は改行（ブロックの境目）を含まない文字列に対して行う。
    // サーバ側の正規形にも改行は無いため。flat 上の位置から chars の位置へ
    // 戻れるように対応表を持つ。
    var flat = ''
    var flatMap = []
    for (var k = 0; k < chars.length; k++) {
      if (chars[k].boundary) continue
      flat += text[k]
      flatMap.push(k)
    }
    return { text: text, chars: chars, flat: flat, flatMap: flatMap, root: root }
  }

  function currentIndex() {
    if (!state.index) {
      var root = document.querySelector('.markdown-section')
      if (!root) return null
      state.index = buildIndex(root)
    }
    return state.index
  }

  function rangeFromIndex(index, start, end) {
    // [start, end) の正規化文字位置から DOM の Range を作る。
    var first = null
    var last = null
    for (var i = start; i < end; i++) {
      var entry = index.chars[i]
      if (!entry || entry.boundary) continue
      if (!first) first = entry
      last = entry
    }
    if (!first || !last) return null
    var range = document.createRange()
    range.setStart(first.node, first.offset)
    range.setEnd(last.node, Math.min(last.offset + 1, last.node.nodeValue.length))
    return range
  }

  function textOfRange(range) {
    var fragment = range.cloneContents()
    var holder = document.createElement('div')
    holder.appendChild(fragment)
    Array.prototype.forEach.call(holder.querySelectorAll(STRIP_SELECTORS), function (element) {
      element.remove()
    })
    return normalizeText(holder.textContent)
  }

  // ---------------------------------------------------------------- 選択

  function blockOf(node) {
    var element = node.nodeType === Node.TEXT_NODE ? node.parentElement : node
    while (element && element !== document.body) {
      if (/^(P|LI|H[1-6]|BLOCKQUOTE|TD|TH|PRE)$/.test(element.tagName)) return element
      element = element.parentElement
    }
    return null
  }

  function nearestHeading(element) {
    // .markdown-section 直下は見出しと本文が兄弟で並ぶ。直前の見出しを遡る。
    var section = document.querySelector('.markdown-section')
    if (!section) return null
    var top = element
    while (top && top.parentElement !== section) top = top.parentElement
    while (top) {
      if (/^H[1-6]$/.test(top.tagName)) return top
      top = top.previousElementSibling
    }
    return null
  }

  function headingInfo(element) {
    var heading = nearestHeading(element)
    if (!heading) return { text: '', level: 0, path: [] }
    var level = parseInt(heading.tagName.slice(1), 10)
    var path = []
    var stack = []
    var section = document.querySelector('.markdown-section')
    var node = section.firstElementChild
    while (node) {
      if (/^H[1-6]$/.test(node.tagName)) {
        var nodeLevel = parseInt(node.tagName.slice(1), 10)
        while (stack.length && stack[stack.length - 1].level >= nodeLevel) stack.pop()
        stack.push({ level: nodeLevel, text: node.textContent.trim() })
        if (node === heading) {
          path = stack.map(function (item) { return item.text })
          break
        }
      }
      node = node.nextElementSibling
    }
    return { text: heading.textContent.trim(), level: level, path: path }
  }

  function sectionMembers(element) {
    // 見出しから、同位以上の次の見出しの手前までの兄弟要素。
    var heading = nearestHeading(element)
    if (!heading) return null
    var level = parseInt(heading.tagName.slice(1), 10)
    var members = [heading]
    var node = heading.nextElementSibling
    while (node) {
      if (/^H[1-6]$/.test(node.tagName) && parseInt(node.tagName.slice(1), 10) <= level) break
      members.push(node)
      node = node.nextElementSibling
    }
    return members
  }

  // ユーザーが引いた選択範囲をそのまま対象にする。単位は範囲から自動で決める：
  // 複数の塊にまたがっていれば節、塊ぜんぶなら発言、その一部なら文。
  // これは**コメントの対象**であって修正の範囲ではない。全体に関わる指摘を一部だけ
  // 選んで書くことがあるので、どこまで直すかは対応する側がコメントの内容で決める。
  function captureSelection() {
    var selection = window.getSelection()
    if (!selection || selection.isCollapsed || selection.rangeCount === 0) return
    var range = selection.getRangeAt(0)
    var section = document.querySelector('.markdown-section')
    if (!section || !section.contains(range.commonAncestorContainer)) return
    if (!textOfRange(range)) return

    var startBlock = blockOf(range.startContainer)
    var endBlock = blockOf(range.endContainer)
    var block = startBlock || endBlock
    if (!block) return

    var unit = 'sentence'
    if (startBlock !== endBlock) {
      unit = 'section'
    } else if (textOfRange(range).length >= normalizeText(block.textContent).length) {
      unit = 'paragraph'
    }

    state.selection = { range: range.cloneRange(), unit: unit, block: block }
    repaint()
    renderPanel()
  }

  // ------------------------------------------------------------ ハイライト

  function overlay() {
    var layer = document.getElementById('dev-comment-overlay')
    if (!layer) {
      layer = document.createElement('div')
      layer.id = 'dev-comment-overlay'
      document.body.appendChild(layer)
    }
    return layer
  }

  function paint(rangesWithClass) {
    var layer = overlay()
    layer.innerHTML = ''
    rangesWithClass.forEach(function (item) {
      // 目印を描けないことがコメントを妨げてはいけないので、ここでの失敗は握る。
      if (!item.range || typeof item.range.getClientRects !== 'function') return
      var rects = item.range.getClientRects()
      for (var i = 0; i < rects.length; i++) {
        var rect = rects[i]
        if (rect.width < 1 || rect.height < 1) continue
        var box = document.createElement('div')
        box.className = 'dev-comment-rect ' + item.className
        box.style.left = rect.left + window.scrollX + 'px'
        box.style.top = rect.top + window.scrollY + 'px'
        box.style.width = rect.width + 'px'
        box.style.height = rect.height + 'px'
        if (item.title) box.title = item.title
        layer.appendChild(box)
      }
    })
  }

  // 目印の Range 解決は本文を走査するので、スクロールのたびにやり直さない。
  // 索引かコメント一覧が変わったときだけ作り直し、repaint は矩形を置くだけ。
  function computeMarkers() {
    var index = currentIndex()
    state.markers = []
    if (!index) return
    state.comments.forEach(function (comment) {
      if (comment.part !== state.part || comment.status === 'resolved') return
      var found = findQuote(index, comment.anchor.quote, comment.anchor.occurrence)
      if (!found) return
      var range = rangeFromIndex(index, found.start, found.end)
      if (!range) return
      state.markers.push({
        range: range,
        className: 'status-' + comment.status,
        title: '#' + comment.id + ' ' + (STATUS_LABEL[comment.status] || comment.status),
      })
    })
  }

  function repaint() {
    if (!state.book) {
      overlay().innerHTML = ''
      return
    }
    if (!state.markers) computeMarkers()
    var items = state.markers.slice()
    if (state.selection) {
      items.push({ range: state.selection.range, className: 'active' })
    }
    if (state.flash && state.flash.until > Date.now()) {
      items.push({ range: state.flash.range, className: 'changed' })
    }
    paint(items)
  }

  // 見つけた位置は chars（＝Range を作れる側）の添字に直して返す。
  function findQuote(index, quote, occurrence) {
    if (!quote) return null
    var position = -1
    for (var i = 0; i < Math.max(occurrence || 1, 1); i++) {
      position = index.flat.indexOf(quote, position + 1)
      if (position < 0) break
    }
    if (position < 0) position = index.flat.indexOf(quote)
    if (position < 0) return null
    var last = Math.min(position + quote.length, index.flatMap.length) - 1
    if (last < position) return null
    return { start: index.flatMap[position], end: index.flatMap[last] + 1 }
  }

  // ------------------------------------------------------------------ 通信

  function api(path, options) {
    return fetch(API + (path || ''), options).then(function (response) {
      if (!response.ok) {
        return response.text().then(function (text) {
          throw new Error(text || ('HTTP ' + response.status))
        })
      }
      return response.json()
    })
  }

  function signature(comments) {
    return comments
      .map(function (comment) {
        var messages = comment.messages || []
        return comment.id + ':' + comment.status + ':' + messages.length
      })
      .join(',')
  }

  function reloadComments(forceRender) {
    if (!state.book) return Promise.resolve()
    return api('?book=' + encodeURIComponent(state.book))
      .then(function (data) {
        var comments = data.comments || []
        var agent = data.agent || { state: 'disconnected' }
        // 1秒ごとに取りに行くので、中身が変わっていないなら描き直さない
        // （入力欄のフォーカスと履歴のスクロール位置を壊さないため）。
        var same = signature(comments) === signature(state.comments) &&
          agent.state === state.agent.state && agent.model === state.agent.model &&
          agent.effort === state.agent.effort && agent.session === state.agent.session
        if (same && !forceRender) return
        state.agent = agent
        state.comments = comments
        state.markers = null
        renderPanel()
        repaint()
      })
      .catch(function () {})
  }

  // ------------------------------------------------------------------ 画面

  // 開発サーバのプレビューはコメントを付けるための場なので、教材ページでは
  // 常にコメントモード。切り替えボタンは置かない。
  function ensureChrome() {
    if (document.getElementById('dev-comment-panel')) return
    var panel = document.createElement('div')
    panel.id = 'dev-comment-panel'
    document.body.appendChild(panel)
  }

  // パネルは常設。上から古い順にコメント履歴が積み上がり、最下段が入力欄。
  // 送信時に「いま選択されている範囲」へのコメントとして扱う。差分描画にせず
  // 毎回組み直すのは、1秒ごとの状態ポーリングで書き換わるのが履歴の数行だけで、
  // 入力中のテキストは state.draft に持っているため。
  function renderPanel() {
    var panel = document.getElementById('dev-comment-panel')
    if (!panel) return
    if (!state.book) {
      panel.style.display = 'none'
      return
    }
    panel.style.display = 'flex'

    var mine = state.comments.filter(function (comment) { return comment.part === state.part })
    mine.sort(function (a, b) { return a.id < b.id ? -1 : 1 })
    var shown = mine.filter(function (comment) { return state.filters[comment.status] })

    var focus = document.activeElement
    var hadFocus = focus && focus.id === 'dev-comment-input'
    var caret = hadFocus ? focus.selectionStart : 0

    panel.innerHTML =
      '<div class="dev-comment-head">' + renderCounts(mine) + renderAgent() + '</div>' +
      renderAgentDetail() +
      '<ol id="dev-comment-log">' +
      (shown.map(renderRow).join('') ||
        '<li class="dev-comment-empty">' +
        (mine.length ? '表示が絞られています' : '本文をなぞって範囲を選び、下の欄に書く') +
        '</li>') +
      '</ol>' +
      renderComposer()

    bindPanel(panel)

    var log = document.getElementById('dev-comment-log')
    if (log) log.scrollTop = log.scrollHeight
    if (hadFocus) {
      var input = document.getElementById('dev-comment-input')
      input.focus()
      input.setSelectionRange(caret, caret)
    }
  }

  // 状態ごとの件数。アイコンを押すとその状態の表示を切り替える。
  function renderCounts(comments) {
    var counts = {}
    comments.forEach(function (comment) {
      counts[comment.status] = (counts[comment.status] || 0) + 1
    })
    return (
      '<span class="dev-comment-counts">' +
      STATUS_ORDER.map(function (status) {
        return (
          '<button type="button" class="dev-comment-count is-' + status +
          (state.filters[status] ? ' is-on' : '') + '" data-filter="' + status +
          '" title="' + STATUS_LABEL[status] + 'の表示切り替え">' +
          STATUS_ICON[status] + '<b>' + (counts[status] || 0) + '</b></button>'
        )
      }).join('') +
      '</span>'
    )
  }

  // 対応側が居るかどうか。ロングポールを掴んでいれば待機中、直前まで来ていたなら
  // 対応中（＝編集していて待ちに戻っていない）、それ以外は未起動。
  function renderAgent() {
    var name = state.agent.state || 'disconnected'
    return (
      '<span class="dev-comment-agent is-' + name + '" title="' + agentHint() + '">' +
      '<i></i>' + (AGENT_LABEL[name] || name) + '</span>'
    )
  }

  // 担当が名乗ったモデルと effort。コメントの直し方はここで変わるので、
  // 誰が受けているのかは常に見えているようにする。
  function renderAgentDetail() {
    if (state.agent.state === 'waiting' || state.agent.state === 'initializing' || state.agent.state === 'working') {
      var model = state.agent.model || 'モデル未申告'
      var effort = state.agent.effort ? ' · effort ' + state.agent.effort : ''
      return '<div class="dev-comment-agent-detail">' + escapeHtml(model + effort) + '</div>'
    }
    // 未接続のときは、状態表示のすぐ下で起動方法を出す。
    return (
      '<div class="dev-comment-agent-detail is-warning">コメントを拾う担当が居ません。別のセッションで：' +
      '<br>claude: <button type="button" class="dev-comment-agent-command" data-copy-command="/comment-eater"' +
      ' title="クリックしてコピー"><code>/comment-eater</code></button>' +
      '<br>codex: <button type="button" class="dev-comment-agent-command" data-copy-command="$comment-eater"' +
      ' title="クリックしてコピー"><code>$comment-eater</code></button></div>'
    )
  }

  function agentHint() {
    if (state.agent.state !== 'waiting' && state.agent.state !== 'initializing' && state.agent.state !== 'working') {
      return 'コメントを拾う担当が繋がっていない'
    }
    return '担当が ' + (AGENT_LABEL[state.agent.state] || state.agent.state)
  }

  function renderRow(comment) {
    var open = !!state.expanded[comment.id]
    var head = comment.body.replace(/\s+/g, ' ').trim()
    var digest = head.length > 28 ? head.slice(0, 28) + '…' : head
    var detail = ''
    if (open) {
      var messages = comment.messages || [
        { role: 'user', body: comment.body },
        { role: 'assistant', body: comment.answer },
      ].filter(function (message) { return message.body })
      detail = '<div class="dev-comment-detail"><div class="dev-comment-thread">' +
        messages.map(function (message) {
          var label = message.role === 'assistant' ? '対応' : 'ユーザー'
          var timestamp = message.created ? '<small>' + escapeHtml(message.created) + '</small>' : ''
          return '<div class="dev-comment-message is-' + message.role + '"><b>' + label + '</b>' +
            timestamp + '<div>' + escapeHtml(message.body) + '</div></div>'
        }).join('') + '</div>'
      if (comment.status === 'stale') {
        detail += '<button type="button" data-resolve="' + comment.id + '">確認して閉じる</button>'
      }
      if (comment.status === 'answered') {
        detail += '<form class="dev-comment-followup" data-followup="' + comment.id + '">' +
          '<textarea rows="3" placeholder="対応結果に追加コメント"></textarea>' +
          '<span class="dev-comment-followup-error"></span>' +
          '<button type="button" data-resolve="' + comment.id + '">確認して閉じる</button>' +
          '<button type="submit">追加送信</button></form>'
      }
      detail += '</div>'
    }
    return (
      '<li class="status-' + comment.status + (open ? ' is-open' : '') + '" data-id="' + comment.id + '">' +
      '<div class="dev-comment-line" data-toggle="' + comment.id + '">' +
      '<span class="dev-comment-status" title="' + (STATUS_LABEL[comment.status] || comment.status) + '">' +
      (STATUS_ICON[comment.status] || '・') + '</span>' +
      '<span class="dev-comment-digest">' + escapeHtml(digest) + '</span>' +
      '</div>' + detail +
      '</li>'
    )
  }

  function renderComposer() {
    var target = state.selection
      ? unitLabel(state.selection.unit) + '：' + escapeHtml(selectionDigest())
      : '<i>本文をなぞって範囲を選ぶ</i>'
    return (
      '<form id="dev-comment-composer">' +
      '<div class="dev-comment-target' + (state.selection ? ' is-set' : '') + '">' + target + '</div>' +
      '<textarea id="dev-comment-input" rows="9" placeholder="指摘を書いて Ctrl+Enter"></textarea>' +
      '<div class="dev-comment-actions">' +
      '<label><input type="radio" name="kind" value="wording"' +
      (state.kind === 'wording' ? ' checked' : '') + '>軽微</label>' +
      '<label><input type="radio" name="kind" value="substance"' +
      (state.kind === 'substance' ? ' checked' : '') + '>内容</label>' +
      '<span class="dev-comment-error"></span>' +
      '<button type="submit">送信</button>' +
      '</div>' +
      '</form>'
    )
  }

  function selectionDigest() {
    var text = textOfRange(state.selection.range).replace(/\n/g, '')
    return text.length > 24 ? text.slice(0, 24) + '…' : text
  }

  function bindPanel(panel) {
    Array.prototype.forEach.call(panel.querySelectorAll('[data-copy-command]'), function (button) {
      button.addEventListener('click', function () {
        copyText(button.getAttribute('data-copy-command')).then(function () {
          button.classList.add('is-copied')
          button.title = 'コピーしました'
          window.setTimeout(function () {
            button.classList.remove('is-copied')
            button.title = 'クリックしてコピー'
          }, 1200)
        }).catch(function () {
          button.title = 'コピーできませんでした'
        })
      })
    })

    Array.prototype.forEach.call(panel.querySelectorAll('[data-filter]'), function (button) {
      button.addEventListener('click', function () {
        var status = button.getAttribute('data-filter')
        state.filters[status] = !state.filters[status]
        renderPanel()
      })
    })

    Array.prototype.forEach.call(panel.querySelectorAll('[data-toggle]'), function (line) {
      line.addEventListener('click', function () {
        var id = line.getAttribute('data-toggle')
        state.expanded[id] = !state.expanded[id]
        renderPanel()
        scrollToComment(id)
      })
    })

    Array.prototype.forEach.call(panel.querySelectorAll('[data-resolve]'), function (button) {
      button.addEventListener('click', function () {
        api('/' + state.book + '/' + button.getAttribute('data-resolve') + '/resolve', { method: 'POST' })
          .then(reloadComments)
          .catch(function (error) { alert(error.message) })
      })
    })

    Array.prototype.forEach.call(panel.querySelectorAll('[data-followup]'), function (form) {
      var id = form.getAttribute('data-followup')
      var input = form.querySelector('textarea')
      var error = form.querySelector('.dev-comment-followup-error')
      input.value = state.followupDrafts[id] || ''
      input.addEventListener('input', function () { state.followupDrafts[id] = input.value })
      input.addEventListener('keydown', function (event) {
        if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
          event.preventDefault()
          form.requestSubmit()
        }
      })
      form.addEventListener('submit', function (event) {
        event.preventDefault()
        var body = input.value.trim()
        if (!body) {
          error.textContent = '空のまま送れない'
          return
        }
        error.textContent = '送信中…'
        api('/' + state.book + '/' + id + '/followup', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ body: body }),
        }).then(function () {
          delete state.followupDrafts[id]
          return reloadComments()
        }).catch(function (failure) { error.textContent = failure.message })
      })
    })

    var form = document.getElementById('dev-comment-composer')
    var input = document.getElementById('dev-comment-input')
    input.value = state.draft
    input.addEventListener('input', function () {
      state.draft = input.value
      try { localStorage.setItem(STORAGE_KEY, input.value) } catch (error) { /* private mode */ }
    })
    input.addEventListener('keydown', function (event) {
      if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
        event.preventDefault()
        submit()
      }
    })
    Array.prototype.forEach.call(form.querySelectorAll('input[name=kind]'), function (radio) {
      radio.addEventListener('change', function () { state.kind = radio.value })
    })
    form.addEventListener('submit', function (event) {
      event.preventDefault()
      submit()
    })
  }

  function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text)
    }
    return new Promise(function (resolve, reject) {
      var input = document.createElement('textarea')
      input.value = text
      input.setAttribute('readonly', '')
      input.style.position = 'fixed'
      input.style.opacity = '0'
      document.body.appendChild(input)
      input.select()
      var copied = document.execCommand && document.execCommand('copy')
      document.body.removeChild(input)
      if (copied) resolve()
      else reject(new Error('copy failed'))
    })
  }

  function scrollToComment(id) {
    var comment = state.comments.filter(function (item) { return item.id === id })[0]
    var index = currentIndex()
    if (!comment || !index) return
    var found = findQuote(index, comment.anchor.quote, comment.anchor.occurrence)
    if (found) {
      var range = rangeFromIndex(index, found.start, found.end)
      if (range) {
        var rect = range.getBoundingClientRect()
        window.scrollTo({ top: rect.top + window.scrollY - window.innerHeight / 3, behavior: 'smooth' })
        return
      }
    }
    var current = rangeNearSourceLine(index, comment.anchor.current_line)
    if (current) {
      var currentRect = current.getBoundingClientRect()
      window.scrollTo({ top: currentRect.top + window.scrollY - window.innerHeight / 3, behavior: 'smooth' })
      return
    }
    // 対応によって元の引用文字列が書き換わった後も、少なくとも同じ節へ戻す。
    var heading = normalizeText(comment.anchor.current_heading || comment.anchor.heading || '')
    if (heading) {
      var candidates = document.querySelectorAll('.markdown-section h1, .markdown-section h2, ' +
        '.markdown-section h3, .markdown-section h4, .markdown-section h5, .markdown-section h6')
      for (var i = 0; i < candidates.length; i++) {
        if (normalizeText(candidates[i].textContent) === heading) {
          candidates[i].scrollIntoView({ behavior: 'smooth', block: 'center' })
          return
        }
      }
    }
  }

  function rangeNearSourceLine(index, lineNumber) {
    if (!lineNumber || !state.markdown) return null
    var lines = state.markdown.split(/\r?\n/)
    var origin = Math.max(0, Math.min(lines.length - 1, lineNumber - 1))
    for (var distance = 0; distance <= 8; distance++) {
      var candidates = distance ? [origin - distance, origin + distance] : [origin]
      for (var i = 0; i < candidates.length; i++) {
        var line = candidates[i]
        if (line < 0 || line >= lines.length) continue
        var needle = normalizeSourceLine(lines[line])
        if (needle.length < 4) continue
        var position = index.flat.indexOf(needle)
        if (position < 0) continue
        var last = Math.min(position + needle.length, index.flatMap.length) - 1
        if (last < position) continue
        var range = rangeFromIndex(index, index.flatMap[position], index.flatMap[last] + 1)
        if (range) return range
      }
    }
    return null
  }

  function normalizeSourceLine(line) {
    return normalizeText(String(line || '')
      .replace(/｜([^｜《》\n]{1,40})《[^｜《》\n]{1,40}》/g, '$1')
      .replace(/!\[([^\]]*)\]\([^)]*\)/g, '$1')
      .replace(/\[([^\]]*)\]\([^)]*\)/g, '$1')
      .replace(/\$\$?[^$]*\$\$?/g, '')
      .replace(/^[#>\-+*\d.]+\s*/, '')
      .replace(/[*`~_<>]/g, ''))
  }

  function unitLabel(unit) {
    return { sentence: '文', paragraph: '発言', section: '節' }[unit] || unit
  }

  function clearSelection() {
    state.selection = null
    repaint()
  }

  function showError(message) {
    var slot = document.querySelector('.dev-comment-error')
    if (slot) slot.textContent = message
  }

  function submit() {
    var body = state.draft.trim()
    if (!body) {
      showError('空のまま送れない')
      return
    }
    if (!state.selection) {
      showError('本文をなぞって範囲を選んでから送る')
      return
    }
    var payload = buildPayload(body, state.kind)
    showError('送信中…')
    api('', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
      .then(function () {
        state.draft = ''
        try { localStorage.removeItem(STORAGE_KEY) } catch (e) { /* noop */ }
        clearSelection()
        reloadComments()
      })
      .catch(function (failure) {
        showError(failure.message)
      })
  }

  function escapeHtml(text) {
    return String(text || '').replace(/[&<>"]/g, function (ch) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch]
    })
  }

  function buildPayload(body, kind) {
    var selection = state.selection
    var quoteFull = textOfRange(selection.range).replace(/\n/g, '')
    var quote = quoteFull.slice(0, 200)
    var tail = quoteFull.length > 200 ? quoteFull.slice(-40) : quoteFull.slice(-Math.min(40, quoteFull.length))
    var heading = headingInfo(selection.block)

    // 節内で同じ文字列が何度も出る場合に備え、節頭からの出現回数を数える。
    // 節の先頭から選択の開始点までを1つの Range にして数えるので、索引は要らない。
    var occurrence = 1
    var members = sectionMembers(selection.block)
    if (members && quote) {
      try {
        var prefixRange = document.createRange()
        prefixRange.setStartBefore(members[0])
        prefixRange.setEnd(selection.range.startContainer, selection.range.startOffset)
        var prefix = textOfRange(prefixRange).replace(/\n/g, '')
        var position = -1
        while ((position = prefix.indexOf(quote, position + 1)) >= 0) occurrence++
      } catch (error) {
        occurrence = 1
      }
    }

    return {
      book: state.book,
      part: state.part,
      kind: kind,
      unit: selection.unit,
      body: body,
      heading: heading.text,
      heading_level: heading.level,
      heading_path: heading.path,
      quote: quote,
      quote_tail: tail,
      occurrence: occurrence,
    }
  }

  // -------------------------------------------------------------- クリック

  // 選択は本文をなぞって作る。パネル内の操作で選択が消えるのを避けたいので、
  // 本文の中で指を離したときだけ拾う。本文のシングルクリックで空の選択に
  // なった場合は、直前のコメント対象を外す。
  document.addEventListener('mouseup', function (event) {
    if (!state.book) return
    if (event.target.closest && event.target.closest('#dev-comment-panel')) return
    var article = event.target.closest && event.target.closest('.markdown-section')
    window.setTimeout(function () {
      var selection = window.getSelection()
      if (article && event.detail === 1 && (!selection || selection.isCollapsed)) {
        clearSelection()
        renderPanel()
        return
      }
      captureSelection()
    }, 0)
  })

  document.addEventListener('keyup', function (event) {
    if (!state.book || !event.shiftKey) return
    window.setTimeout(captureSelection, 0)
  })

  document.addEventListener('keydown', function (event) {
    if (!state.book || event.key !== 'Escape') return
    clearSelection()
    renderPanel()
  })

  window.addEventListener('resize', repaint)
  window.addEventListener('scroll', function () {
    if (state.book) repaint()
  }, { passive: true })

  // ------------------------------------------------------- ルートとリロード

  function routeInfo() {
    var path = window.location.pathname
    var match = path.match(/\/books\/([a-z0-9-]+)\/(?:README\.([0-9]+))?/)
    if (!match) return null
    return { book: match[1], part: match[2] ? parseInt(match[2], 10) : 1 }
  }

  function onRender() {
    state.index = null
    state.markers = null
    state.selection = null
    var route = routeInfo()
    document.body.classList.toggle('dev-comment-mode', !!route)
    if (!route) {
      state.book = null
      overlay().innerHTML = ''
      var panel = document.getElementById('dev-comment-panel')
      if (panel) panel.style.display = 'none'
      return
    }
    ensureChrome()
    state.book = route.book
    state.part = route.part
    if (state.markdownPath !== currentMarkdownPath()) {
      state.markdownPath = currentMarkdownPath()
      state.markdown = ''
      fetchMarkdown().then(function (text) { state.markdown = text }).catch(function () {})
    }
    repaint()
    // 初回描画もサーバが保持する担当情報の取得後に行う。クライアントの仮状態を
    // 「未接続」として一瞬表示しない。
    reloadComments(true)
  }

  function currentMarkdownPath() {
    var route = routeInfo()
    if (!route) return null
    return 'books/' + route.book + '/' + (route.part === 1 ? 'README.md' : 'README.' + route.part + '.md')
  }

  function sitePath() {
    var path = window.location.pathname
    var cut = path.indexOf('/books/')
    return cut < 0 ? '' : path.slice(0, cut)
  }

  function fetchMarkdown() {
    var target = currentMarkdownPath()
    if (!target) return Promise.reject(new Error('not a book page'))
    return fetch(sitePath() + '/' + target, { cache: 'no-store' }).then(function (response) {
      if (!response.ok) throw new Error('HTTP ' + response.status)
      return response.text()
    })
  }

  // ソース Markdown を、描画結果と突き合わせられる正規形にする。
  // comments.py の normalize() と同じ落とし方（ルビ・数式・リンク・記号・空白）。
  function normalizeSource(text) {
    return normalizeText(
      text
        .replace(/｜([^｜《》\n]{1,40})《[^｜《》\n]{1,40}》/g, '$1')
        .replace(/\$\$[^$]*\$\$|\$[^$\n]*\$/g, '')
        .replace(/!\[[^\]]*\]\([^)\s]*\)/g, '')
        .replace(/\[([^\]]*)\]\([^)\s]*\)/g, '$1')
        .replace(/\[\^[^\]\n]+\]/g, '')
        .replace(/[*`~_<>]/g, '')
    )
  }

  // 前後の一致部分を落として、変わった行の範囲だけを残す。編集は普通ひと塊なので
  // これで足りる。複数箇所なら外側の包絡になり、光る範囲が少し広くなるだけ。
  function changedRegion(before, after) {
    if (!before || before === after) return null
    var a = before.split('\n')
    var b = after.split('\n')
    var head = 0
    while (head < a.length && head < b.length && a[head] === b[head]) head++
    var tail = 0
    while (tail < a.length - head && tail < b.length - head &&
           a[a.length - 1 - tail] === b[b.length - 1 - tail]) tail++
    var start = head
    var end = b.length - tail // exclusive
    if (end <= start) {
      // 削除だけの変更。消えた場所の直前の行を目印にする。
      start = Math.max(0, head - 1)
      end = Math.min(b.length, start + 1)
    }
    return { start: start, end: end, lines: b.slice(start, end) }
  }

  function flashRegion(region) {
    var index = currentIndex()
    if (!index || !region) return flashSection()
    var quote = normalizeSource(region.lines.join('')).slice(0, 60)
    if (!quote) return flashSection()
    var found = findQuote(index, quote, 1)
    if (!found) return flashSection()
    var range = rangeFromIndex(index, found.start, found.end)
    if (!range) return flashSection()

    state.flash = { range: range, until: Date.now() + 1600 }
    repaint()
    window.setTimeout(function () {
      state.flash = null
      repaint()
    }, 1600)

    var rect = range.getBoundingClientRect()
    if (rect.top < 60 || rect.bottom > window.innerHeight - 40) {
      window.scrollTo({ top: rect.top + window.scrollY - window.innerHeight / 3, behavior: 'smooth' })
    }
  }

  function flashSection() {
    var section = document.querySelector('.markdown-section')
    if (!section) return
    section.classList.remove('dev-comment-flash')
    void section.offsetWidth
    section.classList.add('dev-comment-flash')
  }

  // docsify は取得済みの Markdown をキャッシュするので、_fetch() を呼び直しても
  // 古い本文が描き直されるだけ。自前で取り直し、その中身を描画系へ直接渡す。
  function softReload() {
    if (!currentMarkdownPath() || !state.vm || typeof state.vm._renderMain !== 'function') return
    var scroll = window.scrollY
    fetchMarkdown()
      .then(function (text) {
        if (text === state.markdown) return
        var region = changedRegion(state.markdown, text)
        state.markdown = text
        state.vm._renderMain(text)
        window.setTimeout(function () {
          onRender()
          window.scrollTo(0, scroll)
          flashRegion(region)
          reloadComments()
        }, 60)
      })
      // 最後に描画できた本文を維持する。次の revision か手動更新で再試行される。
      .catch(function () {})
  }

  function pollRevision() {
    fetch('/__dev/revision', { cache: 'no-store' })
      .then(function (response) { return response.json() })
      .then(function (status) {
        if (state.revision === null) {
          state.revision = status.revision
          return
        }
        if (status.revision !== state.revision) {
          state.revision = status.revision
          softReload()
        }
      })
      .catch(function () {})
  }

  // コメントの状態はサーバのファイル監視で変わるので、本文の再ビルドとは別に
  // 短い間隔で拾う。対応中 → 対応済みがすぐ画面に出ることが体験の要。
  function pollComments() {
    if (state.book) reloadComments()
  }

  // ------------------------------------------------------------------ 見た目

  // 配色はサイト本体（docsify-darklight-theme）の変数に乗せる。明暗の切り替えに
  // そのまま追随し、パネルだけ浮かないようにするため。
  var STYLE = [
    '#dev-comment-overlay{position:absolute;top:0;left:0;width:0;height:0;z-index:12;pointer-events:none}',
    '.dev-comment-rect{position:absolute;border-radius:2px;pointer-events:none}',
    '.dev-comment-rect.active{background:rgba(66,185,131,.25);',
    'outline:1px solid var(--accent,#42b983)}',
    '.dev-comment-rect.status-open{background:rgba(230,162,60,.28)}',
    '.dev-comment-rect.status-answered{background:rgba(66,185,131,.22)}',
    '.dev-comment-rect.status-stale{background:rgba(210,39,120,.22)}',
    '.dev-comment-rect.changed{background:rgba(66,185,131,.4);',
    'animation:dev-comment-fade 1.6s ease-out forwards}',
    '@keyframes dev-comment-fade{0%{opacity:1}70%{opacity:.9}100%{opacity:0}}',
    'body.dev-comment-mode .content{padding-right:340px}',
    // 本文表示中の要約ボタンは、コメントペインではなく本文ペインの右上に置く。
    // 要約へ切り替えた後はスライドに全幅を渡し、コメントペインも隠す。
    'body.dev-comment-mode:not(.slide-mode) #slide-summary-toggle{right:356px}',
    'body.dev-comment-mode.slide-mode #dev-comment-panel{display:none!important}',

    '#dev-comment-panel{display:none;position:fixed;top:0;right:0;bottom:0;width:320px;z-index:28;',
    'flex-direction:column;background:var(--background,#fff);color:var(--textColor,#34495e);',
    'border-left:1px solid var(--borderColor,rgba(0,0,0,.12));font-size:13px;',
    'font-family:var(--siteFont,inherit)}',
    '.dev-comment-head{display:flex;align-items:center;justify-content:space-between;gap:8px;',
    'padding:8px 10px;border-bottom:1px solid var(--borderColor,rgba(0,0,0,.12))}',

    '.dev-comment-agent{display:inline-flex;align-items:center;gap:5px;font-size:11px;font-weight:400;',
    'padding:2px 8px;border-radius:10px;background:var(--codeBackgroundColor,#f8f8f8);',
    'border:1px solid var(--borderColor,rgba(0,0,0,.12))}',
    '.dev-comment-agent i{width:7px;height:7px;border-radius:50%;background:#999}',
    '.dev-comment-agent.is-waiting i{background:var(--accent,#42b983);',
    'box-shadow:0 0 0 3px rgba(66,185,131,.25)}',
    '.dev-comment-agent.is-initializing i{background:#409eff;animation:dev-comment-pulse 1.2s ease-in-out infinite}',
    '.dev-comment-agent.is-working i{background:#e6a23c;animation:dev-comment-pulse 1.2s ease-in-out infinite}',
    '.dev-comment-agent.is-disconnected i{background:var(--highlightColor,#d22778)}',
    '@keyframes dev-comment-pulse{0%,100%{opacity:1}50%{opacity:.35}}',

    '#dev-comment-log{flex:1;overflow-y:auto;margin:0;padding:8px;list-style:none}',
    '#dev-comment-log li{margin:0 0 6px;border:1px solid var(--borderColor,rgba(0,0,0,.12));',
    'border-radius:6px;background:var(--codeBackgroundColor,#f8f8f8)}',
    '#dev-comment-log li.dev-comment-empty{border:none;background:none;opacity:.6;padding:8px}',
    '.dev-comment-line{display:flex;gap:6px;align-items:baseline;padding:6px 8px;cursor:pointer}',
    '.dev-comment-status{flex:none;width:1.3em;text-align:center;font-size:12px;line-height:1.4}',
    '.status-open .dev-comment-status{display:inline-block;color:#e6a23c;',
    'animation:dev-comment-hourglass 1.6s ease-in-out infinite;transform-origin:center}',
    '@keyframes dev-comment-hourglass{0%,35%{transform:rotate(0)}50%,85%{transform:rotate(180deg)}',
    '100%{transform:rotate(360deg)}}',
    '.status-answered .dev-comment-status{color:var(--accent,#42b983)}',
    '.status-stale .dev-comment-status{color:var(--highlightColor,#d22778)}',
    '.status-resolved .dev-comment-status{opacity:.5}',
    '.status-resolved .dev-comment-digest{opacity:.5;text-decoration:line-through}',

    '.dev-comment-agent-detail{padding:4px 10px;font-size:11px;opacity:.65;',
    'border-bottom:1px solid var(--borderColor,rgba(0,0,0,.12));overflow:hidden;',
    'text-overflow:ellipsis;white-space:nowrap}',
    '.dev-comment-agent-detail.is-warning{opacity:1;white-space:normal;line-height:1.6;',
    'background:var(--codeBackgroundColor,#f8f8f8)}',
    '.dev-comment-agent-detail code{font-family:var(--codeFontFamily,monospace)}',
    '.dev-comment-agent-command{padding:1px 4px;border:1px solid transparent;border-radius:3px;',
    'background:none;color:inherit;font:inherit;cursor:pointer}',
    '.dev-comment-agent-command:hover,.dev-comment-agent-command:focus-visible{',
    'border-color:var(--accent,#42b983);background:var(--background,#fff);outline:none}',
    '.dev-comment-agent-command.is-copied{color:var(--accent,#42b983)}',
    '.dev-comment-counts{display:inline-flex;gap:2px}',
    '.dev-comment-count{display:inline-flex;align-items:center;gap:2px;padding:2px 6px;border-radius:9px;',
    'border:1px solid transparent;background:none;color:inherit;font:inherit;font-size:11px;',
    'cursor:pointer;opacity:.4}',
    '.dev-comment-count.is-on{opacity:1;background:var(--codeBackgroundColor,#f8f8f8);',
    'border-color:var(--borderColor,rgba(0,0,0,.12))}',
    '.dev-comment-count b{font-weight:600}',
    '.dev-comment-count.is-open{color:#e6a23c}',
    '.dev-comment-count.is-answered{color:var(--accent,#42b983)}',
    '.dev-comment-count.is-stale{color:var(--highlightColor,#d22778)}',
    '.dev-comment-digest{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;opacity:.85}',
    '.dev-comment-detail{padding:0 8px 8px;white-space:pre-wrap;line-height:1.6}',
    '.dev-comment-thread{display:flex;flex-direction:column;gap:6px;margin-bottom:6px}',
    '.dev-comment-message{padding:6px 8px;border-radius:6px;background:rgba(0,0,0,.035)}',
    '.dev-comment-message.is-assistant{border-left:3px solid var(--accent,#42b983)}',
    '.dev-comment-message.is-user{border-left:3px solid #e6a23c}',
    '.dev-comment-message small{display:block;font-size:9px;opacity:.55}',
    '.dev-comment-followup{display:grid;grid-template-columns:1fr auto;gap:5px;margin-top:7px}',
    '.dev-comment-followup textarea{grid-column:1/-1;box-sizing:border-box;resize:vertical;',
    'font:inherit;padding:5px;border-radius:4px;background:var(--codeBackgroundColor,#fff);',
    'color:inherit;border:1px solid var(--borderColor,rgba(0,0,0,.2))}',
    '.dev-comment-followup-error{grid-column:1/-1;font-size:10px;',
    'color:var(--highlightColor,#d22778)}',
    '.dev-comment-followup button[type=submit]{justify-self:end}',
    '.dev-comment-answer{margin-top:6px;padding:6px 8px;border-radius:4px;white-space:pre-wrap;',
    'background:var(--background,#fff);border:1px solid var(--borderColor,rgba(0,0,0,.12))}',
    '.dev-comment-detail button{margin-top:6px;padding:3px 10px;border-radius:4px;cursor:pointer;',
    'border:1px solid var(--borderColor,rgba(0,0,0,.2));background:var(--background,#fff);',
    'color:inherit;font:inherit;font-size:12px}',

    '#dev-comment-composer{border-top:1px solid var(--borderColor,rgba(0,0,0,.12));padding:8px;',
    'background:var(--background,#fff)}',
    '.dev-comment-target{font-size:12px;margin-bottom:6px;opacity:.6;overflow:hidden;',
    'text-overflow:ellipsis;white-space:nowrap}',
    '.dev-comment-target.is-set{opacity:1;color:var(--accent,#42b983);font-weight:600}',
    '#dev-comment-input{width:100%;box-sizing:border-box;resize:vertical;font:inherit;font-size:13px;',
    'padding:6px;border-radius:4px;background:var(--codeBackgroundColor,#fff);color:inherit;',
    'border:1px solid var(--borderColor,rgba(0,0,0,.2))}',
    '.dev-comment-actions{display:flex;flex-wrap:nowrap;white-space:nowrap;gap:10px;align-items:center;',
    'margin-top:6px;font-size:12px}',
    '.dev-comment-actions label{display:inline-flex;align-items:center;gap:3px;cursor:pointer}',
    '.dev-comment-actions input[type=radio]{margin:0}',
    '.dev-comment-actions button{flex:none;padding:4px 16px;border:none;border-radius:4px;',
    'background:var(--accent,#42b983);color:#fff;font:inherit;font-size:12px;cursor:pointer}',
    '.dev-comment-error{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;',
    'color:var(--highlightColor,#d22778);font-size:11px}',

    '.dev-comment-flash{animation:dev-comment-flash 1s ease-out}',
    '@keyframes dev-comment-flash{from{background:rgba(66,185,131,.14)}to{background:transparent}}',
    '@media (prefers-reduced-motion:reduce){.status-open .dev-comment-status{animation:none}}',
    '@media (max-width:768px){body.dev-comment-mode .content{padding-right:0}',
    'body.dev-comment-mode:not(.slide-mode) #slide-summary-toggle{right:16px}',
    '#dev-comment-panel{width:100%;top:auto;height:60vh}}',
  ].join('')

  var style = document.createElement('style')
  style.textContent = STYLE
  document.head.appendChild(style)

  try {
    state.draft = localStorage.getItem(STORAGE_KEY) || ''
  } catch (error) { /* private mode */ }

  window.setInterval(pollRevision, 500)
  window.setInterval(pollComments, 1000)
  pollRevision()

  if (window.$docsify) {
    window.$docsify.plugins = (window.$docsify.plugins || []).concat(function (hook, vm) {
      state.vm = vm
      hook.doneEach(onRender)
    })
  }
})()
