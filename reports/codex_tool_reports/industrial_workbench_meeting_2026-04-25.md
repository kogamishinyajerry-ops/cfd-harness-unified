## 节1 · 现状裁定
**Sarah**: 还差65%，我能读懂报告，但还不能不看 README 就安全跑完一次设置。  
**David**: 还差80%，现在是“研究级验证报告台”，不是“工业级操作台”。  
**Maya**: 还差72%，信息层级失控，Story 页文字把界面吃掉了。  
**Kai**: 还差78%，没有 geometry/mesh/bc schema，就没有稳定的 workbench 可视化底座。  
**Lin**: 还差60%，教学解释够强，但防误设 checkpoint 还没接管流程。  

## 节2 · Sarah 12 步用户旅程
| 步骤名 | 核心可视化 primitive | 视觉/数据完成信号 | ANSYS Fluent 类比 |
|---|---|---|---|
| 选案 | case matrix | 10 case 状态一眼分层 | Launcher |
| 看几何 | topology SVG | 区域/入口/出口/壁面全点亮 | Display |
| 设物性 | property strip | rho/mu/T 全绿 | Materials |
| 设边界 | BC pin-map | 每个 patch 有 type/value/unit | Boundary Conditions |
| 选模型 | model ladder | solver/湍流/稳态锁定 | Models |
| 看网格 | mesh ladder | 4 档密度可切 | Mesh Display |
| 查质量 | QC band | skew/non-orth/y+ 红黄绿 | Mesh Metrics |
| 跑基线 | checkpoint rail | preflight 5/5 pass | Initialize+Run |
| 盯收敛 | residual SVG | 下降、平台、异常点可见 | Residual Monitor |
| 对gold | overlay SVG | 容差带+偏差点可见 | XY Plot |
| 批量扫 | batch matrix | ≥4 runs 热图完成 | Parametric Study |
| 出报告 | export panel | PDF+xlsx 双绿 | Reports |

## 节3 · 5 个核心 viz primitive 技术方案
| primitive 名 | 库选型 | 关键能力 | 当前 stack 距离 | bundle 估计 | 依赖 |
|---|---|---|---|---|---|
| CaseFrame | 手写 SVG + Tailwind | 几何/patch/BC 一屏 | 远 | 6-10KB | 新 basics endpoint |
| MeshQC | SVG bars | skew/non-orth/y+/GCI | 中 | 4-8KB | 新 mesh-metrics |
| ContractOverlay | SVG + 后端 PNG | gold vs run + tol band | 近 | 8-12KB | 现有 context/renders |
| RunRail | SVG + react-query | checkpoint/residual/live 状态 | 中 | 5-9KB | 现有 stream/checkpoints |
| BatchMatrix | SVG heatmap | 多 run 对比/export | 中偏远 | 6-12KB | 新 aggregate+xlsx |

**Kai**: 若破约束硬上 3D，`vtk.js` npm unpacked 约 30.3MB，`three` 约 37.0MB，`@react-three/fiber` 约 2.17MB 但仍绑 `three`，`trame-vtk` PyPI 分发约 1.64MB 且要 WebSocket/冷启动；本项目当前都输给手写 SVG + 后端 PNG。  

## 节4 · Roadmap (signal-driven · 6 stage)
- `Maya vs David`：Story 常显只留 3 张风险卡；`fvSchemes/fvSolution` 错误进红色 checkpoint，可展开证据，不回到长文。
- `Kai vs Sarah`：不上 trame 常驻长连接；`/learn` 全 HTTP+PNG/SVG，`/pro/run` 用户点 `Live` 才开 SSE。
- `Lin vs Sarah`：guided tour 首访默认 3 步，但首屏可“跳过并记住”；之后只在 checkpoint fail 再唤起。

| Stage | start trigger（signal） | 主交付 viz | 依赖 | 风险 |
|---|---|---|---|---|
| S1 壳层拆分：拆 3294 LOC 单页 | `LOC>2500 && tabs=5` | summary strip | 现有路由 | 路由碎裂 |
| S2 CaseFrame：几何/物性/BC 一屏 | 10 case basics 映射≥8 | topology SVG | 新 basics endpoint | schema drift |
| S3 MeshTrust：质量/GCI 红黄绿 | 4 档 mesh 数据≥8 case | QC band | 新 mesh-metrics | 假安全感 |
| S4 GuardedRun：tour+checkpoint | preflight 事件≥5类 | run rail | stream/checkpoints | 打扰感 |
| S5 GoldOps：overlay+batch | 3 anchor case compare 完整率=100% | overlay+matrix | context + aggregate | 过载 |
| S6 ExportPack：PDF+xlsx | batch rows≥30 且字段齐套=100% | export manifest | pdf + xlsx | 证据不一致 |

## 节5 · David 综合 verdict
> 工业级目标可达68%。底子强在 10 case、gold-overlay、PDF 链路；短板是几何/网格/BC schema 缺位。3294 LOC 不重写，先拆。`/learn` 与 `/pro` 保留双轨：前者前门，后者批量与证据。最糟反模式是“把报告页伪装成工作台”。Stage1 触发后第一周，只做 `workbench-basics` endpoint + CaseFrame 首屏。

