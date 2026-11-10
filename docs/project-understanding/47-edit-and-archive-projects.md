# 47 - Edit and archive projects

Story: US-049, Edit and archive projects.

Status note: this page describes US-049 after its review of 2026-11-09 and the fixes that followed (`src/api` PR #46, `src/ui` PR #28). The advisor asked for project edit and delete in his review of thesis commit `753a97d`; see `docs/thesis-review-code-changes.md` item 9.

## What this story added

Each card in *Projects* now has two buttons:

- **Edit** loads the project into the form, which becomes *Edit project*, with *Save changes* and *Cancel*. Name, description and default language can change.
- **Archive** / **Unarchive** sets the project's status to `archived` or back to `active`.

Archived projects are hidden from the Projects list and from the header's project menu unless *Show archived* is ticked. The project you are working in stays in the header even after you archive it, until you pick another one. If every project is archived, the list says so instead of showing nothing.

## Why archive and not delete

Deleting a project would cascade to its saved queries, collection runs and request logs. Those are the methodological record that the thesis promises to keep after the 30-day purge (8.10.1). Archiving hides a finished study and keeps that record. Deletion stays available to an administrator in the Django admin.

## Files

- `src/ui/src/apiClient.ts`: `updateResearchProject(projectId, input)` sends `PATCH /api/projects/<id>/`, the endpoint that already existed.
- `src/ui/src/projectState.ts`:
  - `replaceProject` swaps an updated project into the list.
  - `visibleProjects(projects, showArchived, keepId?)` is the one filter, used by both the Projects list and the header.
- `src/ui/src/ProjectsSection.tsx`: the edit mode, the buttons and the Show archived checkbox. A field save and a status change cannot run at the same time, because the backend saves every column and could write back an old status.
- `src/ui/src/AppHeader.tsx`: the header menu uses `visibleProjects(…, false, activeProjectId)`.
- `src/api/core/views.py` `ResearchProjectDetailView.perform_update`: turns a database duplicate-name error into the same 400 message as creating a project. This covers the case where two renames to the same name arrive at once.

## Commands

```bash
cd src/api && venv/bin/python manage.py test   # 399 tests
cd src/ui && npm test                          # 132 tests, including visibleProjects
```

## How to test manually

1. `npm run dev` → Projects → Edit a project, change its name, then Save changes. The card and the header show the new name.
2. Rename it to the name of another of your projects. The form shows "A project with this name already exists…".
3. Archive it. The card disappears. Tick Show archived, then Unarchive it.
