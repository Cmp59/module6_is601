import pandas as pd
import pytest

from app.calculation import CalculationFactory
from app.exceptions import HistoryError
from app.history import CalculationHistory, CalculationObserver, CalculationSubject


class RecordingObserver(CalculationObserver):
    def __init__(self):
        self.calculations = []

    def update(self, calculation):
        self.calculations.append(calculation)


def performed_calculation(operator="+", first=2, second=3):
    calculation = CalculationFactory.create(operator, first, second)
    calculation.perform()
    return calculation


def test_subject_notifies_attached_observers_once():
    subject = CalculationSubject()
    observer = RecordingObserver()
    calculation = performed_calculation()

    subject.attach(observer)
    subject.attach(observer)
    subject.notify(calculation)

    assert observer.calculations == [calculation]


def test_subject_detaches_observer_and_ignores_unknown_observer():
    subject = CalculationSubject()
    observer = RecordingObserver()
    subject.attach(observer)
    subject.detach(observer)
    subject.detach(observer)
    subject.notify(performed_calculation())

    assert observer.calculations == []


def test_history_observes_and_auto_saves_calculations(tmp_path):
    history_file = tmp_path / "nested" / "history.csv"
    history = CalculationHistory(history_file)
    calculation = performed_calculation()
    subject = CalculationSubject()
    subject.attach(history)

    subject.notify(calculation)

    assert history.dataframe.to_dict(orient="records") == [
        {"first_operand": 2, "operator": "+", "second_operand": 3, "result": 5}
    ]
    assert history_file.exists()


def test_history_returns_defensive_dataframe_copy(tmp_path):
    history = CalculationHistory(tmp_path / "history.csv", auto_save=False)
    history.add(performed_calculation())
    exposed_copy = history.dataframe
    exposed_copy.drop(index=0, inplace=True)

    assert len(history.dataframe) == 1


def test_history_get_all_and_format_entries(tmp_path):
    history = CalculationHistory(tmp_path / "history.csv", auto_save=False)
    history.add(performed_calculation())

    assert history.get_all()[0]["result"] == 5.0
    assert history.format_entries() == "1. 2 + 3 = 5"


def test_history_keeps_only_most_recent_configured_entries(tmp_path):
    history = CalculationHistory(
        tmp_path / "history.csv", auto_save=False, max_history_size=2
    )
    history.add(performed_calculation("add", 1, 1))
    history.add(performed_calculation("add", 2, 2))
    history.add(performed_calculation("add", 3, 3))

    assert [entry["first_operand"] for entry in history.get_all()] == [2, 3]


def test_history_ignores_auto_save_when_disabled(tmp_path):
    history_file = tmp_path / "history.csv"
    history = CalculationHistory(history_file, auto_save=False)
    history.add(performed_calculation())

    assert not history_file.exists()


def test_history_clear_resets_and_saves(tmp_path):
    history_file = tmp_path / "history.csv"
    history = CalculationHistory(history_file)
    history.add(performed_calculation())

    history.clear()

    assert history.dataframe.empty
    assert history_file.exists()
    assert history.format_entries() == "No calculations yet."


def test_history_loads_saved_dataframe(tmp_path):
    history_file = tmp_path / "history.csv"
    original = CalculationHistory(history_file)
    original.add(performed_calculation("^", 2, 3))
    loaded = CalculationHistory(history_file, auto_save=False)

    loaded.load()

    assert loaded.dataframe.iloc[0]["result"] == 8


def test_history_uses_configured_encoding_for_csv(tmp_path):
    history_file = tmp_path / "history.csv"
    history = CalculationHistory(
        history_file, auto_save=False, encoding="utf-8-sig"
    )
    history.add(performed_calculation())
    history.save()

    assert history_file.read_bytes().startswith(b"\xef\xbb\xbf")
    loaded = CalculationHistory(
        history_file, auto_save=False, encoding="utf-8-sig"
    )
    loaded.load()
    assert loaded.get_all()[0]["result"] == 5


def test_history_load_missing_file_starts_empty(tmp_path):
    history = CalculationHistory(tmp_path / "missing.csv", auto_save=False)

    history.load()

    assert history.dataframe.empty


def test_history_rejects_empty_csv(tmp_path):
    history_file = tmp_path / "empty.csv"
    history_file.write_text("", encoding="utf-8")
    history = CalculationHistory(history_file)

    with pytest.raises(HistoryError, match="Could not load history"):
        history.load()


