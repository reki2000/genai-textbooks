---
marp: true
theme: default
paginate: true
size: 4:3
math: katex
style: |
  svg[data-marpit-svg] {
    height: auto;
    width: 100%;
    aspect-ratio: 960 / 720;
    display: block;
    margin-bottom: 12px;
  }
  section {
    font-size: 22px;
  }
---

# シュレーディンガー方程式 ── 量子力学を再発明する

- 古典物理の破綻から出発し、ボーア模型の限界を確認する
- 「何が波打っているのか」を消去法で確率振幅へ絞り込む
- 道具（複素数・演算子・固有値・ブラケット・交換子）を組んでから方程式を書く
- 満たすべき4条件が方程式の形をほぼ一意に決める

---

## 第1幕　古典物理が壊れる日

---

## 二つの破綻

**紫外破綻**

- 振動数 $\nu$ の電磁波モード数は $\nu^2$ に比例
- 古典的エネルギー等分配則を当てると高振動数でエネルギーが発散
- プランク(1900)：$E = h\nu$ の整数倍しかとれないと仮定すると実験と合う
- $h = 6.63 \times 10^{-34}$ J·s（プランク定数）

**線スペクトル**

- 水素の発光は連続でなく特定波長のみ。バルマー(1885)の規則性：

$$\frac{1}{\lambda} = R_H\left(\frac{1}{2^2} - \frac{1}{n^2}\right), \quad n = 3,4,5,\ldots$$

- $R_H \approx 1.097\times 10^7\,\text{m}^{-1}$。$n=3$ で 656 nm、$n=4$ で 486 nm

---

## 「エネルギーの最小単位」だけでは足りない

- 最小単位を入れると、とれる値が**等間隔**になるだけ
- $1/2^2 - 1/n^2$ という整数の自乗の逆数の差は出てこない
- 量子化のパッチではなく、もっと深い構造が要る

---

## ボーア模型の栄光（1913）

角運動量を量子化する：$L = mvr = n\hbar$
クーロン力＝向心力：$\dfrac{e^2}{4\pi\epsilon_0 r^2} = \dfrac{mv^2}{r}$

$v = n\hbar/(mr)$ を代入すると

$$\frac{e^2}{4\pi\epsilon_0 r^2} = \frac{n^2\hbar^2}{mr^3} \;\Longrightarrow\; r_n = \frac{4\pi\epsilon_0 n^2\hbar^2}{me^2}$$

$r_1 \approx 0.053$ nm（ボーア半径）。$E = -e^2/(8\pi\epsilon_0 r_n)$ より

$$E_n = -\frac{me^4}{2(4\pi\epsilon_0)^2\hbar^2}\cdot\frac{1}{n^2} \approx -\frac{13.6\,\text{eV}}{n^2}$$

$n=2$ を下端にとればバルマー系列を再現する。

---

## ボーア模型の挫折

- ヘリウム（電子2個）では電子間反発 $e^2/(4\pi\epsilon_0 r_{12})$ が入る
- $r_{12}$ は軌道によって変わり、3体問題となって解析的に解けない
- 反発を無視した近似：$E \approx 2\times(-13.6)\times Z^2/n^2 = -108.8$ eV
- 実験値は約 $-79.0$ eV。**30 eV のずれ**
- 根本問題：電子の「位置が確定した軌道」という記述自体が多電子系で破綻する
- 楕円軌道や相対論補正での延命も、ヘリウム以降で系統的に失敗した

→ 力学の枠組みそのものを作り直す必要がある。

**残る疑問**：間違った模型が、なぜ水素だけ小数点以下まで当たったのか（→ 6-3で回収）

---

## 第2幕　粒子は波である

---

## 波動粒子二重性とド・ブロイ関係

- 光は波（干渉・回折）でありながら、光電効果では粒子として振る舞う
- 閾値 $\nu_0$ 以下ではいくら強い光でも電子が出ない。$h\nu < W$ なら1光子で叩き出せない
- 強くしても光子の**個数**が増えるだけで、1個あたりのエネルギーは変わらない
- ド・ブロイ(1924)はこれを逆転：粒子も波動性を持つ

$$\lambda = \frac{h}{p} = \frac{h}{mv}$$

