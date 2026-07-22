import { describe, expect, it, vi } from "vitest";

import { createApiClient } from "./client";

describe("workspace API client", () => {
  it("lists archived workspaces", async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response("[]", { status: 200 }));
    const api = createApiClient("token-123", fetcher);

    await api.listWorkspaces("archived");

    expect(fetcher).toHaveBeenCalledWith(
      "http://127.0.0.1:8100/workspaces?status=archived",
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer token-123" }),
      }),
    );
  });

  it("updates and archives a workspace", async () => {
    const workspace = {
      id: "workspace-1",
      name: "Research",
      slug: "research",
      is_pinned: true,
      archived_at: null,
      updated_at: "2026-07-22T10:00:00Z",
    };
    const fetcher = vi.fn().mockImplementation(
      async () => new Response(JSON.stringify(workspace), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const api = createApiClient("token-123", fetcher);

    await api.updateWorkspace("workspace-1", { name: "Research", is_pinned: true });
    await api.archiveWorkspace("workspace-1");

    expect(fetcher).toHaveBeenNthCalledWith(
      1,
      "http://127.0.0.1:8100/workspaces/workspace-1",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ name: "Research", is_pinned: true }),
      }),
    );
    expect(fetcher).toHaveBeenNthCalledWith(
      2,
      "http://127.0.0.1:8100/workspaces/workspace-1/archive",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("creates a workspace with the session token and returns it", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: "workspace-1", name: "Tài liệu", slug: "tai-lieu" }), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const api = createApiClient("token-123", fetcher);

    await expect(api.createWorkspace("Tài liệu")).resolves.toMatchObject({
      id: "workspace-1",
      name: "Tài liệu",
    });
    expect(fetcher).toHaveBeenCalledWith(
      "http://127.0.0.1:8100/workspaces",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ Authorization: "Bearer token-123" }),
        body: JSON.stringify({ name: "Tài liệu" }),
      }),
    );
  });

  it("restores a workspace with a bodyless POST request", async () => {
    const restored = {
      id: "workspace-1",
      name: "Research",
      slug: "research",
      is_pinned: false,
      archived_at: null,
      updated_at: "2026-07-22T10:00:00Z",
    };
    const fetcher = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(restored), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const api = createApiClient("token-123", fetcher);

    await expect(api.restoreWorkspace("workspace-1")).resolves.toEqual(restored);
    expect(fetcher).toHaveBeenCalledWith(
      "http://127.0.0.1:8100/workspaces/workspace-1/restore",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ Authorization: "Bearer token-123" }),
      }),
    );
    expect(fetcher.mock.calls[0]?.[1]).not.toHaveProperty("body");
  });
});
