# Contributing

1. Read `AGENTS.md` and `CLEAN_ROOM.md`. They apply to people and AI assistants alike.
2. `pip install -e ".[dev]"`, then `pre-commit install` if you use pre-commit.
3. Before pushing: `ruff check . && ruff format --check . && pytest && python scripts/check_markings.py`.
4. New source consulted: add it to `SOURCES.md`. New dependency: add it to `docs/THIRD_PARTY.md`.
5. Architectural choice: add a record under `docs/decisions/`.

Contributions are accepted under Apache 2.0. By opening a pull request you make the
clean-room declaration in `CLEAN_ROOM.md`.
