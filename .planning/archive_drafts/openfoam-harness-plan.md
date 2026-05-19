# OpenFOAM CLI Harness — Standard Operating Procedure

> CLI-Anything 方法论应用于 OpenFOAM 仿真工作流

---

## 1. Overview

本 SOP 定义了为 OpenFOAM 构建 CLI harness 的完整方法论。目标：让 AI Agent 通过标准化 CLI 控制 OpenFOAM 的完整仿真流程——从前处理网格生成、求解器运行、到后处理结果提取——无需人工操作 GUI。

### 设计哲学

```
Agent → CLI-Anything-OpenFOAM → OpenFOAM 原生 CLI (blockMesh, snappyHexMesh, simpleFoam)
                                           ↓
                              生成有效 case 文件 → 调用真实求解器
```

**核心原则**：
- **使用真实 OpenFOAM** — CLI 必须调用 `blockMesh`, `snappyHexMesh`, `simpleFoam` 等真实命令，不重新实现求解器
- **操作原生格式** — 直接读写 `controlDict`, `fvSchemes`, `fvSolution`, `U`, `p` 等文件
- **版本兼容** — 通过自动检测 OpenFOAM 版本，屏蔽版本间的 case 结构差异
- **零妥协** — 没有 GUI、没有截图、没有 RPA，只有纯文本命令和文件操作

---

## 2. OpenFOAM 仿真工作流分析

### 2.1 仿真生命周期

```
┌──────────────────────────────────────────────────────────────────┐
│                        仿真生命周期                                │
│                                                                  │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐         │
│  │  几何    │ → │  网格    │ → │  求解    │ → │  后处理  │         │
│  │  准备    │   │  生成    │   │  运行    │   │  提取    │         │
│  └─────────┘   └─────────┘   └─────────┘   └─────────┘         │
│                                                                  │
│  外围支持：参数化研究、多case管理、结果对比、可视化脚本             │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 OpenFOAM 核心 CLI 工具

| 阶段 | 命令 | 用途 |
|------|------|------|
| **网格** | `blockMesh` | 从 blockMeshDict 生成结构化网格 |
| **网格** | `snappyHexMesh` | 从 STL/STEP 生成复杂边界层网格 |
| **网格** | `cfMesh` | 另外的网格生成选项 |
| **网格** | `checkMesh` | 网格质量检查 |
| **网格** | `transformPoints` | 几何变换 |
| **求解** | `setFields` | 初始化场（IC, volumeFraction） |
| **求解** | `simpleFoam` | 稳态不可压缩求解器 |
| **求解** | `icoFoam` | 瞬态不可压缩求解器 |
| **求解** | `pimpleFoam` | 大时间步瞬态求解器（可压缩/不可压缩） |
| **求解** | `rhoSimpleFoam` | 稳态可压缩求解器 |
| **求解** | `chtMultiRegionFoam` | 多区域耦合求解器（热、结构等） |
| **后处理** | `postProcess` | 内置后处理（grad, div, curl 等） |
| **后处理** | `reconstructPar` | 并行结果重建 |
| **后处理** | `decomposePar` | 并行分解 |
| **工具** | `foamDictionary` | 查询/修改字典文件 |
| **工具** | `foamCalc` | 场计算 |
| **工具** | `patchAverage` | 面平均值提取 |
| **工具** | `wallShearStress` | 壁面剪切应力 |

### 2.3 Case 目录结构

```
motorBike/
├── constant/
│   ├── polyMesh/           # 网格（blockMesh 后生成）
│   │   └── boundary        # 边界条件定义
│   ├── triSurface/         # STL 几何文件
│   │   └── motorBike.stl
│   ├── transportProperties
│   ├── turbulenceProperties
│   └── RASProperties
├── system/
│   ├── controlDict         # 求解器控制（时间、步长、输出）
│   ├── fvSchemes           # 离散格式（梯度、发散、 Laplacian）
│   ├── fvSolution          # 线性求解器设置
│   ├── meshQualityDict     # 网格质量标准
│   └── decomposeParDict    # 并行分解设置
├── 0/                      # 初始/边界条件（时间步 0）
│   ├── U                   # 速度场
│   ├── p                   # 压力场
│   ├── epsilon            # 湍流耗散率
│   └── nut                 # 湍流粘度
└── 0.orig/                # 初始条件备份模板
```

### 2.4 OpenFOAM 版本差异

| 版本 | case 格式变化 | 主要差异 |
|------|--------------|----------|
| v2312 / v2406 | 23xx 系列 | `fvModels`, `fvConstraints` 引入 |
| v10 | 24.xx 系列 | 名称规范，边界条件格式更严格 |
|ESI 版 | OpenFOAM.org | 路径略有不同 |
| Foundation 版 | OpenFOAM.com | 部分命令差异 |

**CLI 必须自动检测版本并适配**。

---

## 3. Phase 1: Codebase Analysis

### 3.1 分析目标

1. **定位 OpenFOAM 安装** — 找到 `OpenFOAM` 环境变量指向的安装路径
2. **识别可用求解器** — 检查 `$FOAM_APPBIN` 中的可用命令
3. **理解 case 数据模型** — 解析 `controlDict`, `fvSchemes`, `fvSolution` 格式
4. **映射 GUI 操作到 CLI** — 每个 GUI 操作对应哪些 OpenFOAM 命令和文件修改

### 3.2 分析输出：Software SOP

创建 `openfoam/OPENFOAM.md`：

```markdown
# OpenFOAM CLI - Software-Specific SOP

