import type { Workspace } from "../api/client";

export function filterWorkspaces(workspaces: Workspace[], query: string): Workspace[] {
  const normalized = query.trim().toLocaleLowerCase();
  if (!normalized) return workspaces;
  return workspaces.filter(({ name }) => name.toLocaleLowerCase().includes(normalized));
}

export function pinnedWorkspaces(workspaces: Workspace[]): Workspace[] {
  return workspaces.filter(({ archived_at, is_pinned }) => archived_at === null && is_pinned);
}

export function orderActiveWorkspaces(workspaces: Workspace[]): Workspace[] {
  return [...workspaces].sort((left, right) => {
    if (left.is_pinned !== right.is_pinned) return left.is_pinned ? -1 : 1;
    if (left.updated_at !== right.updated_at) return left.updated_at > right.updated_at ? -1 : 1;
    if (left.id === right.id) return 0;
    return left.id < right.id ? -1 : 1;
  });
}

export function nextWorkspaceAfterArchive(
  activeWorkspaces: Workspace[],
  activeWorkspaceId: string | null,
  archivedWorkspaceId: string,
): string | null {
  if (activeWorkspaceId !== archivedWorkspaceId) return activeWorkspaceId;
  return activeWorkspaces.find(({ id }) => id !== archivedWorkspaceId)?.id ?? null;
}
