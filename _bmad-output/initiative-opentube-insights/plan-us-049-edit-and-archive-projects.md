---
title: 'US-049 Edit and archive projects'
type: 'feature'
ticket: ''
created: '2026-11-09'
status: 'done'
baseline_revision: 'api=122943fa113abce30e2727ae28a1d90b86781cca ui=ea61084ea42173671922475a5de2222be25f8462'
route: 'full'
route_source: 'auto'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
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
- [x] Backend: owner context on the detail view, if missing, plus a duplicate-rename test.
- [x] `apiClient.ts`: `updateResearchProject`, with a test.
- [x] `projectState.ts`: replace-by-id helper, with a test.
- [x] `ProjectsSection.tsx` and `App.tsx`: edit mode, the archive toggle and the Show archived filter.
- [x] `i18n.ts`: the new Spanish entries.

**Acceptance Criteria:**
- Given an archived project, when Show archived is off, then it is not listed, and the API still returns it.
- Given `npm run build`, then a new text without a Spanish entry fails.

## Review Triage Log

Pass 1 (quick), 6 findings: 5 patch, 1 reject.

- **low, patch.** With every project archived and Show archived off, the list is blank: the empty-state check uses the unfiltered list. Fix: an "all archived" message.
- **medium, patch.** The header's Active project select still lists archived projects, so the frozen "hidden unless Show archived is ticked" holds only in one section. Fix: the header lists active projects plus the currently active one.
- **low, patch.** A field edit and an archive on the same project can be in flight together. DRF's full `save()` can write a stale `status`. Fix: disable the status buttons while a save is pending, and Edit/Save while a status change is pending.
- **low, patch.** `ResearchProjectDetailView` lacks the create view's `IntegrityError` → 400 mapping, so two concurrent renames to one name return 500, against the "never a 500" rule. Fix: a `perform_update` mirroring `perform_create`.
- **low, patch.** The Show archived filter is an inline expression with no test, so the matrix row Archive ("the card disappears") has none. Fix: a pure helper in `projectState.ts` with a test, which the header reuses.
- **low, reject.** Edit overwrites an unsaved create draft. It is rarely met, and keeping a second draft state is more than a direct correction.

## Verification

**Commands:**
- `cd src/api && venv/bin/python manage.py test` -- expected: all pass.
- `cd src/ui && npm test && npm run build && npm run lint` -- expected: clean.

**Manual checks:**
- In `npm run dev`:
  - Edit a project's name.
  - Archive it, tick Show archived, then unarchive it.
  - Try a duplicate name.