50 eV の電子：$p = \sqrt{2mE} \approx 3.82\times10^{-24}$ kg·m/s、$\lambda \approx 0.17$ nm
→ 原子間隔と同スケール。結晶が回折格子になる
→ デイヴィソン・ガーマー(1927)がニッケル結晶で回折を観測

---

## 二重スリット：1個ずつ飛ばしても干渉する

- 電子1個は、スクリーン上の**1点**に着弾する（粒子の振る舞い）
- 何万発も蓄積すると、着弾点の分布に**干渉縞**が現れる
- 古典的粒子は1経路しか通れない。媒質の振動なら2スリットを同時に通れるが1点に落ちない
- どちらのモデルも、両方を同時には説明できない

---

## 何が波打っているのか ── 二つの案の死

**案1：電荷が空間に薄く広がって波打つ**

- 広がっているなら、スクリーンの広い範囲に薄く電荷が付くはず
- 実際は1個分の電荷が1点に着弾する。半分ずつに割れない → **棄却**

**案2：確率そのものが波打つ**

- 干渉縞の暗線では合成確率が $0$。だが $P_1(x) > 0$、$P_2(x) > 0$
- **確率は非負**。非負量をいくら重ねても打ち消し合えない
- 干渉には引き算が要るが、確率に引き算はない → **棄却**

---

## 波打つ量が満たすべき条件

1. 重ね合わせると**打ち消し合える**（符号、より一般に位相を持つ）
2. その量そのものは観測されない（観測されるのは1点への着弾）
3. その量から**非負の確率**を作る手続きがある

→ 波打っているのは確率ではなく「確率のもと」
→ 干渉パターンが存在する以上、電子には**位相**がある

**残る疑問**：位相は $e^{i\theta}$ ── 複素数で記述されるのか（→ 4-1で回収）

---

## 第3幕　確率振幅への跳躍

---

## ボルンの確率解釈（1926）

- 電子の波を $\psi(x)$ と書く。$\psi$ 自体は直接観測できない
- 観測できるのは $|\psi(x)|^2$ ＝ 位置 $x$ に電子を見つける**確率密度**

**「知らないだけ」（隠れた変数）との違いは実験で出る**

スリット1・2を通る振幅を $A_1, A_2$ とすると

$$P_{\text{classical}} = |A_1|^2 + |A_2|^2, \qquad P_{\text{QM}} = |A_1 + A_2|^2 = |A_1|^2 + |A_2|^2 + 2\,\mathrm{Re}(A_1^*A_2)$$

$A_1 = A_2 = 1/\sqrt{2}$ なら $P_{\text{classical}} = 1$、$P_{\text{QM}} = 2$ で**2倍違う**
経路差が半波長なら $A_2 = -A_1$ で $P_{\text{QM}} = 0$、$P_{\text{classical}} = 1$

ベル(1964)の不等式とアスペ(1982)の実験が、隠れた変数の最も自然な形式を棄却した。

---

## 到達点

- $\psi(x)$ は**確率振幅**であり、$|\psi(x)|^2$ が確率密度
- $\psi$ は**複素数値**でなければならない（位相が干渉を生むから）
- 規格化条件：$\displaystyle\int_{-\infty}^{\infty}|\psi(x)|^2\,dx = 1$
- 「知らないだけ」ではなく、測定するまで本当に不定

**残る疑問**：位置を1点に絞り込むと、波長＝運動量はどうなるのか（→ 4-5で回収）

---

## 第4幕　道具の構築

---

## 4-1　実数の波はなぜダメか

$\psi(x,t) = \sin(kx-\omega t)$ とすると $\rho = |\psi|^2 = \sin^2(kx-\omega t)$。

- $kx - \omega t = 0, \pi, 2\pi, \ldots$ で $\rho = 0$
- 何にもぶつからない自由粒子なのに、半波長ごとに「絶対にいない点」が等間隔に並ぶ
- 空間のどこにも特別な場所がないはずなのに、特別な点が生じる
- 1点 $x_0$ を固定すると $\rho(x_0,t)$ が $0$ と $1$ を周期的に往復する。粒子が現れたり消えたりする

→ 実数の波では $|\psi|^2$ が波の振動を引きずる。**位相が確率に漏れる**。棄却。

---

