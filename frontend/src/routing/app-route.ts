import { useCallback, useEffect, useState } from "react";

export type AppRoute = "/chat" | "/workspaces";

export interface RouteBrowser {
  location: { readonly pathname: string };
  history: {
    pushState(state: unknown, unused: string, target: string): void;
    replaceState(state: unknown, unused: string, target: string): void;
  };
  addEventListener(type: "popstate", listener: () => void): void;
  removeEventListener(type: "popstate", listener: () => void): void;
  getPathname?(): string;
}

function getPathname(browser: RouteBrowser): string {
  return browser.getPathname?.() ?? browser.location.pathname;
}

export function normalizeAppRoute(pathname: string): AppRoute {
  return pathname === "/workspaces" ? "/workspaces" : "/chat";
}

export function initializeAppRoute(browser?: RouteBrowser): AppRoute {
  if (!browser) return "/chat";

  const pathname = getPathname(browser);
  const route = normalizeAppRoute(pathname);
  if (pathname !== route) browser.history.replaceState(null, "", route);
  return route;
}

export function navigateAppRoute(
  browser: RouteBrowser,
  current: AppRoute,
  target: AppRoute,
): boolean {
  if (current === target) return false;
  browser.history.pushState(null, "", target);
  return true;
}

export function subscribeToAppRoute(
  browser: RouteBrowser,
  listener: (route: AppRoute) => void,
): () => void {
  const onPopState = () => listener(normalizeAppRoute(getPathname(browser)));
  browser.addEventListener("popstate", onPopState);
  return () => browser.removeEventListener("popstate", onPopState);
}

export function useAppRoute(): readonly [AppRoute, (target: AppRoute) => void] {
  const browser = typeof window === "undefined" ? undefined : window;
  const [route, setRoute] = useState<AppRoute>(() => initializeAppRoute(browser));

  useEffect(() => browser ? subscribeToAppRoute(browser, setRoute) : undefined, [browser]);

  const navigate = useCallback((target: AppRoute) => {
    if (browser && navigateAppRoute(browser, route, target)) setRoute(target);
  }, [browser, route]);

  return [route, navigate] as const;
}