## OpenFOAM 安装

- 路径：`$FOAM_PROJECT_DIR`（通常是 `/opt/openfoam10` 或 `~/OpenFOAM/OpenFOAM-10`）
- 版本检测：`foamVersion` 文件内容
- 关键命令：`blockMesh`, `snappyHexMesh`, `simpleFoam`, `pimpleFoam`, `postProcess`

## Case 文件格式

### controlDict 关键字段
- `startFrom`: latestTime | startTime | constant
- `startTime`: scalar
- `endTime`: scalar
- `deltaT`: scalar
- `writeControl`: timeStep | runTime | adjustableRunTime | clockTime | cpuTime
- `writeInterval`: scalar
- `purgeWrite`: int
- `solver`: 选择求解器

### fvSchemes 格式
```yaml
ddtSchemes:
  default: Euler

divSchemes:
  default: none
  div(phi,U): Gauss linearV

laplacianSchemes:
  default: Gauss linear corrected
```

### fvSolution 格式
```yaml
solvers:
  p:
    solver: PCG
    tolerance: 1e-6
    relTol: 0.01

relaxationFactors:
  fields:
    p: 0.3
  equations:
    U: 0.7
```

## 网格生成流程

1. 创建 case 目录结构
2. 编写 `system/controlDict`（仅 mesh 相关设置）
3. 编写 `constant/polyMesh/boundary` 或 `system/snappyHexMeshDict`
4. 调用 `blockMesh` 或 `snappyHexMesh`
5. 可选：`checkMesh -latestTime`

## 求解运行流程

1. 设置边界条件（0/ 目录）
2. 设置 `system/controlDict`（时间、步长、求解器）
3. 设置 `system/fvSchemes`
4. 设置 `system/fvSolution`
5. 可选： decompositionPar
6. 调用求解器
7. 监控日志输出

## 后处理流程