## 4-1　複素数の必然性

$\psi(x,t) = e^{i(kx-\omega t)}$ とすると

$$|\psi|^2 = e^{i(kx-\omega t)}\cdot e^{-i(kx-\omega t)} = e^0 = 1$$

- 空間的にも時間的にも確率密度が一定。自由粒子として自然
- $e^{i\theta}$ は位相が回っても絶対値が動かない
- 干渉に必要な位相を $\psi$ の中に保持しながら、確率は静かにしていられる
- 規格化 $\int|\psi|^2dx = 1$ が時間で変わらないことを**ユニタリ性**という。その最も簡単な実現が $|e^{i\theta}|^2 = 1$

**回収**：干渉の位相と確率の保存、どちらも独立に複素数を要求する。

---

## 4-2　演算子 ── 物理量は「数」でなく「操作」

**位置**：$\hat{x}\,\psi(x) = x\,\psi(x)$（掛け算）

**運動量**：$p = \hbar k$ を平面波 $e^{ikx}$ から引き出す操作を探す

$$\frac{d}{dx}e^{ikx} = ik\,e^{ikx} \;\Longrightarrow\; -i\hbar\frac{d}{dx}e^{ikx} = \hbar k\,e^{ikx} = p\,e^{ikx}$$

$$\hat{p} = -i\hbar\frac{d}{dx}$$

- 素朴案「数 $mv$ を掛ける」では、波数 $k$ との関係が全く出てこない
- 波長・振動数という**波の構造は微分でしか読み取れない**

---

## 4-2　ハミルトニアン

$$\hat{T} = \frac{\hat{p}^2}{2m} = \frac{1}{2m}\left(-i\hbar\frac{d}{dx}\right)^2 = -\frac{\hbar^2}{2m}\frac{d^2}{dx^2}$$

$(-i)^2 = -1$ からマイナスが付く。ポテンシャルは $V(x)$ を掛けるだけ。

$$\hat{H} = \hat{T} + V(\hat{x}) = -\frac{\hbar^2}{2m}\frac{d^2}{dx^2} + V(x)$$

**検算**（箱、$V=0$、$\psi_n = \sqrt{2/L}\sin(n\pi x/L)$）：

$$\hat{H}\psi_n = \frac{\hbar^2}{2m}\left(\frac{n\pi}{L}\right)^2\psi_n = \frac{n^2\pi^2\hbar^2}{2mL^2}\,\psi_n$$

元の関数の定数倍が返る ── 固有値方程式。

---

## 4-3　固有値問題と測定値

$\hat{A}\psi = a\psi$ のとき $\psi$ を固有関数、$a$ を固有値と呼ぶ。

**基本原理**：物理量 $\hat{A}$ の測定値は固有値 $a$ のどれかに限られる（＝エネルギー量子化の正体）

重ね合わせ $\psi = \frac{1}{\sqrt2}(\psi_1+\psi_2)$ に $\hat H$ を作用させると $\frac{1}{\sqrt2}(E_1\psi_1 + E_2\psi_2)$。
$E_1 \neq E_2$ なら $\psi$ の定数倍でなく、**固有状態ではない**。

- **ボルンの規則**：$\psi = \sum_n c_n\psi_n$ のとき固有値 $a_n$ が出る確率は $|c_n|^2$
- $\sum_n|c_n|^2 = 1$ は規格化条件と同じ
- **期待値**：$\langle\hat{A}\rangle = \int\psi^*\hat{A}\psi\,dx$。上の例では $(E_1+E_2)/2$
- 期待値は統計的平均であり、1回の測定で得られる値ではない（出るのは $E_1$ か $E_2$）

---

## 4-4　ヒルベルト空間とブラケット記法

なぜ抽象化するか：位置表示 $\psi(x)$ も運動量表示 $\tilde\psi(p)$ も同じ物理状態を記述する。

素朴案 $\mathbb{R}^n$ が足りない理由 ── $x$ は連続変数なので基底が非可算無限個必要、かつ $\psi$ は複素数値。
→ **無限次元・複素**のベクトル空間に内積を入れた**ヒルベルト空間** $\mathcal{H} = L^2(\mathbb{R})$。

