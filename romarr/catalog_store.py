"""Durable inventory generations and small background-work primitives.

The JSON Store remains the owner of settings, Wanted and legacy queue state.
This database owns large, replaceable inventory observations and the durable
coordination records needed to bridge those two stores safely.

The default journal is rollback mode. WAL is deliberately not enabled here:
ROMarr installations commonly put their state on bind mounts, NAS volumes or
LXC storage whose locking and fsync semantics have not been qualified.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


class UnsupportedCatalogSchema(RuntimeError):
    """Raised when a newer database must be preserved for a newer ROMarr."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"),
                      sort_keys=True)


def _object(value: str | None, default=None):
    if not value:
        return default
    try:
        result = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default
    return result


def stable_item_id(source_id: str, locator: str) -> str:
    raw = f"{source_id}\0{locator}".encode("utf-8", "surrogatepass")
    return hashlib.sha256(raw).hexdigest()


class CatalogStore:
    """Single serialized SQLite writer for inventory, jobs and outbox rows."""

    SCHEMA_VERSION = 1
    MAX_OPERATION_RESULTS = 20_000

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._db = sqlite3.connect(str(self.path), timeout=10,
                                   check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA foreign_keys=ON")
        self._db.execute("PRAGMA busy_timeout=10000")
        self._db.execute("PRAGMA synchronous=FULL")
        try:
            self._migrate()
        except Exception:
            self._db.close()
            raise

    def _migrate(self) -> None:
        with self._lock:
            version = int(self._db.execute("PRAGMA user_version").fetchone()[0])
            if version > self.SCHEMA_VERSION:
                raise UnsupportedCatalogSchema(
                    f"{self.path} uses catalog schema {version}, newer than "
                    f"this ROMarr supports ({self.SCHEMA_VERSION}); preserve "
                    "the database and upgrade ROMarr before starting it."
                )
            self._db.execute("PRAGMA journal_mode=DELETE")
            if version == self.SCHEMA_VERSION:
                return
            ddl = """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                checksum TEXT NOT NULL,
                applied_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS instance_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS library_sources (
                source_id TEXT PRIMARY KEY,
                backend TEXT NOT NULL,
                namespace TEXT NOT NULL,
                config_revision TEXT NOT NULL,
                active_generation TEXT,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS scan_runs (
                run_id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL REFERENCES library_sources(source_id),
                config_revision TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                finished_at TEXT,
                visited_directories INTEGER NOT NULL DEFAULT 0,
                visited_entries INTEGER NOT NULL DEFAULT 0,
                emitted_items INTEGER NOT NULL DEFAULT 0,
                skipped_entries INTEGER NOT NULL DEFAULT 0,
                truncation_reason TEXT NOT NULL DEFAULT '',
                error TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(source_id) REFERENCES library_sources(source_id)
            );
            CREATE INDEX IF NOT EXISTS ix_scan_runs_source_status
                ON scan_runs(source_id, status, updated_at DESC);
            CREATE TABLE IF NOT EXISTS scan_directories (
                run_id TEXT NOT NULL REFERENCES scan_runs(run_id) ON DELETE CASCADE,
                relative_path TEXT NOT NULL,
                cursor_name TEXT NOT NULL DEFAULT '',
                state TEXT NOT NULL DEFAULT 'pending',
                PRIMARY KEY(run_id, relative_path)
            );
            CREATE INDEX IF NOT EXISTS ix_scan_directories_pending
                ON scan_directories(run_id, state, relative_path);
            CREATE TABLE IF NOT EXISTS scan_items (
                run_id TEXT NOT NULL REFERENCES scan_runs(run_id) ON DELETE CASCADE,
                source_id TEXT NOT NULL,
                locator TEXT NOT NULL,
                item_id TEXT NOT NULL,
                platform_slug TEXT NOT NULL DEFAULT '',
                normalized_title TEXT NOT NULL DEFAULT '',
                payload TEXT NOT NULL,
                PRIMARY KEY(run_id, locator)
            );
            CREATE INDEX IF NOT EXISTS ix_scan_items_system_title
                ON scan_items(run_id, platform_slug, normalized_title, item_id);
            CREATE INDEX IF NOT EXISTS ix_scan_items_item_id
                ON scan_items(source_id, item_id, run_id);
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                state TEXT NOT NULL,
                idempotency_key TEXT NOT NULL UNIQUE,
                generation TEXT,
                payload TEXT NOT NULL,
                result TEXT NOT NULL DEFAULT '{}',
                cancel_epoch INTEGER NOT NULL DEFAULT 0,
                attempts INTEGER NOT NULL DEFAULT 0,
                lease_owner TEXT NOT NULL DEFAULT '',
                lease_until TEXT,
                next_attempt_at TEXT,
                error TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS ix_jobs_admission
                ON jobs(state, next_attempt_at, created_at);
            CREATE TABLE IF NOT EXISTS job_items (
                job_id TEXT NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
                item_key TEXT NOT NULL,
                state TEXT NOT NULL,
                payload TEXT NOT NULL,
                error TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL,
                PRIMARY KEY(job_id, item_key)
            );
            CREATE TABLE IF NOT EXISTS selection_previews (
                preview_id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL DEFAULT '',
                inventory_generation TEXT NOT NULL DEFAULT '',
                policy_revision TEXT NOT NULL DEFAULT '',
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS ix_previews_expiry
                ON selection_previews(expires_at);
            CREATE TABLE IF NOT EXISTS acquisition_outbox (
                operation_id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL REFERENCES jobs(job_id),
                target_identity TEXT NOT NULL,
                payload TEXT NOT NULL,
                state TEXT NOT NULL,
                result TEXT NOT NULL DEFAULT '{}',
                error TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS ix_outbox_state
                ON acquisition_outbox(state, created_at);
            """
            checksum = hashlib.sha256(ddl.encode("utf-8")).hexdigest()
            try:
                self._db.executescript("BEGIN IMMEDIATE;\n" + ddl)
                self._db.execute(
                    "INSERT OR REPLACE INTO schema_migrations "
                    "(version,checksum,applied_at) VALUES (?,?,?)",
                    (1, checksum, _now()))
                self._db.execute("PRAGMA user_version=1")
                self._db.commit()
            except Exception:
                self._db.rollback()
                raise

    def close(self) -> None:
        with self._lock:
            self._db.close()

    # -- scan generations -------------------------------------------------

    def register_source(self, source_id: str, backend: str, namespace: str,
                        config_revision: str) -> None:
        with self._lock:
            self._db.execute(
                "INSERT INTO library_sources(source_id,backend,namespace,"
                "config_revision,updated_at) VALUES (?,?,?,?,?) "
                "ON CONFLICT(source_id) DO UPDATE SET backend=excluded.backend,"
                "namespace=excluded.namespace,updated_at=excluded.updated_at",
                (source_id, backend, namespace, config_revision, _now()))
            current = self._db.execute(
                "SELECT config_revision FROM library_sources WHERE source_id=?",
                (source_id,)).fetchone()[0]
            if current != config_revision:
                self._db.execute(
                    "UPDATE library_sources SET config_revision=?,updated_at=? "
                    "WHERE source_id=?", (config_revision, _now(), source_id))
                self._db.execute(
                    "UPDATE scan_runs SET status='superseded',finished_at=?,updated_at=? "
                    "WHERE source_id=? AND status='running'",
                    (_now(), _now(), source_id))
            self._db.commit()

    def ensure_scan(self, source_id: str, config_revision: str) -> str:
        """Return the resumable run, or create one with a root checkpoint."""
        with self._lock:
            row = self._db.execute(
                "SELECT run_id FROM scan_runs WHERE source_id=? AND "
                "config_revision=? AND status='running' ORDER BY started_at DESC LIMIT 1",
                (source_id, config_revision)).fetchone()
            if row:
                return str(row[0])
            run_id = uuid.uuid4().hex
            now = _now()
            self._db.execute(
                "INSERT INTO scan_runs(run_id,source_id,config_revision,status,"
                "started_at,updated_at) VALUES (?,?,?,'running',?,?)",
                (run_id, source_id, config_revision, now, now))
            self._db.execute(
                "INSERT INTO scan_directories(run_id,relative_path) VALUES (?, '')",
                (run_id,))
            self._db.commit()
            return run_id

    def next_scan_directory(self, run_id: str) -> dict | None:
        with self._lock:
            row = self._db.execute(
                "SELECT relative_path,cursor_name FROM scan_directories "
                "WHERE run_id=? AND state='pending' "
                "ORDER BY length(relative_path),relative_path LIMIT 1", (run_id,)
            ).fetchone()
        return dict(row) if row else None

    def scan_directory_count(self, run_id: str) -> int:
        with self._lock:
            row = self._db.execute(
                "SELECT count(*) FROM scan_directories WHERE run_id=?", (run_id,)
            ).fetchone()
        return int(row[0])

    def record_scan_batch(self, run_id: str, source_id: str,
                          games: list[dict], *, visited_entries: int = 0,
                          skipped_entries: int = 0) -> None:
        if not games and not visited_entries and not skipped_entries:
            return
        rows = []
        for game in games:
            locator = str(game.get("locator") or "")
            if not locator:
                continue
            rows.append((run_id, source_id, locator,
                         str(game.get("id") or stable_item_id(source_id, locator)),
                         str(game.get("platform_slug") or ""),
                         str(game.get("name") or "").casefold(), _json(game)))
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                if rows:
                    self._db.executemany(
                        "INSERT INTO scan_items(run_id,source_id,locator,item_id,"
                        "platform_slug,normalized_title,payload) VALUES (?,?,?,?,?,?,?) "
                        "ON CONFLICT(run_id,locator) DO UPDATE SET "
                        "item_id=excluded.item_id,platform_slug=excluded.platform_slug,"
                        "normalized_title=excluded.normalized_title,payload=excluded.payload",
                        rows)
                self._db.execute(
                    "UPDATE scan_runs SET visited_entries=visited_entries+?,"
                    "skipped_entries=skipped_entries+?,emitted_items=(SELECT count(*) "
                    "FROM scan_items WHERE run_id=?),updated_at=? WHERE run_id=?",
                    (int(visited_entries), int(skipped_entries), run_id, _now(), run_id))
                self._db.commit()
            except Exception:
                self._db.rollback()
                raise

    def finish_scan_directory(self, run_id: str, relative_path: str,
                              child_directories: list[str], *,
                              cursor_name: str | None, entry_count: int) -> None:
        """Persist discovered children and the resumable per-directory cursor."""
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                for child in child_directories:
                    self._db.execute(
                        "INSERT OR IGNORE INTO scan_directories(run_id,relative_path) "
                        "VALUES (?,?)", (run_id, child))
                if cursor_name is None:
                    self._db.execute(
                        "UPDATE scan_directories SET state='done',cursor_name='' "
                        "WHERE run_id=? AND relative_path=?", (run_id, relative_path))
                else:
                    self._db.execute(
                        "UPDATE scan_directories SET state='pending',cursor_name=? "
                        "WHERE run_id=? AND relative_path=?",
                        (cursor_name, run_id, relative_path))
                self._db.execute(
                    "UPDATE scan_runs SET visited_directories=(SELECT count(*) FROM "
                    "scan_directories WHERE run_id=? AND state='done'),updated_at=? "
                    "WHERE run_id=?", (run_id, _now(), run_id))
                self._db.commit()
            except Exception:
                self._db.rollback()
                raise

    def finish_scan(self, run_id: str, *, complete: bool,
                    error: str = "", truncation_reason: str = "") -> bool:
        """Complete and publish only a generation with no pending work."""
        now = _now()
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                run = self._db.execute(
                    "SELECT source_id,config_revision,status FROM scan_runs WHERE run_id=?",
                    (run_id,)).fetchone()
                if not run:
                    self._db.rollback()
                    return False
                pending = self._db.execute(
                    "SELECT 1 FROM scan_directories WHERE run_id=? AND state='pending' LIMIT 1",
                    (run_id,)).fetchone()
                source = self._db.execute(
                    "SELECT config_revision FROM library_sources WHERE source_id=?",
                    (run["source_id"],)).fetchone()
                publish = bool(complete and pending is None and source
                               and source[0] == run["config_revision"]
                               and run["status"] == "running")
                status = "complete" if publish else (
                    "failed" if error and not truncation_reason else "partial")
                self._db.execute(
                    "UPDATE scan_runs SET status=?,finished_at=?,updated_at=?,error=?,"
                    "truncation_reason=? WHERE run_id=?",
                    (status, now, now, error, truncation_reason, run_id))
                if publish:
                    self._db.execute(
                        "UPDATE library_sources SET active_generation=?,updated_at=? "
                        "WHERE source_id=? AND config_revision=?",
                        (run_id, now, run["source_id"], run["config_revision"]))
                self._db.commit()
                return publish
            except Exception:
                self._db.rollback()
                raise

    def scan_status(self, source_id: str) -> dict:
        with self._lock:
            source = self._db.execute(
                "SELECT * FROM library_sources WHERE source_id=?", (source_id,)
            ).fetchone()
            run = self._db.execute(
                "SELECT * FROM scan_runs WHERE source_id=? "
                "ORDER BY started_at DESC LIMIT 1", (source_id,)).fetchone()
            active = str(source["active_generation"] or "") if source else ""
            active_run = self._db.execute(
                "SELECT config_revision,status FROM scan_runs WHERE run_id=?",
                (active,)).fetchone() if active else None
            active_current = bool(
                active_run and active_run["status"] == "complete"
                and active_run["config_revision"] == source["config_revision"])
            count = 0
            if active:
                count = int(self._db.execute(
                    "SELECT count(*) FROM scan_items WHERE run_id=?", (active,)
                ).fetchone()[0])
            elif run and run["status"] in ("running", "partial"):
                count = int(self._db.execute(
                    "SELECT count(*) FROM scan_items WHERE run_id=?", (run["run_id"],)
                ).fetchone()[0])
        if not source:
            return {"source_id": source_id, "status": "not_scanned", "count": 0,
                    "complete": False, "generation": ""}
        result = {"source_id": source_id, "status": "not_scanned", "count": count,
                  "complete": active_current, "generation": active,
                  "last_complete_available": bool(active),
                  "active_current": active_current,
                  "active_config_revision": (active_run["config_revision"]
                                             if active_run else ""),
                  "config_revision": source["config_revision"]}
        if run:
            result.update({"status": run["status"], "run_id": run["run_id"],
                           "started_at": run["started_at"],
                           "updated_at": run["updated_at"],
                           "visited_directories": run["visited_directories"],
                           "visited_entries": run["visited_entries"],
                           "emitted_items": run["emitted_items"],
                           "skipped_entries": run["skipped_entries"],
                           "run_config_revision": run["config_revision"],
                           "error": run["error"],
                           "truncation_reason": run["truncation_reason"]})
            result["scan_complete"] = run["status"] == "complete"
            if active:
                result["generation"] = active
                result["complete"] = active_current
        return result

    def scan_page(self, source_id: str, *, limit: int = 500,
                  offset: int = 0, generation: str = "") -> list[dict]:
        with self._lock:
            if not generation:
                source = self._db.execute(
                    "SELECT active_generation FROM library_sources WHERE source_id=?",
                    (source_id,)).fetchone()
                generation = str(source[0] or "") if source else ""
                if not generation:
                    run = self._db.execute(
                        "SELECT run_id FROM scan_runs WHERE source_id=? AND "
                        "status IN ('running','partial') ORDER BY started_at DESC LIMIT 1",
                        (source_id,)).fetchone()
                    generation = str(run[0]) if run else ""
            if not generation:
                return []
            rows = self._db.execute(
                "SELECT payload FROM scan_items WHERE source_id=? AND run_id=? "
                "ORDER BY platform_slug,normalized_title,locator LIMIT ? OFFSET ?",
                (source_id, generation, max(1, min(int(limit), 5000)),
                 max(0, int(offset)))).fetchall()
        return [row for item in rows if (row := _object(item[0], {}))]

    def scan_source_summary(self) -> list[dict]:
        with self._lock:
            ids = [str(row[0]) for row in self._db.execute(
                "SELECT source_id FROM library_sources ORDER BY source_id")]
        return [self.scan_status(source_id) for source_id in ids]

    def invalidate_scan(self, source_id: str) -> None:
        with self._lock:
            self._db.execute(
                "UPDATE scan_runs SET status='superseded',finished_at=?,updated_at=? "
                "WHERE source_id=? AND status='running'", (_now(), _now(), source_id))
            self._db.commit()

    # -- durable jobs and the JSON Store bridge ---------------------------

    def create_job(self, kind: str, idempotency_key: str, payload: dict,
                   *, generation: str = "") -> dict:
        key = str(idempotency_key or uuid.uuid4().hex)
        now = _now()
        with self._lock:
            row = self._db.execute(
                "SELECT * FROM jobs WHERE idempotency_key=?", (key,)).fetchone()
            if row:
                return self._job(row)
            job_id = uuid.uuid4().hex
            self._db.execute(
                "INSERT INTO jobs(job_id,kind,state,idempotency_key,generation,payload,"
                "created_at,updated_at) VALUES (?,?, 'queued',?,?,?,?,?)",
                (job_id, str(kind), key, generation, _json(payload), now, now))
            self._db.commit()
            return self.get_job(job_id)

    def create_wanted_operation(self, items: list[tuple[str, str]], *,
                                idempotency_key: str = "") -> tuple[str, str]:
        key = idempotency_key or uuid.uuid4().hex
        payload = {"items": [{"game": str(game), "platform": str(platform)}
                             for game, platform in items]}
        job = self.create_job("wanted.bulk", key, payload)
        operation_id = f"wanted:{job['job_id']}"
        now = _now()
        with self._lock:
            self._db.execute(
                "INSERT OR IGNORE INTO acquisition_outbox(operation_id,job_id,"
                "target_identity,payload,state,created_at,updated_at) "
                "VALUES (?,?,? ,?,'pending',?,?)",
                (operation_id, job["job_id"], "legacy-store:wanted",
                 _json(payload), now, now))
            self._db.commit()
        return job["job_id"], operation_id

    def acknowledge_outbox(self, operation_id: str, result: dict) -> None:
        now = _now()
        with self._lock:
            self._db.execute(
                "UPDATE acquisition_outbox SET state='acknowledged',result=?,error='',"
                "updated_at=? WHERE operation_id=?",
                (_json(result), now, operation_id))
            row = self._db.execute(
                "SELECT job_id FROM acquisition_outbox WHERE operation_id=?",
                (operation_id,)).fetchone()
            if row:
                self._db.execute(
                    "UPDATE jobs SET state='completed',result=?,error='',updated_at=? "
                    "WHERE job_id=?", (_json(result), now, row[0]))
            self._db.commit()

    def fail_outbox(self, operation_id: str, error: str, *, uncertain=False) -> None:
        state = "uncertain" if uncertain else "pending"
        with self._lock:
            self._db.execute(
                "UPDATE acquisition_outbox SET state=?,error=?,updated_at=? "
                "WHERE operation_id=?", (state, str(error)[:500], _now(), operation_id))
            self._db.commit()

    def pending_outbox(self, limit: int = 100) -> list[dict]:
        with self._lock:
            rows = self._db.execute(
                "SELECT operation_id,job_id,target_identity,payload,state,error "
                "FROM acquisition_outbox WHERE state='pending' ORDER BY created_at "
                "LIMIT ?", (max(1, min(int(limit), 500)),)).fetchall()
        return [{**dict(row), "payload": _object(row["payload"], {})} for row in rows]

    @staticmethod
    def _job(row: sqlite3.Row) -> dict:
        result = dict(row)
        result["payload"] = _object(result.get("payload"), {})
        result["result"] = _object(result.get("result"), {})
        return result

    def get_job(self, job_id: str) -> dict | None:
        with self._lock:
            row = self._db.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
        return self._job(row) if row else None

    def list_jobs(self, *, limit: int = 100, state: str = "") -> list[dict]:
        cap = max(1, min(int(limit), 500))
        with self._lock:
            if state:
                rows = self._db.execute(
                    "SELECT * FROM jobs WHERE state=? ORDER BY created_at DESC LIMIT ?",
                    (state, cap)).fetchall()
            else:
                rows = self._db.execute(
                    "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (cap,)
                ).fetchall()
        return [self._job(row) for row in rows]

    def lease_next_job(self, owner: str, *, lease_seconds: int = 60,
                       kinds: tuple[str, ...] = ()) -> dict | None:
        """Atomically claim one eligible job; external work is never in this tx."""
        now = datetime.now(timezone.utc)
        lease_until = (now.timestamp() + max(5, min(int(lease_seconds), 3600)))
        lease_text = datetime.fromtimestamp(lease_until, timezone.utc).isoformat(timespec="seconds")
        now_text = now.isoformat(timespec="seconds")
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                sql = ("SELECT * FROM jobs WHERE ((state IN ('queued','waiting_retry') "
                       "AND (next_attempt_at IS NULL OR next_attempt_at<=?)) OR "
                       "(state='running' AND lease_until<=?))")
                args: list[Any] = [now_text, now_text]
                if kinds:
                    sql += " AND kind IN (" + ",".join("?" for _ in kinds) + ")"
                    args.extend(kinds)
                sql += " ORDER BY created_at LIMIT 1"
                row = self._db.execute(sql, args).fetchone()
                if not row:
                    self._db.commit()
                    return None
                self._db.execute(
                    "UPDATE jobs SET state='running',lease_owner=?,lease_until=?,"
                    "attempts=attempts+1,updated_at=? WHERE job_id=?",
                    (str(owner), lease_text, now_text, row["job_id"]))
                self._db.commit()
            except Exception:
                self._db.rollback()
                raise
        return self.get_job(str(row["job_id"]))

    def finish_job(self, job_id: str, *, state: str = "completed",
                   result: dict | None = None, error: str = "",
                   next_attempt_at: str | None = None) -> None:
        if state not in {"queued", "running", "waiting_retry", "blocked", "paused",
                         "completed", "completed_with_errors", "failed", "cancelled"}:
            raise ValueError("invalid durable job state")
        with self._lock:
            self._db.execute(
                "UPDATE jobs SET state=?,result=?,error=?,next_attempt_at=?,"
                "lease_owner='',lease_until=NULL,updated_at=? WHERE job_id=?",
                (state, _json(result or {}), str(error)[:500], next_attempt_at,
                 _now(), job_id))
            self._db.commit()

    def cancel_job(self, job_id: str) -> bool:
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                cursor = self._db.execute(
                    "UPDATE jobs SET cancel_epoch=cancel_epoch+1,state='cancelled',"
                    "lease_owner='',lease_until=NULL,updated_at=? WHERE job_id=? "
                    "AND state NOT IN ('completed','completed_with_errors','failed','cancelled')",
                    (_now(), job_id))
                if cursor.rowcount:
                    self._db.execute(
                        "UPDATE acquisition_outbox SET state='cancelled',updated_at=? "
                        "WHERE job_id=? AND state='pending'", (_now(), job_id))
                self._db.commit()
            except Exception:
                self._db.rollback()
                raise
        return cursor.rowcount == 1

    def put_preview(self, payload: dict, *, source_id: str = "",
                    inventory_generation: str = "", policy_revision: str = "",
                    ttl_seconds: int = 1800) -> str:
        preview_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc)
        expires = datetime.fromtimestamp(now.timestamp() + max(60, min(ttl_seconds, 86400)),
                                         timezone.utc).isoformat(timespec="seconds")
        with self._lock:
            self._db.execute("DELETE FROM selection_previews WHERE expires_at<=?",
                             (now.isoformat(timespec="seconds"),))
            self._db.execute(
                "INSERT INTO selection_previews(preview_id,source_id,inventory_generation,"
                "policy_revision,payload,created_at,expires_at) VALUES (?,?,?,?,?,?,?)",
                (preview_id, source_id, inventory_generation, policy_revision,
                 _json(payload), now.isoformat(timespec="seconds"), expires))
            self._db.commit()
        return preview_id

    def get_preview(self, preview_id: str) -> dict | None:
        now = _now()
        with self._lock:
            row = self._db.execute(
                "SELECT * FROM selection_previews WHERE preview_id=? AND expires_at>?",
                (preview_id, now)).fetchone()
        if not row:
            return None
        result = dict(row)
        result["payload"] = _object(result["payload"], {})
        return result

    # -- backup and diagnostics -------------------------------------------

    def backup_to(self, destination: str | Path) -> Path:
        """Create a transactionally consistent SQLite backup without stopping writes."""
        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_name(target.name + f".{uuid.uuid4().hex}.tmp")
        try:
            with self._lock:
                with sqlite3.connect(str(temp)) as dest:
                    self._db.backup(dest)
            os.replace(temp, target)
        except Exception:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass
            raise
        return target

    def diagnostics(self) -> dict:
        with self._lock:
            version = int(self._db.execute("PRAGMA user_version").fetchone()[0])
            sizes = {table: int(self._db.execute(
                f"SELECT count(*) FROM {table}").fetchone()[0])
                for table in ("library_sources", "scan_runs", "scan_items",
                              "jobs", "job_items", "selection_previews",
                              "acquisition_outbox")}
            journal = str(self._db.execute("PRAGMA journal_mode").fetchone()[0])
        return {"path": str(self.path), "schema_version": version,
                "journal_mode": journal, "counts": sizes}
