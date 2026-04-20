# Whitelist Audit — 10 Golden V&V Cases

**Document type:** V&V knowledge-layer audit report
**Scope:** `knowledge/whitelist.yaml` (10 冷启动白名单基准案例)
**Method:** 交叉核对原始文献 + `knowledge/corrections/` 历史偏差记录 (100+ 条) + 物理合理性审查
**Author:** Cowork agent, 2026-04-20
**Governance:** autonomous turf (docs/). 本文档**不修改** `knowledge/gold_standards/` 或 `knowledge/whitelist.yaml` — 所有 gold-value 改动需走外部 gate (DEC-V61-003 禁区条款)
**Status:** Draft v1 — 供外部 gate 包 (Q-new: whitelist remediation) 作为输入

---

## 1. Executive Summary

dashboard 显示 10 个 case 里 **0 PASS / 2 HAZARD / 1 FAIL / 7 NO RUN**。这个结果背后是**三类独立缺陷**同时存在,不能混为一谈:

| 缺陷类别 | 涉及 case 数 | 修复路径 |
|---|---|---|
| **A. 元数据内部自相矛盾** (Re 与湍流模型不匹配、参数与 gold 注释冲突) | 4 | autonomous turf — 可直接在 whitelist 层修 |
| **B. Gold-standard 数值有误** (与原始论文或基本物理定律不符) | 5 | **外部 gate** — 需走 Q-new: whitelist remediation |
| **C. Harness 基础设施 bug** (comparator schema / parameter plumbing / sample config) | 7 (重叠) | autonomous turf — 在 `src/` 里修,但需新增测试 |

其中 C 类是 `knowledge/corrections/` 历史上**反复出现**的:`sample_config_mismatch` ×28、`comparator_schema_mismatch` ×14、`parameter_plumbing_mismatch` ×12、`boundary_condition` ×6。这些不是单次运行的偶然偏差,是**结构性**的管线错误。

关键发现:**当前 3 个 HAZARD/FAIL 的 case 即便把 gold 数字改对也不会 PASS,因为 solver 的实际输出偏差幅度是 90-347% 量级,远超任何合理 tolerance**。修 gold 只是让 gate queue 减少噪音;要真 PASS 必须先治 C 类。

## 2. 分类与缺陷矩阵

| # | Case | Re/Ra | 湍流模型 | A (元数据) | B (Gold) | C (Infra) | Dashboard 状态 |
|---|------|-------|---------|-----------|----------|-----------|---------------|
| 1 | Lid-Driven Cavity | 100 | laminar | — | ✗ 严重 | ✗ sample_config | NO RUN (corrections 史: 15 次 QUANTITY_DEVIATION) |
| 2 | Backward-Facing Step | 7600 | k-epsilon | — | — (待核) | ✗ geometry_model | NO RUN |
| 3 | Circular Cylinder Wake | 100 | k-omega SST | ✗ 严重 | — | ✗ sample_config | HAZARD |
| 4 | Turbulent Flat Plate | 50000 | k-omega SST | ✗ | ✗ | ✗ comparator | HAZARD |
| 5 | Fully Developed Pipe | 50000 | k-epsilon | — | ✗ | ✗ comparator | NO RUN |
| 6 | Differential Heated Cavity | Ra=1e10 | k-omega SST | — | ✗ 严重 | ✗ parameter_plumbing | FAIL |
| 7 | Plane Channel Flow (DNS) | Re_τ=180 | laminar (DNS) | — | — | ✗ comparator | NO RUN |
| 8 | Axisymmetric Impinging Jet | 10000 | k-omega SST | — | — (待核) | ✗ boundary_condition | NO RUN |
| 9 | NACA 0012 Airfoil | 3×10⁶ | k-omega SST | — | ✗ | ✗ sample_config | NO RUN |
| 10 | Rayleigh-Bénard Convection | Ra=1e6 | k-omega SST | ✗ | — (核准) | ✗ parameter_plumbing | NO RUN |

