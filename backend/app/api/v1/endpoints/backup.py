"""
Database Backup API Endpoints.

Provides REST endpoints for:
  - Export database to JSON (download)
  - Import database from JSON (upload, with conflict strategy)
  - Create binary .db backup
  - List / delete backups
  - Trigger manual backup
  - View backup schedule status

All endpoints require admin or super_admin role.
"""

import logging
import tempfile
from pathlib import Path
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.models.user import User
from app.services.backup_service import BackupService, ConflictStrategy, backup_service

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Request / Response Models ---


class ExportRequest(BaseModel):
    """Request body for export endpoint."""

    tables: Optional[list[str]] = None
    exclude_tables: Optional[list[str]] = None


class ImportResponse(BaseModel):
    """Response for import endpoint."""

    imported: dict[str, int]
    skipped: dict[str, int]
    updated: dict[str, int]
    errors: list[str]
    pre_import_backup: Optional[str]
    dry_run: bool
    conflict_strategy: str
    summary: dict[str, int]


class BackupInfo(BaseModel):
    """Backup file information."""

    filename: str
    path: str
    type: str
    size_bytes: int
    size_human: str
    created_at: str
    is_pre_import: bool


class BackupListResponse(BaseModel):
    """Response for list backups endpoint."""

    backups: list[BackupInfo]
    total: int
    backup_dir: str


# --- Endpoints ---


@router.post("/export", summary="Export database to JSON")
async def export_database(
    current_user: Annotated[User, Depends(require_permission("user.read"))],
    request: ExportRequest = ExportRequest(),
):
    """
    Export the database to a JSON file and return it for download.

    - Exports all tables by default
    - Optionally specify `tables` to export only specific tables
    - Optionally specify `exclude_tables` to skip certain tables
    - Includes schema version for compatibility checking

    Requires: admin permission (user.read)
    """
    try:
        logger.info(f"📦 Admin {current_user.email} requested database export")

        tables = request.tables
        exclude_tables = request.exclude_tables
        result = backup_service.export_to_json(
            tables=tables, exclude_tables=exclude_tables
        )

        export_path = Path(result["path"])
        filename = export_path.name

        logger.info(
            f"✅ Export complete for {current_user.email}: "
            f"{result.get('total_rows')} rows, "
            f"{result.get('file_size_bytes')} bytes"
        )

        return FileResponse(
            path=str(export_path),
            filename=filename,
            media_type="application/json",
            headers={
                "X-Export-Tables": ",".join(result.get("tables", [])),
                "X-Export-Rows": str(result.get("total_rows")),
                "X-Schema-Version": result.get("schema_version", "unknown"),
            },
        )
    except Exception as e:
        logger.error(f"❌ Export failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {e}",
        )


@router.post("/export/metadata", summary="Export database and return metadata only")
async def export_database_metadata(
    current_user: Annotated[User, Depends(require_permission("user.read"))],
    request: ExportRequest = ExportRequest(),
):
    """
    Export the database to a JSON file and return metadata (not the file itself).
    Useful for scheduled/programmatic backups.

    Returns export metadata including file path, row counts, etc.

    Requires: admin permission
    """
    try:
        logger.info(f"📦 Admin {current_user.email} requested export metadata")

        tables = request.tables
        exclude_tables = request.exclude_tables
        result = backup_service.export_to_json(
            tables=tables, exclude_tables=exclude_tables
        )
        return result
    except Exception as e:
        logger.error(f"❌ Export failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}",
        )


