# DEC-V61-048 Round 1 — 10-case 深度阅读价值评审

## Overall judgment
- 总体“阅读价值”评分：`4/10`
- 结论先说在前面：这 10 个 `/learn` case 目前更像“带证据的教学型产品页”，不是“可以直接指定给研究生精读 20-30 分钟的 CFD 方法学阅读材料”。我不会把其中任何一个页面原样发给研究生并说“请精读后下周讨论”；最多只会把其中 2-3 个当作课堂讨论引子，并且前提是我自己先补一页讲义。证据基础很清楚：Story tab 的主叙事固定为“physics bullets → literature image(s) → why validation matters → common pitfall → 4 个 TeachingCard → observable → 单条参考文献”，叙事骨架统一但过薄，缺少 textbook-style 的历史线、物理图景、数值权衡、复现实操与失败诊断链。`file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:340-456`
- 主要结构性问题：
  - `learnCases.ts` 把每个 case 的 narrative 压缩成 1 个 teaser、1 个 why-validation、1 个 pitfall 和 4 个 2-4 句 TeachingCard；接口注释本身就把卡片定位成“短段落”，这对“首次理解 setup”足够，对 graduate-level 精读远远不够。`file: ui/frontend/src/data/learnCases.ts:17-44`
  - Story tab 只有一个 `canonical_ref` 字符串，参考文献区也只是原样回显这一行文本，没有“为什么选这篇”“它在 benchmark lineage 中处于什么位置”“学生下一篇该读什么”。`file: ui/frontend/src/data/learnCases.ts:19-21` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:453-456`
  - Mesh tab 做的是通用网格收敛 slider，而不是 case-specific 的 geometry / patch / wall-normal resolution 讲解；它能教“数值逼近”，不能教“这张网格为什么长这样”。`file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:939-1095`
  - Run tab 明确把真正的 solver 执行和收敛监测推给 Pro Workbench，学习页本身没有从零 reproducing pipeline，也没有命令级 runbook。`file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1245-1263`
  - 对九个 Tier-C visual-only case，ScientificComparisonReportSection 在 Story tab 上只直接展示一张真实 contour 和一张 residuals 图；这能证明“跑过”，不能承担“教会读者看懂这个流动”的任务。`file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1617-1684`
  - Hero 图是中性的 line-art，组件设计规则明确写了“Never render text labels inside the SVG”；这保证了视觉整洁，但也意味着学生看不到 domain dimensions、patch labels、采样位置、关键流动结构标注。`file: ui/frontend/src/components/learn/CaseIllustration.tsx:1-10`
- 最值得读的 2-3 case（现状）：
  - `plane_channel_flow`：因为它真实地暴露了“数值上像 pass、物理上却不兼容”的方法学陷阱，现有内容已经具备课堂讨论价值。`file: ui/frontend/src/data/learnCases.ts:139-162` `file: knowledge/gold_standards/plane_channel_flow.yaml:7-27`
  - `impinging_jet`：因为“几何简化 + solver under-convergence”这两个风险同时被讲出来了，页面有工程诚实感。`file: ui/frontend/src/data/learnCases.ts:165-187` `file: knowledge/gold_standards/impinging_jet.yaml:8-27`
  - `differential_heated_cavity`：因为它把“目标从 Ra=1e10 降到 Ra=1e6”写成了一个 regime-selection lesson，而不仅是一次降规格。`file: ui/frontend/src/data/learnCases.ts:237-258` `file: knowledge/gold_standards/differential_heated_cavity.yaml:5-26`
- 最需要补的 2-3 case：
  - `lid_driven_cavity`：它本该是全站最像“教材章节”的旗舰页，但现在只是一个诚实、正确、仍然很薄的 catalog note。`file: ui/frontend/src/data/learnCases.ts:49-67`
  - `rayleigh_benard_convection`：物理上最富故事性，但当前页面把线性失稳、对流胞、Nu-Ra 标度、2D/3D 差异全部压成了一页短摘。`file: ui/frontend/src/data/learnCases.ts:216-234`
  - `duct_flow`：角区二次流这一真正有教学价值的物理几乎没有被展开，页面主要停在“f 是对的”。`file: ui/frontend/src/data/learnCases.ts:261-279`

## Per-case deep-dive

### 1. lid_driven_cavity
**Current reading value**: `4/10`  
**If I were assigning reading material**: `skip`

Lid-driven cavity 本应是整套 `/learn` 最像“教材第一章”的页面，因为它既是 CFD benchmark culture 的起点之一，也是“离散格式、压力速度耦合、网格分辨率、角点奇异性、主涡/二级涡”这些概念第一次同场出现的地方。但当前页面把它压成了一个标准化骨架：一个一句话 teaser、三条 physics bullets、一段 why-validation、一段 common pitfall，再加四张短 TeachingCard。叙事是清楚的，但不足以支撑 graduate course 的“精读”。你知道“几乎每一本 CFD 教材的第一个算例”这件事，却不知道为什么是 Ghia 1982 成了课堂共同语言，而不是更早的 Burggraf 1966，或者更高精度的 Botella & Peyret 1998。页面也没有把 Re=100、400、1000 作为一个学习路径展开，而只是把它们列成 bullet。`file: ui/frontend/src/data/learnCases.ts:53-67` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:340-456`

物理直觉层面，LDC 当前最大的问题是“知道 observable，不等于看懂流动”。页面告诉学生要看 `u_centerline`、也告诉学生主涡和二级涡需要被分辨，但没有真正解释“为什么腔体流的 fingerprint 是角区二级涡的出现顺序”“为什么中心线速度剖面会在中上部翻符号”“为什么顶角奇异性是一个边界数据而不是物理奇点”。现有 literature images 只有中心线剖面和一个“shape calibrated”的流函数示意图，它们对 benchmark 数字是有帮助的，对流动机理的视觉教学仍然偏弱。尤其当 Story tab 的 hero illustration 还明确避免任何文字标签时，学生并不会天然知道哪条边是 moving lid、哪两个角区最先冒出 secondary eddies。`file: ui/frontend/src/data/flowFields.ts:19-31` `file: ui/frontend/src/components/learn/CaseIllustration.tsx:9-10` `file: ui/frontend/src/components/learn/CaseIllustration.tsx:38-57`

数值教学层面，LDC 的四张 TeachingCard 其实已经比常见 demo 页认真得多：它说清楚了 `simpleFoam` 而不是 `pimpleFoam`，说清楚了 uniform mesh、reference pressure、`sample` utility 和第二道主涡位置验证。问题不在“错”，而在“太快”。一个 graduate reader 真正想读到的是：为什么对 steady Re=100 cavity，SIMPLE 比 transient route 更像 benchmark-grade choice；129×129 对二阶 FD 的历史意义是什么；40×40 教学网格和 129×129 benchmark 网格之间误差会如何表现；如果你把 `movingWall` 错写成普通 wall，会在 residual、contour、centerline curve 上分别出现什么症状。Mesh tab 也只是一个通用 convergence slider，并没有 domain schematic、patch labels、sampling line 标注或 Richardson/GCI 的具体解释，因此数值 pedagogy 仍然是“结果型”的，不是“构造型”的。`file: ui/frontend/src/data/learnCases.ts:64-67` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:410-440` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:941-1095`

