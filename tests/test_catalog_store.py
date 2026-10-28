import sqlite3

import pytest

from romarr.catalog_store import CatalogStore, UnsupportedCatalogSchema


def _publish(store, source_id, revision, locator):
    run_id = store.ensure_scan(source_id, revision)
    store.record_scan_batch(run_id, source_id, [{
        "id": f"{source_id}:{locator}", "locator": locator,
        "name": locator, "platform_slug": "psx",
    }], visited_entries=1)
    store.finish_scan_directory(run_id, "", [], cursor_name=None, entry_count=1)
    assert store.finish_scan(run_id, complete=True) is True
    return run_id


def test_scan_generation_promotes_atomically_and_keeps_last_good_on_partial(tmp_path):
    store = CatalogStore(tmp_path / "catalog.sqlite3")
    store.register_source("library-a", "folder", "/roms", "rev-1")
    first = _publish(store, "library-a", "rev-1", "psx/First.chd")

    second = store.ensure_scan("library-a", "rev-1")
    store.record_scan_batch(second, "library-a", [{
        "id": "library-a:psx/Incomplete.chd", "locator": "psx/Incomplete.chd",
        "name": "Incomplete", "platform_slug": "psx",
    }], visited_entries=1)
    store.finish_scan(second, complete=False,
                      truncation_reason="test safety limit")

    status = store.scan_status("library-a")
    assert status["generation"] == first
    assert status["complete"] is True
    assert status["last_complete_available"] is True
    assert [row["locator"] for row in store.scan_page("library-a")] == [
        "psx/First.chd"]


def test_scan_checkpoints_resume_after_reopening_database(tmp_path):
    path = tmp_path / "catalog.sqlite3"
    store = CatalogStore(path)
    store.register_source("library-a", "folder", "/roms", "rev-1")
    run_id = store.ensure_scan("library-a", "rev-1")
    store.finish_scan_directory(run_id, "", ["psx"], cursor_name="B.iso",
                                entry_count=25)
    store.close()

    resumed = CatalogStore(path)
    assert resumed.ensure_scan("library-a", "rev-1") == run_id
    assert resumed.next_scan_directory(run_id) == {
        "relative_path": "", "cursor_name": "B.iso"}
    assert resumed.scan_directory_count(run_id) == 2


def test_config_revision_invalidates_export_completeness_but_preserves_rows(tmp_path):
    store = CatalogStore(tmp_path / "catalog.sqlite3")
    store.register_source("library-a", "folder", "/roms", "rev-1")
    first = _publish(store, "library-a", "rev-1", "psx/First.chd")
    store.register_source("library-a", "folder", "/roms", "rev-2")

    status = store.scan_status("library-a")
    assert status["generation"] == first
    assert status["last_complete_available"] is True
    assert status["complete"] is False
    assert store.scan_page("library-a")[0]["locator"] == "psx/First.chd"
    assert store.ensure_scan("library-a", "rev-2") != first


def test_job_creation_is_idempotent_and_outbox_ack_survives_restart(tmp_path):
    path = tmp_path / "catalog.sqlite3"
    store = CatalogStore(path)
    job_id, operation_id = store.create_wanted_operation(
        [("Final Fantasy VII", "psx")], idempotency_key="client-operation-7")
    duplicate_job, duplicate_operation = store.create_wanted_operation(
        [("Different payload", "ps2")], idempotency_key="client-operation-7")
    assert duplicate_job == job_id
    assert duplicate_operation == operation_id
    leased = store.lease_next_job("worker-a")
    assert leased["job_id"] == job_id
    assert leased["attempts"] == 1
    assert store.lease_next_job("worker-b") is None
    assert store.pending_outbox()[0]["operation_id"] == operation_id
    store.acknowledge_outbox(operation_id, {"added": 1})
    store.close()

    reopened = CatalogStore(path)
    assert reopened.pending_outbox() == []
    assert reopened.get_job(job_id)["state"] == "completed"
    assert reopened.get_job(job_id)["result"] == {"added": 1}


def test_cancelling_a_queued_job_cancels_its_unapplied_outbox(tmp_path):
    store = CatalogStore(tmp_path / "catalog.sqlite3")
    job_id, operation_id = store.create_wanted_operation(
        [("Game", "psx")], idempotency_key="cancel-before-apply")
    assert store.cancel_job(job_id) is True
    assert store.get_job(job_id)["state"] == "cancelled"
    assert store.pending_outbox() == []
    assert store._db.execute(
        "SELECT state FROM acquisition_outbox WHERE operation_id=?",
        (operation_id,)).fetchone()[0] == "cancelled"


def test_catalog_backup_is_a_consistent_sqlite_database(tmp_path):
    store = CatalogStore(tmp_path / "catalog.sqlite3")
    store.register_source("library-a", "folder", "/roms", "rev-1")
    _publish(store, "library-a", "rev-1", "psx/First.chd")
    backup = store.backup_to(tmp_path / "backup.sqlite3")

    with sqlite3.connect(backup) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert connection.execute("SELECT count(*) FROM scan_items").fetchone()[0] == 1
        assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "delete"


def test_newer_catalog_schema_is_preserved_and_refused(tmp_path):
    path = tmp_path / "catalog.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA user_version=99")

    with pytest.raises(UnsupportedCatalogSchema):
        CatalogStore(path)