1. `postProcess -func <functionObject>` 或
2. 使用 ParaView + `paraFoam` 或
3. `foamCalc` 直接提取标量
4. `reconstructPar` 重建并行结果
```

---

## 4. Phase 2: CLI Architecture Design

### 4.1 命令组设计

```
openfoam
├── case
│   ├── new          # 创建新 case 目录结构
│   ├── info         # 显示 case 信息
│   ├── validate     # 验证 case 完整性
│   ├── list         # 列出已有 cases
│   └── convert      # 版本/格式转换
│
├── mesh
│   ├── generate     # 生成网格（blockMesh / snappyHexMesh）
│   ├── check        # checkMesh 质量检查
│   ├── refine       # 网格加密
│   ├── transform    # 几何变换
│   └── export       # 导出为其他格式
│
├── setup
│   ├── boundary     # 设置边界条件
│   ├── properties   # 设置物性（湍流、输运属性）
│   ├── schemes      # 设置离散格式
│   ├── solvers      # 设置求解器参数
│   ├── initial      # 设置初始条件
│   └── parameters   # 参数化设置（替换变量）
│
├── solve
│   ├── run          # 运行求解器
│   ├── status       # 查看运行状态
│   ├── stop         # 停止求解
│   ├── decompose    # 并行分解
│   └── reconstruct  # 重建并行结果
│
├── postprocess
│   ├── extract      # 场提取（压力、速度、湍流量）
│   ├── average      # 空间/时间平均
│   ├── probe        # 探针点数据
│   ├── forces       # 力/力矩计算
│   ├── field        # 场计算（梯度、散度、旋度）
│   └── report       # 生成标准报告
│
├── parameters
│   ├── set          # 设置参数值
│   ├── sweep        # 参数扫描（单参数）
│   ├── design       # DOE 设计
│   └── optimize     # 优化运行
│
└── session
    ├── save        # 保存 session
    ├── load        # 加载 session
    ├── undo        # 撤销
    ├── redo        # 重做
    └── history     # 历史记录
```

### 4.2 状态模型

```json
{
  "version": "1.0",
  "openfoam_version": "v2312",
  "case_path": "/cases/motorBike",
  "case_name": "motorBike",
  "state": {
    "phase": "solved",
    "current_time": 1000,
    "latest_time": 1000,
    "mesh_exists": true,
    "running": false
  },
  "configuration": {
    "solver": "simpleFoam",
    "mesh_method": "snappyHexMesh",
    "turbulence": "kEpsilon",
    "parallel": false,
    "processors": 4
  },
  "parameters": {
    "U_inlet": 10.0,
    "nu": 1e-5,
    "k": 0.1,
    "epsilon": 0.01
  },
  "boundary_conditions": {
    "U": { "inlet": {"type": "fixedValue", "value": [10, 0, 0]} },
    "p": { "outlet": {"type": "zeroGradient"} }
  },
  "history": []
}
```

### 4.3 输出格式

**Human mode**:
```
✓ Mesh generated: 2.3M cells in 45s
✓ Solver converged in 124 iterations
✓ Residuals: p=1.2e-6, U=8.3e-7
```

**JSON mode** (`--json`):
```json
{
  "status": "success",
  "phase": "solve",
  "time": 1000,
  "residuals": {
    "p": 1.2e-6,
    "U": 8.3e-7,
    "epsilon": 2.1e-5
  },
  "iterations": 124,
  "duration_seconds": 45.2
}
```

---

## 5. Phase 3: Implementation

### 5.1 目录结构

```
openfoam/
└── agent-harness/
    ├── OPENFOAM.md              # 本文档
    ├── setup.py                 # PyPI 配置
    └── cli_anything/            # PEP 420 命名空间
        └── openfoam/            # 子包（__init__.py 存在）
            ├── __init__.py
            ├── __main__.py      # python -m cli_anything.openfoam
            ├── README.md         # 安装与使用
            ├── openfoam_cli.py   # Click CLI 入口
            │
            ├── core/
            │   ├── __init__.py
            │   ├── case.py       # case 创建/打开/保存/信息
            │   ├── mesh.py       # 网格生成命令
            │   ├── setup.py      # 边界/物性/格式设置
            │   ├── solve.py      # 求解器运行
            │   ├── postprocess.py # 后处理提取
            │   ├── parameters.py  # 参数化研究
            │   └── session.py    # undo/redo 状态管理
            │
            ├── utils/
            │   ├── __init__.py
            │   ├── openfoam_backend.py  # OpenFOAM CLI 封装
            │   ├── version.py     # 版本检测与适配
            │   ├── dict_parser.py # OpenFOAM 字典解析
            │   └── repl_skin.py   # 统一 REPL 皮肤（复制自 plugin）
            │
            └── tests/
                ├── TEST.md       # 测试计划与结果
                ├── test_core.py   # 单元测试
                └── test_full_e2e.py # E2E 测试
```

### 5.2 核心模块 API

#### `openfoam_backend.py` — OpenFOAM 真实命令封装

```python
"""关键函数签名"""

def find_openfoam() -> tuple[str, str]:
    """返回 (OpenFOAM安装路径, 版本字符串)
    找不到时抛出 RuntimeError 并给出安装指令"""

