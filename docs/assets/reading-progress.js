/* Local, per-browser reading progress for docsify books. */
(function () {
  'use strict';

  var basePath = window.readerProgressBasePath || '';
  var storageKey = 'genai-textbooks-reading-progress-v1';
  var entries = loadEntries();
  var active = null;
  var saveTimer = null;
  var restoring = false;

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function loadEntries() {
    try {
      var stored = JSON.parse(window.localStorage.getItem(storageKey) || '{}');
      return stored && typeof stored === 'object' && !Array.isArray(stored) ? stored : {};
    } catch (error) {
      return {};
    }
  }

  function persist() {
    try {
      window.localStorage.setItem(storageKey, JSON.stringify(entries));
    } catch (error) {
      // Storage can be disabled or full. Continue without breaking reading.
    }
  }

  function bookId(path) {
    if (path.indexOf(basePath + '/books/') !== 0) return null;
    var rest = path.slice((basePath + '/books/').length);
    var match = rest.match(/^([a-zA-Z0-9-]+)(?:\/(?:index\.html)?|$)/);
    return match ? match[1] : null;
  }

  function idForLink(link) {
    try {
      var url = new URL(link.href, window.location.href);
      return url.origin === window.location.origin ? bookId(url.pathname) : null;
    } catch (error) {
      return null;
    }
  }

  function bookUrl(id) {
    return basePath + '/books/' + encodeURIComponent(id) + '/';
  }

  function getEntry(id) {
    var entry = entries[id];
    return entry && typeof entry === 'object' && !Array.isArray(entry) ? entry : null;
  }

  function progressPercent(entry) {
    return entry ? clamp(Number(entry.furthest) || 0, 0, 100) : 0;
  }

  function makeProgress(entry) {
    var percent = progressPercent(entry);
    var outer = document.createElement('div');
    outer.className = 'reader-progress';
    outer.setAttribute('role', 'progressbar');
    outer.setAttribute('aria-label', '読書進捗');
    outer.setAttribute('aria-valuemin', '0');
    outer.setAttribute('aria-valuemax', '100');
    outer.setAttribute('aria-valuenow', String(percent));

    var track = document.createElement('div');
    track.className = 'reader-progress-track';
    var fill = document.createElement('span');
    fill.className = 'reader-progress-fill';
    fill.style.width = percent + '%';
    track.appendChild(fill);
    outer.appendChild(track);
    return outer;
  }

  function makeLabel(entry) {
    var percent = progressPercent(entry);
    var label = document.createElement('span');
    label.className = 'reader-progress-label';
    label.textContent = entry.done ? '読了' : percent + '%';
    return label;
  }

  function makeResumeLink(id, label) {
    var link = document.createElement('a');
    link.href = bookUrl(id) + '?resume=1';
    link.className = 'reader-resume';
    link.textContent = label || '続きから読む →';
    return link;
  }

  function renderHome(article) {
    var headings = article.querySelectorAll('h2');
    var catalogHeading = null;
    for (var i = 0; i < headings.length; i++) {
      if (headings[i].textContent.indexOf('教材一覧') !== -1) {
        catalogHeading = headings[i];
        break;
      }
    }
    if (!catalogHeading) return;

    var recent = Object.keys(entries).map(function (id) {
      return { id: id, entry: getEntry(id) };
    }).filter(function (item) {
      return item.entry && !item.entry.done && progressPercent(item.entry) > 0;
    }).sort(function (a, b) {
      return (b.entry.updated || 0) - (a.entry.updated || 0);
    }).slice(0, 3);

    if (recent.length) {
      var section = document.createElement('section');
      section.className = 'reader-continue';
      var title = document.createElement('h2');
      title.textContent = '読書を再開';
      section.appendChild(title);
      var items = document.createElement('div');
      items.className = 'reader-continue-items';

      recent.forEach(function (item) {
        var card = document.createElement('div');
        card.className = 'reader-continue-item';
        var top = document.createElement('div');
        top.className = 'reader-continue-top';
        var name = document.createElement('a');
        name.className = 'reader-continue-title';
        name.href = bookUrl(item.id);
        name.textContent = item.entry.title || item.id;
        top.appendChild(name);
        top.appendChild(makeLabel(item.entry));
        card.appendChild(top);
        card.appendChild(makeProgress(item.entry));
        card.appendChild(makeResumeLink(item.id));
        items.appendChild(card);
      });
      section.appendChild(items);
      catalogHeading.parentNode.insertBefore(section, catalogHeading);
    }

    // A catalog item is a generated h4 with a book link inside.
    article.querySelectorAll('h4').forEach(function (heading) {
      var links = heading.querySelectorAll('a[href]');
      var id = null;
      var title = '';
      links.forEach(function (link) {
        var candidate = idForLink(link);
        if (candidate && !id) {
          id = candidate;
          title = link.textContent.trim();
        }
      });
      if (!id) return;
      var entry = getEntry(id);
      if (!entry || progressPercent(entry) === 0) return;
      if (!entry.title && title) {
        entry.title = title;
        persist();
      }

      var display = document.createElement('div');
      display.className = 'reader-progress-top';
      display.appendChild(makeProgress(entry));
      display.appendChild(makeLabel(entry));
      display.querySelector('.reader-progress').style.flex = '1';
      heading.insertAdjacentElement('afterend', display);
    });
  }

  function renderSidebar() {
    document.querySelectorAll('.sidebar a[href]').forEach(function (link) {
      var id = idForLink(link);
      if (!id) return;
      var url = new URL(link.href, window.location.href);
      if (url.search || url.hash) return; // Ignore nested table-of-contents links.
      var entry = getEntry(id);
      var percent = progressPercent(entry);
      var mark = link.querySelector('.reader-sidebar-mark');
      if (!percent) {
        if (mark) mark.remove();
        return;
      }
      if (!mark) {
        mark = document.createElement('span');
        mark.className = 'reader-sidebar-mark';
        link.appendChild(mark);
      }
      var status = entry.done ? 'done' : 'in-progress';
      var value = entry.done ? '✓' : '●';
      var description = entry.done ? '読了' : percent + '%まで到達';
      if (mark.textContent !== value) mark.textContent = value;
      if (mark.getAttribute('title') !== description) {
        mark.title = description;
        mark.setAttribute('aria-label', description);
      }
      if (mark.dataset.status !== status) mark.dataset.status = status;
    });
  }

  function headingsIn(article) {
    return Array.prototype.slice.call(article.querySelectorAll('h1,h2,h3,h4,h5,h6')).filter(function (heading) {
      return heading.id || heading.querySelector('[id]');
    });
  }

  function headingId(heading) {
    return heading.id || heading.querySelector('[id]').id;
  }

  function absoluteTop(element) {
    return element.getBoundingClientRect().top + window.scrollY;
  }

  function savePosition() {
    if (!active || !active.article.isConnected || restoring || document.body.classList.contains('slide-mode')) return;
    var article = active.article;
    var start = absoluteTop(article);
    var end = start + article.getBoundingClientRect().height;
    if (end <= start) return;

    var readingPoint = window.scrollY + window.innerHeight * 0.65;
    var percentage = clamp(Math.round(100 * (readingPoint - start) / (end - start)), 0, 100);
    var completed = article.getBoundingClientRect().bottom <= window.innerHeight + 20;
    var entry = getEntry(active.id) || {};
    var heads = headingsIn(article);
    var anchor = null;
    var section = 0;
    for (var i = 0; i < heads.length; i++) {
      if (absoluteTop(heads[i]) > window.scrollY + 120) break;
      anchor = heads[i];
      var headTop = absoluteTop(anchor);
      var nextTop = i + 1 < heads.length ? absoluteTop(heads[i + 1]) : end;
      section = clamp((window.scrollY - headTop) / Math.max(1, nextTop - headTop), 0, 1);
    }

    entry.title = article.querySelector('h1') ? article.querySelector('h1').textContent.trim() : (entry.title || active.id);
    entry.position = percentage;
    entry.furthest = Math.max(progressPercent(entry), completed ? 100 : percentage);
    entry.done = Boolean(entry.done || completed);
    entry.updated = Date.now();
    entry.anchor = anchor ? headingId(anchor) : null;
    entry.section = section;
    entries[active.id] = entry;
    persist();
    renderSidebar();
  }

  function scheduleSave() {
    if (!active || restoring || document.body.classList.contains('slide-mode')) return;
    clearTimeout(saveTimer);
    saveTimer = setTimeout(savePosition, 220);
  }

  function restorePosition(id) {
    var entry = getEntry(id);
    if (!entry || !active || active.id !== id) return;
    var article = active.article;
    var start = absoluteTop(article);
    var end = start + article.getBoundingClientRect().height;
    var target = null;
    var heads = headingsIn(article);
    if (entry.anchor) {
      for (var i = 0; i < heads.length; i++) {
        if (headingId(heads[i]) === entry.anchor) {
          var current = absoluteTop(heads[i]);
          var next = i + 1 < heads.length ? absoluteTop(heads[i + 1]) : end;
          target = current + clamp(Number(entry.section) || 0, 0, 1) * (next - current);
          break;
        }
      }
    }
    if (target === null) {
      target = start + clamp(Number(entry.position) || 0, 0, 100) / 100 * (end - start) - window.innerHeight * 0.65;
    }
    window.scrollTo(0, Math.max(0, target));
  }

  function renderBook(article, id) {
    var entry = getEntry(id);
    if (!entry || entry.done || (Number(entry.position) || 0) < 3) return;
    var heading = article.querySelector('h1');
    if (!heading) return;
    var banner = document.createElement('div');
    banner.className = 'reader-book-resume';
    var button = document.createElement('button');
    button.type = 'button';
    button.textContent = '前回の続きから読む（' + progressPercent(entry) + '%まで到達） →';
    button.addEventListener('click', function () {
      restoring = true;
      restorePosition(id);
      requestAnimationFrame(function () { restoring = false; });
      banner.remove();
    });
    banner.appendChild(button);
    heading.insertAdjacentElement('afterend', banner);
  }

  function clearResumeParam() {
    var params = new URLSearchParams(window.location.search);
    if (!params.has('resume')) return;
    params.delete('resume');
    var query = params.toString();
    window.history.replaceState(window.history.state, '', window.location.pathname + (query ? '?' + query : '') + window.location.hash);
  }

  function onPage() {
    clearTimeout(saveTimer);
    active = null;
    var article = document.querySelector('.markdown-section');
    if (!article) return;

    var id = bookId(window.location.pathname);
    if (id) {
      active = { id: id, article: article };
      renderBook(article, id);
      if (new URLSearchParams(window.location.search).get('resume') === '1') {
        clearResumeParam();
        restoring = true;
        requestAnimationFrame(function () {
          requestAnimationFrame(function () {
            if (active && active.id === id) restorePosition(id);
            restoring = false;
          });
        });
      }
    } else {
      renderHome(article);
    }
    renderSidebar();
    // The sidebar can finish loading after the article.
    setTimeout(renderSidebar, 100);
  }

  document.addEventListener('scroll', scheduleSave, { passive: true });
  window.addEventListener('scroll', scheduleSave, { passive: true });
  window.addEventListener('pagehide', function () {
    clearTimeout(saveTimer);
    savePosition();
  });
  document.addEventListener('visibilitychange', function () {
    if (document.hidden) {
      clearTimeout(saveTimer);
      savePosition();
    }
  });
  window.$docsify.plugins.push(function (hook) {
    hook.beforeEach(function (markdown) {
      // Never attribute a freshly rendered page's scroll position to the prior book.
      clearTimeout(saveTimer);
      active = null;
      return markdown;
    });
    hook.doneEach(onPage);
  });
})();