深度与密度上，这个 case 目前大约只有 1100 个中文字符的叙事量，折合大约 650-700 English-word equivalent，足够做一张优秀的课程网站卡片，不够做一篇可分配的阅读。Graduate CFD methodology 里，LDC 至少应该像一个 1500-2500 英文词的小章节：先讲 benchmark lineage，再讲物理图像，再讲 solver/mesh/BC 权衡，再讲 failure modes，最后给出 reproducing pipeline 和 next reading。现在的页面把所有这些维度都碰到了，但都没有走到“可读 20 分钟”的阈值。`file: ui/frontend/src/data/learnCases.ts:49-67`

**Concrete补齐 list** (prioritized):
- 🔴 history chain：当前只有“几乎每一本 CFD 教材的第一个算例”这一句，必须补一个“Burggraf 1966 → Ghia 1982 → Botella & Peyret 1998”的 benchmark lineage，解释为什么课程首页锚定 Ghia 1982，而不是更早或更高精度的论文。建议插入位置：Story tab 的“为什么要做验证”之后、新增“历史基准链” section。`file: ui/frontend/src/data/learnCases.ts:53-62` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:390-395`
- 🔴 reproducibility pipeline：TeachingCard 提到了 `simpleFoam`、`sample utility` 和 comparator，但学习页没有从 `blockMeshDict` 到 `blockMesh` 到 `simpleFoam` 到 `sample` 的命令级 runbook。建议在 “CFD 全流程” 之后增加 6-step 命令块，至少给出最小命令序列。`file: ui/frontend/src/data/learnCases.ts:64-67` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:410-440` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1245-1263`
- 🟠 mesh / BC schematic：当前 hero 图故意不加文字标签，Mesh tab 也没有 geometry schematic；应补一张带 lid arrow、四边 patch 名称、中心线采样位置的 SVG/ASCII block diagram，放在 Mesh tab 标题之前。`file: ui/frontend/src/components/learn/CaseIllustration.tsx:1-10` `file: ui/frontend/src/components/learn/CaseIllustration.tsx:38-57` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:999-1006`
- 🟠 annotated contour：现有流函数示意图和比较报告不能替代“标注过的真实流场”。建议新增一张 `contour_u_magnitude.png` 的 annotation overlay，标出 primary vortex、top-corner secondary eddy、bottom-corner recirculation onset。建议位置：ScientificComparisonReportSection 之后、literature reference 之前。`file: ui/frontend/src/data/flowFields.ts:19-31` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:356-388` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1705-1784`
- 🟡 regime ladder：physics bullets 只列出 `Re=100 / 400 / 1000`，没有告诉学生这些点分别增加了什么现象。建议新增一个 “Re-path” 小表，把主涡、二级涡、steady assumption 的变化讲清。插入位置：`这个问题是什么` section 之后。`file: ui/frontend/src/data/learnCases.ts:57-60` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:340-350`

### 2. backward_facing_step
**Current reading value**: `6/10`  
**If I were assigning reading material**: `conditional-on-补`

Backward-facing step 是 10 个 case 里我最接近“愿意拿去做课堂讨论”的页面之一，因为它已经不只是一个数值展示，而是明确把 benchmark 选择和 tolerance 来源说得比一般教学页更诚实：`learnCases.ts` 把 Le-Moin-Kim 1997 DNS、Driver & Seegmiller 1985 experiment、Armaly 1983 envelope 都点到了，gold YAML 也把“6.26 是 blended engineering anchor 而不是纯 DNS 数字”写清楚了。这是 graduate methodology 很看重的写法：它承认 benchmark 不是单一神谕，而是 regime、expansion ratio、inlet BL、2D/3D simplification 之间的折中。`file: ui/frontend/src/data/learnCases.ts:74-88` `file: knowledge/gold_standards/backward_facing_step.yaml:10-23` `file: knowledge/gold_standards/backward_facing_step.yaml:27-44`

但即便如此，BFS 还没有到“可精读”的原因，是它现在仍然主要在讲“Xr/H 怎么对上”，没有真正把 separation physics 展开。页面提到“回流区”“重新贴壁”“再附着点”，却没有把 shear layer roll-up、recirculation bubble、pressure recovery、reattachment heat/momentum transfer 这条物理链讲成一个可视化故事。唯一 literature figure 是 `xr_vs_re.png`，这对 benchmark location 有帮助，却没有让学生在视觉上认出 step lip、separated shear layer 和 reattachment zone。对于研究生读物，我希望能看到至少一张带 step geometry 和 sampling line 的 schematic，以及一张把 `x_r` 标在真实 contour 上的注释图。`file: ui/frontend/src/data/flowFields.ts:80-87` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:358-388` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1617-1684`

数值 pedagogy 方面，BFS 当前已经有了一个相当好的起点：它明确说了为什么教学上先用 `kEpsilon` 而不是 `kOmegaSST`，也说了 quick-run 的 800 cells 和 authoritative 36000 cells 之间会有 G5 under-resolution issue。但它仍然缺少“alternative path”的展开。一个 graduate student 应该从这一页读到：如果你换成 `kOmegaSST`，你期望 Xr/H 向哪个方向动、为什么；如果你转成 transient LES，你的 observable 为什么从单一 Xr/H 扩展到 time-averaged wall shear / fluctuating reattachment bubble；front/back `empty` 这件事在 BFS 里意味着什么 3D physics 被拿掉了。现在这些洞见都只是隐含在 YAML 的 preconditions 和 one-line cards 里。`file: ui/frontend/src/data/learnCases.ts:83-88` `file: knowledge/gold_standards/backward_facing_step.yaml:31-43`

从 density 看，这页大约 1300 多中文字符，折合 800 English-word equivalent 左右，在 10 个 case 里已经算是偏厚的，但还主要是“结论密度”，不是“解释密度”。所以我的结论不是 skip，而是 conditional：只要补上 step geometry 读图、Xr/H extraction figure、failure-mode checklist 和 benchmark lineage 的 next-reading，这页就能进入 graduate reading shortlist。`file: ui/frontend/src/data/learnCases.ts:70-88`

**Concrete补齐 list** (prioritized):
- 🔴 separation narrative：必须新增一段“从 step lip 到 shear layer 到 recirculation bubble 到 reattachment”的物理 walkthrough，不然学生知道 `Xr/H` 这个数字，却不知道这个数字在流场里指向哪里。建议位置：`这个问题是什么` 之后。`file: ui/frontend/src/data/learnCases.ts:74-88` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:340-350`
- 🔴 geometry + sampling schematic：当前没有一张标出 `H`、expansion ratio 1.125、`x_r` 搜索线和下壁零剪切交点的示意图。建议在 Mesh tab slider 前加 SVG/ASCII block diagram。`file: ui/frontend/src/data/learnCases.ts:86-88` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:996-1006`
- 🟠 benchmark lineage：YAML 已经写明 6.26 是 blended anchor，但学习页没有把 Armaly / Driver / Le-Moin-Kim 三者关系说出来。建议新增 `why this paper, not another` 小节，并给出 next reading。`file: knowledge/gold_standards/backward_facing_step.yaml:10-23` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:390-395`
- 🟠 extraction figure：observable card 说的是“沿下壁 y=0.01H 扫描零点”，但页面没有展示 wall-shear sign change 长什么样。建议新增一张 `tau_w(x)` 或 near-wall `u_x(x)` 曲线图，当前工作点用竖线标 `x_r/H=6.26`。`file: ui/frontend/src/data/learnCases.ts:88` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:443-450`
- 🟡 troubleshooting checklist：目前只有一个 pitfall，缺少按优先级排序的 BFS 诊断链。建议新增 “若 `x_r/H<0` / residuals plateau / quick-run pass but G5 fail / outlet recirculation” 四条检查顺序。插入位置：`常见陷阱` 之后。`file: ui/frontend/src/data/learnCases.ts:84` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:397-404`

