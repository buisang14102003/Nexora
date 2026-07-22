# Promote Worktree to Root Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `Desktop/Ai-RAG` the working project directory and remove the nested Git worktree without losing its uncommitted changes.

**Architecture:** Preserve the worktree's current changes in a commit on `codex/local-workspace-rag-mvp`. Fast-forward `main` at the repository root to that commit, then remove the now-redundant registered worktree.

**Tech Stack:** Git worktrees; existing Python and React project files.

## Global Constraints

- Preserve every existing tracked and untracked project change in `.worktrees/local-workspace-rag-mvp`.
- Do not copy `.env`, virtual environments, cache directories, or other ignored local runtime artifacts into the root.
- End with all tracked application files directly below `Desktop/Ai-RAG` and no `.worktrees` directory.

---

### Task 1: Preserve the worktree state

**Files:**
- Modify: Git index and history in `.worktrees/local-workspace-rag-mvp`

- [ ] **Step 1: Review the pending changes**

Run: `git -C .worktrees/local-workspace-rag-mvp status --short`

Expected: modified application, test, configuration, and documentation files are listed.

- [ ] **Step 2: Commit the complete project state**

Run: `git -C .worktrees/local-workspace-rag-mvp add -A`

Run: `git -C .worktrees/local-workspace-rag-mvp commit -m "chore: prepare project root"

Expected: one commit records the current worktree state.

### Task 2: Promote the project branch to root

**Files:**
- Modify: repository root working tree and `main` branch

- [ ] **Step 1: Fast-forward main to the project branch**

Run: `git merge --ff-only codex/local-workspace-rag-mvp`

Expected: project files, including `README.md`, appear directly at the repository root.

- [ ] **Step 2: Verify the root is clean and contains the project**

Run: `git status --short`

Run: `test -f README.md && test -f compose.yaml && test -f pyproject.toml`

Expected: no status output; all three file checks succeed.

### Task 3: Remove the obsolete worktree

**Files:**
- Delete: `.worktrees/local-workspace-rag-mvp`
- Delete: `.worktrees`

- [ ] **Step 1: Remove the registered worktree**

Run: `git worktree remove .worktrees/local-workspace-rag-mvp`

Expected: Git removes the worktree directory and its registration.

- [ ] **Step 2: Remove the empty parent directory**

Run: `rmdir .worktrees`

Expected: the directory no longer exists.

- [ ] **Step 3: Verify the final repository state**

Run: `git worktree list --porcelain`

Run: `git status --short`

Run: `test -f README.md && test -d app && test -d frontend && test ! -e .worktrees`

Expected: only the repository root worktree is listed, the working tree is clean, and the root project structure is present.
