# Workspace and Chat Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Chat and Workspace management distinct `/chat` and `/workspaces` browser routes with reliable refresh and Back/Forward behavior.

**Architecture:** Add one small routing module that normalizes paths and wraps the browser History API, then make `App.tsx` render and navigate from that route instead of React-only `contentMode`. Keep routing out of Sidebar and WorkspaceManager by retaining their existing callback interfaces.

**Tech Stack:** React 19, TypeScript 5.8, browser History API, Vitest 3, Vite 6.

## Global Constraints

- `/chat` renders the existing Knowledge and Chat panels.
- `/workspaces` renders the existing Workspace management screen.
- `/` and unsupported frontend paths are replaced with `/chat` without adding a history entry.
- Do not add a routing dependency.
- The route is the only source of truth for the visible main screen; remove `contentMode`.
- Do not add workspace or session IDs to URLs.
- Do not change backend endpoints, database schema, or visual design.
- Use test-first development and run only targeted frontend tests plus the frontend production build; do not run the full repository test suite.

---

### Task 1: Browser route utility

**Files:**
- Create: `frontend/src/routing/app-route.ts`
- Create: `frontend/src/routing/app-route.test.ts`

**Interfaces:**
- Produces: `AppRoute = "/chat" | "/workspaces"`.
- Produces: `normalizeAppRoute(pathname: string): AppRoute`.
- Produces: `initializeAppRoute(browser?: RouteBrowser): AppRoute`.
- Produces: `navigateAppRoute(browser: RouteBrowser, current: AppRoute, target: AppRoute): boolean`.
- Produces: `subscribeToAppRoute(browser: RouteBrowser, listener: (route: AppRoute) => void): () => void`.
- Produces: `useAppRoute(): readonly [AppRoute, (target: AppRoute) => void]`.

- [ ] **Step 1: Write failing route tests**

Create `frontend/src/routing/app-route.test.ts` with a minimal fake browser and these behaviors:

```ts
import { describe, expect, it, vi } from "vitest";

import {
  initializeAppRoute,
  navigateAppRoute,
  normalizeAppRoute,
  subscribeToAppRoute,
} from "./app-route";

function createBrowser(pathname: string) {
  const listeners = new Set<() => void>();
  return {
    location: { pathname },
    history: {
      pushState: vi.fn((_state: unknown, _unused: string, target: string) => {
        pathname = target;
      }),
      replaceState: vi.fn((_state: unknown, _unused: string, target: string) => {
        pathname = target;
      }),
    },
    addEventListener: vi.fn((_type: "popstate", listener: () => void) => listeners.add(listener)),
    removeEventListener: vi.fn((_type: "popstate", listener: () => void) => listeners.delete(listener)),
    getPathname: () => pathname,
    emitPopState: () => listeners.forEach((listener) => listener()),
  };
}

describe("app routing", () => {
  it.each([
    ["/chat", "/chat"],
    ["/workspaces", "/workspaces"],
    ["/", "/chat"],
    ["/unknown", "/chat"],
  ] as const)("normalizes %s to %s", (pathname, expected) => {
    expect(normalizeAppRoute(pathname)).toBe(expected);
  });

  it("replaces unsupported initial paths with /chat", () => {
    const browser = createBrowser("/unknown");
    expect(initializeAppRoute(browser)).toBe("/chat");
    expect(browser.history.replaceState).toHaveBeenCalledWith(null, "", "/chat");
  });

  it("pushes only when navigating to a different route", () => {
    const browser = createBrowser("/chat");
    expect(navigateAppRoute(browser, "/chat", "/chat")).toBe(false);
    expect(navigateAppRoute(browser, "/chat", "/workspaces")).toBe(true);
    expect(browser.history.pushState).toHaveBeenCalledTimes(1);
    expect(browser.history.pushState).toHaveBeenCalledWith(null, "", "/workspaces");
  });

  it("reports normalized routes on popstate and unsubscribes", () => {
    const browser = createBrowser("/workspaces");
    const listener = vi.fn();
    const unsubscribe = subscribeToAppRoute(browser, listener);
    browser.emitPopState();
    expect(listener).toHaveBeenCalledWith("/workspaces");
    unsubscribe();
    browser.emitPopState();
    expect(listener).toHaveBeenCalledTimes(1);
  });
});
```

- [ ] **Step 2: Run the new test and verify RED**

Run: `cd frontend && npm test -- src/routing/app-route.test.ts`

Expected: FAIL because `./app-route` does not exist.

- [ ] **Step 3: Implement the minimal route module**