### 3. circular_cylinder_wake
**Current reading value**: `5/10`  
**If I were assigning reading material**: `conditional-on-补`

Cylinder wake 现在最有价值的地方，不是它讲清楚了 Kármán vortex street，而是它讲清楚了一个验证方法学陷阱：`Strouhal` 如果被 canonical-band shortcut 硬编码，就会变成“看起来总在 0.18-0.22 之间”的假通过。这一点 narrative 和 gold YAML 是对齐的，而且 Gold YAML 把 “Strouhal extractor reflects solver physics” 直接标成 false，这对 graduate class 非常有讨论价值。`file: ui/frontend/src/data/learnCases.ts:95-109` `file: knowledge/gold_standards/circular_cylinder_wake.yaml:14-24`

但作为“涡脱 benchmark 的阅读材料”，这页依旧偏薄。现在的 history context 只有 `Williamson 1996 (review)` 这一行，以及 `St≈0.2` 的一句普适关系；没有告诉学生为什么课程里常常让你先读 Williamson review，再去读 Roshko 的早期实验或 Henderson 关于 2D/3D transition 的工作；也没有解释 `Re≈47` 的 steady-to-periodic threshold、`Re≈180` 后 3D modes 开始出现、`Re≈300` 以后二维教学设定如何失真。结果就是页面教会了一个 benchmark number，却没有教 benchmark regime map。`file: ui/frontend/src/data/learnCases.ts:95-104` `file: ui/frontend/src/data/flowFields.ts:47-53`

物理直觉方面，hero 图和 literature 图都在暗示“有一列交替脱落的涡”，但 Story tab 上没有一段真正把圆柱表面分离点、尾迹基底压、升力振荡和 Strouhal 频率之间的关系讲成文。读者知道要在尾迹 probe 上做 FFT，也知道需要 `20-30` 个 shedding cycles，但不知道为什么 start-up transient 必须丢弃、为什么对称初始场会让 shedding 推迟、为什么 domain truncation 会污染 `St`。更重要的是，Story tab 的真实 solver 证据在 Tier-C 分支下只是一张 `|U| contour` 和一张 residuals 图，没有涡核标注、没有 probe 位置、没有 FFT 结果可视化。`file: ui/frontend/src/data/learnCases.ts:105-109` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1617-1684`

深度上，这页大约 650 English-word equivalent，够做“concept card”，不够做“assigned reading”。如果补上一张 `Re–St`/regime map、一个 probe-and-FFT workflow panel、一张带 separation points 与 vortex street phase 标注的 contour，以及一段从 Roshko/Williamson 延伸到现代 LES/DNS 的 next-reading，reading value 会明显上升。`file: ui/frontend/src/data/learnCases.ts:91-109`

**Concrete补齐 list** (prioritized):
- 🔴 regime map：当前只有 `St(Re)` 图，没有“steady wake → 2D periodic shedding → 3D mode A/B”的过渡说明。建议新增 `Re` regime ladder，当前工作点 `Re=100` 用 marker 标出。`file: ui/frontend/src/data/learnCases.ts:99-104` `file: ui/frontend/src/data/flowFields.ts:47-53`
- 🔴 temporal workflow：页面提到了 `Δt≈0.01`、`20-30 个周期` 和 FFT，但没有从 `probe placement → discard transients → Hann window → peak picking` 讲成 reproducible pipeline。建议在 `CFD 全流程` 后新增时间序列 runbook。`file: ui/frontend/src/data/learnCases.ts:106-109` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:410-440`
- 🟠 annotated wake image：Tier-C 只显示 raw contour 与 residuals，学生看不到 separation point、near wake recirculation、vortex core 的标注。建议新增一张注释版 wake contour，放在 raw contour 旁。`file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1661-1674`
- 🟠 citation ladder：`Williamson 1996` 现在只是一个 review 名字。建议在参考区扩成 “Williamson review / Roshko experiment / Henderson 3D transition” 三层阅读链。`file: ui/frontend/src/data/learnCases.ts:96` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:453-456`
- 🟡 failure checklist：把对称初始场、采样窗口过短、domain too short、hardcoded St shortcut 四个 failure mode 做成 checklist，插在 `常见陷阱` 之后。`file: ui/frontend/src/data/learnCases.ts:104-105` `file: knowledge/gold_standards/circular_cylinder_wake.yaml:14-24` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:397-404`

### 4. turbulent_flat_plate
**Current reading value**: `6/10`  
**If I were assigning reading material**: `conditional-on-补`

Flat plate 这页的优点，是它不是在教“边界层有多酷”，而是在教“regime honesty 比命名惯性更重要”。页面把 `turbulent_flat_plate` 这个稳定 case_id 明说成“实际上是 laminar Blasius regime”，而且为什么要改、以前错在哪、为什么不能用 1/7 次幂 turbulent engineering formula，都写了。这在 methodology 课程里是有价值的，因为它展示了 benchmark 选择并不只是选一篇论文，而是先看 case 真在算什么物理。`file: ui/frontend/src/data/learnCases.ts:112-136` `file: knowledge/gold_standards/turbulent_flat_plate.yaml:5-31`

但它距离 textbook-grade 还差一个关键台阶：它现在更像“纠错说明”，不是“边界层章节”。它告诉了你 `Cf=0.664/√Re_x`，告诉了你 `Re_x=25000` 时 `Cf=0.00420`，却没有把这个公式从 Prandtl boundary-layer scaling 讲出来，也没有把 `δ_99~5√(νx/U)`、边界层厚度随 `x` 增长、壁面剪应力沿流向递减这几个最基本的 physical ideas 连成一个 mental model。Graduate student 应该读完页面以后脑子里有一张“从 leading edge 开始 boundary layer 逐渐长厚”的图，而不是 فقط 记住 x=0.5 这一票数值。`file: ui/frontend/src/data/learnCases.ts:122-136` `file: ui/frontend/src/data/flowFields.ts:33-45`

