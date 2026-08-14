# やる夫が位相幾何学を応用するようです 図版生成記録

- 生成手段：ChatGPT 画像生成（8枚）／`scripts/figs/topological-sensor-coverage.py` による決定的な描画（2枚）
- 生成日：2026-08-12〜08-14
- 納品ZIP：`tmp/topological-sensor-coverage-figures.zip`（受領、10枚すべて不合格）
- 修正ZIP：`tmp/topological-sensor-coverage-figures-fix-1.zip`（受領、7枚採用／3枚不合格）、`tmp/topological-sensor-coverage-figures-fix-2.zip`（受領、2枚採用／1枚不合格）
- 期待寸法：1536×1024（画像生成分）

## 配色（この教材での割り当て）

`conventions.md` の固定パレットを、この教材では次の意味に割り当てる。全10図で守る。

| 役割 | 値 | この教材での意味 |
|---|---|---|
| `MAIN` 青 | `#1f6fd0` | システムが持つ組合せ構造。通信辺、単体（三角形タイル）、複体 |
| `FOCUS` 橙 | `#e07b1f` | いま注目しているクラス。代表閉路、投入した移動センサー、最遠点 |
| `WARN` 赤 | `#cf3b2d` | 未被覆の穴、複体と現実の食い違い、閉じなかった裂け目、幻のクラス |
| `MUTED` 灰 | `#8d8d8d` | 現実の物理。監視区域、検知円盤、境界部分複体、補助線 |
| 淡い地色 | 青 `#e6eefb` / 橙 `#f6e6b8` / 赤 `#fbeae8` / 灰 `#f2f2f2` | 領域の塗り分け |

読み口は「灰＝現実にあるが座標として知り得ないもの、青＝端末データから作れるもの、赤＝その二つが食い違う場所」で全図共通。

## 方針（この教材固有）

- **当初は模式図をすべてChatGPTの画像生成で作る方針**だった（ユーザー指定）。実際には fig3・fig4 の2枚だけ3回連続で不合格になり、ユーザーの同意のもと `scripts/figs/topological-sensor-coverage.py` へ移した。残る8枚は画像生成のまま採用。
- **画像生成が通った図と通らなかった図の線引き。** 事前には「頂点数・辺数・三角形の枚数が答えになる図（fig5・fig6・fig7）が危ない」と見ていたが、そこは通った（fig6 の三角形8枚の分割は1回目から正しかった）。落ちたのは **連続量の不等式が意味を決める図** で、fig3・fig4 の配置が成り立つ条件は

      d/2 < r < d/sqrt(3)   （d = 中心間距離、r = 検知半径）

  という狭い区間であり、上端を超えた瞬間に中央の未被覆域が消えて図の意味が正反対になる。比を 0.51 と数値で与えても、絶対座標をピクセルで与えても、画像生成は3回ともこの区間を外した。**離散的な個数より、狭い区間に収める連続量のほうが画像生成には難しい。**
- 枚数：本文約31,800字に対し10枚。目安（1万字あたり3枚＝約9.5枚）どおり。
- 第4幕（境界行列の掃き出し）は**0枚**。境界行列も掃き出しの過程も本文に完全に書かれており、図から本文を復元しても本文以上の情報が出ない。均等配分しない判断。

## Phase 1

### 採用 10枚

