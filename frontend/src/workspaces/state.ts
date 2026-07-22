import type { Workspace } from "../api/client";

export function filterWorkspaces(workspaces: Workspace[], query: string): Workspace[] {
  const normalized = query.trim().toLocaleLowerCase();
  if (!normalized) return workspaces;
  return workspaces.filter(({ name }) => name.toLocaleLowerCase().includes(normalized));
}

export function pinnedWorkspaces(workspaces: Workspace[]): Workspace[] {
  return workspaces.filter(({ archived_at, is_pinned }) => archived_at === null && is_pinned);
}

export function nextWorkspaceAfterArchive(
  activeWorkspaces: Workspace[],
  activeWorkspaceId: string | null,
  archivedWorkspaceId: string,
): string | null {
  if (activeWorkspaceId !== archivedWorkspaceId) return activeWorkspaceId;
  return activeWorkspaces.find(({ id }) => id !== archivedWorkspaceId)?.id ?? null;
}