数值教学层面，四张卡片其实已经很不错：`simpleFoam + laminar`、4:1 wall grading、上壁 `slip`、用 interior-cell gradient 计算 `τ_w`，这些都比普通教程更接近真实 OpenFOAM practice。但页面仍缺两样关键东西。第一，缺一张 geometry/BC schematic，把 `x=0.5m` 抽取位置、上壁 slip、下壁 no-slip、流向发展方向画出来。第二，缺一个“如果你错误启用湍流模型/如果 Spalding fallback 触发/如果上壁太低导致 blockage”的 troubleshooting walk。当前 pitfall 只有一个段落，信息量还不足以支持“诊断式阅读”。`file: ui/frontend/src/data/learnCases.ts:133-136` `file: knowledge/gold_standards/turbulent_flat_plate.yaml:21-30` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:397-440`

以篇幅算，这页已经有 750 English-word equivalent 左右，是整个站里比较接近“可读”的一页；但它的厚度主要花在 regime correction，而不是 boundary-layer pedagogy 本身。如果加上 Blasius 物理推导的最小版、transition threshold 的 next step、壁面梯度提取示意图和 failure checklist，这页可以成为“研究生方法课第一周的好材料”。`file: ui/frontend/src/data/learnCases.ts:112-136`

**Concrete补齐 list** (prioritized):
- 🔴 physical model anchor：必须补一段从 `δ_99(x)`、`Cf(x)`、leading-edge boundary layer growth 出发的物理叙事，而不只是“这里不是 turbulent”。建议插在 `这个问题是什么` 之后。`file: ui/frontend/src/data/learnCases.ts:122-136` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:340-350`
- 🔴 geometry/BC figure：当前没有一张标出 plate、上壁 slip、`x=0.5m` sample station、wall grading 方向的示意图。建议新增 SVG，放在 Mesh tab 标题之前。`file: ui/frontend/src/data/learnCases.ts:134-136` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:996-1006`
- 🟠 derivation note：`Cf=0.664/√Re_x` 被直接给出，但没有告诉读者它来自 Blasius similarity，而非经验 curve-fit。建议在 literature section 扩成 “Blasius 1908 / Schlichting chapter / transition at Re_x≈3e5–5e5” 三项 next reading。`file: ui/frontend/src/data/learnCases.ts:123-129` `file: knowledge/gold_standards/turbulent_flat_plate.yaml:15-16` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:453-456`
- 🟠 diagnostic checklist：把“误开 k-ε / 上壁过低产生 blockage / wall-gradient extraction 失败触发 fallback / 网格不足导致 Cf 偏高偏低”做成 ordered checklist。`file: ui/frontend/src/data/learnCases.ts:131-136` `file: knowledge/gold_standards/turbulent_flat_plate.yaml:27-30`
- 🟡 local-vs-global observable：现在只取 `x=0.5m` 一票。建议在 Story 或 Compare 附一张 `Cf(x)` 发展曲线，帮助学生理解“局部标量与全场发展”的关系。可复用现有 `cf_comparison.png`，但需要在 caption 里解释它的教学意图。`file: ui/frontend/src/data/flowFields.ts:40-45` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:358-388`

### 5. plane_channel_flow
**Current reading value**: `7/10`  
**If I were assigning reading material**: `conditional-on-補`

Plane channel 是我认为当前最接近“值得研究生读”的页面，不是因为它把 channel flow 讲得最完整，而是因为它把一个在研究训练里极其重要的认知障碍讲得很直接：`ATTEST_PASS` 不等于 physics-compatible。`learnCases.ts` 和 gold YAML 在这里形成了很强的 pedagogy 共振：页面写明这是 “incompatibility teaching case”，gold YAML 进一步解释 laminar `icoFoam` at `Re_bulk=5600` 不可能生成 `Re_tau=180` turbulent log-law，并明确指出 comparator path 的假阳性危险。这种“把错误路径当教材”的写法，是方法学课程真正需要的。`file: ui/frontend/src/data/learnCases.ts:145-162` `file: knowledge/gold_standards/plane_channel_flow.yaml:7-27`

然而这页仍然没有完全跨过可分配阅读的门槛，因为它现在更像一份 incident report，而不是一章 channel-flow pedagogy。页面能让学生明白“不兼容”，但不能让学生真正理解“Poiseuille parabolic profile”和“turbulent wall law”之间在物理、统计量、边界条件、网格需求、时间平均上的系统差异。唯一 literature image 是 `Spalding composite wall profile`，这只能提醒学生 log-law 的形状，不能帮助他们建立 “periodic streamwise DNS + driving pressure gradient + wall units + time average” 这一整套 canonical setup 的 mental model。`file: ui/frontend/src/data/flowFields.ts:55-61` `file: ui/frontend/src/data/learnCases.ts:153-162`

数值和 workflow 方面，这页已经天然适合做 graduate reading，因为它涉及 solver、mesh、boundary condition、observable extraction 四层 simultaneously wrong 的情况。问题是页面还没有把这四层做成一个 structured diagnostic ladder。它说了 `icoFoam` 错、mesh 远不够、inlet/outlet 与 periodic mismatch、`u_tau` 数学正确但物理错误，可是学生并不知道如果自己在一个新 repo 里遇到类似问题，应先检查哪一层。作为阅读材料，我希望看到一个“症状 → 证据 → 误判风险 → 正确修复路径”的表，而不是目前分散在 pitfall、TeachingCard 和 physics contract 里的碎片化说明。`file: ui/frontend/src/data/learnCases.ts:157-162` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:505-635`

从篇幅看，这页已经接近 900-950 English-word equivalent，问题不是字数，而是组织方式。只要补一段“Poiseuille vs turbulent channel” 的并列表、一张 wall-unit schematic、一条从 Kim 1987 到 Moser 1999 再到 Hoyas/Jiménez 的阅读链，以及一个 false-pass diagnostic table，这页就足以成为一篇非常好的 graduate methodology reading。`file: ui/frontend/src/data/learnCases.ts:139-162`