| ID | ファイル名 | 節 | アンカー（この発言の直後） | 問い | 層 |
|---|---|---|---|---|---|
| 1 | `fig1-ring-connected-but-hole.png` | 1-1 | 「周りはぐるっとセンサーで囲まれているのに、中央だけぽっかり空いてるお。」 | 全ノードが連結でも、なぜ中央が見えていないのか | 実体 |
| 2 | `fig2-same-graph-different-shape.png` | 2-1 | 「辺の有無しかないのに、正方形の絵を描いた瞬間、存在しない90度や中心点を思い込むお。」 | 同じ近接グラフから、実際の配置は1つに決まるか | 実体 |
| 3 | `fig3-disks-and-nerve.png` | 3-1 | 「**円盤を広げる操作と、複体に面を1枚足す操作が、同じタイミングで起きる** んだお。」 | 円盤の重なりが変わると、nerveの何が変わるか | 実体＋記号 |
| 4 | `fig4-rips-triangle-vs-real-hole.png` | 3-1 | 「**通信は三角形、現実は穴**。」 | 同じ通信関係から、なぜ現実にない面ができるのか | 実体＋記号 |
| 5 | `fig5-fan-does-not-close.png` | 5-1 | 「**扇の要が、扇の全部の骨に届いてない** んだお。」 | 移動センサー1台で、なぜ扇が閉じないのか | 記号 |
| 6 | `fig6-second-sensor-closes.png` | 5-1 | 「**今度こそ消えたお**。」 | 2台目のM6は、なぜ1台目のM5とも結ばれる必要があるのか | 記号 |
| 7 | `fig7-persistence-map.png` | 6-1 | 「が、強信号から弱信号まで残った独立クラス数を表すんだお。」 | 穴の数が両側で同じでも、なぜ写像の階数を見る必要があるのか | 記号 |
| 8 | `fig8-collapse-boundary-to-point.png` | 7-1 | 「1枚欠けると面に裂け目ができ、2サイクルでなくなる。」 | 外周を1点とみなすと、4枚の面はなぜ閉じたサイクルになるのか | 記号 |
| 9 | `fig9-missing-tile-tear.png` | 7-2 | 「区域を埋める相対的な面が作れなくなったお。」 | 面が1枚欠けると、潰した後の形はどう変わるか | 記号 |
| 10 | `fig10-circumcenter-radius.png` | 8-1 | 「「複体を描いたら本当に覆えているか」を、$\rho_d$ の上限で保証してるんだお。」 | Rips三角形の内部で頂点から最も遠い点は、検知円に入るのか | 量 |

挿入位置はすべて**再発見の後**に取ってある。fig1 を「輪の中央は見えているか？」の前に置くと答えの先出しになるため、やる夫が自分で気づいた発言の直後にした。fig3 と fig4 も、やる夫が▽の空白と「通信は三角形、現実は穴」に自力で到達した後に置く。

fig3 の導入にあたり、本文 3-1 の ASCII アート（円盤3枚と ▲ の共通部分を描いた `text` フェンス）は削除する。同じ内容を fig3 の右パネルが担当し、作図規約の外にある手描き図が1つだけ残るのを避けるため。

### 却下

| 候補 | 節 | 却下理由 |
|---|---|---|
| 次数を上げた太い環（左右10台と通信しても中央は空く） | 1-1 | fig1 と同じ絵の変奏で、問いが2つになる。本文の「円環を太くしろ」で十分に復元できる |
| 312台を西側1割へ寄せた配置 | 1-2 | 「西側はセンサーだらけ、東側は空っぽ」で一意に復元できる |
| 包除原理の重なり回数 | 1-2 | 定義の図解。図が負ける情報 |
| 正方形の境界行列と掃き出し | 4-2 | 行列も階数も掃き出しの手順も本文に全部ある |
| 通信記録→複体→行列→ホモロジー→配置 の全体像 | 1-2 / 8-2 | 本文に同じ矢印の式がある。「入力→処理→出力」型の箱と矢印 |
| バーコード（`z_noise:[12,14)` と `z_major:[11,23)`） | 6-2 | 横棒2本。数値3個の棒グラフにあたる。本文から一意に復元できる |
| フィルトレーション全体を描いたバーコード | 6-2 | 本文にない閾値列とデータを持ち込むことになる |
| 相対鎖群 `C_k(K,F)=C_k(K)/C_k(F)` の商の図解 | 7-1 | fig8 の「潰す」操作がそのまま商の絵になっている。重複 |
| 挟み撃ち `R_rs ⊆ Č ⊆ R_rw` の入れ子 | 8-1 | 包含関係の列挙で、本文の式そのもの。fig10 で半径条件の実体だけを描く |

## 最終プロンプト

初回プロンプトの全文は `scripts/figs/topological-sensor-coverage-prompt.txt`。
修正プロンプトの全文は `scripts/figs/topological-sensor-coverage-prompt-fix-1.txt`。

## 検査

### 第1回（`tmp/topological-sensor-coverage-figures.zip`、2026-08-12）

ZIP検査は合格。10個のPNG、内部パスは `topological-sensor-coverage/`、CRC・PNG構造・1536×1024px すべて正常。**科学的内容の検査で10枚すべて不合格。**