---

## 3. Per-Case Audit

### 3.1 Lid-Driven Cavity (Re=100, laminar)

**whitelist 声明:** 参考 Ghia et al. 1982 (DOI 10.1016/0021-9991(82)90058-4),Re=100,沿垂直中线 u 速度。

**Gold 参考值:**
```
y=0.0625, u=-0.03717
y=0.1250, u=-0.04192
y=0.5000, u= 0.02526
y=0.7500, u= 0.33304
y=1.0000, u= 1.00000
```

**审计发现:**

- **(B-严重) Re 与 gold 值不符**。Ghia 1982 Table I 中:
  - Re=100 在 y=0.5 处 u ≈ **-0.06205**(非正值)
  - Re=1000 在 y=0.0547 处 u = **-0.03717**、y=0.1094 处 u = **-0.04192**
  - 前两行 (y=0.0625, y=0.125) 的 u 数值 **恰好是 Ghia Re=1000 的数值**,但 y 坐标不对且 Re label 标为 100
  - y=0.5 处 u=+0.02526 **符号与任何 Re 下的 Ghia 表都不符**(层流腔体中线 u 应为负)
  - y=0.75 处 u=0.33304 不在 Ghia 任何 Re 值附近
  - **结论**:gold 表是**多个 Re 的 Ghia 值混杂 + 部分数值可能人工编造**。严重污染。

- **(C) 历史偏差 (最近一次 20260415T063238)**:
  - y=0.5 期望 0.02526,实测 -0.0624,rel_err = **346.8%**
  - y=0.75 期望 0.33304,实测 -0.086,rel_err = **125.9%**
  - 所有 5 个点都失败
  - 自动归因:`sample_config_mismatch`,impact_scope=CLASS
  - **观察**:实测的负值实际上更接近 Ghia Re=100 的物理解。这反证了 **solver 大概率正在正确求解 Re=100 层流腔体,而 gold 是错的**。

- **(C-次要) Sampling 坐标**。whitelist 使用均匀 y 网格 (0.0625, 0.125, 0.5, 0.75, 1.0),与 Ghia 的非均匀网格 (0.0547, 0.0625, 0.0703, 0.1016, 0.1094 ...) 错位。对比器要么做线性插值,要么精确命中,当前 schema 不清楚。

**建议(外部 gate)**:用 Ghia 1982 Table I 的 Re=100 列,按原表 y 坐标替换整个 gold 块。若保留均匀 y 坐标,需要从论文的图 3 数字化或引用后续如 Botella & Peyret 1998 的谱方法解。

---

### 3.2 Backward-Facing Step (Re=7600, k-epsilon)

**whitelist 声明:** Driver & Seegmiller 1985,Re=7600,膨胀比 1.125,再附长度 Xr/H = 6.26,tolerance 10%。

**审计发现:**

- **(元数据)** 参数合理。Driver-Seegmiller 原始 Re 是**基于台阶高度**的 36000,但许多后续研究用基于入口动量厚度的 Re≈7600,这个 label 不是 bug 只是表达口径差异——应在 whitelist 的 `reference` 字段补注明 "Re based on momentum thickness"。
- **(C)** `knowledge/corrections/` 存在 5 次 `GEOMETRY_MODEL_MISMATCH` 和 3 次 `COMPARATOR_SCHEMA_MISMATCH`。推测是 reattachment_length 的定位算法(从 wall shear 转号点检测)在粗网格下不稳定,且 comparator 字段名可能是 `reattachment_length` vs `Xr_over_H`。
- **(B)** 6.26 是 Driver-Seegmiller 的标定值,但**膨胀比 1.125 下典型值是 6.0-6.26**;不同后续数值研究给出 5.7-6.4 的散度。tolerance 10% 合理。
- **Verdict:** 元数据和 gold 基本可信,问题在 C 类 infra。

---

