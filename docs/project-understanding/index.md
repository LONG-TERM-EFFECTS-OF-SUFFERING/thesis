# Project understanding

This folder is the learning layer for the thesis app. It explains what each implemented story added, how the files connect, what commands to run and what concepts are worth understanding before moving on.

These notes are different from the formal thesis chapters. The thesis explains the academic work. This folder explains the code in beginner-friendly language.

## Reading Order

1. [Glossary](glossary.md).

2. [Commands](commands.md).

3. [01 - Local backend and database](01-local-backend-and-database.md).

## Story notes

|                                 file                                 | story  | status |                                                               what it explains                                                                |
| :------------------------------------------------------------------: | :----: | :----: | :-------------------------------------------------------------------------------------------------------------------------------------------: |
| [01-local-backend-and-database.md](01-local-backend-and-database.md) | US-001 |  Done  | Django backend scaffold, SQLite, PostgreSQL, Docker Compose, migrations, environment config, health checks and the `src/` nested-repo layout. |

## How to use this folder

- Read the story page after a BMAD story is implemented and reviewed.

- Use [commands.md](commands.md) when you forget what a terminal command does.

- Use [glossary.md](glossary.md) when a repeated term feels fuzzy.

- Update the story page after review fixes so it describes the final reviewed code.

## Documentation rule

After each BMAD story is implemented, reviewed and fixed, add or update one story-specific page in this folder. The page should explain:

- what changed.

- why it was added.

- what each important file does.

- how the files connect.

- what commands to run.

- how to test manually.

- common errors and what they mean.

- beginner concepts to understand before the next story.