| ファイル | 機械検査 | 原寸 | 360px | 本文整合 | 判定 |
|---|---|---|---|---|---|
| `fig1-ring-connected-but-hole.png` | pass | fail | fail | fail | 不合格 |
| `fig2-same-graph-different-shape.png` | pass | fail | fail | fail | 不合格 |
| `fig3-disks-and-nerve.png` | pass | fail | fail | fail | 不合格 |
| `fig4-rips-triangle-vs-real-hole.png` | pass | fail | fail | fail | 不合格 |
| `fig5-fan-does-not-close.png` | pass | fail | fail | pass | 不合格 |
| `fig6-second-sensor-closes.png` | pass | fail | fail | pass | 不合格 |
| `fig7-persistence-map.png` | pass | fail | pass | pass | 不合格 |
| `fig8-collapse-boundary-to-point.png` | pass | fail | fail | fail | 不合格 |
| `fig9-missing-tile-tear.png` | pass | fail | fail | fail | 不合格 |
| `fig10-circumcenter-radius.png` | pass | fail | pass | fail | 不合格 |

#### 不合格の内容

**幾何が本文と矛盾する（4枚）**

- `fig1`：中央の未被覆域が小さな真円として描かれ、その周囲は検知円で覆われた灰色。**被覆済みの場所に赤い未被覆の印が載っている。** 実際の未被覆域は8本の円弧で囲まれた星形。8個のセンサーが円周上に等間隔で並んでいない。
- `fig3`：右パネルの円盤中心が左パネルとずれている（半径だけを変える指定が守られていない）。3重交差域が直線の▽の輪郭として描かれ、塗られていない。左パネルの「A」「B」「C」が2枚ずつの重なり領域ではなく円盤B3の内部にある。「中央は未被覆」もB3の内部にあり、B3を指して見える。右パネルのタイトルが円盤の線と重なって読めない。
- `fig4`：左パネルの円盤の重なりが大きすぎ、中央が灰色（被覆済み）。fig1と同じ誤り。赤い未被覆域が直線の三角形。
- `fig2`：「システムが持つデータ」が正方形として描かれている。**本文がまさに「正方形の絵を描いた瞬間、存在しない90度や中心点を思い込む」と警告している箇所なので、図が本文を否定している。** 右パネルの「曲がった通路」が細長い帯になっておらず、幅広の灰色の塊。

**潰した後の形が読めない（2枚）**

- `fig8`：右の閉曲面が、大きな楕円の中に細長いレンズ形と縦線が入った図になっており、線が5本あって面が何枚に分かれているか分からない。左の中心頂点に `v5` ラベルがない。
- `fig9`：右の面が閉じたまま塗られ、赤いジグザグが面の上に載っているだけ。開口として読めず、輪郭も途切れていない。赤い線が輪郭の外へはみ出している。左の中心頂点に `v5` ラベルがない。

**位相・個数は正しいがラベルが読めない（4枚）**

- `fig5`：**右パネルの位相は完全に正しい。** 外周順序 87-91-104-118-121-109、青いスポーク4本、灰の破線2本、塗った三角形3枚、残る閉路の五角形すべて本文どおり。左パネルの中心頂点に `v5` ラベルがない。`M5` が破線と辺に重なって読めない。「弱信号のみ」が破線ではなく外周辺の近くにあり、どの線を指すか不明。
- `fig6`：**三角形8枚の分割は完全に正しい**（M5扇3枚＋M6と外周3枚＋M5の辺を挟む2枚、六角形を隙間なく充填、V−E+F=8−15+8=1）。ただしM6がM5のほぼ真下にあるため橙の2枚が針状のくさびになり三角形として読めない。`M5` `M6` が線と重なって読めない。「M5自身とも結ぶ」が橙の辺ではなく109-M6の近くにある。「M6と外周 3枚」が頂点ラベル「118」に重なる。360px幅でM5とM6が区別できない。
- `fig7`：構造は正しく、左右の頂点位置も一致している（3か所すべてオフセット一定）。クラスの輪が青い辺なしで橙だけで描かれ、配色規約（青＝組合せ構造、橙＝注目クラス）から外れている。「クラスBは消える」が塗りと対角線に重なって読めない。**10枚中もっとも惜しい。**
- `fig10`：検知円の半径比は正しい（円半径／1辺 ≈ 0.69、指定0.71）。外心は3円の内側にある。ただし橙の点が3頂点から等距離でない（上の頂点まで約0.52辺、下の頂点まで約0.60辺）。「外心」と「頂点から最も遠い点」が同じ場所に重なり、橙の破線と青い辺を横切って両方読めない。

#### 第1回の全図に共通する誤り

