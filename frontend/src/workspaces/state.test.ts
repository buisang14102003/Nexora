import { describe, expect, it } from "vitest";

import type { Workspace } from "../api/client";
import { filterWorkspaces, nextWorkspaceAfterArchive, pinnedWorkspaces } from "./state";

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
});
