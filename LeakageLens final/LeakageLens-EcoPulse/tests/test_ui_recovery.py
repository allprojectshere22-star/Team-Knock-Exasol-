from contextlib import nullcontext

import pandas as pd

from src import ui


class FakeStreamlit:
    def __init__(self, session_state, button_result=False):
        self.session_state = session_state
        self.button_result = button_result
        self.buttons = []
        self.messages = []
        self.rerun_called = False

    def warning(self, message):
        self.messages.append(message)

    def info(self, message):
        self.messages.append(message)

    def button(self, label, key):
        self.buttons.append((label, key))
        return self.button_result

    def spinner(self, _message):
        return nullcontext()

    def success(self, message):
        self.messages.append(message)

    def error(self, message):
        self.messages.append(message)

    def page_link(self, page, label, icon):
        self.messages.append((page, label, icon))

    def rerun(self):
        self.rerun_called = True


def test_empty_exasol_snapshot_can_be_explicitly_run_against_local_invoices(monkeypatch):
    session_state = {
        "ll_data": {"invoices": pd.DataFrame([{"invoice_id": "I1"}])},
        "ll_exasol_loaded": True,
        "ll_exasol_counts": {"invoices": 0},
    }
    fake_streamlit = FakeStreamlit(session_state, button_result=True)
    monkeypatch.setattr(ui, "st", fake_streamlit)

    def run_local():
        assert session_state["ll_exasol_loaded"] is False
        assert session_state["ll_mode"] == "Local mode · session data"
        return [{"finding_id": "F1"}]

    monkeypatch.setattr(ui, "run_analysis", run_local)

    assert ui.show_local_analysis_recovery("test_run_local")
    assert fake_streamlit.buttons == [
        ("Run locally with current session data", "test_run_local")
    ]
    assert fake_streamlit.rerun_called
    assert "Local analysis complete: 1 finding." in fake_streamlit.messages


def test_empty_exasol_snapshot_links_to_import_without_local_invoices(monkeypatch):
    session_state = {
        "ll_data": {"invoices": pd.DataFrame()},
        "ll_exasol_loaded": True,
        "ll_exasol_counts": {"invoices": 0},
    }
    fake_streamlit = FakeStreamlit(session_state)
    monkeypatch.setattr(ui, "st", fake_streamlit)

    assert ui.show_local_analysis_recovery("test_run_local")
    assert fake_streamlit.buttons == []
    assert (
        "pages/data_import.py",
        "Open Data Import",
        ":material/upload_file:",
    ) in fake_streamlit.messages