### 3.3 Circular Cylinder Wake (Re=100, **k-omega SST**) ← 物理选择错误

**whitelist 声明:** Williamson 1996,Re=100,瞬态,k-omega SST。gold St = 0.165 (tol 5%)。

**审计发现:**

- **(A-严重) 湍流模型选择与物理不符**。Re=100 圆柱绕流是**层流**的周期性 von Kármán 涡脱落(湍流化在 Re≈200-250 开始)。在层流区域使用 k-omega SST 会:
  - 强行引入不存在的湍流粘度
  - 使 St 偏低(通常 0.14-0.16 范围)
  - 产生非物理的尺度化耗散
- **(Gold)** St = 0.165 实际上是 Williamson (1996) 对 Re=100 的实验/DNS 拟合值(`St = -3.3265/Re + 0.1816 + 1.6×10⁻⁴·Re`,在 Re=100 给 St=0.164)。gold 值本身对。
- **(C)** corrections 里有 1 次 `QUANTITY_DEVIATION`,时间较早。
- **Verdict:** **A 类问题**。应把 `turbulence_model: k-omega SST` 改为 `laminar`,solver 从 pimpleFoam 保留(瞬态),或改 icoFoam。这是 autonomous turf 内可修的——whitelist 的 `turbulence_model` 字段不是 gold_standards 禁区。

**建议(autonomous)**:
```yaml
turbulence_model: laminar  # Re=100 is below turbulent transition (~Re=200)
solver: pimpleFoam  # (unchanged — transient)
```

---

### 3.4 Turbulent Flat Plate ZPG (Re=50000, k-omega SST)

**whitelist 声明:**
```yaml
Re: 50000
plate_length: 1.0
gold:
  x=0.5, Cf=0.0076   # description 注释: "x_physical=0.5m, Re_x=25000"
  x=1.0, Cf=0.0061
```

**审计发现:**

- **(A-严重) 参数与 gold 内部自相矛盾**。
  - 如果 plate_length=1.0m 是全板长度,入口 Re=50000 意味着 U·L/ν = 50000,即在 x=1.0 时 Re_x=50000。那么 x=0.5 时 Re_x=25000。
  - Re_x=25000 **远低于湍流转捩** (通常自然转捩发生在 Re_x ≈ 5×10⁵,trip 可提前到 ~10⁵)。
  - description 注释 `"Cf = 0.0576/Re_x^0.2 (Spalding)"` 是**湍流**摩擦律。
  - Spalding 在 Re_x=25000 给 Cf = 0.0576/25000^0.2 = **0.0076** ✓ 数字匹配 whitelist
  - 但 **在 Re_x=25000 实际上 Blasius 层流律才对**:Cf_Blasius = 0.664/√Re_x = 0.664/√25000 = **0.0042**
  - whitelist 在层流区域套用湍流相关,结果 Cf 偏高约 80%
- **(B) Gold 值口径错误**。若要保留"湍流"标签,Re 需要至少 3×10⁶(典型 NASA 验证网格),plate_length 保持 1.0 但 ν 调低。否则应改为层流 Blasius。
- **(C)** corrections 有 11 次 `QUANTITY_DEVIATION` + 1 次 `COMPARATOR_SCHEMA_MISMATCH`。
- **Verdict:** **A + B 复合**。最干净的修法是**把 Re 提到 3×10⁶**(NASA TMR turbulent flat plate 标准值),保持 Spalding 湍流 Cf 对照。这是 **B 类**改动(gold_standards 禁区),需外部 gate。

---

### 3.5 Fully Developed Turbulent Pipe (Re=50000, k-epsilon)

**whitelist 声明:** Nikuradse/Moody,Re=50000,D=0.1m,gold Darcy 摩擦因子 f=0.0185 (tol 8%)。

**审计发现:**