**Concrete补齐 list** (prioritized):
- 🔴 comparative pedagogy：必须新增一个 `Laminar Poiseuille vs turbulent channel DNS` 的并列表，覆盖 velocity shape、wall units、BC、time averaging、mesh scale、solver family。建议插在 `为什么要做验证` 后。`file: ui/frontend/src/data/learnCases.ts:157-162` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:390-395`
- 🔴 diagnostic ladder：把当前的 incompatibility 拆成四层检查顺序：solver regime、BC class、mesh scale、observable semantics。建议新增 `false pass checklist` section，紧跟 `常见陷阱`。`file: ui/frontend/src/data/learnCases.ts:158-162` `file: knowledge/gold_standards/plane_channel_flow.yaml:10-27` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:397-404`
- 🟠 wall-unit schematic：现在只有一张 `u+` profile 图，没有 channel half-height、`y+`、`u_tau`、periodic streamwise direction 的示意图。建议新增 SVG，放在 Mesh tab 前。`file: ui/frontend/src/data/flowFields.ts:55-61` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:996-1006`
- 🟠 next-reading ladder：把 `Kim 1987 / Moser 1999 / Dean friction correlation / Hoyas & Jiménez higher-Re DNS` 做成简短阅读链，说明为什么课程在这里选 `Re_tau=180`。`file: knowledge/gold_standards/plane_channel_flow.yaml:7-9` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:453-456`
- 🟡 current-vs-future path：TeachingCard 说了 Phase 9 会迁移 solver，但没有明确写“proper path 长什么样”。建议在 Run tab 新增对照 runbook：当前 `icoFoam` teaching path vs future DNS/LES path。`file: ui/frontend/src/data/learnCases.ts:159-162` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1245-1320`

### 6. impinging_jet
**Current reading value**: `7/10`  
**If I were assigning reading material**: `conditional-on-補`

Impinging jet 和 plane channel 一样，当前的教学价值主要来自“它没有假装一切正常”。页面明确写了两个 gap：几何上是 2D planar slice 而不是 axisymmetric wedge；数值上 `p_rgh` hitting iteration cap。gold YAML 又把这两点分别变成 precondition #1 和 #2。对于研究生方法课，这很有价值，因为它把“你以为自己在做的 canonical benchmark”和“你的 adapter 真在做什么”之间的距离讲得足够直白。`file: ui/frontend/src/data/learnCases.ts:165-187` `file: knowledge/gold_standards/impinging_jet.yaml:8-27`

但如果把它当成“冲击射流 benchmark 章节”，当前页面仍然明显不够。它告诉学生 `Nu(r/D)` 在驻点最大，会径向衰减，也给了一张 `nu_radial.png`，但没有把冲击射流真正有趣的物理展开：自由射流 core 如何撞上底板、为什么驻点附近湍流各向异性会让 `k-ε` 系统性高估、`H/D` 改变为什么会重排 radial heat-transfer peak。更关键的是，用户 prompt 里提到的 benchmark lineage 问题在这里尤为突出：当前页面给出 `Cooper 1984 / Behnad 2013`，却没有解释为什么不是很多工程师更熟悉的 Baughn & Shimizu 1989，或后来的 Lee & Lee 2000。对 graduate reader 来说，“为什么选这组文献做 anchor” 本身就是方法学内容。`file: ui/frontend/src/data/learnCases.ts:173-187` `file: ui/frontend/src/data/flowFields.ts:71-78`

数值与 workflow visibility 方面，这页已经具备教学骨架：它指出了 `empty` vs `wedge`、指出了 `kEpsilon` 只是 legacy engineering choice、指出当前没有稳定温度场因而 comparator 不该继续跑。但它仍缺一张真正的 geometry contrast 图。Hero illustration 画的是一个理想化轴对称喷嘴撞板图，而 TeachingCard 又说真实 adapter 用的是 planar `empty` patch；学生如果不仔细读字，只看图，反而会被英雄图误导成“这页展示的是 axisymmetric flow”。这是少数需要把 hero 与真实 mesh schematic 拉开来处理的页面。`file: ui/frontend/src/components/learn/CaseIllustration.tsx:238-260` `file: ui/frontend/src/data/learnCases.ts:185-186`

就文字量而言，这页大概 850 English-word equivalent，已经足够支撑一个很好的“how not to trust a benchmark” short reading。它现在离“可分配”只差三样东西：一张理想几何 vs 实际几何对照图、一条从 nozzle setup 到 Nu extraction 的命令级 pipeline、和一个按 likelihood 排序的 solver diagnosis checklist。`file: ui/frontend/src/data/learnCases.ts:165-187`

**Concrete补齐 list** (prioritized):
- 🔴 geometry truth table：必须新增 “intended axisymmetric wedge vs actual planar empty” 对照图，不然 hero line-art 与真实 adapter 设置之间存在误导风险。建议位置：Story tab `这个问题是什么` 之后。`file: ui/frontend/src/data/learnCases.ts:173-186` `file: knowledge/gold_standards/impinging_jet.yaml:8-17` `file: ui/frontend/src/components/learn/CaseIllustration.tsx:238-260`
- 🔴 benchmark lineage：补一个 “Cooper 1984 / Baughn-Shimizu 1989 / Behnad 2013” 的 anchor 说明，解释当前选择的原因，以及现代 `k-ω SST`/`v2f` 研究应接在什么地方读。`file: ui/frontend/src/data/learnCases.ts:174-175` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:453-456`
- 🟠 stagnation-zone pedagogy：增加一段对“驻点 Nu 为什么最高、wall jet 为什么径向衰减”的物理说明，并在 `nu_radial.png` 上标出 `r/D=0`、`1`、peak decay 区。`file: ui/frontend/src/data/flowFields.ts:71-78`
- 🟠 ordered diagnosis：当前页面知道 A4 fail，但没给排查顺序。建议新增 checklist：先查 axis patch、再查 pressure-velocity coupling、再查 thermal BC、最后查 turbulence model。插入位置：`常见陷阱` 之后。`file: knowledge/gold_standards/impinging_jet.yaml:15-27` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:397-404`
- 🟡 command pipeline：在 Run tab 增加最小可复现实验步骤，包括 mesh generation、boundary assignment、solver launch、wall-gradient extraction。当前页面只有去 Pro Workbench 的 CTA。`file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1245-1263`

### 7. naca0012_airfoil
**Current reading value**: `5/10`  
**If I were assigning reading material**: `conditional-on-補`

NACA 0012 页面的优点是它不是“空气动力学神话”，而是“一个很诚实的 Cp extraction lesson”。页面和 gold YAML 都很清楚：当前 adapter 提取的是 near-surface cell-average，而不是 exact-surface pressure tap，所以形状对、幅值系统性衰减；这解释了为什么 verdict 是 `PASS_WITH_DEVIATIONS` 风格而不是无脑 pass。这种 honest limitation disclosure 很好，也确实符合 methodology 课程的精神。`file: ui/frontend/src/data/learnCases.ts:208-213` `file: knowledge/gold_standards/naca0012_airfoil.yaml:14-29`

但作为 airfoil reading material，它最大的问题是“流动物理被 extraction disclaimer 吞掉了”。页面告诉学生是 `α=0°` attached flow、zero lift、farfield 要 15-20c、`kOmegaSST` 合适，却没有真正讲出任何 aerodynamics intuition：前缘停滞点在哪里、为什么表面会出现 suction peak、为什么对称翼型在零攻角时上下表面 `Cp` 应该镜像、为什么 farfield 太近会造成 blockage-induced pressure shift。现有 literature 图只有 `cp_distribution.png` 一张，而且 caption 仍以数据来源和偏差形态为主，没有把翼型表面的 pressure recovery 讲成视觉故事。`file: ui/frontend/src/data/learnCases.ts:194-213` `file: ui/frontend/src/data/flowFields.ts:89-96`

这一页还有一个特别适合提升 reading value 的切口：citation lineage 目前是混杂的。`learnCases.ts` 的 `canonical_ref` 是 `Ladson et al. · NASA TM 1996`，gold YAML 的 source 却写成 `Thomas 1979 / Lada & Gostling 2007`，而 physics contract 用的是 “exact surface points vs near-surface averages” 这条解释线。即便这在事实层面最终可以统一，现在的 pedagogy 问题是：页面没有告诉学生这些名字之间的关系。对于研究生，这不是小事；它决定了他们去读 wind-tunnel data、computed fit、还是后续整理版资料。`file: ui/frontend/src/data/learnCases.ts:195-196` `file: knowledge/gold_standards/naca0012_airfoil.yaml:3-4` `file: knowledge/gold_standards/naca0012_airfoil.yaml:16-28`

以密度算，这页接近 940 English-word equivalent，数字不少，但大半信息都在 setup honesty，而不在 aerodynamic reasoning。补一张 farfield + surface-band schematic、一段 Cp shape walkthrough、一个 “Thomas/Ladson/Lada” 阅读链和一个 blockage / y+ / sampling mismatch troubleshooting table 之后，这页可以从“工程说明”升级成“好读的 benchmark essay”。`file: ui/frontend/src/data/learnCases.ts:190-213`

**Concrete补齐 list** (prioritized):
- 🔴 Cp physical walkthrough：必须补充“stagnation point → suction region → pressure recovery → trailing-edge closure”的文字与注释图，否则学生只看见一条曲线，不理解 airfoil pressure physics。建议位置：literature image 之后。`file: ui/frontend/src/data/learnCases.ts:203-213` `file: ui/frontend/src/data/flowFields.ts:89-96`
- 🔴 source lineage：把 `Ladson`、`Thomas`、`Lada & Gostling` 之间的角色说明清楚，告诉学生当前页面锚定哪一份数据、哪一份只是 shape context。`file: ui/frontend/src/data/learnCases.ts:195` `file: knowledge/gold_standards/naca0012_airfoil.yaml:3-4` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:453-456`
- 🟠 farfield / extraction schematic：新增一张标有 `15-20c` farfield boundary、surface band `0.02c`、upper/lower split 的示意图。建议放在 Mesh tab 标题前。`file: ui/frontend/src/data/learnCases.ts:211-213` `file: knowledge/gold_standards/naca0012_airfoil.yaml:15-27` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:996-1006`
- 🟠 solver alternatives：TeachingCard 只说了为什么用 `kOmegaSST`，但没有把 inviscid/potential flow、transition model、`k-ε` 的 alternative path 讲出来。建议扩充 Solver card 到 5-8 句。`file: ui/frontend/src/data/learnCases.ts:210-212` `file: ui/frontend/src/data/learnCases.ts:33-39`
- 🟡 troubleshooting ladder：建议新增 “farfield too close / y+ 不合适 / surface-band 过厚 / α 设置错误 / exact-surface vs cell-average mismatch” 五步诊断。插入位置：`常见陷阱` 之后。`file: ui/frontend/src/data/learnCases.ts:209-213` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:397-404`

