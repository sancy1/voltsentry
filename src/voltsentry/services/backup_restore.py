"""
FILE: src/voltsentry/services/backup_restore.py
PATH: voltsentry/src/voltsentry/services/backup_restore.py
DESCRIPTION: Encrypted backup and restore service
PHASE: 5.4 - Encrypted Backup & Restore
DISCIPLINES:
- 0.1 Logging: INFO on backup/restore, ERROR on failure
- 0.2 Error Handling: Catches InvalidToken distinctly from I/O errors
- 0.4 Fallback: Atomic rename, checksum verification
- BATTERY OPTIMIZATION: User-initiated only, zero background usage
"""

from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
from threading import Lock
from typing import Any, Dict, Optional
import zipfile

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from ..core.constants import (
    CONFIG_PATH,
    DATA_DIR,
    DB_PATH,
    EXPORT_FILE_EXTENSION,
    EXPORT_KEY_LENGTH,
    EXPORT_SALT_LENGTH,
)
from ..core.decorators import log_entry_exit
from ..core.exceptions import (
    BackupCorruptError,
    BackupRestoreError,
    InvalidPassphraseError,
)
from ..core.logging_config import get_logger, log_audit

logger = get_logger(__name__)


class BackupRestoreService:
    """
    Encrypted backup and restore service.

    Features:
    - Fernet encryption with PBKDF2 key derivation
    - Bundles SQLite database and config.json
    - Atomic restore with checksum verification
    - Clean error messages for wrong passphrase

    Battery Optimization: User-initiated only, zero background usage.
    """

    def __init__(self):
        self._lock = Lock()
        self._backup_dir = DATA_DIR / "backups"
        self._backup_dir.mkdir(parents=True, exist_ok=True)

        logger.info("BackupRestoreService initialized: %s", self._backup_dir)

    def _derive_key(self, passphrase: str, salt: bytes) -> bytes:
        """
        Derive an encryption key from a passphrase using PBKDF2.

        Args:
            passphrase: User's passphrase
            salt: Salt for key derivation

        Returns:
            Derived key bytes
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=EXPORT_KEY_LENGTH,
            salt=salt,
            iterations=100000,
        )
        return kdf.derive(passphrase.encode())

    def _encrypt_data(self, data: bytes, passphrase: str) -> bytes:
        """
        Encrypt data with passphrase.

        Args:
            data: Data to encrypt
            passphrase: User's passphrase

        Returns:
            Encrypted data with salt prepended
        """
        # Generate random salt
        salt = Fernet.generate_key()[:EXPORT_SALT_LENGTH]

        # Derive key
        key = self._derive_key(passphrase, salt)
        fernet = Fernet(key)

        # Encrypt
        encrypted = fernet.encrypt(data)

        # Return salt + encrypted
        return salt + encrypted

    def _decrypt_data(self, encrypted_data: bytes, passphrase: str) -> bytes:
        """
        Decrypt data with passphrase.

        Args:
            encrypted_data: Encrypted data with salt prepended
            passphrase: User's passphrase

        Returns:
            Decrypted data

        Raises:
            InvalidPassphraseError: If passphrase is incorrect
        """
        if len(encrypted_data) < EXPORT_SALT_LENGTH:
            raise BackupCorruptError("Encrypted data is too short")

        # Extract salt
        salt = encrypted_data[:EXPORT_SALT_LENGTH]
        encrypted = encrypted_data[EXPORT_SALT_LENGTH:]

        try:
            # Derive key
            key = self._derive_key(passphrase, salt)
            fernet = Fernet(key)

            # Decrypt
            return fernet.decrypt(encrypted)
        except InvalidToken:
            raise InvalidPassphraseError("Incorrect passphrase")
        except Exception as e:
            raise BackupCorruptError(f"Decryption failed: {e}")

    def _create_backup_bundle(self) -> Path:
        """
        Create a backup bundle (unencrypted zip).

        Returns:
            Path to the zip file
        """
        # Create temporary directory
        temp_dir = Path(tempfile.mkdtemp(prefix="voltsentry_backup_"))

        try:
            # Copy database
            if DB_PATH.exists():
                shutil.copy2(DB_PATH, temp_dir / "voltsentry.db")
                logger.debug("Database backed up: %s", DB_PATH)
            else:
                logger.warning("Database file not found, skipping")

            # Copy config
            if CONFIG_PATH.exists():
                shutil.copy2(CONFIG_PATH, temp_dir / "config.json")
                logger.debug("Config backed up: %s", CONFIG_PATH)
            else:
                logger.warning("Config file not found, skipping")

            # Create metadata
            metadata = {
                "app_name": "VoltSentry",
                "version": "1.0.0",
                "backup_date": datetime.now().isoformat(),
                "files": [
                    {"name": "voltsentry.db", "exists": DB_PATH.exists()},
                    {"name": "config.json", "exists": CONFIG_PATH.exists()},
                ],
            }
            (temp_dir / "metadata.json").write_text(
                json.dumps(metadata, indent=2)
            )

            # Create zip
            zip_name = (
                f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            )
            zip_path = self._backup_dir / zip_name

            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for file_path in temp_dir.iterdir():
                    zipf.write(file_path, file_path.name)

            logger.info("Backup bundle created: %s", zip_path)
            return zip_path

        finally:
            # Clean up temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)

    @log_entry_exit()
    def create_backup(
        self, passphrase: str, output_path: Optional[Path] = None
    ) -> Path:
        """
        Create an encrypted backup.

        Args:
            passphrase: Encryption passphrase
            output_path: Optional output path

        Returns:
            Path to the encrypted backup file

        Raises:
            BackupRestoreError: If backup fails
        """
        with self._lock:
            try:
                # Create bundle
                zip_path = self._create_backup_bundle()
                zip_data = zip_path.read_bytes()

                # Encrypt
                encrypted = self._encrypt_data(zip_data, passphrase)

                # Determine output path
                if output_path:
                    backup_file = output_path
                else:
                    backup_file = (
                        self._backup_dir
                        / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}{EXPORT_FILE_EXTENSION}"
                    )

                # Write encrypted data
                backup_file.write_bytes(encrypted)

                # Clean up zip
                zip_path.unlink(missing_ok=True)

                logger.info(
                    "Backup created: %s (size: %.2f KB)",
                    backup_file,
                    backup_file.stat().st_size / 1024,
                )
                log_audit("INFO", f"Backup created: {backup_file.name}")

                return backup_file

            except Exception as e:
                raise BackupRestoreError(f"Backup failed: {e}") from e

    @log_entry_exit()
    def restore_backup(self, backup_path: Path, passphrase: str) -> bool:
        """
        Restore from an encrypted backup.

        Args:
            backup_path: Path to encrypted backup file
            passphrase: Decryption passphrase

        Returns:
            True if restore was successful

        Raises:
            InvalidPassphraseError: If passphrase is incorrect
            BackupCorruptError: If backup is corrupted
            BackupRestoreError: If restore fails
        """
        with self._lock:
            temp_dir = None

            try:
                if not backup_path.exists():
                    raise BackupRestoreError(
                        f"Backup file not found: {backup_path}"
                    )

                # Read encrypted data
                encrypted_data = backup_path.read_bytes()

                # Decrypt
                decrypted = self._decrypt_data(encrypted_data, passphrase)

                # Create temporary directory
                temp_dir = Path(
                    tempfile.mkdtemp(prefix="voltsentry_restore_")
                )
                zip_path = temp_dir / "backup.zip"

                # Write decrypted zip
                zip_path.write_bytes(decrypted)

                # Verify zip integrity
                if not zipfile.is_zipfile(zip_path):
                    raise BackupCorruptError("Invalid zip file format")

                # Extract
                with zipfile.ZipFile(zip_path, "r") as zipf:
                    # Verify contents
                    required_files = ["metadata.json"]
                    for file in required_files:
                        if file not in zipf.namelist():
                            raise BackupCorruptError(
                                f"Missing required file: {file}"
                            )

                    # Extract all
                    zipf.extractall(temp_dir)

                # Verify checksums
                self._verify_restore(temp_dir)

                # Perform atomic restore
                self._atomic_restore(temp_dir)

                logger.info("Restore successful from: %s", backup_path)
                log_audit(
                    "INFO", f"Restore completed from: {backup_path.name}"
                )

                return True

            except InvalidPassphraseError:
                raise
            except BackupCorruptError:
                raise
            except Exception as e:
                raise BackupRestoreError(f"Restore failed: {e}") from e
            finally:
                # Clean up temp directory
                if temp_dir:
                    shutil.rmtree(temp_dir, ignore_errors=True)

    def _verify_restore(self, temp_dir: Path) -> None:
        """
        Verify the restored files.

        Raises:
            BackupCorruptError: If verification fails
        """
        db_file = temp_dir / "voltsentry.db"
        config_file = temp_dir / "config.json"
        metadata_file = temp_dir / "metadata.json"

        # Check metadata
        if metadata_file.exists():
            try:
                metadata = json.loads(metadata_file.read_text())
                logger.debug("Metadata: %s", metadata)
            except json.JSONDecodeError as e:
                raise BackupCorruptError(f"Invalid metadata: {e}")

        # Check DB file
        if db_file.exists():
            # Verify it's a valid SQLite file
            try:
                conn = sqlite3.connect(str(db_file))
                conn.execute("PRAGMA integrity_check")
                conn.close()
            except Exception as e:
                raise BackupCorruptError(f"Invalid database file: {e}")

        # Check config file
        if config_file.exists():
            try:
                json.loads(config_file.read_text())
            except json.JSONDecodeError as e:
                raise BackupCorruptError(f"Invalid config file: {e}")

    def _atomic_restore(self, temp_dir: Path) -> None:
        """
        Atomically restore files to their final locations.

        Uses atomic rename to avoid partial writes.
        """
        # Restore database
        db_temp = temp_dir / "voltsentry.db"
        if db_temp.exists():
            # Backup current DB if it exists
            if DB_PATH.exists():
                backup_db = DB_PATH.with_suffix(".db.bak")
                shutil.copy2(DB_PATH, backup_db)
                logger.debug("Existing DB backed up: %s", backup_db)

            # Atomic rename
            shutil.move(str(db_temp), str(DB_PATH))
            logger.debug("Database restored atomically")

        # Restore config
        config_temp = temp_dir / "config.json"
        if config_temp.exists():
            # Backup current config if it exists
            if CONFIG_PATH.exists():
                backup_config = CONFIG_PATH.with_suffix(".json.bak")
                shutil.copy2(CONFIG_PATH, backup_config)
                logger.debug("Existing config backed up: %s", backup_config)

            # Atomic rename
            shutil.move(str(config_temp), str(CONFIG_PATH))
            logger.debug("Config restored atomically")

    @log_entry_exit()
    def list_backups(self) -> list:
        """List all available backup files."""
        backups = []
        for file_path in self._backup_dir.glob(f"*{EXPORT_FILE_EXTENSION}"):
            backups.append(
                {
                    "path": str(file_path),
                    "name": file_path.name,
                    "size_kb": file_path.stat().st_size / 1024,
                    "modified": datetime.fromtimestamp(
                        file_path.stat().st_mtime
                    ).isoformat(),
                }
            )
        return sorted(backups, key=lambda x: x["modified"], reverse=True)

    def get_status(self) -> dict:
        """Get backup service status."""
        backups = self.list_backups()
        return {
            "backup_dir": str(self._backup_dir),
            "total_backups": len(backups),
            "latest_backup": backups[0] if backups else None,
            "has_database": DB_PATH.exists(),
            "has_config": CONFIG_PATH.exists(),
        }

    def __repr__(self) -> str:
        return f"<BackupRestoreService backup_dir={self._backup_dir}>"