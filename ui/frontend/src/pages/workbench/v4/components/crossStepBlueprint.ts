import type { V4PipelineStepId } from "@/theme/industrial_minimalist";

export interface V4ViewportModeSpec {
  id: V4PipelineStepId;
  label: string;
  englishLabel: string;
  description: string;
}

export const CROSS_STEP_BLUEPRINT_TASK = {
  sourceImage: ".planning/blueprints/v3/08-cross-step.png",
  pageTask: "求解仍在运行时，把主视图切到网格检查而不中断 pipeline 状态",
  activePipelineStep: "solver",
  viewportMode: "mesh",
  bottomDock: "residuals",
} as const;

export const CROSS_STEP_BLUEPRINT_DOCK = {
  activeStep: "solver",
  viewportMode: "mesh",
  content: "residuals",
  label: "Residuals dock",
  note: "Pipeline stays on Solver while the main viewport inspects Mesh.",
} as const;

export const V4_VIEWPORT_MODES = [
  {
    id: "import",
    label: "导入",
    englishLabel: "Import",
    description: "源文件摄入与 provenance",
  },
  {
    id: "geometry",
    label: "几何",
    englishLabel: "Geometry",
    description: "CAD 分件与装配关系",
  },
  {
    id: "mesh",
    label: "网格",
    englishLabel: "Mesh",
    description: "线框层与网格质量",
  },
  {
    id: "physics",
    label: "物理",
    englishLabel: "Physics",
    description: "物理场和模型配置",
  },
  {
    id: "boundary",
    label: "边界",
    englishLabel: "Boundary",
    description: "BC patch 贴体着色",
  },
  {
    id: "solver",
    label: "求解",
    englishLabel: "Solver",
    description: "流线、残差和遥测",
  },
  {
    id: "post",
    label: "后处理",
    englishLabel: "Post",
    description: "结果场与 TrustGate",
  },
  {
    id: "doe",
    label: "DOE",
    englishLabel: "DOE",
    description: "设计探索候选集",
  },
] as const satisfies readonly V4ViewportModeSpec[];

export function viewportModeLabel(mode: V4PipelineStepId): string {
  return V4_VIEWPORT_MODES.find((item) => item.id === mode)?.label ?? mode;
}

export function viewportModeEnglishLabel(mode: V4PipelineStepId): string {
  return V4_VIEWPORT_MODES.find((item) => item.id === mode)?.englishLabel ?? mode;
}
