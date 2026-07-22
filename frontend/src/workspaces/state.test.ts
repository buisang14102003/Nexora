import { describe, expect, it } from "vitest";

import type { Workspace } from "../api/client";
import { createMutationLock, filterWorkspaces, nextWorkspaceAfterArchive, orderActiveWorkspaces, pinnedWorkspaces } from "./state";

const workspaces: Workspace[] = [
  {
    id: "1",
    name: "Product Research",
    slug: "product-research",
    is_pinned: true,
    archived_at: null,
    updated_at: "2026-07-22T12:00:00Z",
  },
  {
    id: "2",
    name: "Support",
    slug: "support",
    is_pinned: false,
    archived_at: null,
    updated_at: "2026-07-21T12:00:00Z",
  },
];

describe("workspace state", () => {
  it("filters names without case sensitivity", () => {
    expect(filterWorkspaces(workspaces, "research").map(({ id }) => id)).toEqual(["1"]);
    expect(filterWorkspaces(workspaces, " PRODUCT ").map(({ id }) => id)).toEqual(["1"]);
  });

  it("returns only active pinned workspaces", () => {
    expect(pinnedWorkspaces(workspaces).map(({ id }) => id)).toEqual(["1"]);
  });

  it("selects the first remaining workspace after the active one is archived", () => {
    expect(nextWorkspaceAfterArchive(workspaces, "1", "1")).toBe("2");
    expect(nextWorkspaceAfterArchive([workspaces[0]], "1", "1")).toBeNull();
    expect(nextWorkspaceAfterArchive(workspaces, "2", "1")).toBe("2");
  });

  it("orders active workspaces by pin, updated time, and id", () => {
    const unordered: Workspace[] = [
      { ...workspaces[1], id: "b", updated_at: "2026-07-22T12:00:00Z" },
      { ...workspaces[0], id: "d", updated_at: "2026-07-21T12:00:00Z" },
      { ...workspaces[1], id: "a", updated_at: "2026-07-22T12:00:00Z" },
      { ...workspaces[0], id: "c", updated_at: "2026-07-23T12:00:00Z" },
    ];

    expect(orderActiveWorkspaces(unordered).map(({ id }) => id)).toEqual(["c", "d", "a", "b"]);
    expect(unordered.map(({ id }) => id)).toEqual(["b", "d", "a", "c"]);
  });

  it("allows only one workspace mutation at a time", () => {
    const lock = createMutationLock();

    expect(lock.tryAcquire()).toBe(true);
    expect(lock.tryAcquire()).toBe(false);
    expect(lock.isLocked()).toBe(true);

    lock.release();

    expect(lock.isLocked()).toBe(false);
    expect(lock.tryAcquire()).toBe(true);
  });
});