### 8. rayleigh_benard_convection
**Current reading value**: `4/10`  
**If I were assigning reading material**: `skip`

Rayleigh-Bénard 当前是我最不愿意直接发给学生的一页之一，因为它把一个本来可以极其迷人的主题压得过于平：`Ra_c≈1708`、`Nu~Ra^α`、`Boussinesq`、`Ra=1e6` 这些关键词都在，但页面没有把它们组织成任何真正的理论故事。学生现在读到的是“critical value、对流胞、Nu-Ra scaling、Boussinesq validity”四个被点名的概念，却读不到从 Rayleigh linear stability、Bénard 实验、Chandrasekhar 理论、Grossmann-Lohse scaling 到当前选用的 Chaivat 2006 benchmark 之间的关系。换句话说，这页碰到的材料都是 textbook-worthy 的，组织方式却仍然是 product-page-worthy 的。`file: ui/frontend/src/data/learnCases.ts:216-234` `file: knowledge/gold_standards/rayleigh_benard_convection.yaml:9-23`

物理直觉层面，问题更明显。RBC 最适合教学的地方恰恰是“从纯导热态到对流胞自发出现”的视觉转变，但当前页面没有给出一张 cell pattern、温度 plume 或导热/对流对比图。唯一 literature image 是一张 `Nu(Ra)` scaling plot；这对 benchmark 很好，对“流动长什么样”几乎没有帮助。Hero illustration 也只是通用 line art，不带边界标签和 plume 标注。对于 graduate student，我希望这一页至少让他在脑中形成一张图：底部热壁生成 thermal boundary layer，达到临界后上升 plume 与下降冷 plume 形成对流胞，而 `Nu` 只是这整个结构的一个压缩测量。现在这张图不存在。`file: ui/frontend/src/data/flowFields.ts:63-69` `file: ui/frontend/src/components/learn/CaseIllustration.tsx:1-10`

数值方面，页面告诉你 `buoyantBoussinesqSimpleFoam`、`Ra~1e6`、`δ_T/L≈Ra^-1/4`，也告诉你 extractor 取热壁热流换算 `Nu`。但它没有告诉你为什么这里仍然用 2D、为什么侧壁条件在 RBC 与 DHC 中不同、为什么 `Ra=1e6` 在这里被叫做 `soft-turbulence band` 而 solver 还是 laminar、以及 oscillating convergence 在这个问题里何时是物理症状、何时是数值症状。gold YAML 里其实有 “Convergence OSCILLATING but Nu stable” 这样的重要信息，但它没有被翻译成教学文本。`file: ui/frontend/src/data/learnCases.ts:229-234` `file: knowledge/gold_standards/rayleigh_benard_convection.yaml:5-22`

从字数算，这页也是 580-600 English-word equivalent 级别，明显低于题材本身应该承载的深度。我不会把它指定成 reading；我会先要求补一条理论脉络、两张基础图（conduction vs convection、cell/plume annotated contour）、以及一张 diagnostic table，然后才考虑作为课程阅读。`file: ui/frontend/src/data/learnCases.ts:216-234`

**Concrete补齐 list** (prioritized):
- 🔴 theory lineage：必须把 `Rayleigh/Bénard/Chandrasekhar/Grossmann-Lohse/Chaivat` 的关系写成一段“历史与理论链”，否则当前 citation surface 只是名字堆叠。建议位置：`为什么要做验证` 后。`file: ui/frontend/src/data/learnCases.ts:221-234` `file: knowledge/gold_standards/rayleigh_benard_convection.yaml:9-23`
- 🔴 flow-structure visualization：当前只有 `Nu(Ra)` 曲线，没有导热态 vs 对流态、plume、cell structure 的图。建议新增 annotated contour/streamline 图，放在 literature reference 前。`file: ui/frontend/src/data/flowFields.ts:63-69` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:358-388`
- 🟠 regime map：新增 `Ra_c≈1708` 到 `Ra=1e6` 当前工作点的 regime ladder，明确 2D/3D、steady/unsteady、Boussinesq validity 边界。`file: ui/frontend/src/data/learnCases.ts:224-234`
- 🟠 diagnostic checklist：把 gravity sign、reference temperature、sidewall insulation、oscillatory convergence、Boussinesq validity 做成 ordered troubleshooting table。`file: ui/frontend/src/data/learnCases.ts:230-234` `file: knowledge/gold_standards/rayleigh_benard_convection.yaml:5-22`
- 🟡 geometry/BC schematic：加一张 bottom hot / top cold / side insulated 的 labeled diagram，区分 RBC 与 DHC。建议放在 Mesh tab 标题前。`file: ui/frontend/src/data/learnCases.ts:231-233` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:996-1006`

### 9. differential_heated_cavity
**Current reading value**: `6/10`  
**If I were assigning reading material**: `conditional-on-補`

Differential heated cavity 是现有 10 个 case 里“regime selection pedagogy”最完整的一页之一。它把从 `Ra=1e10` 降到 `Ra=1e6` 的决定写成了一个教训：不是因为变简单就退缩，而是因为 `Ra=1e6` 才是当前网格和 solver 能诚实支撑的 benchmark。这种写法很符合 graduate methodology 的气质，因为它公开承认 benchmark 不是看起来越猛越好，而是要看“你能否把前提条件满足”。`file: ui/frontend/src/data/learnCases.ts:241-258` `file: knowledge/gold_standards/differential_heated_cavity.yaml:5-26`