1. **ラベルの重なり。** 10枚すべてで、文字が線・塗り・他の文字と重なっている箇所がある。
2. **未被覆領域の描き方。** 灰色（被覆済み）の上に赤い印を載せる誤りが fig1・fig4 で発生。円弧で囲まれた領域を直線の多角形として描く誤りが fig1・fig3・fig4 で発生。
3. **中心頂点のラベル落ち。** fig5・fig8・fig9 の左パネルで中心の `v5` が欠落。
4. **指定した比・座標の不履行。** fig3 の中心位置、fig10 の外心位置。

### 第2回（`tmp/topological-sensor-coverage-figures-fix-1.zip`、2026-08-14）

ZIP検査は合格。10個のPNG、内部パス・CRC・PNG構造・1536×1024px すべて正常。**7枚合格、3枚不合格。**

| ファイル | 機械検査 | 原寸 | 360px | 本文整合 | 判定 |
|---|---|---|---|---|---|
| `fig1-ring-connected-but-hole.png` | pass | pass | pass | pass | **採用** |
| `fig2-same-graph-different-shape.png` | pass | fail | pass | fail | 不合格 |
| `fig3-disks-and-nerve.png` | pass | fail | fail | fail | 不合格 |
| `fig4-rips-triangle-vs-real-hole.png` | pass | fail | fail | pass | 不合格 |
| `fig5-fan-does-not-close.png` | pass | pass | pass | pass | **採用** |
| `fig6-second-sensor-closes.png` | pass | pass | pass | pass | **採用** |
| `fig7-persistence-map.png` | pass | pass | pass | pass | **採用** |
| `fig8-collapse-boundary-to-point.png` | pass | pass | pass | pass | **採用** |
| `fig9-missing-tile-tear.png` | pass | pass | pass | pass | **採用** |
| `fig10-circumcenter-radius.png` | pass | pass | pass | pass | **採用** |

#### 採用7枚の確認内容

- `fig1`：未被覆域が8本の円弧で囲まれた星形になり、被覆済みの上に赤を置く誤りが解消。8個のセンサーが円周上に等間隔。360pxでも赤い穴が読める。残る難：「どの検知円にも入らない」の引き出し線が通信辺3-4を横切る。
- `fig5`：右パネルの位相（外周順序、スポーク4本、破線2本、三角形3枚、残る五角形）が本文どおり。左の `v5`、右の `M5` ともラベルが読める。
- `fig6`：三角形8枚の分割（M5扇3＋M6と外周3＋M5の辺を挟む2）が正しく、$V-E+F=8-15+8=1$ と整合。M6をM5の左下へ寄せたので橙の2枚が三角形として読める。残る難：「M6」の引き出し線が頂点109の近くを通り、指す先が紛らわしい。
- `fig7`：青い辺の上に橙を重ねる配色になり規約に適合。左右の頂点位置が3か所ともオフセット一定で一致。「クラスBは消える」が図形の外へ出た。
- `fig8`：輪郭2本＋内部の実線1本・破線1本の合計4本の弧で、切れ目のない閉じた面として読める。左の `v5` あり。
- `fig9`：`fig8` と同じ座標で、欠けた区画が白く抜け、赤い縁の裂け目として読める。
- `fig10`：外心が3頂点から等距離になり、検知円の半径比も条件を満たす（円半径／1辺 ≈ 0.67 > 0.577）。2つのラベルが分離して読める。残る難：「検知円」の引き出し線が円に届かず空白で止まる。

#### 不合格3枚の理由

- `fig3`：**半径比が守られず、被覆済みの場所を未被覆と表示する誤りが再発。** 円盤半径が中心間距離の 0.73 倍（指定 0.54 倍）で描かれており、この比では3枚が共通部分を持つ＝中央は覆われている。それなのに中央に赤い未被覆域がある。左右のマスで中心位置もずれており、3重の重なりは直線の▽の輪郭で塗られていない。「A」「B」「C」が重なり領域ではなく画像の隅にある。「中央は未被覆」「3枚が重なる」が下段の nerve のすぐ上にあり、nerve を指して見える。
- `fig4`：半径比は正しくなり（0.54倍）、幾何は本文と一致した。ただし**円盤が小さく、未被覆域が360px幅で判別できない**。3枚の等半径円盤が「ペアで重なるが3重交差なし」を満たすとき、中央の穴は中心間距離のせいぜい 7.7% にしかならないという幾何学的制約があるので、円盤自体を大きく描く以外に見せる方法がない。ラベル4個がパネル下部に2行で並び、対象を指していない。
- `fig2`：上段のグラフが不規則な四角形になった点は改善。**右パネルの「曲がった通路」が、幅一定の帯ではなく丸い塊として塗りつぶされている。** 通路（道）に見えず、細長くもない。4頂点の並びと4辺の結び方は正しい。