def run_blockmesh(case_path: Path, dict_path: Path | None = None) -> dict:
    """调用 blockMesh，返回 {'success': bool, 'output': str, 'cells': int}"""

def run_snappyhexmesh(case_path: Path, stl_name: str, **kwargs) -> dict:
    """调用 snappyHexMesh，支持 parallel 参数"""

def run_solver(case_path: Path, solver: str, parallel: bool = False,
               n_processors: int = 1, **kwargs) -> dict:
    """调用求解器（simpleFoam/icoFoam/pimpleFoam 等）
    返回 {'success': bool, 'final_time': float, 'residuals': dict}"""

def run_checkmesh(case_path: Path) -> dict:
    """checkMesh 质量检查"""

def run_postprocess(case_path: Path, func: str, time: str = "latestTime") -> dict:
    """postProcess 调用"""

def extract_patch_average(case_path: Path, field: str, patch: str, time: str = "latestTime") -> float:
    """提取某 patch 上某场的平均值"""

def get_latest_time(case_path: Path) -> float:
    """获取 case 最新时间目录"""

def get Foam_version() -> str:
    """检测 OpenFOAM 版本"""
```

#### `dict_parser.py` — OpenFOAM 字典解析

```python
"""OpenFOAM 字典（dictionary）文件解析/写入"""

def read_dict(path: Path) -> dict:
    """读取 OpenFOAM 字典文件为 Python dict（支持嵌套）"""

def write_dict(path: Path, data: dict) -> None:
    """将 Python dict 写回 OpenFOAM 字典格式"""

def patch_dict(path: Path, updates: dict) -> None:
    """部分更新字典文件"""

def substitute_vars(path: Path, var_map: dict) -> None:
    """替换 #var# 形式的变量"""
```

#### `version.py` — 版本检测与适配

```python
"""版本兼容性层"""

FOAM_VERSIONS = ["v2312", "v2406", "v10", "v2412"]

def detect_version() -> str:
    """自动检测 OpenFOAM 版本"""

def get_case_template(version: str) -> dict:
    """获取指定版本的 case 目录模板"""

def get_solver_aliases(version: str) -> dict:
    """获取求解器别名（如 simpleFoam 在不同版本的路径）"""
```

### 5.3 命令组实现细节

#### `case new`

```bash
openfoam case new --name motorBike --template simpleFoam [--parallel 4]
```

行为：
1. 创建 `motorBike/` 目录结构
2. 从模板复制 `system/`, `constant/`, `0/`（根据求解器类型选择模板）
3. 自动检测 OpenFOAM 版本并适配
4. 生成 session JSON 文件
5. 返回 case 信息

#### `mesh generate`

```bash
# blockMesh 方式
openfoam mesh generate --method blockmesh --dict blockMeshDict.yaml

# snappyHexMesh 方式
openfoam mesh generate --method snappy --geometry motorBike.stl \
    --castellated --snap -- layers --quality

# 或指定复杂参数
openfoam mesh generate --method snappy \
    --geometry motorBike.stl \
    --maxLocalCells 10000000 \
    --maxGlobalCells 20000000 \
    --featureAngle 30 \
    --nCellsBetweenLevels 3 \
    --resolution 2
```

#### `setup boundary`

```bash
openfoam setup boundary --patch inlet --type patch
openfoam setup boundary --patch wall --type wall --condition "noSlip"
openfoam setup boundary --patch outlet --type patch
```

支持 YAML 批量配置：
```bash
openfoam setup boundary --from-yaml boundaries.yaml
```

#### `solve run`

```bash
# 本地运行
openfoam solve run --solver simpleFoam

# 并行运行
openfoam solve run --solver simpleFoam --parallel --processors 8

# 带监控
openfoam solve run --solver simpleFoam --monitor residual --interval 10

