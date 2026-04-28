// Test-only stub for the entire @kitware/vtk.js tree. Vitest loads vtk.js
// modules at evaluation time before vi.mock can intercept; even with
// hoisted mocks the parser walks the package and runs out of heap on the
// vtk.js Profiles registration sweep.
//
// Aliasing the whole `@kitware/vtk.js/*` namespace to this single module
// (configured in vitest.config.ts test.alias) gives every visualization
// test a deterministic, lightweight handle to mock against. Production
// builds resolve through the real package; only the test environment uses
// this stub.

const proxyHandler: ProxyHandler<Record<string, unknown>> = {
  get(target, prop) {
    if (prop in target) return target[prop as string];
    if (prop === "default") return target;
    if (prop === "__esModule") return true;
    return () => undefined;
  },
};

const stubInstance = new Proxy({}, proxyHandler);
const stubFactory = {
  newInstance: () => stubInstance,
};

const stub = new Proxy(stubFactory as unknown as Record<string, unknown>, proxyHandler);
export default stub;
