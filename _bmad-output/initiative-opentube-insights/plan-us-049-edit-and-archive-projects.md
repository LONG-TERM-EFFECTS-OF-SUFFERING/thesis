---
title: 'US-049 Edit and archive projects'
type: 'feature'
ticket: ''
created: '2026-11-09'
status: 'ready-for-dev'
baseline_revision: ''
route: 'full'
route_source: 'auto'
review: ''
review_source: ''
lenses_ran: []
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The Projects section can only create and select projects. The advisor asked for edit and delete.

**Approach:** Each project card gets *Edit*. It opens a form for name, description and default language, which sends the existing `PATCH`. It also gets *Archive* / *Unarchive*, which sends `PATCH {status}`. Archived projects are hidden unless *Show archived* is ticked. There is no delete in the app: it would cascade to the saved queries, runs and request logs that the thesis keeps as the methodological record, so deletion stays in the Django admin.

## Boundaries & Constraints

**Always:**
- Use the existing `ResearchProjectDetailView` (`PATCH`, owner-scoped, 404 for others).
- Every fetch that writes React state goes through `latestRequest`, as AGENTS.md requires.
- New text goes through `t()` and has Spanish entries. The language field uses the US-043 selector.
- A duplicate name shows the API's validation message in the form, never a 500.
- Archiving the active project keeps it active until the researcher selects another one.

**Never:**
- No delete endpoint, no new backend model field and no migration.
- No change to how queries, runs or results behave for archived projects.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Edit | change the name and save | the card and the header show the new name | — |
| Duplicate name | rename to another of your projects | the form shows "A project with this name already exists…" | 400 from the API |
| Archive | click Archive | status `archived`; the card disappears unless Show archived is ticked | — |
| Unarchive | Show archived, then Unarchive | status `active`; the card is back in the default list | — |
| Cancel | open Edit, change fields, Cancel | nothing sent; the card is unchanged | — |

</frozen-after-approval>

## Code Map

- `src/api/core/views.py` `ResearchProjectDetailView` (`RetrieveUpdateAPIView`, `patch` only). Confirm that its serializer context carries `owner`, so `ResearchProjectSerializer.validate_name` runs on update (`serializers.py` ~203). If the context lacks it, a duplicate rename hits the unique constraint and returns 500. Add the context, mirroring the list view, plus a backend test for a duplicate rename (400).
- `src/ui/src/apiClient.ts`: `createResearchProject` (~885) is the pattern. Add `updateResearchProject(projectId, input: Partial<ResearchProjectInput & {status}>)` with JSDoc, and test it with a stubbed `fetch` in `tests/projectApi.test.ts`.
- `src/ui/src/ProjectsSection.tsx`: the create form (`buildProjectInput`, `updateProjectForm`) and the cards (`project-card`, ~168). Reuse the form fields for edit mode.
- `src/ui/src/App.tsx`: owns the project list and the active project. Find how a created project is merged in (`projectState.ts`) and merge an updated one the same way, by id.
- `src/ui/src/projectState.ts` and `tests/projectState.test.ts`: add a pure helper that replaces a project by id, with a test.
- `src/ui/src/i18n.ts`: Spanish entries for Edit, Archive, Unarchive, Show archived, Save changes and Cancel.

## Tasks & Acceptance

**Execution:**
- [ ] Backend: owner context on the detail view, if missing, plus a duplicate-rename test.
- [ ] `apiClient.ts`: `updateResearchProject`, with a test.
- [ ] `projectState.ts`: replace-by-id helper, with a test.
- [ ] `ProjectsSection.tsx` and `App.tsx`: edit mode, the archive toggle and the Show archived filter.
- [ ] `i18n.ts`: the new Spanish entries.

**Acceptance Criteria:**
- Given an archived project, when Show archived is off, then it is not listed, and the API still returns it.
- Given `npm run build`, then a new text without a Spanish entry fails.

## Verification

**Commands:**
- `cd src/api && venv/bin/python manage.py test` -- expected: all pass.
- `cd src/ui && npm test && npm run build && npm run lint` -- expected: clean.

**Manual checks:**
- In `npm run dev`:
  - Edit a project's name.
  - Archive it, tick Show archived, then unarchive it.
  - Try a duplicate name.
