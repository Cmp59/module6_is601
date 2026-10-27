# Module 5 Enhanced Calculator

A command-line calculator built with Python and object-oriented design.

## Setup

Create and activate a virtual environment, then install the project dependencies:

```powershell
python -m venv .venv
\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell blocks activation scripts, run this once for the current terminal:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## Run the Calculator

```powershell
python main.py
```

The calculator accepts the word commands `add`, `subtract`, `multiply`, `divide`, `power`, `root`, `modulus`, `int_divide`, `percent`, and `abs_diff`. For `root`, enter the radicand first and the root degree second. `percent` computes `(first number / second number) * 100`. Available commands are `help`, `history`, `clear`, `undo`, `redo`, `save`, `load`, and `exit` (`q` also exits). `clear` deletes current-session history and resets undo/redo. `undo` removes the most recent entry, and `redo` restores the last undone entry. On startup, earlier session CSVs are loaded into a separate pandas archive, leaving the new session history empty. `load` lists those archived calculations and copies the selected entry into the current session. Each REPL session writes a uniquely named CSV file with `first_operand`, `operator`, `second_operand`, and `result` columns, plus a matching `.txt` session journal with start/end times, entered inputs, and completed calculations. Both files are stored beside the configured history file; the CSV auto-saves after changes and on exit.

Copy `.env.example` to `.env` to configure the application. Relative directories are resolved from the project root, so the project remains portable when downloaded to another computer. The application creates the folders when it first writes files.

- `CALCULATOR_HISTORY_DIR`: directory for per-session CSV files and their matching `.txt` journals. Default: `data/history`.
- `CALCULATOR_LOG_DIR` and `CALCULATOR_LOG_FILE`: directory and filename for the application log. Relative log filenames are placed inside the configured log directory. Defaults: `data/logs` and `calculator.log`.
- `CALCULATOR_MAX_HISTORY_SIZE`: maximum number of entries retained in each session history. Newer entries replace older ones after the limit. Default: `10000` entries.
- `CALCULATOR_AUTO_SAVE`: automatically save the CSV after history changes. Accepts `true` or `false`; default: `true`.
- `CALCULATOR_PRECISION`: decimal places retained in calculation results. Default: `10`.
- `CALCULATOR_MAX_INPUT_VALUE`: maximum absolute value accepted for either operand. Default: `1000000000`.
- `CALCULATOR_DEFAULT_ENCODING`: encoding used for CSV, journal, and log files. Default: `utf-8`.
- `CALCULATOR_HISTORY_FILE`: optional filename or legacy path setting; the default filename is `history.csv`.

## Run Tests

Run the test suite with coverage:

```powershell
python -m pytest
```

The project requires 100% test coverage. To enforce that requirement locally, run:

```powershell
python -m pytest --cov-fail-under=100
```

## Project Structure

- `app/calculator_repl.py`: Interactive calculator REPL
- `app/calculation.py`: Calculation instances and `CalculationFactory`
- `app/operations.py`: Arithmetic strategies and `OperationFactory`
- `app/history.py`: Observer-based pandas history and CSV persistence
- `app/calculator.py`: Facade coordinating calculation, history, and state
- `app/calculator_memento.py`: Immutable state snapshots for undo and redo
- `app/calculator_config.py`: Validated dotenv/environment configuration
- `app/input_validators.py`: REPL command and numeric input helpers
- `app/exceptions.py`: Calculator-specific exceptions
- `tests/test_operations.py`: Parameterized arithmetic tests
- `tests/test_calculations.py`: Calculation, factory, and history tests
- `tests/test_calculator_repl.py`: REPL tests
- `tests/test_calculator_config.py`: Configuration tests
- `tests/test_calculator_memento.py`: Memento tests
- `tests/test_exceptions.py`: Exception hierarchy tests
- `tests/test_history.py`: Observer and CSV history tests
- `tests/test_input_validators.py`: Input validation tests
- `.github/workflows/ci.yml`: GitHub Actions configuration