- **(B) Gold 值偏低**。Blasius 相关 Darcy 式 f = 0.316/Re^0.25,在 Re=50000 给 **f=0.0211**。whitelist 的 0.0185 与 Blasius 差 **12.3%**,超出 8% tolerance。两种可能:
  - (a) 值来自 Moody 图读数(精度有限)
  - (b) 使用 Fanning 口径转换时出错(Fanning = Darcy/4)
  - 最佳做法:gold 直接用解析式 `f_expected = 0.316 / Re^0.25`(runtime 计算而非 hardcode),tolerance 降至 5%。
- **(C)** corrections 里有 **4 次 `COMPARATOR_SCHEMA_MISMATCH`**——评判器找不到 `friction_factor` 字段。evidence: `Quantity 'friction_factor' not found in execution result`。这是结构性 bug,需要在 `src/v_and_v/comparator.py` 加字段 fallback/alias 表。
- **Verdict:** **B + C**。B 改 gold (外部 gate),C 可 autonomous 修。

---

### 3.6 Differential Heated Cavity Natural Convection (Ra=1e10, k-omega SST)

**whitelist 声明:** Ampofo & Karayiannis 2003,Ra=1×10¹⁰,Pr=0.71,gold Nu=30 (tol 15%)。

**审计发现:**

- **(B-严重) Gold Nu 值与基本尺度律差一个数量级**。
  - 方腔自然对流的 Churchill-Chu 相关:Nu ≈ 0.15·Ra^(1/3) for Ra > 10⁹,turbulent。Ra=1e10 给 **Nu ≈ 325**。
  - 更保守的 MacGregor-Emery 相关 Nu = 0.046·Ra^(1/3):在 Ra=1e10 给 **Nu ≈ 100**。
  - Ampofo-Karayiannis 原始实验是 **Ra=1.58×10⁹**(不是 1e10),Nu ≈ 62。
  - whitelist 的 Nu=30 既不是 Ra=1.58e9 的值,也不是 Ra=1e10 的尺度律估计。来源不明。
- **(C) Parameter plumbing 证据**。corrections 历史最近 6 次全是 `PARAMETER_PLUMBING_MISMATCH`——`Ra=1e10 未被正确传递到 solver`。solver 实际运行的 Ra 很可能是默认值(比如 1e3 或 1e5),所以 Nu 实测只有 3.0(即自然对流几乎没启动)。
- 叠加效应:**gold 错了 一个数量级 × solver 参数也错 → 实测 Nu=3 vs 期望 Nu=30,差 90%,但两边都偏离真实物理**。即便 infra 修好 solver 跑出 Nu≈200+,它会和当前 gold=30 差 7 倍,触发更严重的 FAIL。
- **Verdict:** **B + C 严重叠加**。必须两边一起修,否则任何一边的修复都会让 contract 更糟。

---

### 3.7 Plane Channel Flow DNS (Re_τ=180, "laminar")

**whitelist 声明:** Kim 1987 / Moser 1999 DNS,Re_τ=180,gold u+(y+) 剖面:(0,0), (5, 5.4), (30, 14.5), (100, 22.8),tol 5%。

**审计发现:**

- **(A) `turbulence_model: laminar` 语义澄清**。DNS 意味着"直接数值模拟,不做任何封闭"——在 OpenFOAM 语境里就是用不带湍流模型的求解器 (如 pisoFoam, icoFoam) 加上足够细的网格。whitelist 标 "laminar" 是 **OpenFOAM 的约定**,表意正确,但对外部读者有误导。应在 `reference` 字段加一行:`"DNS: no turbulence closure; resolved scales at Re_tau=180"`。
- **(Gold)** Moser 1999 Re_τ=180 经典值在标准 y+ 采样点:
  - y+=5.0: u+ ≈ 4.97(whitelist 5.4,偏高 8%)
  - y+=30: u+ ≈ 13.6(whitelist 14.5,偏高 6.6%)
  - y+=100: u+ ≈ 18.3(whitelist 22.8,偏高 **25%**)
  - y+=100 的 Moser 值来自 log-law 区 `u+ ≈ (1/0.4)·ln(y+) + 5.5 ≈ 17.0`;whitelist 22.8 不符合标准 log-law,可能是从图中误读。
