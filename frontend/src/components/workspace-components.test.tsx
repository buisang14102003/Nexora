import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import type { Workspace } from "../api/client";
import { Sidebar } from "./Sidebar";
import { WorkspaceManager } from "./WorkspaceManager";

const activePinned: Workspace = {
  id: "pinned",
  name: "Pinned research",
  slug: "pinned-research",
  is_pinned: true,
  archived_at: null,
  updated_at: "2026-07-22T12:00:00Z",
};

const activeUnpinned: Workspace = {
  ...activePinned,
  id: "unpinned",
  name: "Unpinned support",
  slug: "unpinned-support",
  is_pinned: false,
};

const archivedPinned: Workspace = {
  ...activePinned,
  id: "archived",
  name: "Archived plans",
  slug: "archived-plans",
  archived_at: "2026-07-22T13:00:00Z",
};

const managerCallbacks = {
  onLoadArchived: vi.fn(async () => undefined),
  onCreate: vi.fn(async () => undefined),
  onOpen: vi.fn(),
  onUpdate: vi.fn(async () => undefined),
  onArchive: vi.fn(async () => undefined),
  onRestore: vi.fn(async () => undefined),
};

describe("workspace component structure", () => {
  it("renders only active pinned workspaces in the sidebar", () => {
    const html = renderToStaticMarkup(<Sidebar
      workspaces={[activePinned, activeUnpinned, archivedPinned]}
      activeWorkspaceId="pinned"
      managerActive={false}
      sessions={[]}
      activeSessionId={null}
      onOpenManager={vi.fn()}
      onSelectWorkspace={vi.fn()}
      onNewChat={vi.fn(async () => undefined)}
      onSelectSession={vi.fn(async () => undefined)}
      onRenameSession={vi.fn(async () => undefined)}
      onDeleteSession={vi.fn(async () => undefined)}
      onLogout={vi.fn()}
    />);

    expect(html).toContain("Pinned research");
    expect(html).not.toContain("Unpinned support");
    expect(html).not.toContain("Archived plans");
  });

  it("renders active and archived controls with native button semantics", () => {
    const html = renderToStaticMarkup(<WorkspaceManager
      activeWorkspaces={[activePinned]}
      archivedWorkspaces={[archivedPinned]}
      loading={false}
      error=""
      {...managerCallbacks}
    />);

    expect(html).toContain(">Active</button>");
    expect(html).toContain(">Archived</button>");
    expect(html).toContain("Pinned research");
    expect(html).not.toContain('role="tablist"');
    expect(html).not.toContain('role="tab"');
  });

  it("keeps the active empty state visible when archived loading failed", () => {
    const html = renderToStaticMarkup(<WorkspaceManager
      activeWorkspaces={[]}
      archivedWorkspaces={[]}
      loading={false}
      error="Archived workspaces could not be loaded."
      {...managerCallbacks}
    />);

    expect(html).toContain("Create your first workspace");
    expect(html).not.toContain("Archived workspaces could not be loaded.");
    expect(html).toContain("New workspace");
    expect(html).not.toContain("<dialog");
  });
});