| 記号 | 名前 | 意味 |
|---|---|---|
| $\lvert\psi\rangle$ | ケット | 状態ベクトル（列ベクトル、$\psi(x)$）|
| $\langle\psi\rvert$ | ブラ | 双対ベクトル（共役転置、$\psi^*(x)$）|
| $\langle\phi\mid\psi\rangle$ | ブラケット | 内積 $\int\phi^*\psi\,dx$ |

$\langle x|\psi\rangle = \psi(x)$、$\langle p|\psi\rangle = \tilde\psi(p)$ ── 同じ抽象状態を違う基底で具象化しているだけ。
直交正規性は $\langle\psi_m|\psi_n\rangle = \delta_{mn}$ と書ける。

---

## 4-4　エルミート演算子

測定値が実数であるためには $\hat{A} = \hat{A}^\dagger$（$\langle\phi|\hat{A}\psi\rangle = \langle\hat{A}^\dagger\phi|\psi\rangle$）が要る。

1. 固有値は全て実数（→ 測定値が実数）
2. 異なる固有値の固有関数は直交（→ 正規直交基底が作れる）

$\hat{p}$ の検証：

$$\langle\phi|\hat p\psi\rangle = -i\hbar\int\phi^*\frac{\partial\psi}{\partial x}dx = -i\hbar\left(\Big[\phi^*\psi\Big]_{-\infty}^{\infty} - \int\frac{\partial\phi^*}{\partial x}\psi\,dx\right)$$

規格化可能なら $|x|\to\infty$ で $\psi,\phi\to 0$ なので境界項は消え

$$= \int\left(-i\hbar\frac{\partial\phi}{\partial x}\right)^{*}\psi\,dx = \langle\hat p\phi|\psi\rangle$$

$\partial_x$ 単独は部分積分で符号が反転して**反**エルミート。$-i\hbar$ を掛けることで複素共役の符号反転と相殺する。$\hat p$ の $i$ は趣味ではなく、測定値を実数にするための要請。

---

## 4-5　交換子と不確定性原理

$$[\hat{A},\hat{B}] = \hat{A}\hat{B} - \hat{B}\hat{A}$$

$$\hat x\hat p\psi = -i\hbar x\psi', \qquad \hat p\hat x\psi = -i\hbar(\psi + x\psi')$$

$$[\hat{x},\hat{p}]\psi = -i\hbar x\psi' + i\hbar\psi + i\hbar x\psi' = i\hbar\psi \;\Longrightarrow\; [\hat{x},\hat{p}] = i\hbar \neq 0$$

ロバートソンの不等式 $\Delta A\cdot\Delta B \geq \frac12\left|\langle[\hat A,\hat B]\rangle\right|$ に代入して

$$\Delta x\cdot\Delta p \geq \frac{\hbar}{2}$$

**回収**：$\Delta x \to 0$ なら $\Delta p \to \infty$。局在した波束をフーリエ変換すると全運動量成分が混ざる。
逆に $[\hat A,\hat B] = 0$ なら下限がゼロで同時固有状態が存在する。自由粒子では $[\hat H,\hat p] = 0$ なので、平面波 $e^{ikx}$ が両方の固有状態になる。

---

## 道具の総括

1. **波動関数**は複素数値（位相回転でユニタリ性を保つ）
2. **物理量**はエルミート演算子（固有値が実数、固有関数が正規直交）
3. **測定値**は固有値で、確率は展開係数の絶対値2乗（ボルンの規則）
4. **ブラケット**で表示に依存しない抽象記述ができる
5. **交換子**が非ゼロの物理量対は同時に確定値をとれない

---

## 第5幕　方程式を書き下す

---

## 満たすべき4条件

1. **線形性** ── $\Psi_1,\Psi_2$ が解なら $c_1\Psi_1 + c_2\Psi_2$ も解。干渉（振幅の重ね合わせ）が要求する
2. **時間について1階微分** ── $\Psi(x,t_0)$ だけで未来が一意に決まるべき。波動関数だけで状態が完全に記述されるから
3. **ド・ブロイ関係との整合** ── 平面波が解で $E = \hbar\omega = \hbar^2k^2/(2m)$ を再現する
4. **確率保存** ── $\int|\Psi|^2dx = 1$ が時間で変わらない（ユニタリ性）

---