不过，这页仍然没有把 differential heating 这个问题最值得读的物理讲足。学生知道左右壁一个热一个冷，上下绝热，也知道 `Nu_avg=8.80`，却还不知道为什么这个问题的主循环是由侧壁热羽和冷羽驱动、为什么热边界层主要长在竖壁而不是底壁、以及它与 Rayleigh-Bénard 的 bottom-heated mechanism 有什么根本不同。唯一 literature image 还是一张 `Nu(Ra)` scaling 图，对“difference-heated square cavity 里的 circulation cell 与 thermal plume”几乎没有视觉教学作用。`file: ui/frontend/src/data/flowFields.ts:98-105` `file: ui/frontend/src/data/learnCases.ts:244-258`

数值上，这页其实已经很适合升级成强阅读材料：它有清晰的 regime correction、有 de Vahl Davis 1983 这一经典 anchor、有 `δ_T/L≈0.032` 这类具体量纲估算，也有 `buoyantBoussinesqSimpleFoam + laminar` 的 solver story。它欠缺的只是“把数字和图像缝起来”。例如，页面没有一张 local `Nu(y)` 分布图，没有一张等温线/流线图，没有一张标出 hot wall、cold wall、adiabatic walls、gravity 方向和 circulation loop 的 schematic。Mesh tab 也只是在讲 convergence，不是在讲边界层主要生长在哪里。`file: ui/frontend/src/data/learnCases.ts:253-258` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:941-1095`

以篇幅看，这页大约 770 English-word equivalent，已经足以做一篇不错的 discussion note。补上“DHC vs RBC”的概念对照、plume/streamline 注释图、local `Nu(y)` 图，以及“为什么不追更高 Ra”的 failure-mode ladder 之后，我会愿意把它发给学生作为一篇短 reading。`file: ui/frontend/src/data/learnCases.ts:237-258`

**Concrete补齐 list** (prioritized):
- 🔴 DHC vs RBC contrast：必须明确写出“side-heated cavity 与 bottom-heated RBC 的驱动机制差异”，否则学生容易把两者混成一类自然对流。建议插在 `这个问题是什么` 后。`file: ui/frontend/src/data/learnCases.ts:248-258` `file: knowledge/gold_standards/differential_heated_cavity.yaml:5-17`
- 🔴 plume / circulation figure：当前没有一张侧热侧冷方腔里的流线/等温线注释图。建议新增 annotated contour，标出热羽、冷羽、主循环。`file: ui/frontend/src/data/flowFields.ts:98-105` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:358-388`
- 🟠 boundary-layer schematic：用一张 SVG 标出左右热边界层、上下绝热、gravity 方向和 local Nu integration 壁面。建议放在 Mesh tab 前。`file: ui/frontend/src/data/learnCases.ts:255-258` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:996-1006`
- 🟠 local observable expansion：除了 `Nu_avg=8.80`，建议再加一张 `Nu(y)` 或 wall heat-flux 分布图，让学生看到“平均值是怎么来的”。`file: ui/frontend/src/data/learnCases.ts:258` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:443-450`
- 🟡 failure ladder：把“Ra 提得过高 / wall cells 不够 / Boussinesq 使用越界 / gravity sign 错 / cached adapter artifact”整理成 ordered checklist。`file: ui/frontend/src/data/learnCases.ts:253-258` `file: knowledge/gold_standards/differential_heated_cavity.yaml:27-35`

### 10. duct_flow
**Current reading value**: `4/10`  
**If I were assigning reading material**: `skip`

Duct flow 当前是典型的“benchmark 数值对了，但该讲的物理没讲出来”的页面。`learnCases.ts` 确实提到了真正有趣的点：square duct 的 corner secondary flow 需要非线性湍流模型，线性 eddy-viscosity RANS 抓不住；`Darcy f` 是 canonical observable，不是平板的 `Cf`。gold YAML 也非常诚实地把过去 `pipe` 标签改成 `duct`，把 Jones 1976 的 rectangular-duct correlation 讲清楚。可问题在于，这些价值都被压在了“friction factor 命名诚实”的层面，真正让这个问题值得 graduate student 读的 secondary-flow physics 没有被展开。`file: ui/frontend/src/data/learnCases.ts:261-279` `file: knowledge/gold_standards/duct_flow.yaml:11-49`

现在的 literature image 只有一张 `f_vs_re` 曲线，这对于“为什么用 Jones 1976 而不是 Moody pipe chart”是有效的；但如果我是课程老师，我真正想让学生在这一页上学到的是：非圆截面湍流因为 Reynolds-stress anisotropy 会生成弱但真实的二次流，这些二次流怎样把高动量流体推向角区、为什么线性 `k-ε` 只能把 bulk friction factor 做对而抓不住 cross-stream pattern。页面目前没有任何 cross-section flow figure、没有任何 secondary-vortex 示意图、也没有任何“f 只是压缩掉这些复杂结构后的一个标量”这样的说明。`file: ui/frontend/src/data/flowFields.ts:107-114` `file: ui/frontend/src/data/learnCases.ts:269-279`

数值 pedagogy 方面，这页同样只走到了一半。它说了 `50·D_h` 的充分发展长度、`60×60` 截面足够估 `f`、`100×100` 才更适合看 corner secondary flow，也提到了 `y+<30` / `<1` 两种 wall-treatment 路线。可是学习页没有 geometry schematic，没有 `D_h=4A/P` 的图解，没有 periodic 与 long straight duct 两种建模方式的对照，没有“为什么 current benchmark 只看 `f` 而不看 secondary-vortex intensity”的方法学说明。更不用说 troubleshooting：如果 `f` 对了但 corner flow 完全没了，该怎么判断这是模型限制而不是代码 bug？这恰恰是 graduate class 最想读的内容。`file: ui/frontend/src/data/learnCases.ts:276-279` `file: knowledge/gold_standards/duct_flow.yaml:22-49`

目前这页大约 600 English-word equivalent，只能算“honest benchmark note”，远不到 assigned reading。我的结论是 skip，直到它把 cross-section physics、model limitation 和 diagnostic logic 补齐。`file: ui/frontend/src/data/learnCases.ts:261-279`

**Concrete补齐 list** (prioritized):
- 🔴 secondary-flow pedagogy：必须新增一段“为什么 square duct 会出现 corner secondary flow、为什么 `k-ε` 抓不住”的物理说明。建议插在 `这个问题是什么` 后。`file: ui/frontend/src/data/learnCases.ts:269-276` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:340-350`
- 🔴 cross-section visualization：当前没有任何截面二次流示意图。建议新增 cross-section vector/SVG 图，标出角区二次涡和高动量迁移路径。`file: ui/frontend/src/data/flowFields.ts:107-114`
- 🟠 geometry/definition schematic：补一张标出 square duct、`D_h=4A/P`、periodic vs long-duct setup、wall-function region 的图。建议放在 Mesh tab 前。`file: ui/frontend/src/data/learnCases.ts:277-279` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:996-1006`
- 🟠 benchmark rationale：参考区要说明为什么这里选 `f` 作为 canonical observable，而不是 pressure drop profile、secondary-flow intensity 或 Reynolds stress anisotropy。`file: ui/frontend/src/data/learnCases.ts:267-279` `file: knowledge/gold_standards/duct_flow.yaml:24-32` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:453-456`
- 🟡 diagnostic checklist：新增 “f 对了但 secondary flow 消失 / 入口未充分发展 / geometry label 错回 pipe / y+ 超界 / periodic BC 未闭合” 五步检查。`file: ui/frontend/src/data/learnCases.ts:274-279` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:397-404`

