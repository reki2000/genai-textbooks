#!/usr/bin/env node
/*
 * 教材図版の SVG を PNG 化して目視確認するためのスクリプト。
 *
 *   node .claude/skills/yaruo-figures/scripts/render_svg.js <svg-dir> [out-dir]
 *
 * 事前に一度だけ:
 *   mkdir -p /tmp/svgshot && cd /tmp/svgshot && npm install @resvg/resvg-js
 *   # 日本語フォントが無い環境（fc-list :lang=ja が空）では文字が豆腐になる。
 *   # WSL なら: cp /mnt/c/Windows/Fonts/{YuGothR.ttc,YuGothB.ttc} ~/.local/share/fonts/ && fc-cache -f
 *
 * resvg を使うのは、rsvg-convert や headless chromium と違って
 * システム共有ライブラリ（sudo 必須）を要求しないため。
 */
const fs = require('fs');
const path = require('path');
const os = require('os');

const MODULE_DIRS = ['/tmp/svgshot/node_modules', path.join(os.homedir(), 'node_modules')];

function loadResvg() {
  for (const dir of MODULE_DIRS) {
    try {
      return require(path.join(dir, '@resvg/resvg-js'));
    } catch (e) { /* 次の候補へ */ }
  }
  try {
    return require('@resvg/resvg-js');
  } catch (e) {
    console.error('@resvg/resvg-js が見つからない。次を実行する:\n' +
      '  mkdir -p /tmp/svgshot && cd /tmp/svgshot && npm install @resvg/resvg-js');
    process.exit(1);
  }
}

const svgDir = process.argv[2];
const outDir = process.argv[3] || '/tmp/svgshot/out';
if (!svgDir) {
  console.error('usage: render_svg.js <svg-dir> [out-dir]');
  process.exit(1);
}

const { Resvg } = loadResvg();
fs.mkdirSync(outDir, { recursive: true });

const files = fs.readdirSync(svgDir).filter((f) => f.endsWith('.svg')).sort();
if (files.length === 0) {
  console.error(`SVG が無い: ${svgDir}`);
  process.exit(1);
}

for (const f of files) {
  const svg = fs.readFileSync(path.join(svgDir, f), 'utf8');
  const resvg = new Resvg(svg, {
    // 教材ページの地色と区別できるよう、カード外を中間グレーで塗る。
    // カードの縁と余白のはみ出しがこれで見える。
    background: '#8a8f94',
    fitTo: { mode: 'width', value: 1520 },  // 実寸 760 の 2 倍。文字の重なりを判定できる解像度
    font: { loadSystemFonts: true, defaultFontFamily: 'Yu Gothic' },
  });
  const out = path.join(outDir, f.replace(/\.svg$/, '.png'));
  fs.writeFileSync(out, resvg.render().asPng());
  console.log(out);
}