## 候補A：波動方程式 ── 棄却

$$\frac{\partial^2\Psi}{\partial t^2} = v^2\frac{\partial^2\Psi}{\partial x^2}$$

平面波 $e^{i(kx-\omega t)}$ を代入：左辺 $=-\omega^2\Psi$、右辺 $=-v^2k^2\Psi$ → $\omega = vk$

- 分散関係が線形。$E \propto p$ は光の関係
- 非相対論的粒子には $E = p^2/(2m)$、つまり $\omega \propto k^2$ が必要 → **条件3に違反**
- 時間2階微分なので初期条件に $\Psi$ と $\partial\Psi/\partial t$ の2つが要る → **条件2にも違反**

---

## 候補B：拡散方程式 ── 棄却

$$\frac{\partial\Psi}{\partial t} = D\frac{\partial^2\Psi}{\partial x^2} \quad (D\ \text{は実数})$$

平面波代入：左辺 $=-i\omega\Psi$、右辺 $=-Dk^2\Psi$ → $\omega = iDk^2$（純虚数）

$$\Psi = e^{ikx}e^{-i(iDk^2)t} = e^{ikx}e^{Dk^2t}$$

$D<0$ なら $e^{-|D|k^2t}$ で指数減衰し、$\int|\Psi|^2dx$ が減っていく → **条件4に違反**

拡散方程式は熱が平衡へ向かう不可逆過程の方程式。量子力学の時間発展は可逆（ユニタリ）でなければならない。

---

## 候補C：$i$ を入れる

$\omega$ が虚数になるのが原因なら、$D$ を純虚数にすればよい。$D = i\alpha$ とおくと

$$\frac{\partial\Psi}{\partial t} = i\alpha\frac{\partial^2\Psi}{\partial x^2} \;\Longrightarrow\; -i\omega = -i\alpha k^2 \;\Longrightarrow\; \omega = \alpha k^2 \ (\text{実数})$$

条件3より $E = \hbar\omega = \hbar\alpha k^2$ を $E = \hbar^2k^2/(2m)$ と比較して $\alpha = \hbar/(2m)$。

$$\frac{\partial\Psi}{\partial t} = \frac{i\hbar}{2m}\frac{\partial^2\Psi}{\partial x^2} \;\Longrightarrow\; i\hbar\frac{\partial\Psi}{\partial t} = -\frac{\hbar^2}{2m}\frac{\partial^2\Psi}{\partial x^2}$$

右辺は $\hat p^2/(2m) = \hat T$、自由粒子のハミルトニアン。

---

## 確率保存の確認

$$\frac{d}{dt}\int|\Psi|^2dx = \int\left(\frac{\partial\Psi^*}{\partial t}\Psi + \Psi^*\frac{\partial\Psi}{\partial t}\right)dx$$

方程式とその複素共役を代入して

$$= \frac{i\hbar}{2m}\int\left(-\frac{\partial^2\Psi^*}{\partial x^2}\Psi + \Psi^*\frac{\partial^2\Psi}{\partial x^2}\right)dx$$

部分積分を2回。境界項は $\Psi\to 0$（$x\to\pm\infty$）で消え、被積分関数が打ち消し合って $= 0$。

これは 4-4 で $\hat p$ のエルミート性を確かめたときと**同じ部分積分**で、境界項が消える条件も同じ。
$\hat p$ のエルミート性と確率保存は、「規格化可能な波動関数は無限遠でゼロ」という一点に乗った同じ性質の別の顔。

---

## 時間依存シュレーディンガー方程式

ポテンシャルを含めて

$$i\hbar\frac{\partial\Psi}{\partial t} = \hat{H}\Psi = \left[-\frac{\hbar^2}{2m}\frac{\partial^2}{\partial x^2} + V(x)\right]\Psi$$

- 左辺は状態の時間変化率、右辺は全エネルギー演算子の作用
- 一文でいえば「**ハミルトニアンが波動関数の時間発展を決める**」
- $i$ が位相回転を保証し、確率を保存する
- 4条件がこの形をほぼ一意に決めた

シュレーディンガー自身(1926)は「量子化＝固有値問題」として、ド・ブロイ波を古典力学の変分原理に載せる道筋で到達した。順序は違うが着地点は同じ。