- **(C)** corrections 有 **7 次 `COMPARATOR_SCHEMA_MISMATCH`**。字段 `u_mean_profile` 可能被 solver 吐成 `U_mean_y` 或类似。
- **Verdict:** 元数据语义 OK(只需注释),gold y+=100 点值需复核 — **B 类**,外部 gate。

---

### 3.8 Axisymmetric Impinging Jet Re=10000 (k-omega SST)

**whitelist 声明:** Cooper 1984,Re=10000,H/D=2,gold 局部 Nu:(r/D=0, Nu=25), (r/D=1, Nu=12),tol 15%。

**审计发现:**

- **(Gold)** Cooper-Lockwood 的 H/D=2、Re=10000 在停滞点 Nu_stagnation ≈ 25-30,**whitelist 值合理**。r/D=1.0 处 Nu 会下降到 12-15 区间,也合理。
- **(C-严重)** corrections **15+ 次** `QUANTITY_DEVIATION` + 3 次 `COMPARATOR_SCHEMA_MISMATCH`。最近一次 (20260416T043643):`expected=25, actual=0.146, rel_err=99.4%`。实测 Nu≈0 意味着**冲击板根本没有被加热或者温度边界条件设错了**——这是 boundary_condition 根因。
- 这个 case 是 "gold 对 / 元数据对 / infra 烂" 的纯净例子。
- **Verdict:** 纯 **C 类**。autonomous 修——检查 `src/case_builder/impinging_jet_template.py` 的 T 边界条件。

---

### 3.9 NACA 0012 Airfoil External (Re=3×10⁶, k-omega SST, α=0°)

**whitelist 声明:** Thomas 1979,Re=3×10⁶,α=0°,gold Cp:(x/c=0, Cp=1.0), (x/c=0.3, Cp=-0.5), (x/c=1.0, Cp=0.2),tol 20%。

**审计发现:**

- **(B) Gold 值有问题**。
  - `x/c=0, Cp=1.0` ✓ 驻点 Cp=1 是精确值(伯努利),正确。
  - `x/c=0.3, Cp=-0.5` ✓ NACA 0012 α=0° 中部吸力峰在这附近,Cp≈-0.5 合理。
  - **`x/c=1.0, Cp=0.2` ✗** 对称翼型零攻角,**尾缘 Cp 应接近 0**(可能 0.1 附近表达粘性尾流闭合)。Cp=0.2 在实验上和无粘理论都偏高。AGARD AR-138 NACA 0012 α=0° 尾缘 Cp ≈ 0.15,属临界值;Thomas 1979 原始数据可能给了更低。
- **(C)** 最近 2 次 corrections 记录:NACA case 有 **9KB** 的大 deviation 文件(非常详细 Cp(x) 剖面 × 2 条,共 170+ 点)。自动归因 `sample_config_mismatch`:executor 吐 `pressure_coefficient_x` + `pressure_coefficient` 数组,但 gold 用键式 `pressure_coefficient[x_over_c=0.0000]`。evidence:
  - x/c=0.0 期望 1.0,实测 **0.579**,rel_err 42%
  - x/c=0.3 期望 -0.5,实测 **-0.339**,rel_err 32%
  - x/c=1.0 期望 0.2,实测 **0.110**,rel_err 45%
- **关键观察**:实测 Cp(x/c=1)=0.110 **反而更接近真实物理**(尾缘 Cp ≈ 0.1-0.15 范围)。solver 是对的,gold 是错的,加上 comparator 字段不匹配,三重 bug 叠在一起。
- **Verdict:** **B + C**。B 改 `Cp(x/c=1.0)=0.15`(外部 gate),C 在 `src/v_and_v/comparator.py` 加 `pressure_coefficient_x + pressure_coefficient` → keyed lookup 的 fallback(autonomous)。