# 后台运行
openfoam solve run --solver pimpleFoam --detach
```

---

## 6. Phase 4: Test Planning

### 6.1 测试清单

#### Unit Tests (`test_core.py`) — ~80 tests

| 模块 | 函数 | 测试内容 | 预估数 |
|------|------|----------|--------|
| `version.py` | `detect_version` | 检测各版本路径 | 5 |
| `version.py` | `get_solver_aliases` | 别名映射正确 | 4 |
| `dict_parser.py` | `read_dict` | 解析 controlDict, fvSchemes, fvSolution | 10 |
| `dict_parser.py` | `write_dict` | 写回格式与原始一致 | 8 |
| `dict_parser.py` | `patch_dict` | 部分更新不破坏其他字段 | 6 |
| `dict_parser.py` | `substitute_vars` | 变量替换正确 | 5 |
| `openfoam_backend.py` | `find_openfoam` | 找不到时报错，找得到返回路径 | 3 |
| `openfoam_backend.py` | `get_latest_time` | 各时间目录格式 | 6 |
| `case.py` | `create_case` | 目录结构正确创建 | 8 |
| `case.py` | `validate_case` | 缺文件时报告正确 | 5 |
| `mesh.py` | `parse_checkmesh_output` | 残差解析正确 | 6 |
| `session.py` | `undo_redo` | 状态正确保存/恢复 | 8 |
| `solve.py` | `parse_residuals` | 日志解析 | 6 |
| **总计** | | | **80** |

#### E2E Tests (`test_full_e2e.py`) — ~60 tests

**E2E Native**（不调用真实求解器）：

| 测试场景 | 验证内容 | 预估数 |
|----------|----------|--------|
| 创建 simpleFoam case | 目录结构、文件内容正确 | 8 |
| 创建 pimpleFoam case | 目录结构正确、求解器参数不同 | 6 |
| 设置边界条件 | controlDict / 0/U 内容正确 | 10 |
| 修改物性参数 | transportProperties 正确 | 6 |
| 参数替换 | `#var#` 替换生效 | 5 |
| session 保存/加载 | JSON 序列化正确 | 5 |
| **小计** | | **40** |

**E2E True Backend**（调用真实 OpenFOAM）：

| 测试场景 | 验证内容 | 预估数 |
|----------|----------|--------|
| `blockMesh` 运行 | 网格生成、boundary 文件存在 | 4 |
| `checkMesh` 运行 | 输出解析、cells 数量合理 | 3 |
| `simpleFoam` 短运行（10步） | 收敛、结果文件存在 | 4 |
| `postProcess` 提取 | 提取的数值合理 | 3 |
| 并行分解/重建 | 结果一致性 | 3 |
| 完整工作流 | case → mesh → solve → extract | 3 |
| **小计** | | **20** |

**总计：100 tests**

### 6.2 真实工作流测试场景

#### Scenario 1: 稳态外流仿真

```
Simulates: 汽车外流场稳态仿真
Operations:
  1. case new --name carAero --template simpleFoam
  2. setup boundary --patch inlet --type velocity --value "10 0 0"
  3. mesh generate --method blockmesh --geometry "box"
  4. solve run --solver simpleFoam --endTime 500
  5. postprocess extract --field U --patch outlet --operator average
Verified:
  - 网格存在且 > 0 cells
  - 求解器收敛（残差 < 1e-5）
  - U 提取值在合理范围
```

#### Scenario 2: 瞬态层流到湍流

```
Simulates: 圆柱绕流瞬态仿真
Operations:
  1. case new --name cylinder --template icoFoam
  2. setup initial --field U --type uniform --value "1 0 0"
  3. mesh generate --method blockmesh
  4. solve run --solver icoFoam --deltaT 0.001 --endTime 5.0
  5. postprocess extract --field U --probe "(0.1 0 0)" --operator timeHistory
Verified:
  - 时间序列数据完整
  - 流场符合物理规律
```

#### Scenario 3: 参数化 DOE

```
Simulates: 入口速度参数扫描
Operations:
  1. case new --name paramStudy --template simpleFoam
  2. parameters sweep --var U_inlet --values "5 10 15 20"
  3. for each value: solve run --solver simpleFoam --endTime 200
  4. postprocess extract --field dragForce --patch body
Verified:
  - 所有 case 收敛
  - dragForce 与速度单调关系
```

---

## 7. Phase 5: Implementation — 关键设计决策

### 7.1 Case 文件操作：直接读写，不调用求解器