Create `frontend/src/routing/app-route.ts`. Define a narrow `RouteBrowser` interface for `location.pathname`, `history.pushState`, `history.replaceState`, and popstate listeners. Implement normalization, initial `replaceState`, different-route `pushState`, subscription cleanup, and a React hook that updates state after pushes and popstate. Use `/chat` when `window` is unavailable.

The hook must have this behavior:

```ts
export function useAppRoute(): readonly [AppRoute, (target: AppRoute) => void] {
  const browser = typeof window === "undefined" ? undefined : window;
  const [route, setRoute] = useState<AppRoute>(() => initializeAppRoute(browser));

  useEffect(() => browser ? subscribeToAppRoute(browser, setRoute) : undefined, [browser]);

  const navigate = useCallback((target: AppRoute) => {
    if (browser && navigateAppRoute(browser, route, target)) setRoute(target);
  }, [browser, route]);

  return [route, navigate] as const;
}
```

For tests, `initializeAppRoute` and `subscribeToAppRoute` must read `browser.getPathname?.() ?? browser.location.pathname` so the fake browser can reflect history changes without mutating a readonly DOM location.

- [ ] **Step 4: Run the route test and verify GREEN**

Run: `cd frontend && npm test -- src/routing/app-route.test.ts`

Expected: all route tests PASS.

- [ ] **Step 5: Commit the route utility**

```bash
git add frontend/src/routing/app-route.ts frontend/src/routing/app-route.test.ts
git commit -m "feat: add browser app routing"
```

### Task 2: Route-driven application shell

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/workspace-components.test.tsx`

**Interfaces:**
- Consumes: `useAppRoute(): readonly [AppRoute, (target: AppRoute) => void]` from Task 1.
- Preserves: all existing `Sidebar` and `WorkspaceManager` props and callback signatures.

- [ ] **Step 1: Write a failing structural integration test**

Add to `frontend/src/components/workspace-components.test.tsx`:

```ts
import { readFileSync } from "node:fs";

it("uses pathname routing instead of local content mode", () => {
  const source = readFileSync(new URL("../App.tsx", import.meta.url), "utf8");
  expect(source).toContain("useAppRoute()");
  expect(source).toContain('route === "/workspaces"');
  expect(source).not.toContain("contentMode");
});
```

- [ ] **Step 2: Run the integration test and verify RED**

Run: `cd frontend && npm test -- src/components/workspace-components.test.tsx`

Expected: FAIL because `App.tsx` still uses `contentMode` and does not call `useAppRoute()`.

- [ ] **Step 3: Replace `contentMode` with the route hook**

In `frontend/src/App.tsx`:

- Import `useAppRoute` from `./routing/app-route`.
- Remove `ContentMode` and the `contentMode` state.
- Add `const [route, navigate] = useAppRoute();` at the start of `App`.
- Remove the content-mode reset from `logout`; keep the supported current route.
- After creating or opening a workspace, call `navigate("/chat")`.
- Keep archive, restore, update, search, and filters on `/workspaces`; do not navigate inside `archiveWorkspace`.
- Use `route === "/workspaces"` for the manager shell class, `managerActive`, and the manager/content conditional.
- Make `onOpenManager` call `navigate("/workspaces")`.
- Make `onNewChat` call `navigate("/chat")` before invoking the existing `newChat()`.

The resulting navigation callbacks must follow this shape:

```tsx
const managerActive = route === "/workspaces";

function openWorkspace(nextWorkspaceId: string) {
  setWorkspaceId(nextWorkspaceId);
  navigate("/chat");
}

// Sidebar props
managerActive={managerActive}
onOpenManager={() => navigate("/workspaces")}
onNewChat={async () => {
  navigate("/chat");
  return newChat();
}}
```

- [ ] **Step 4: Run targeted frontend tests and verify GREEN**

Run:

```bash
cd frontend
npm test -- src/routing/app-route.test.ts src/components/workspace-components.test.tsx src/workspaces/state.test.ts
```

Expected: all targeted tests PASS.

- [ ] **Step 5: Build the frontend**

Run: `cd frontend && npm run build`

Expected: TypeScript and Vite production build succeed without errors.

- [ ] **Step 6: Verify browser behavior**

With the existing local frontend running, verify:

1. `/` normalizes to `/chat`.
2. Sidebar Workspaces changes the URL and visible screen to `/workspaces`.
3. Opening a workspace changes the URL and visible screen to `/chat`.
4. Back and Forward keep URL and visible screen synchronized.
5. Refreshing `/chat` and `/workspaces` preserves the selected screen.
6. The browser console has no new errors.

- [ ] **Step 7: Commit the App integration**

```bash
git add frontend/src/App.tsx frontend/src/components/workspace-components.test.tsx
git commit -m "feat: separate chat and workspace routes"
```