---

### 3.10 Rayleigh-Bénard Convection (Ra=1e6, **k-omega SST**)

**whitelist 声明:** Chaivat 2006,Ra=10⁶,Pr=0.71,aspect_ratio=2.0,gold Nu=10.5 (tol 15%),湍流模型 k-omega SST。

**审计发现:**

- **(A) 湍流模型选择偏保守但可接受**。Rayleigh-Bénard 在 Ra=10⁶ 处于**弱湍流过渡区**(Ra_c ≈ 1708 开始对流,Ra ≈ 10⁴-10⁵ 稳态 roll,Ra ≈ 10⁵-10⁶ 时非稳态,Ra>10⁷ 全湍流)。用 SST 可能过度耗散,更好的选择是 DNS/LES 或 laminar (足够解析)。不算 bug,但在文档里标注"边界选择"。
- **(Gold)** Nu=10.5 at Ra=10⁶:
  - Globe-Dropkin 相关 Nu = 0.069·Ra^(1/3)·Pr^0.074,Ra=10⁶ 给 Nu≈7.1
  - 大 Ra 尺度律 Nu ∝ Ra^(2/7) 给 Nu ≈ 9-10
  - **10.5 在合理区间上限**,可接受。
- **(C-严重) Parameter plumbing**。corrections 最近 6 次**全是** `PARAMETER_PLUMBING_MISMATCH`。最近一次 (20260415T055254):`expected=10.5, actual=0.008, rel_err=99.9%`。**Nu≈0 意味着浮力项根本没启动**,Ra 值从未注入 solver template。这和 §3.6 Differential Heated Cavity 是**同一类 bug**。
- **Verdict:** **C 严重**。纯 infra 问题,autonomous 修。需要排查 `src/case_builder/buoyant_template.py` 或等价路径,确认 Ra/Pr 参数写入 `transportProperties` 和 `g` 向量。

---

## 4. Cross-Cutting Infrastructure Findings

汇总 10 个 case 中反复出现的 infra bug 类别:

### 4.1 `comparator_schema_mismatch` (7 次受影响)

**涉及:** Pipe (friction_factor 字段缺失)、Flat Plate、Channel DNS (u_mean_profile)、Impinging Jet、NACA 0012 (keyed vs array Cp)。

**根因:** ResultComparator 假设 solver output 和 gold_standard 使用同一套字段名,但实际 solver 的 post/sampleDict 输出往往是 `<quantity>_x` + `<quantity>` 数组,gold 是 `<quantity>[index=value]` 键式查找。

**修法:** 在 `src/v_and_v/comparator.py` 加:
1. 字段 alias 表(e.g. `friction_factor` ← `f` ← `fDarcy` ← `fanning_f * 4`)
2. Array→Keyed adapter:接受 `{quantity_x: [...], quantity: [...]}` 自动转成 `{quantity[x=0.3]: ..., quantity[x=0.5]: ...}`
3. 插值兜底:当 sampling 点不精确匹配 gold 点时,做线性插值并在 contract 里标注 `interpolated: true`

这是 autonomous turf 内的 `src/` 改动 — 需要新增测试(`tests/v_and_v/test_comparator_aliases.py`)。改动不碰 `knowledge/gold_standards/`,不碰 gate 列表。

### 4.2 `parameter_plumbing_mismatch` (3 个 case,12+ 次记录)

**涉及:** Differential Heated Cavity (Ra=1e10 没注入)、Rayleigh-Bénard (Ra=1e6 没注入)、可能还有 Impinging Jet 的 heat-flux BC。

**根因:** `whitelist.yaml` 的 `parameters:` 块(如 `Ra: 10000000000`)在 case-builder 转成 OpenFOAM dict 时路径不对。可能的断点:
- `transportProperties` 的 `nu`, `beta`, `rho`, `Cp` 计算
- `g` 重力向量
- `T` 边界温度差
- `constant/physicalProperties` 的 `Ra` / `Pr` 替换占位符

