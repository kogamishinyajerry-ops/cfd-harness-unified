/**
 * V86.5 · V7.D Post-Run Hand-off contract tests
 *
 * Asserts the V7.D contract from .planning/blueprints/v7/INDEX.md:
 *   - notifyCompleted(runId, caseId) updates lastCompletedRunId +
 *     lastCompletedCaseId + sets audit_in_flight=true
 *   - On audit-package success: lastAuditPackage populated,
 *     audit_in_flight=false, audit_error=null
 *   - On audit-package failure: audit_error populated, audit_in_flight=false,
 *     lastCompletedRunId still set (audit failure does NOT erase completion)
 *   - Empty runId/caseId → no-op
 *   - reset() clears all state
 *   - Concurrent notifyCompleted: second notify's audit-package response
 *     wins · prior response (if late) is ignored
 *   - V130: hook does NOT call audit-package on mount (no useEffect
 *     auto-invocation)
 */
import { describe, expect, it, vi } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";

import { usePostRunHandoffV7 } from "../usePostRunHandoffV7";
import type { AuditPackageBuildResponse } from "@/types/audit_package";

const FAKE_BUNDLE: AuditPackageBuildResponse = {
  bundle_id: "B-LDC-1",
  manifest_id: "M-1",
  case_id: "lid_driven_cavity",
  run_id: "R-1",
  build_fingerprint: "abcd1234abcd1234",
  git_repo_commit_sha: "deadbeef",
  comparator_verdict: "PASS",
  pdf_available: true,
  pdf_error: null,
  downloads: {
    manifest_json: "/api/audit-packages/B-LDC-1/manifest.json",
    bundle_zip: "/api/audit-packages/B-LDC-1/bundle.zip",
    bundle_html: "/api/audit-packages/B-LDC-1/bundle.html",
    bundle_pdf: "/api/audit-packages/B-LDC-1/bundle.pdf",
    bundle_sig: "/api/audit-packages/B-LDC-1/bundle.sig",
  },
  evidence_summary: [],
  signature_hex: "ff",
};