@router.post(
    "/import", response_model=ImportResponse, summary="Import database from JSON"
)
async def import_database(
    current_user: Annotated[User, Depends(require_permission("user.update"))],
    file: UploadFile = File(..., description="JSON backup file to import"),
    conflict_strategy: str = Query(
        default=ConflictStrategy.SKIP.value,
        description="How to handle conflicting rows: 'skip' = ignore conflicts (safest), "
        "'update' = overwrite existing, 'error' = abort on conflict",
    ),
    tables: Optional[str] = Query(
        default=None,
        description="Comma-separated list of tables to import (default: all)",
    ),
    dry_run: bool = Query(
        default=False,
        description="If true, simulate import without writing to DB",
    ),
):
    """
    Import data from a JSON backup file into the database.

    **Safety features:**
    - Automatically creates a pre-import backup before any changes
    - Default conflict strategy is 'skip' (never overwrites existing data)
    - Supports dry-run mode to preview changes
    - Schema version compatibility check

    **Conflict strategies:**
    - `skip`: Skip rows that already exist (safest, no data loss)
    - `update`: Update existing rows with imported data
    - `error`: Abort on first conflict (strictest)

    Requires: admin permission (user.update)
    """
    try:
        logger.info(
            f"📥 Admin {current_user.email} importing database "
            f"(strategy={conflict_strategy}, dry_run={dry_run})"
        )

        # Validate file
        if not file.filename.endswith(".json"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only .json backup files are accepted",
            )

        # Read and validate size
        content = await file.read()
        if len(content) > 100 * 1024 * 1024:  # 100 MB
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Backup file too large (max 100 MB)",
            )

        # Write to temp file
        try:
            tmp = tempfile.NamedTemporaryFile(mode="wb", suffix=".json", delete=False)
            tmp.write(content)
            tmp_path = tmp.name
            tmp.close()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to read uploaded file: {str(e)}",
            )

        # Parse tables parameter
        table_list = None
        if tables:
            table_list = [t.strip() for t in tables.split(",")]

        # Perform import
        strategy = ConflictStrategy(conflict_strategy)
        result = backup_service.import_from_json(
            input_path=tmp_path,
            conflict_strategy=strategy,
            tables=table_list,
            dry_run=dry_run,
        )

        prefix = "🔍 [DRY RUN]" if dry_run else "✅"
        logger.info(f"{prefix} Import by {current_user.email}: {result.get('summary')}")

        # Clean up temp file
        Path(tmp_path).unlink(missing_ok=True)

        return ImportResponse(**result)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"❌ Import failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}",
        )


@router.post("/binary", summary="Create binary .db backup")
async def create_binary_backup(
    current_user: Annotated[User, Depends(require_permission("user.read"))],
):
    """
    Create a binary copy of the SQLite database file.

    Uses SQLite's online backup API, which is safe even while
    the database is being written to.

    Requires: admin permission
    """
    try:
        logger.info(f"💾 Admin {current_user.email} requested binary backup")
        result = backup_service.create_binary_backup()
        return result
    except Exception as e:
        logger.error(f"❌ Binary backup failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Binary backup failed: {str(e)}",
        )


@router.get("/list", summary="List all backups")
async def list_backups(
    current_user: Annotated[User, Depends(require_permission("user.read"))],
):
    """
    List all available backup files with metadata.

    Returns backup files sorted by date (newest first),
    including file size, type, and creation time.

    Requires: admin permission
    """
    backups = backup_service.list_backups()
    return BackupListResponse(
        backups=[BackupInfo(**b) for b in backups],
        total=len(backups),
        backup_dir=str(backup_service.backup_dir),
    )


@router.get("/download/{filename}", summary="Download a backup file")
async def download_backup(
    filename: str,
    current_user: Annotated[User, Depends(require_permission("user.read"))],
):
    """
    Download a specific backup file by filename.

    Requires: admin permission
    """
    filepath = backup_service.backup_dir / filename
    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backup file not found: {filename}",
        )

    # Safety: ensure file is within backup directory
    if filepath.resolve().parent != backup_service.backup_dir.resolve():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    media_type = (
        "application/json" if filename.endswith(".json") else "application/octet-stream"
    )
    return FileResponse(
        path=str(filepath),
        filename=filename,
        media_type=media_type,
    )


@router.delete("/{filename}", summary="Delete a backup file")
async def delete_backup(
    filename: str,
    current_user: Annotated[User, Depends(require_permission("user.delete"))],
):
    """
    Delete a specific backup file.

    Requires: admin permission (user.delete)
    """
    try:
        result = backup_service.delete_backup(filename)
        return result
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"❌ Delete failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Delete failed: {str(e)}",
        )


@router.post("/trigger", summary="Trigger manual backup")
async def trigger_manual_backup(
    current_user: Annotated[User, Depends(require_permission("user.read"))],
):
    """
    Trigger a full manual backup (JSON export + binary backup + rotation).

    Requires: admin permission
    """
    try:
        logger.info(f"🔄 Admin {current_user.email} triggered manual backup")
        result = backup_service.scheduled_backup()
        return result
    except Exception as e:
        logger.error(f"❌ Manual backup failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Manual backup failed: {str(e)}",
        )


@router.post("/rotate", summary="Rotate old backups")
async def rotate_backups(
    current_user: Annotated[User, Depends(require_permission("user.delete"))],
):
    """
    Manually trigger backup rotation to clean up old files.

    Keeps the newest backups up to the configured max_backups limit.

    Requires: admin permission (user.delete)
    """
    try:
        result = backup_service.rotate_backups()
        return result
    except Exception as e:
        logger.error(f"❌ Rotation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rotation failed: {str(e)}",
        )
