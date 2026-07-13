## Tests Structure

- `unit/`: core and runner unit tests (`core/`, `runners/`, `tui/`).
- `integration/`: end-to-end style checks (file_compare, parallel, path_handling, etc).
- `demos/`: manual/interactive scripts, not run in CI by default.

### TUI Tests (`unit/tui/`)

| File | Coverage |
|------|----------|
| `test_search_functions.py` | Search helpers: substring, regex, fuzzy match/scoring |
| `test_case_controller.py` | `CaseController`: init, load/save, CRUD, search, tags, dirty flag, `_parse_from_dict` |
| `test_widgets_data.py` | `StepsEditor`/`ExpectedEditor` data layer: load/to_steps/to_dict, deep copy, roundtrip |
| `test_app.py` | `run_tui` error handling, `CaseManagerApp` construction, CLI arg parsing |

## Run Commands

- Run all configured scopes: `python -m tests.run_all --scope all`
- Unit only: `python -m tests.run_all --scope unit`
- Integration only: `python -m tests.run_all --scope integration`
- TUI tests only: `python -m pytest tests/unit/tui/ -v`
- Filter with pytest args: `python -m tests.run_all --scope integration --extra "-k h5"`

`demos/` scripts are standalone (e.g., `python tests/demos/h5_filter_demo.py`).