**修法:** 在 `src/case_builder/<template>.py` 加 pre-run assertion:writer 后立刻解析生成的 case dict,检查 `Ra_from_params ≈ g·β·ΔT·L³ / (ν·α)` 一致。失败直接 abort,避免"solver 跑了但 Ra 没进去"的 silent failure。

### 4.3 `sample_config_mismatch` (5 个 case,28+ 次记录)

**涉及:** Lid-Driven Cavity、NACA 0012、Cylinder Wake、(可能)Flat Plate、Channel DNS。

**根因:** `sampleDict`(OpenFOAM 的 post-processing 采样配置)里 probe 点、线、面的坐标与 gold_standard 的 `reference_values` 坐标不精确匹配。当前 ResultComparator 要求**精确命中**,不做插值。

**修法:** §4.1 的"插值兜底"同时解决此条。另外 case-builder 应基于 gold 的 `reference_values` **自动生成**对应的 sampleDict,而不是让两边独立手写,避免漂移。

### 4.4 `boundary_condition` (Impinging Jet 专有)

**根因:** Impinging Jet 冲击板温度 BC 可能被写成 `zeroGradient` 而非 `fixedValue`/`externalWallHeatFlux`,导致传热几乎为零。solver 跑成功但 Nu≈0。

**修法:** 在 `src/case_builder/impinging_jet_template.py` 显式设 `T` 在冲击板用 `fixedValue 350K`(与 Cooper 实验一致),jet 入口 `fixedValue 293K`。加单元测试校验 BC 写入。

---

## 5. Recommendations

### 5.1 Autonomous turf (can proceed without external gate)

1. **Fix A-class 元数据矛盾 in whitelist.yaml**(Circular Cylinder `k-omega SST → laminar`、Rayleigh-Bénard 湍流模型标注建议)。这部分 **whitelist.yaml 的 `turbulence_model`/`solver` 字段不在 gold_standards 禁区**,可直接修。需生成 DEC 记录说明变更。
2. **Fix C-class infra bugs** in `src/v_and_v/comparator.py`、`src/case_builder/*.py`。每个 bug 新增测试。预计 3-5 个 commits,每个可独立回滚。
3. **Tighten pre-run assertions**:case-builder 写完 dict 后立刻反解校验 Re/Ra/Pr 一致。
4. **Enrich `knowledge/whitelist.yaml` 文档字段**:为每个 case 加 `description_extended`,明确 Re 基准口径(`based_on: momentum_thickness` vs `step_height` 等)、湍流模型选择理由。

### 5.2 External gate (Q-new: whitelist remediation)

需打包提交外部 gate review 的 gold 修正,按严重度排序:

| # | Case | 当前 gold | 建议 gold | 依据 |
|---|------|----------|-----------|------|
| 1 | Lid-Driven Cavity | 5 行混杂 Re 数值 | Ghia 1982 Table I, Re=100 column | 原始论文 Table I |
| 2 | Differential Heated Cavity | Nu=30 at Ra=1e10 | Nu=325 (Churchill-Chu) 或改 Ra=1.58e9, Nu=62 (Ampofo-K.) | 原始论文 + 尺度律 |
| 3 | Fully Developed Pipe | f=0.0185 | f = 0.316/Re^0.25 (Blasius,runtime 计算) | Blasius 解析式 |
| 4 | Turbulent Flat Plate | Re=50000 + Spalding | Re=3×10⁶ + Spalding,或 Re=50000 + Blasius 层流 | NASA TMR 标准 |
| 5 | NACA 0012 TE | Cp(x/c=1)=0.2 | Cp(x/c=1)=0.15 | AGARD AR-138 |
| 6 | Channel DNS y+=100 | u+=22.8 | u+=17.0 (log-law) 或 18.3 (Moser) | Moser 1999 |