## Cross-case patterns
- TeachingCard bodies systematically lack “alternative path” discussion. 接口注释把四张 card 定义为“2-4 sentences, concrete numbers, novice-friendly”，这对 onboarding 很好，对 graduate reading 不够。统一建议：把每张 TeachingCard 升级成 5-8 句，固定包含 `why this choice`, `main alternative`, `if you switch, what changes`, `failure symptom` 四个槽位。`file: ui/frontend/src/data/learnCases.ts:33-39`
- All 10 cases lack a true benchmark-lineage section. 现在每个 case 只有一个 `canonical_ref` 字符串，而参考文献区只是回显这一行文本。建议在 Story tab 增加统一的 `Why this benchmark` 区块，字段可以扩成 `primary_ref`, `why_primary`, `secondary_ref`, `next_reading`。`file: ui/frontend/src/data/learnCases.ts:19-21` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:453-456`
- All 10 cases lack command-level reproducibility inline. Run tab 明确把 solver execution 推给 Pro Workbench，Story tab 的 `CFD 全流程` 只有叙事没有命令。建议每个 case 增加 5-7 行 command runbook，至少覆盖 mesh / solve / extract / compare 四步。`file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:410-440` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1245-1263`
- Mesh tab is globally under-pedagogical for geometry-specific learning. 现在它统一展示 quantity vs mesh density 的 slider 和 sparkline，这对“数值收敛”有用，但完全不能替代 domain/patch/measurement schematic。建议每个 case 在 Mesh tab 上方增加 case-specific 静态 schematic。`file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:996-1095`
- Visualization density is still too low for textbook-grade reading. `flowFields.ts` 里大多数 case 只有 1 张 literature figure；Tier-C visual-only 页面又只直接给出 1 张 contour + 1 张 residual。总图像预算够证明“做过”，不够支撑“读懂”。统一建议每个 case 至少配置：`(1) geometry/BC schematic`, `(2) one literature benchmark figure`, `(3) one annotated solver contour`, `(4) one workflow/observable figure`。`file: ui/frontend/src/data/flowFields.ts:18-116` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:358-388` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1617-1684`
- Failure-mode pedagogy is consistently underbuilt. 现在每页只有一个 `common_pitfall` 段落，这对提醒足够，对诊断不够。建议统一新增 `If this goes wrong` checklist，按 likelihood 排 4-6 条，格式固定为 `symptom / likely cause / first check / next fix`。`file: ui/frontend/src/data/learnCases.ts:29-31` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:397-404`
- Support tabs are unevenly pedagogical. Compare tab 偏 evidence surface，Mesh tab 偏 numeric control，Run tab 偏 CTA，Advanced tab 明确是 audit/governance for pro users。这些并不坏，但意味着 Story tab 必须承担更多 textbook-like narrative；目前它的负担和文本长度不匹配。`file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:17-25` `file: ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1434-1508`

## Summary: recommended batch plan for Claude

Grouped by theme, not per-case, for efficient implementation:

- Batch A: `Benchmark lineage + next-reading ladder`
  - Affected cases: all 10
  - Scope: 扩展 `learnCases.ts` narrative schema，为每个 case 增加 `why_this_ref`, `secondary_refs`, `next_reading_zh`，并在 Story tab `参考文献` 前新增 `历史基准链` 区块。
  - Why first: 这是阅读价值提升最大的低风险文字批次，能立刻把“单 citation token”升级成“可跟读的 benchmark lineage”。
  - Estimated LOC: `+250 ~ +400` lines in `learnCases.ts` + `+60 ~ +100` lines in `LearnCaseDetailPage.tsx`.

- Batch B: `Reproducibility runbook + failure checklist`
  - Affected cases: all 10
  - Scope: 每个 case 增加 `workflow_steps_zh` 和 `troubleshooting_zh` 数据块；Story tab 新增 “从 0 到结果” section，Run tab 新增 command snippet / checklist 渲染。
  - Why second: 用户当前不满意的一个核心点，是“这些页不值得读”；而可执行的 reproducing pipeline 与 diagnostic ladder 是把 product page 升级成 teaching page 的最短路径。
  - Estimated LOC: `+350 ~ +550` lines in `learnCases.ts` + `+120 ~ +180` lines in `LearnCaseDetailPage.tsx`.

- Batch C: `Geometry/BC schematics`
  - Affected cases: all 10
  - Scope: 为每个 case 新增 1 张 labeled SVG/ASCII schematic，至少标出 domain dimensions、patch types、采样位置、关键物理特征；在 Mesh tab 顶部统一渲染。
  - Why third: 当前 line-art hero 太中性，Mesh tab 又没有 geometry pedagogy；这个批次能显著提升“第一眼看懂问题设置”的能力。
  - Estimated LOC/assets: `10 张 SVG/JSON 资产` + `+80 ~ +140` lines render glue。

- Batch D: `Annotated solver evidence`
  - Affected cases: priority 6 = `lid_driven_cavity`, `backward_facing_step`, `circular_cylinder_wake`, `impinging_jet`, `naca0012_airfoil`, `differential_heated_cavity`
  - Scope: 在现有 `reports/phase5_renders/*/contour_u_magnitude.png` 基础上生成注释版 overlay，标出主涡/分离线/驻点/热羽/pressure recovery 等；Story tab 优先展示 “raw + annotated” 成对图。
  - Why fourth: 图像密度与教学密度是用户这轮 complaint 的核心，尤其是“case 没有阅读价值”往往就是因为没有 enough figures to think with。
  - Estimated LOC/assets: `6-12` 新增图像资产 + `+60 ~ +120` lines in rendering logic。

- Batch E: `TeachingCard 2.0`
  - Affected cases: all 10
  - Scope: 把四张 card 从“短说明”升级成“mini-essay”，统一加入 `why this choice`, `main alternative`, `when it breaks`, `what to inspect`。对 `plane_channel_flow` / `impinging_jet` / `duct_flow` 强化 “alternative solver/model path”。
  - Why fifth: 这是最接近 textbook paragraph 的文字升级，会把当前的“setup facts”提升成“numerical reasoning”。
  - Estimated LOC: `+300 ~ +500` lines in `learnCases.ts`, UI 改动很小。

- Batch F: `Three flagship reading upgrades`
  - Affected cases: `lid_driven_cavity`, `rayleigh_benard_convection`, `duct_flow`
  - Scope: 这三页是当前“最不像可分配阅读”的短板：LDC 需要 benchmark flagship 化，RBC 需要理论链重建，duct 需要把 secondary-flow physics 从暗线拉成主线。每页做专项扩写与专项配图。
  - Why last: 这是高收益但 case-specific 的深加工，适合在通用基建完成后做。
  - Estimated LOC/assets: `每页 +120 ~ +220 行 narrative 等价内容`，外加 1-2 张新增图/页。

如果只做一轮、追求 impact-per-LOC，我建议 Claude 的优先顺序是：`Batch A → Batch B → Batch C → Batch F`。A/B 会先把“能不能读”从 4/10 拉到 6/10；C/F 才能把部分 case 拉到真正接近 graduate reading 的 7/10+。