検査コマンド：

```bash
python3 .claude/skills/zuhan/scripts/check_image_zip.py \
  tmp/topological-sensor-coverage-figures.zip \
  --id topological-sensor-coverage \
  --expect fig1-ring-connected-but-hole.png \
  --expect fig2-same-graph-different-shape.png \
  --expect fig3-disks-and-nerve.png \
  --expect fig4-rips-triangle-vs-real-hole.png \
  --expect fig5-fan-does-not-close.png \
  --expect fig6-second-sensor-closes.png \
  --expect fig7-persistence-map.png \
  --expect fig8-collapse-boundary-to-point.png \
  --expect fig9-missing-tile-tear.png \
  --expect fig10-circumcenter-radius.png \
  --width 1536 --height 1024 \
  --extract-to /tmp/zuhan-topological-sensor-coverage
```

### 第3回（`tmp/topological-sensor-coverage-figures-fix-2.zip`、2026-08-14）

ZIP検査は合格。3個のPNG、内部パス・CRC・PNG構造・1536×1024px すべて正常。**2枚合格、1枚不合格。**

| ファイル | 機械検査 | 原寸 | 360px | 本文整合 | 判定 |
|---|---|---|---|---|---|
| `fig2-same-graph-different-shape.png` | pass | pass | pass | pass | **採用** |
| `fig3-disks-and-nerve.png` | pass | fail | fail | fail | 不合格 |
| `fig4-rips-triangle-vs-real-hole.png` | pass | pass | pass | pass | **採用** |

#### 採用2枚の確認内容

- `fig2`：通路が幅一定のU字の帯になり、内側が白く抜けた。v1 と v4 が両端、v2 と v3 が底の側で、4辺の結び方も正しい。上段の抽象グラフも正方形でない四角形のまま。360pxでも3つの図が判別できる。残る難：U字の開口が帯の幅より広く、v4-v1 の辺だけ他の3辺より明らかに長い。
- `fig4`：中心間距離365px・半径185px（比 0.507）で、指定の 0.51 を満たす。外接半径211px > 半径185px なので中央に本当に穴が空き、赤い曲線三角形が幾何学的に正しい位置と形になった。360pxでも赤い印が判別できる。右パネルの赤い破線が左パネルと同じ形。残る難：「中央は未被覆」「覆われていない場所」の引き出し線が青い辺を横切る。

#### 不合格1枚の理由

- `fig3`：**被覆済みの場所を未被覆と表示する誤りが3回連続で再発。** 円盤半径が中心間距離の 0.76 倍（指定 0.51 倍）で描かれており、この比では3枚が共通部分を持つ。実際に赤く塗られた領域の中心 (375,290) は、3つの円盤中心すべてから半径以内にあり、**3枚すべてに覆われている**。それを「中央は未被覆」と表示している。左右のマスで中心位置も一致していない（左の中心間距離205px、右280px）。加えて「B1」「B2」「B3」が下付き文字で描かれており、共通仕様の禁止事項に反する。A・B・C の位置と引き出し線の処理は改善していた。
  - 同じ指示で `fig4`（2パネル）は 0.51 を守れたのに `fig3`（2行2列）は守れない。マスが小さいと円盤を大きく描こうとする傾向がある。次回は比ではなく**キャンバス上の絶対座標と半径をピクセルで指定**する。

### 第4回（`scripts/figs/topological-sensor-coverage.py`、2026-08-14）

fig3・fig4 を決定的な描画へ移した。両図は同じ3円盤配置を共有するので、片方だけコードにすると同じ配置の図が2種類の幾何で並ぶ。よって採用済みだった fig4 も作り直した（`fig4-...png` は削除）。

| ファイル | 機械検査 | 原寸 | 360px | 本文整合 | 判定 |
|---|---|---|---|---|---|
| `fig3-disks-and-nerve.svg` | pass | pass | pass | pass | **採用** |
| `fig4-rips-triangle-vs-real-hole.svg` | pass | pass | pass | pass | **採用** |

コードに移して分かったこと：

