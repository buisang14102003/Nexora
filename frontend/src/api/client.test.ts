import { describe, expect, it, vi } from "vitest";

import { createApiClient } from "./client";

describe("workspace API client", () => {
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
});