describe("usePostRunHandoffV7 contract · V86.5 · V7.D", () => {
  it("initial state · all null · audit_in_flight=false", () => {
    const buildImpl = vi.fn();
    const { result } = renderHook(() => usePostRunHandoffV7({ buildImpl }));
    expect(result.current.lastCompletedRunId).toBeNull();
    expect(result.current.lastCompletedCaseId).toBeNull();
    expect(result.current.lastAuditPackage).toBeNull();
    expect(result.current.audit_in_flight).toBe(false);
    expect(result.current.audit_error).toBeNull();
  });

  it("V130: hook does NOT call audit-package on mount", () => {
    const buildImpl = vi.fn();
    renderHook(() => usePostRunHandoffV7({ buildImpl }));
    expect(buildImpl).not.toHaveBeenCalled();
  });

  it("notifyCompleted populates last_* fields + sets audit_in_flight=true", async () => {
    const buildImpl = vi.fn().mockResolvedValue(FAKE_BUNDLE);
    const { result } = renderHook(() => usePostRunHandoffV7({ buildImpl }));
    act(() => {
      result.current.notifyCompleted("R-1", "lid_driven_cavity");
    });
    expect(result.current.lastCompletedRunId).toBe("R-1");
    expect(result.current.lastCompletedCaseId).toBe("lid_driven_cavity");
    expect(result.current.audit_in_flight).toBe(true);
    await waitFor(() => {
      expect(result.current.audit_in_flight).toBe(false);
    });
    // buildImpl signature is (caseId, runId) per api.client
    expect(buildImpl).toHaveBeenCalledWith("lid_driven_cavity", "R-1");
  });

  it("audit success → lastAuditPackage populated, audit_error null", async () => {
    const buildImpl = vi.fn().mockResolvedValue(FAKE_BUNDLE);
    const { result } = renderHook(() => usePostRunHandoffV7({ buildImpl }));
    act(() => {
      result.current.notifyCompleted("R-1", "lid_driven_cavity");
    });
    await waitFor(() => {
      expect(result.current.lastAuditPackage).not.toBeNull();
    });
    expect(result.current.lastAuditPackage?.bundle_id).toBe("B-LDC-1");
    expect(result.current.audit_error).toBeNull();
    expect(result.current.audit_in_flight).toBe(false);
  });

  it("audit failure → audit_error populated, lastCompletedRunId preserved", async () => {
    const buildImpl = vi.fn().mockRejectedValue(new Error("audit api 500"));
    const { result } = renderHook(() => usePostRunHandoffV7({ buildImpl }));
    act(() => {
      result.current.notifyCompleted("R-1", "lid_driven_cavity");
    });
    await waitFor(() => {
      expect(result.current.audit_in_flight).toBe(false);
    });
    expect(result.current.audit_error).toBe("audit api 500");
    // Completion is preserved · failure does NOT erase it (per reverse-stop #10)
    expect(result.current.lastCompletedRunId).toBe("R-1");
    expect(result.current.lastCompletedCaseId).toBe("lid_driven_cavity");
    expect(result.current.lastAuditPackage).toBeNull();
  });

  it("empty runId or caseId → no-op", () => {
    const buildImpl = vi.fn();
    const { result } = renderHook(() => usePostRunHandoffV7({ buildImpl }));
    act(() => {
      result.current.notifyCompleted("", "lid_driven_cavity");
    });
    expect(buildImpl).not.toHaveBeenCalled();
    expect(result.current.lastCompletedRunId).toBeNull();
    act(() => {
      result.current.notifyCompleted("R-1", "");
    });
    expect(buildImpl).not.toHaveBeenCalled();
    expect(result.current.lastCompletedRunId).toBeNull();
  });

  it("reset() clears all state", async () => {
    const buildImpl = vi.fn().mockResolvedValue(FAKE_BUNDLE);
    const { result } = renderHook(() => usePostRunHandoffV7({ buildImpl }));
    act(() => {
      result.current.notifyCompleted("R-1", "lid_driven_cavity");
    });
    await waitFor(() => {
      expect(result.current.lastAuditPackage).not.toBeNull();
    });
    act(() => {
      result.current.reset();
    });
    expect(result.current.lastCompletedRunId).toBeNull();
    expect(result.current.lastCompletedCaseId).toBeNull();
    expect(result.current.lastAuditPackage).toBeNull();
    expect(result.current.audit_in_flight).toBe(false);
    expect(result.current.audit_error).toBeNull();
  });

  it("concurrent notifyCompleted · second wins, first stale ignored", async () => {
    // First call: slow resolve.
    let resolveFirst: (v: AuditPackageBuildResponse) => void = () => {};
    const firstPromise = new Promise<AuditPackageBuildResponse>((r) => {
      resolveFirst = r;
    });
    const buildImpl = vi
      .fn()
      .mockImplementationOnce(() => firstPromise)
      .mockResolvedValueOnce({ ...FAKE_BUNDLE, bundle_id: "B-2", run_id: "R-2" });
    const { result } = renderHook(() => usePostRunHandoffV7({ buildImpl }));
    act(() => {
      result.current.notifyCompleted("R-1", "lid_driven_cavity");
    });
    // Second completion before first resolves
    act(() => {
      result.current.notifyCompleted("R-2", "lid_driven_cavity");
    });
    await waitFor(() => {
      expect(result.current.lastAuditPackage?.bundle_id).toBe("B-2");
    });
    // Late first resolution must NOT clobber state
    act(() => {
      resolveFirst({ ...FAKE_BUNDLE, bundle_id: "B-1-LATE" });
    });
    // Microtask flush
    await new Promise((r) => setTimeout(r, 0));
    expect(result.current.lastAuditPackage?.bundle_id).toBe("B-2");
    expect(result.current.lastCompletedRunId).toBe("R-2");
  });
});
