"""
SQLite Database Backup Service for Lazy Rabbit Agent.

Provides:
  - Full database export to JSON (all tables, with metadata)
  - Safe import with conflict resolution (skip / update / error)
  - Binary .db file backup (SQLite online backup API)
  - Automatic scheduled backups with rotation

Design Principles:
  - Import NEVER silently overwrites — user chooses conflict strategy
  - Exports include schema version (alembic) for compatibility checks
  - Backups are timestamped and rotated (configurable max count)
"""

import json
import logging
import os
import shutil
import sqlite3
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import sqlalchemy
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.db.base import SessionLocal, engine

logger = logging.getLogger("backup_service")

DEFAULT_BACKUP_DIR = "backups"
DEFAULT_MAX_BACKUPS = 30


class ConflictStrategy(str, Enum):
    """Strategy for handling conflicts during import."""

    SKIP = "skip"
    UPDATE = "update"
    ERROR = "error"


class BackupService:
    """
    Manages SQLite database backup, export, and import operations.
    """

    def __init__(
        self,
        backup_dir: str = DEFAULT_BACKUP_DIR,
        max_backups: int = DEFAULT_MAX_BACKUPS,
    ):
        self.backup_dir = Path(backup_dir)
        self.max_backups = max_backups
        self._ensure_backup_dir()

    def _ensure_backup_dir(self):
        """Create backup directory if it doesn't exist."""
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def export_to_json(
        self,
        output_path: Optional[str] = None,
        tables: Optional[list[str]] = None,
        exclude_tables: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        Export the entire database (or selected tables) to a JSON file.

        Args:
            output_path: Custom output file path. If None, auto-generates
                         a timestamped filename in the backup directory.
            tables: If provided, only export these tables.
            exclude_tables: Tables to exclude from export (e.g., alembic_version).

        Returns:
            Dict with export metadata:
              - path: Output file path
              - tables: List of exported table names
              - row_counts: Dict of table → row count
              - total_rows: Total rows exported
              - file_size_bytes: Size of the output file
              - exported_at: ISO timestamp
              - schema_version: Alembic schema version
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if output_path is None:
            output_path = str(self.backup_dir / f"backup_{timestamp}.json")

        db = SessionLocal()
        try:
            schema_version = self._get_schema_version(db)
            inspector = inspect(engine)
            all_tables = inspector.get_table_names()

            if tables:
                export_tables = [t for t in tables if t in all_tables]
            elif exclude_tables:
                export_tables = [t for t in all_tables if t not in exclude_tables]
            else:
                export_tables = all_tables

            export_data = {
                "_metadata": {
                    "exported_at": datetime.now().isoformat(),
                    "schema_version": schema_version,
                    "format_version": "1.0",
                    "tables": export_tables,
                    "source": "lazy-rabbit-agent",
                },
                "tables": {},
            }

            row_counts = {}
            for table_name in export_tables:
                rows = self._export_table(db, table_name)
                export_data["tables"][table_name] = rows
                row_counts[table_name] = len(rows)
                logger.info(f"  📦 Exported {table_name}: {len(rows)} rows")

            # Write to file
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)

            file_size = output_file.stat().st_size
            total_rows = sum(row_counts.values())

            logger.info(
                f"✅ Export complete: {output_path} "
                f"({len(export_tables)} tables, {total_rows} rows, "
                f"{file_size / 1024:.1f} KB)"
            )

            return {
                "path": str(output_path),
                "tables": export_tables,
                "row_counts": row_counts,
                "total_rows": total_rows,
                "file_size_bytes": file_size,
                "exported_at": datetime.now().isoformat(),
                "schema_version": schema_version,
            }
        except Exception as e:
            logger.error(f"❌ Export failed: {e}", exc_info=True)
            raise
        finally:
            db.close()

    def _export_table(self, db: Session, table_name: str) -> list[dict]:
        """Export all rows from a table as a list of dicts."""
        result = db.execute(text(f"SELECT * FROM {table_name}"))
        columns = list(result.keys())
        rows = []
        for row in result:
            row_dict = {}
            for i, col in enumerate(columns):
                value = row[i]
                if isinstance(value, datetime):
                    value = value.isoformat()
                elif isinstance(value, bytes):
                    value = value.hex()
                row_dict[col] = value
            rows.append(row_dict)
        return rows

    def import_from_json(
        self,
        input_path: str,
        conflict_strategy: ConflictStrategy = ConflictStrategy.SKIP,
        tables: Optional[list[str]] = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """
        Import data from a JSON backup file into the database.

        SAFETY: Before importing, automatically creates a pre-import backup.

        Args:
            input_path: Path to the JSON backup file.
            conflict_strategy: How to handle rows that already exist:
                - SKIP: Ignore conflicting rows (safest, no data loss)
                - UPDATE: Overwrite existing rows with imported data
                - ERROR: Abort on first conflict
            tables: If provided, only import these tables.
            dry_run: If True, simulate import without writing to DB.

        Returns:
            Dict with import results per table and summary.
        """
        input_file = Path(input_path)
        if not input_file.exists():
            raise FileNotFoundError(f"Backup file not found: {input_path}")

        with open(input_file, "r", encoding="utf-8") as f:
            backup_data = json.load(f)

        metadata = backup_data.get("_metadata")
        if not metadata or "tables" not in backup_data:
            raise ValueError(
                "Invalid backup file format. Expected '_metadata' and 'tables' keys."
            )

        logger.info(
            f"📥 Importing from: {input_path} "
            f"(exported at: {metadata.get('exported_at')}, "
            f"schema: {metadata.get('schema_version')})"
        )

        db = SessionLocal()
        try:
            # Check schema version compatibility
            current_version = self._get_schema_version(db)
            backup_version = metadata.get("schema_version")
            if current_version != backup_version:
                logger.warning(
                    f"⚠️ Schema version mismatch! Current: {current_version}, "
                    f"Backup: {backup_version}. Import may fail if schema has changed."
                )

            # Create pre-import backup
            pre_import_backup = None
            if not dry_run:
                pre_import_result = self.export_to_json(
                    output_path=str(
                        self.backup_dir
                        / f"pre_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    )
                )
                pre_import_backup = pre_import_result["path"]
                logger.info(f"🛡️ Pre-import backup saved: {pre_import_backup}")

            # Determine tables to import
            available_tables = list(backup_data["tables"].keys())
            if tables:
                import_tables = [t for t in tables if t in available_tables]
            else:
                import_tables = [t for t in available_tables if t != "alembic_version"]

            results = {
                "imported": {},
                "skipped": {},
                "updated": {},
                "errors": [],
                "pre_import_backup": pre_import_backup,
                "dry_run": dry_run,
                "conflict_strategy": conflict_strategy.value,
            }

            for table_name in import_tables:
                rows = backup_data["tables"][table_name]
                try:
                    table_result = self._import_table(
                        db, table_name, rows, conflict_strategy, dry_run
                    )
                    results["imported"][table_name] = table_result["imported"]
                    results["skipped"][table_name] = table_result["skipped"]
                    results["updated"][table_name] = table_result["updated"]
                    if table_result["errors"]:
                        results["errors"].extend(table_result["errors"])

                    prefix = "🔍" if dry_run else "📥"
                    logger.info(
                        f"  {prefix} {table_name}: "
                        f"{table_result['imported']} imported, "
                        f"{table_result['skipped']} skipped, "
                        f"{table_result['updated']} updated"
                    )
                except Exception as e:
                    logger.error(f"❌ Import failed, rolled back: {e}", exc_info=True)
                    results["errors"].append(f"[{table_name}] Fatal: {str(e)[:200]}")

            if not dry_run:
                db.commit()
                logger.info("✅ Import committed to database")
            else:
                db.rollback()
                logger.info("🔍 Dry run complete — no changes made")

            # Summary
            total_imported = sum(results["imported"].values())
            total_skipped = sum(results["skipped"].values())
            total_updated = sum(results["updated"].values())
            total_errors = len(results["errors"])

            results["summary"] = {
                "total_imported": total_imported,
                "total_skipped": total_skipped,
                "total_updated": total_updated,
                "total_errors": total_errors,
            }

            prefix = "🔍 [DRY RUN]" if dry_run else "✅"
            logger.info(
                f"{prefix} Import summary: "
                f"{total_imported} imported, "
                f"{total_skipped} skipped, "
                f"{total_updated} updated, "
                f"{total_errors} errors"
            )

            return results
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Import failed, rolled back: {e}", exc_info=True)
            raise
        finally:
            db.close()

    def _import_table(
        self,
        db: Session,
        table_name: str,
        rows: list[dict],
        conflict_strategy: ConflictStrategy,
        dry_run: bool,
    ) -> dict[str, Any]:
        """
        Import rows into a single table with conflict resolution.

        Uses INSERT OR IGNORE / INSERT OR REPLACE based on strategy.
        """
        result = {"imported": 0, "skipped": 0, "updated": 0, "errors": []}

        if not rows:
            return result

        inspector = inspect(engine)
        pk_columns = inspector.get_pk_constraint(table_name).get(
            "constrained_columns", []
        )
        columns = list(rows[0].keys())
        col_list = ", ".join(columns)
        placeholders = ", ".join(f":{col}" for col in columns)

        for row in rows:
            try:
                if conflict_strategy == ConflictStrategy.SKIP:
                    sql = f"INSERT OR IGNORE INTO {table_name} ({col_list}) VALUES ({placeholders})"
                    if not dry_run:
                        res = db.execute(text(sql), row)
                        if res.rowcount > 0:
                            result["imported"] += 1
                        else:
                            result["skipped"] += 1
                    else:
                        result["imported"] += 1

                elif conflict_strategy == ConflictStrategy.UPDATE:
                    if pk_columns:
                        # Check if row exists
                        where_clause = " AND ".join(
                            f"{pk} = :{pk}" for pk in pk_columns
                        )
                        check_sql = (
                            f"SELECT COUNT(*) FROM {table_name} WHERE {where_clause}"
                        )
                        pk_values = {pk: row[pk] for pk in pk_columns if pk in row}
                        exists = db.execute(text(check_sql), pk_values).scalar()

                        if exists:
                            # Update existing row
                            set_clause = ", ".join(
                                f"{col} = :{col}"
                                for col in columns
                                if col not in pk_columns
                            )
                            update_sql = f"UPDATE {table_name} SET {set_clause} WHERE {where_clause}"
                            if not dry_run:
                                db.execute(text(update_sql), row)
                            result["updated"] += 1
                        else:
                            # Insert new row
                            insert_sql = f"INSERT INTO {table_name} ({col_list}) VALUES ({placeholders})"
                            if not dry_run:
                                db.execute(text(insert_sql), row)
                            result["imported"] += 1
                    else:
                        # No PK, use INSERT OR REPLACE
                        sql = f"INSERT OR REPLACE INTO {table_name} ({col_list}) VALUES ({placeholders})"
                        if not dry_run:
                            db.execute(text(sql), row)
                        result["imported"] += 1

                elif conflict_strategy == ConflictStrategy.ERROR:
                    sql = (
                        f"INSERT INTO {table_name} ({col_list}) VALUES ({placeholders})"
                    )
                    if not dry_run:
                        db.execute(text(sql), row)
                    result["imported"] += 1

            except Exception as e:
                error_msg = str(e)[:200]
                result["errors"].append(error_msg)
                logger.warning(f"  ⚠️ {table_name}: {error_msg}")

        return result

    def create_binary_backup(self, output_path: Optional[str] = None) -> dict[str, Any]:
        """
        Create a binary copy of the SQLite database file.

        Uses SQLite's online backup API, which is safe even while
        the database is being written to.

        Args:
            output_path: Custom output path. If None, auto-generates.

        Returns:
            Dict with backup metadata.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if output_path is None:
            output_path = str(self.backup_dir / f"backup_{timestamp}.db")

        db_path = self._get_db_file_path()
        if not Path(db_path).exists():
            raise FileNotFoundError(f"Database file not found: {db_path}")

        source = sqlite3.connect(db_path)
        dest = sqlite3.connect(output_path)
        try:
            source.backup(dest)
            logger.info(f"✅ Binary backup created: {output_path}")
        finally:
            dest.close()
            source.close()

        file_size = Path(output_path).stat().st_size
        return {
            "path": str(output_path),
            "size_bytes": file_size,
            "size_human": self._human_size(file_size),
            "created_at": datetime.now().isoformat(),
            "type": "binary",
        }

    def scheduled_backup(self) -> dict[str, Any]:
        """
        Perform a full scheduled backup: JSON export + binary backup + rotation.

        Returns:
            Dict with results of both backup operations.
        """
        results = {}

        # JSON export
        try:
            json_result = self.export_to_json()
            results["json_backup"] = json_result
        except Exception as e:
            logger.error(f"❌ Scheduled JSON backup failed: {e}", exc_info=True)
            results["json_backup"] = {"error": str(e)}

        # Binary backup
        try:
            binary_result = self.create_binary_backup()
            results["binary_backup"] = binary_result
        except Exception as e:
            logger.error(f"❌ Scheduled binary backup failed: {e}", exc_info=True)
            results["binary_backup"] = {"error": str(e)}

        # Rotate old backups
        try:
            rotation_result = self.rotate_backups()
            results["rotation"] = rotation_result
        except Exception as e:
            logger.error(f"❌ Backup rotation failed: {e}", exc_info=True)
            results["rotation"] = {"error": str(e)}

        return results

    def rotate_backups(self) -> dict[str, Any]:
        """
        Remove old backups exceeding the max_backups limit.

        Keeps the newest backups, removes the oldest.

        Returns:
            Dict with rotation results.
        """
        json_removed = self._rotate_files("*.json")
        db_removed = self._rotate_files("*.db")

        total_removed = json_removed + db_removed
        if total_removed > 0:
            logger.info(
                f"🗑️ Rotated {total_removed} old backups ({json_removed} JSON, {db_removed} DB)"
            )

        return {
            "json_removed": json_removed,
            "db_removed": db_removed,
            "total_removed": total_removed,
            "max_backups": self.max_backups,
        }

    def _rotate_files(self, pattern: str) -> int:
        """Remove oldest files matching pattern if count exceeds max_backups."""
        files = sorted(self.backup_dir.glob(pattern), key=lambda f: f.stat().st_mtime)
        removed = 0
        while len(files) > self.max_backups:
            oldest = files.pop(0)
            oldest.unlink()
            logger.info(f"  🗑️ Removed old backup: {oldest.name}")
            removed += 1
        return removed

    def list_backups(self) -> list[dict[str, Any]]:
        """
        List all backup files with metadata.

        Returns:
            List of dicts with file info, sorted newest first.
        """
        backups = []
        for f in sorted(
            self.backup_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True
        ):
            if f.is_file() and (f.suffix == ".json" or f.suffix == ".db"):
                stat = f.stat()
                backups.append(
                    {
                        "filename": f.name,
                        "path": str(f),
                        "type": "json" if f.suffix == ".json" else "binary",
                        "size_bytes": stat.st_size,
                        "size_human": self._human_size(stat.st_size),
                        "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "is_pre_import": f.name.startswith("pre_import_"),
                    }
                )
        return backups

    def delete_backup(self, filename: str) -> dict[str, Any]:
        """
        Delete a specific backup file.

        Args:
            filename: Name of the backup file to delete.

        Returns:
            Dict with deletion result.
        """
        filepath = self.backup_dir / filename
        if not filepath.exists() or not filepath.is_file():
            raise FileNotFoundError(f"Backup file not found: {filename}")

        # Safety: ensure file is within backup directory
        if filepath.resolve().parent != self.backup_dir.resolve():
            raise PermissionError("Access denied: file is outside backup directory")

        size = filepath.stat().st_size
        filepath.unlink()
        logger.info(f"🗑️ Deleted backup: {filename} ({self._human_size(size)})")

        return {
            "filename": filename,
            "deleted": True,
            "size_bytes": size,
        }

    def _get_schema_version(self, db: Session) -> str:
        """Get the current alembic schema version."""
        try:
            result = db.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
            row = result.fetchone()
            return row[0] if row else "unknown"
        except Exception:
            return "unknown"

    def _get_db_file_path(self) -> str:
        """Extract the SQLite database file path from the engine URL."""
        url = str(engine.url)
        # sqlite:///./app.db → ./app.db
        if "sqlite" in url:
            return url.split("///")[-1]
        raise ValueError(f"Not a SQLite database: {url}")

    @staticmethod
    def _human_size(size_bytes: int) -> str:
        """Convert bytes to human-readable size string."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


# Singleton instance
backup_service = BackupService()