OpenFOAM 的 case 文件是纯文本（字典格式），Python 可以直接读写，无需调用任何 OpenFOAM 命令即可：
- 读取 `controlDict` → `foamDictionary` 或直接读文件
- 修改 `fvSchemes` → 直接写文件
- 设置边界条件 → 写 `0/U`, `0/p` 等文件

只有**渲染/求解/后处理**才需要调用真实 OpenFOAM 命令。

### 7.2 版本适配：自动检测 + 模板系统

```python
def _get_case_template(solver: str, version: str) -> dict:
    templates = {
        "simpleFoam": {
            "v2312": {...},
            "v2406": {...},
            "v10": {...},
        },
        "icoFoam": {...},
    }
    return templates.get(solver, templates["simpleFoam"]).get(version)
```

### 7.3 并行支持：自动检测 MPI

```python
def _detect_mpi() -> bool:
    """检查是否安装了 OpenMPI 或 MPICH"""
    return shutil.which("mpirun") is not None
```

### 7.4 渲染 Gap 规避

OpenFOAM CLI 的"渲染"就是求解器运行本身。CLI-Anything 的 OpenFOAM harness 不生成中间格式再转换，而是：
1. **生成有效 case 文件**（Python 直接写 OpenFOAM 字典格式）
2. **调用真实求解器**（`simpleFoam`, `pimpleFoam` 等）
3. **验证输出**（检查时间目录、场文件、收敛指标）

---

## 8. Phase 6: Test Documentation

（TEST.md 模板 — 实施后填入结果）

```markdown
# OpenFOAM CLI - Test Plan & Results

## Test Inventory

- `test_core.py`: ~80 unit tests planned
- `test_full_e2e.py`: ~60 E2E tests planned
- **Total**: ~140 tests planned

## Unit Test Plan

### dict_parser.py
- `read_dict`: 解析 OpenFOAM 字典格式，包括嵌套字典
- `write_dict`: 写回格式与原始一致（保留 FoamFile 头）
- `patch_dict`: 部分更新保留其他字段
- `substitute_vars`: #VAR# 形式变量替换

### openfoam_backend.py
- `find_openfoam`: 找不到时报错信息友好
- `get_latest_time`: 支持 0, 0.1, 1000 等格式
- `parse_checkmesh_output`: 解析 Quality 表格

### case.py
- `create_case`: 目录结构完整
- `validate_case`: 检测缺失文件

## E2E Test Plan

### Native (no real OpenFOAM)
- 创建各类型 case 模板
- 边界条件 YAML 配置
- 参数替换

### True Backend (real OpenFOAM commands)
- blockMesh 端到端
- simpleFoam 短时收敛
- postProcess 场提取

## Test Results

(after running pytest -v --tb=no)
```

---

## 9. Phase 6.5: SKILL.md Generation

生成 `cli_anything/openfoam/skills/SKILL.md`：

```yaml
---
name: "cli-anything-openfoam"
description: "OpenFOAM CFD simulation workflow CLI - mesh generation, solver execution, and post-processing"
---

# OpenFOAM CLI Skill

## Installation

```bash
pip install cli-anything-openfoam
# Requires: OpenFOAM (apt install openfoam)
```

## Command Groups

### case
- `case new --name <name> --template <solver>` - 创建新 case
- `case info --project <path>` - 显示 case 信息
- `case validate --project <path>` - 验证完整性

### mesh
- `mesh generate --method <blockmesh|snappy> ...` - 生成网格
- `mesh check --project <path>` - 网格质量检查

### setup
- `setup boundary --project <path> --patch <name> ...` - 设置边界条件
- `setup properties --project <path> --turbulence <model>` - 设置物性

### solve
- `solve run --project <path> --solver <name>` - 运行求解器
- `solve status --project <path>` - 查看状态

### postprocess
- `postprocess extract --project <path> --field <name> --patch <name>` - 提取场数据

## JSON Mode

所有命令支持 `--json` 输出：

```bash
openfoam case info --project ./motorBike --json
```

## Agent Usage

```bash
# 完整外流场仿真工作流
openfoam case new --name carAero --template simpleFoam -o carAero.json
openfoam setup boundary --project ./carAero --patch inlet --type velocity --value "10 0 0"
openfoam mesh generate --project ./carAero --method blockmesh
openfoam solve run --project ./carAero --solver simpleFoam --endTime 500
openfoam postprocess extract --project ./carAero --field U --patch outlet --operator average
```
```