---

## 5-4　時間非依存シュレーディンガー方程式

変数分離 $\Psi(x,t) = \psi(x)T(t)$ を代入し、両辺を $\psi T$ で割る：

$$i\hbar\frac{T'(t)}{T(t)} = \frac{\hat{H}\psi(x)}{\psi(x)}$$

左辺は $t$ のみ、右辺は $x$ のみの関数。等しいなら両辺とも定数 $E$：

$$T(t) = e^{-iEt/\hbar}\ (\text{位相回転}), \qquad \hat{H}\psi = E\psi$$

後者がハミルトニアンの固有値方程式そのもの。一般解は

$$\Psi(x,t) = \sum_n c_n\,\psi_n(x)\,e^{-iE_nt/\hbar}$$

各固有状態が独立に位相回転する。異なるエネルギーの重ね合わせでは $|\Psi|^2$ が干渉項で時間変化する（量子ビート）。

---

## 第6幕　検証と見晴らし

---

## 6-1　箱の中の粒子

$V=0$（$0<x<L$）、外は $V=\infty$。$k^2 = 2mE/\hbar^2$ とおくと $\psi'' = -k^2\psi$。

一般解 $\psi = A\sin kx + B\cos kx$、境界条件 $\psi(0)=0$ より $B=0$、$\psi(L)=0$ より $kL = n\pi$。

$$E_n = \frac{n^2\pi^2\hbar^2}{2mL^2}, \qquad \psi_n(x) = \sqrt{\frac{2}{L}}\sin\!\left(\frac{n\pi x}{L}\right)$$

- **零点エネルギー**：$n=0$ では $\psi=0$（粒子なし）なので $n\geq 1$、$E_1 > 0$
  閉じ込めで $\Delta x \leq L$ → $\Delta p \geq \hbar/(2L)$ → 運動エネルギーが残る。不確定性原理と整合
- **対応原理**：$E_{n+1}/E_n = (n+1)^2/n^2 \to 1$。高い準位ほど古典的な連続スペクトルに近づく

---

## 6-2　調和振動子 ── 代数的解法

$V = \frac12 m\omega^2x^2$。昇降演算子を定義する：

$$\hat a = \sqrt{\frac{m\omega}{2\hbar}}\left(\hat x + \frac{i\hat p}{m\omega}\right), \qquad \hat a^\dagger = \sqrt{\frac{m\omega}{2\hbar}}\left(\hat x - \frac{i\hat p}{m\omega}\right)$$

$[\hat x,\hat x] = [\hat p,\hat p] = 0$ より交差項だけが残り、$[\hat x,\hat p] = i\hbar$ を使うと

$$[\hat a,\hat a^\dagger] = \frac{m\omega}{2\hbar}\cdot\frac{-2i}{m\omega}\cdot i\hbar = 1$$

---

## 6-2　代数だけで全固有値が出る

$\hat H = \hbar\omega\left(\hat a^\dagger\hat a + \frac12\right)$、数演算子 $\hat N = \hat a^\dagger\hat a$、$\hat N|n\rangle = n|n\rangle$。

$$\hat N(\hat a|n\rangle) = \hat a(\hat a^\dagger\hat a - 1)|n\rangle = (n-1)(\hat a|n\rangle)$$

$\hat a|n\rangle \propto |n-1\rangle$（1段下げる）、同様に $\hat a^\dagger|n\rangle \propto |n+1\rangle$（1段上げる）。
最低状態では $\hat a|0\rangle = 0$ より $E_0 = \hbar\omega/2 > 0$（零点エネルギー再び）。

$$E_n = \hbar\omega\left(n + \frac12\right), \quad n = 0,1,2,\ldots$$

微分方程式を一切解かず、$[\hat a,\hat a^\dagger] = 1$ という代数関係だけで等間隔 $\Delta E = \hbar\omega$ が出た。
$\hat a^\dagger$ は場の量子論で「光子を1個生成する」演算子になる。

---

## 6-3　水素原子

$V(r) = -e^2/(4\pi\epsilon_0 r)$ は球対称。球座標で変数分離して $\psi_{nlm} = R_{nl}(r)\,Y_l^m(\theta,\phi)$。

| 量子数 | 範囲 | 物理的意味 |
|---|---|---|
| $n$（主）| $1,2,3,\ldots$ | エネルギー $E_n = -13.6/n^2$ eV |
| $l$（方位）| $0,1,\ldots,n{-}1$ | 角運動量の大きさ $L = \hbar\sqrt{l(l+1)}$ |
| $m$（磁気）| $-l,\ldots,+l$ | 角運動量の $z$ 成分 $L_z = m\hbar$ |

$Y_l^m$ は球面調和関数。節面の数は $l$ に等しい。

- $l=0$：$Y_0^0 = 1/\sqrt{4\pi}$（定数）→ **s軌道**（球対称）
- $l=1$：$Y_1^0 \propto \cos\theta$、$Y_1^{\pm1} \propto \sin\theta\,e^{\pm i\phi}$ → **p軌道**（ダンベル型）
- $l=2$ → **d軌道**（四つ葉型）

---

## ボーア模型はなぜ水素だけ当たったのか

- ボーアは $L = n\hbar$ と仮定したが、正しくは $L = \hbar\sqrt{l(l+1)}$、$l = 0,\ldots,n-1$
- **$l=0$（s軌道）は角運動量ゼロ**で円軌道では記述できない。ボーアはこれを見逃していた
- それでもエネルギーが一致したのは、水素では $E_n$ が $l$ に依存しない（**縮退**）から
- ヘリウムでは電子間反発がこの縮退を破り、$l$ の情報が効いてボーア模型では扱えなくなる

**ボーアの成功は縮退による偶然の一致だった。**

---

## 6-4　混成軌道は固有解ではない

$sp^2$ 混成軌道は SE の固有解ではなく、人間が手で固有解を線形結合した近似。
分子（原子が複数）では厳密解が得られないため、方向性のある基底を作る。

$$|sp^2_1\rangle = \tfrac{1}{\sqrt3}|s\rangle + \sqrt{\tfrac23}|p_x\rangle, \quad
|sp^2_{2,3}\rangle = \tfrac{1}{\sqrt3}|s\rangle - \tfrac{1}{\sqrt6}|p_x\rangle \pm \tfrac{1}{\sqrt2}|p_y\rangle$$

直交性の検算（$|s\rangle,|p_x\rangle,|p_y\rangle$ は正規直交）：

$$\langle sp^2_1|sp^2_2\rangle = \frac13 - \frac{\sqrt2}{\sqrt{18}} = \frac13 - \frac13 = 0$$

$\{|s\rangle,|p_x\rangle,|p_y\rangle\}$ からのユニタリ変換＝基底の取り直しであって、新しい物理ではない。
3つの軌道は120°間隔で3方向を向き、ベンゼン環の平面構造とグラフェンの六角格子の起源となる。

---

## 全行程の振り返り

1. 古典物理の破綻とボーア模型の限界 → 力学そのものの再構築が要る
2. ド・ブロイ関係 $\lambda = h/p$。ただし何が波打つかは未定
3. 波動関数は確率振幅。$|\psi|^2$ が確率密度。干渉が「知らないだけ」を否定する
4. 道具5つ：複素数（ユニタリ性）、演算子（微分）、固有値（測定値）、ブラケット（抽象記法）、交換子（不確定性）
5. 4条件で候補を棄却し、$i\hbar\,\partial_t\Psi = \hat H\Psi$ にほぼ一意に到達
6. 箱・調和振動子・水素で検証。ボーア模型の偶然の成功も説明された

要所はいずれも「うまくいかない」地点だった ── 実数の棄却が複素数の必然性へ、演算子の順序依存が不確定性原理へ、候補の棄却が方程式の一意性へつながった。

---

## この先の地図

扱ったのは**1粒子・非相対論的**なシュレーディンガー方程式。ここから先には：

- **多粒子系** ── パウリの排他律、スレーター行列式
- **スピン** ── 軌道の波動関数からは出てこない内部自由度。非相対論の枠内ではパウリ方程式として外挿的に導入し、ディラック方程式では要請せずとも自然に現れる
- **場の量子論** ── 粒子の生成と消滅。調和振動子の $\hat a^\dagger$ がここで本領を発揮する

どれもヒルベルト空間・演算子・固有値・交換子という同じ土台の上に立つ。