def test_history_rejects_wrong_csv_columns(tmp_path):
    history_file = tmp_path / "wrong.csv"
    pd.DataFrame({"wrong": [1]}).to_csv(history_file, index=False)
    history = CalculationHistory(history_file)

    with pytest.raises(HistoryError, match="invalid column layout"):
        history.load()


def test_history_wraps_load_os_errors(tmp_path, monkeypatch):
    history = CalculationHistory(tmp_path / "history.csv")

    def fail_read(_path, **_kwargs):
        raise PermissionError("denied")

    monkeypatch.setattr(pd, "read_csv", fail_read)
    with pytest.raises(HistoryError, match="Could not load history"):
        history.load()


def test_history_wraps_save_os_errors(tmp_path):
    parent_is_file = tmp_path / "not-a-directory"
    parent_is_file.write_text("x", encoding="utf-8")
    history = CalculationHistory(parent_is_file / "history.csv")

    with pytest.raises(HistoryError, match="Could not save history"):
        history.save()


def test_history_rejects_unperformed_calculation(tmp_path):
    history = CalculationHistory(tmp_path / "history.csv", auto_save=False)
    calculation = CalculationFactory.create("+", 2, 3)

    with pytest.raises(HistoryError, match="before it is performed"):
        history.add(calculation)


def test_history_restore_rows(tmp_path):
    history = CalculationHistory(tmp_path / "history.csv", auto_save=False)
    history.restore_rows([(1, "*", 4, 4)])

    assert history.dataframe.iloc[0]["operator"] == "*"


def test_history_restore_rows_auto_saves(tmp_path):
    history_file = tmp_path / "history.csv"
    history = CalculationHistory(history_file)
    history.restore_rows([(1, "*", 4, 4)])

    assert history_file.exists()


def test_history_saved_entries_reject_invalid_archive_columns(tmp_path):
    pd.DataFrame({"unexpected": [1]}).to_csv(
        tmp_path / "history_previous.csv", index=False
    )
    history = CalculationHistory(tmp_path / "history_current.csv", auto_save=False)

    with pytest.raises(HistoryError, match="invalid column layout"):
        history.load_saved_sessions(
            tmp_path / "history.csv", tmp_path / "history_current.csv"
        )


def test_history_saved_entries_wrap_csv_read_errors(tmp_path, monkeypatch):
    archive_file = tmp_path / "history_previous.csv"
    archive_file.write_text("first_operand,operator,second_operand,result\n", encoding="utf-8")
    history = CalculationHistory(tmp_path / "history_current.csv", auto_save=False)

    def fail_read(_path, **_kwargs):
        raise PermissionError("denied")

    monkeypatch.setattr(pd, "read_csv", fail_read)
    with pytest.raises(HistoryError, match="Could not read saved history"):
        history.load_saved_sessions(
            tmp_path / "history.csv", tmp_path / "history_current.csv"
        )


def test_history_loads_archives_on_start_and_excludes_current_file(tmp_path):
    archive_rows = [[7, "^", 2, 49]]
    columns = ["first_operand", "operator", "second_operand", "result"]
    pd.DataFrame(archive_rows, columns=columns).to_csv(
        tmp_path / "history_previous.csv", index=False
    )
    pd.DataFrame([[1, "+", 1, 2]], columns=columns).to_csv(
        tmp_path / "history_current.csv", index=False
    )
    history = CalculationHistory(tmp_path / "history_current.csv", auto_save=False)

    history.load_saved_sessions(
        tmp_path / "history.csv", tmp_path / "history_current.csv"
    )

    assert history.dataframe.empty
    assert history.get_saved_entries() == (
        {
            "first_operand": 7,
            "operator": "^",
            "second_operand": 2,
            "result": 49,
            "_session_file": tmp_path / "history_previous.csv",
        },
    )


def test_history_loads_empty_archive_when_no_session_files_exist(tmp_path):
    history = CalculationHistory(tmp_path / "history_current.csv", auto_save=False)

    history.load_saved_sessions(
        tmp_path / "history.csv", tmp_path / "history_current.csv"
    )

    assert history.get_saved_entries() == ()


def test_history_csv_has_explicit_operand_columns(tmp_path):
    history_file = tmp_path / "history.csv"
    history = CalculationHistory(history_file)
    history.add(performed_calculation())

    loaded = pd.read_csv(history_file)

    assert list(loaded.columns) == [
        "first_operand",
        "operator",
        "second_operand",
        "result",
    ]