---

## 10. Phase 7: PyPI Publishing

### setup.py

```python
from setuptools import setup, find_namespace_packages

setup(
    name="cli-anything-openfoam",
    version="1.0.0",
    packages=find_namespace_packages(include=["cli_anything.*"]),
    install_requires=[
        "click>=8.0.0",
        "prompt-toolkit>=3.0.0",
        "pyyaml>=6.0",
    ],
    entry_points={
        "console_scripts": [
            "cli-anything-openfoam=cli_anything.openfoam.openfoam_cli:main",
        ],
    },
    python_requires=">=3.10",
    package_data={
        "cli_anything.openfoam": ["skills/*.md"],
    },
)
```

### README.md 关键内容

```markdown
# OpenFOAM CLI

## 依赖

- **Python 3.10+**
- **OpenFOAM** — `apt install openfoam`（Debian/Ubuntu）或从 openfoam.org 安装

## 安装

```bash
pip install git+https://github.com/YOUR_NAME/cli-anything-openfoam.git
```

## 快速开始

```bash
# 创建 case
cli-anything-openfoam case new --name motorBike --template simpleFoam

# 设置边界
cli-anything-openfoam setup boundary --project ./motorBike --patch inlet --type velocity --value "10 0 0"

# 生成网格
cli-anything-openfoam mesh generate --project ./motorBike --method blockmesh

# 运行求解
cli-anything-openfoam solve run --project ./motorBike --solver simpleFoam --endTime 1000

# 提取结果
cli-anything-openfoam postprocess extract --project ./motorBike --field U --patch body --operator average
```

## 测试

```bash
cd openfoam/agent-harness
python -m pytest cli_anything/openfoam/tests/ -v
CLI_ANYTHING_FORCE_INSTALLED=1 python -m pytest cli_anything/openfoam/tests/ -v -s
```
```

---

## 11. 关键经验教训（从已有 Harness 提炼）

### Lesson 1: 使用真实软件是硬性要求

```
✅ 正确：生成 blockMeshDict → 调用 blockMesh → 验证网格文件
❌ 错误：用 Python 写一个"类似 OpenFOAM"的求解器
```

### Lesson 2: 验证输出，而非仅检查退出码

```python
# 错误做法
result = subprocess.run(["simpleFoam"], check=True)
return result.returncode == 0

# 正确做法
result = subprocess.run(["simpleFoam"], check=True)
latest = get_latest_time(case_path)
assert latest >= start_time, "Time didn't advance"
assert (case_path / latest / "U").exists(), "Velocity field not written"
assert residuals["U"] < 1e-5, "Not converged"
```

### Lesson 3: 版本差异必须屏蔽

OpenFOAM v10 与 v2312 的 `controlDict` 格式有细微差异。CLI 必须在写入前检测版本并规范化。

### Lesson 4: 文件锁用于 session 保存

当多个 CLI 命令同时修改同一 session JSON 时，需要文件锁：
- 使用 `fcntl.LOCK_EX`（macOS/Linux）
- Windows 回退到无锁（可能损坏时警告）

---

## 12. 实施路线图

```
Week 1: Phase 1-2
  ├── OpenFOAM 安装检测与版本适配
  ├── 字典解析器实现
  ├── case 创建/验证命令

Week 2: Phase 3 (mesh + setup)
  ├── blockMesh/snappyHexMesh 封装
  ├── 边界条件设置命令
  ├── 物性/湍流模型设置

Week 3: Phase 3 (solve + postprocess)
  ├── 求解器运行与监控
  ├── 后处理提取命令
  ├── 并行支持

Week 4: Phase 4-6
  ├── 测试编写
  ├── 完整 E2E 验证
  └── TEST.md 完成

Week 5: Phase 6.5-7
  ├── SKILL.md 生成
  ├── setup.py + PyPI 发布
  └── README 完善
```

---

*本文档遵循 CLI-Anything HARNESS.md 方法论*
