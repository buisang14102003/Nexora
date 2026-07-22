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

  it("does not push when a stale rendered route differs from the current pathname", () => {
    const browser = createBrowser("/workspaces");

    expect(navigateAppRoute(browser, "/chat", "/workspaces")).toBe(false);
    expect(browser.history.pushState).not.toHaveBeenCalled();
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

  it("replaces unsupported popstate paths with /chat", () => {
    const browser = createBrowser("/unknown");
    const listener = vi.fn();
    subscribeToAppRoute(browser, listener);

    browser.emitPopState();

    expect(browser.history.replaceState).toHaveBeenCalledWith(null, "", "/chat");
    expect(browser.getPathname()).toBe("/chat");
    expect(listener).toHaveBeenCalledWith("/chat");
  });
});