所有改动应伴随:
- 完整 DOI + 页码引用
- 对应的 pytest test case 验证
- DEC-V61-*** 决策记录 (autonomous_governance=7/10 下可以自动草拟,需 reviewer 确认)

### 5.3 为什么 dashboard 显示 0 PASS —— 修复顺序

**先修 C 再修 B**。若先改 gold 值,solver 实测的病态输出(Nu=0.008、Cp 数组字段名不对)仍会导致 contract 对不上。建议顺序:

1. 先做 **§5.1.2 (C-class infra)** — comparator aliases + parameter plumbing + sample config。这一步完成后,重新跑 10 个 case:
   - Cylinder Wake、Impinging Jet、NACA 0012 可能直接 PASS(gold 对,只是字段问题)
   - Pipe、Flat Plate 提升到 HAZARD/FAIL 但数值合理
   - Heated Cavity、RB 提升到 FAIL 但 solver 实际跑出合理 Nu
2. 再走 **§5.2 (B-class gold)** 外部 gate,修剩下 5-6 条 gold 值。
3. 第二轮跑 10 个 case → 目标 **≥8 PASS / ≤2 HAZARD / 0 FAIL**。

这就是从"0 pass"到"投稿级 V&V"的实际路径。

---

## 6. Appendix — 外部 Gate 包建议内容

递交给 external reviewer 时的 bundle 清单:

- `docs/whitelist_audit.md` (本文档)
- `knowledge/corrections/<history>.yaml` (全部 100+ 条,作为证据链)
- `knowledge/whitelist.yaml.proposed` (含修正 gold 值的 draft,不改原文件)
- `.planning/gates/Q-new_whitelist_remediation.md` (gate 请求书)
- 对每个 B-class 修正:原始论文 PDF 或 DOI 链接 + 页码截图

Gate 回来后,由 reviewer 或 autonomous_governance=7/10 阈值批准的流程写入 `knowledge/gold_standards/` 和 `knowledge/whitelist.yaml`。

---

## 7. Changelog

- **2026-04-20** (v1) — 初稿,由 Cowork agent 根据 dashboard 0 pass 观察触发,交叉核 whitelist.yaml + corrections/ + 原始文献。
- **2026-04-20** (v1.1) — 落地 §5.1 C 类 infra 修复的前两项 (autonomous turf,无需 external gate):
  - **C1 · ResultComparator field alias 层** — `src/result_comparator.py` 新增 `CANONICAL_ALIASES` 表 + `_lookup_with_alias` helper;canonical 键优先于 alias;companion-axis 查找透传 alias(`pressure_coefficient` → `Cp` 时 `pressure_coefficient_x` → `Cp_x`);failure summary 暴露尝试过的 alias 与可用键,供操作员回查 correction 文件时排障。`tests/test_result_comparator.py` 新增 `TestFieldAliases` 8 条用例,全部 green。直接消除 `comparator_schema_mismatch` ×14 的再发生路径。
  - **C2 · Case-builder pre-run assertion (parameter plumbing)** — `src/foam_agent_adapter.py` 新增 `ParameterPlumbingError` 异常 + 两个 static verifier (`_verify_buoyant_case_plumbing` / `_verify_internal_channel_plumbing`)。生成器写完 case 文件后把 `constant/physicalProperties` 与 `constant/g` 读回磁盘,重算 `Ra_effective = g·β·dT·L³/(ν·α)` 或 `Re_effective = 1/ν`,与 `task_spec` 声明值比对(tol=1%),漂移即 raise。`tests/test_foam_agent_adapter.py` 新增 14 条测试(解析器 + 正常 round-trip + tamper 检测 + 缺文件 + 零 ν 守卫),全部 green。158/158 regression 亦 green。消除 `parameter_plumbing_mismatch` ×12 的静默 fallback 路径。
  - **C3 · sampleDict 自动生成** — 尚未落地 (task pending);覆盖 NACA / Impinging Jet / LDC,由 gold `reference_values` 的坐标自动 emit sampleDict。