- **本文と図の向きが食い違っていた。** 本文は「中央の**▽**が空いてる」と書き、削除した ASCII アートも円盤1が上・2が右下・3が左下だった。この配置でこそ未被覆域が ▽、3枚共通部分が ▲ になる。最初に書いたコードは円盤2枚を上に置いており、両方とも上下が反転していた。`triangle()` の docstring にこの制約を書いて固定した。
- 半径比は `check_config()` が `d/2 < r < d/sqrt(3)`（未被覆域あり）と `r > d/sqrt(3)`（3枚共通部分あり）を assert する。重心が円盤に覆われているかも突き合わせるので、比を間違えると生成が止まる。
- 未被覆域と3枚共通部分の輪郭は、2円の交点と「各円のうち重心に最も近い側の弧」から計算する。どちらも同じ作図で出る（`middle_region()`）。手で三角形を置いていない。
- 2枚ずつの重なりは、透明度に頼らず**レンズ形を計算して一段濃い地色で塗った**。A・B・C のラベルが指す対象が実体として見えるようになる。

## 修正指示

- 第1回：`scripts/figs/topological-sensor-coverage-prompt-fix-1.txt`（10枚すべて再生成）。
- 第2回：`scripts/figs/topological-sensor-coverage-prompt-fix-2.txt`（fig2・fig3・fig4 の3枚のみ）。円盤の半径と中心間距離をピクセル数で固定し、「3枚の等半径円盤が2枚ずつ重なり3重交差しないとき、中央の穴は中心間距離の最大でも 7.7% にしかならない」という幾何学的事実を明示して、誇張ではなく円盤を大きく描くことで見せるよう指示した。
- 第3回：`scripts/figs/topological-sensor-coverage-prompt-fix-3.txt`（fig3 のみ）。比ではなく絶対座標と半径をピクセルで与える内容にしたが、**ChatGPTへは投入していない。** 同じ配置を3回外したことから、ユーザーの判断でこの図を決定的な描画へ移したため。記録として残す。

第1回修正版の検査コマンド：

```bash
python3 .claude/skills/zuhan/scripts/check_image_zip.py \
  tmp/topological-sensor-coverage-figures-fix-1.zip \
  --id topological-sensor-coverage \
  --expect fig1-ring-connected-but-hole.png \
  --expect fig2-same-graph-different-shape.png \
  --expect fig3-disks-and-nerve.png \
  --expect fig4-rips-triangle-vs-real-hole.png \
  --expect fig5-fan-does-not-close.png \
  --expect fig6-second-sensor-closes.png \
  --expect fig7-persistence-map.png \
  --expect fig8-collapse-boundary-to-point.png \
  --expect fig9-missing-tile-tear.png \
  --expect fig10-circumcenter-radius.png \
  --width 1536 --height 1024 \
  --extract-to /tmp/zuhan-tsc-fix-1
```

第3回修正版の検査コマンド：

```bash
python3 .claude/skills/zuhan/scripts/check_image_zip.py \
  tmp/topological-sensor-coverage-figures-fix-3.zip \
  --id topological-sensor-coverage \
  --expect fig3-disks-and-nerve.png \
  --width 1536 --height 1024 \
  --extract-to /tmp/zuhan-tsc-fix-3
```

## 本文への埋め込み状況

採用10枚は `docs/books/topological-sensor-coverage/figs/` へ置き、本文へ図番号つきで挿入済み。各図の直前の発言末尾に、その図を指す一文を足してある。

| 図番号 | ファイル | 節 |
|---|---|---|
| 図1-1 | `fig1-ring-connected-but-hole.png` | 1-1 |
| 図2-1 | `fig2-same-graph-different-shape.png` | 2-1 |
| 図3-1 | `fig3-disks-and-nerve.svg` | 3-1 |
| 図3-2 | `fig4-rips-triangle-vs-real-hole.svg` | 3-1 |
| 図5-1 | `fig5-fan-does-not-close.png` | 5-1 |
| 図5-2 | `fig6-second-sensor-closes.png` | 5-1 |
| 図6-1 | `fig7-persistence-map.png` | 6-1 |
| 図7-1 | `fig8-collapse-boundary-to-point.png` | 7-1 |
| 図7-2 | `fig9-missing-tile-tear.png` | 7-2 |
| 図8-1 | `fig10-circumcenter-radius.png` | 8-1 |

未挿入なし。3-1 の ASCII アート（円盤3枚と ▲ の共通部分を描いた `text` フェンス）は fig3 が担当するので削除した。
