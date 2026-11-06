"""
Ingestion Manager & Process-Level Ownership Coordinator (Task 7.6.4).
Guarantees that exactly one process owns camera video ingestion and YOLO inference,
preventing duplicate worker threads, duplicate RTSP streams, and duplicate inference loops.
Uses OS-level kernel file locking (msvcrt on Windows, fcntl on Linux/POSIX)
so ownership is automatically released if the process terminates or crashes.
"""
import os
import sys
import logging
from typing import Optional

logger = logging.getLogger("uvicorn")


class IngestionCoordinator:
    def __init__(self, lock_file_path: Optional[str] = None):
        if lock_file_path is None:
            upload_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "uploads")
            os.makedirs(upload_dir, exist_ok=True)
            lock_file_path = os.path.join(upload_dir, "camera_ingestion.lock")
        self.lock_file_path = lock_file_path
        self._lock_fp = None
        self._is_owner = False

    @property
    def is_owner(self) -> bool:
        return self._is_owner

    def acquire_ownership(self) -> bool:
        """
        Attempts to acquire single-owner ingestion leadership via kernel file locking.
        Returns True if acquired; False if another process already owns ingestion.
        """
        if self._is_owner:
            return True

        fp = None
        try:
            fp = open(self.lock_file_path, "a+b")
            fp.seek(0)

            if sys.platform == "win32":
                import msvcrt
                # LK_NBLCK locks 1 byte from current file position non-blocking
                msvcrt.locking(fp.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

            # Acquired successfully! Record leader metadata
            # On Windows, msvcrt.locking locks byte 0 exclusively. Writing a 1-byte prefix '0' at offset 0
            # allows secondary processes to safely seek past byte 0 and read 'pid=...' without PermissionError.
            fp.seek(0)
            fp.truncate(0)
            pid_info = f"0\npid={os.getpid()}\n".encode("utf-8")
            fp.write(pid_info)
            fp.flush()

            self._lock_fp = fp
            self._is_owner = True
            logger.info(f"[INGESTION][LEADER] Successfully acquired camera ingestion lock (PID: {os.getpid()}).")
            return True

        except (IOError, OSError, PermissionError, BlockingIOError):
            # Lock is held by another active process
            if fp is not None:
                try:
                    fp.close()
                except Exception:
                    pass
            self._lock_fp = None
            self._is_owner = False
            return False

    def release_ownership(self):
        """Releases the kernel lock on clean shutdown."""
        if self._is_owner and self._lock_fp is not None:
            try:
                if sys.platform == "win32":
                    import msvcrt
                    self._lock_fp.seek(0)
                    msvcrt.locking(self._lock_fp.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self._lock_fp.fileno(), fcntl.LOCK_UN)
                self._lock_fp.close()
            except Exception as e:
                logger.warning(f"[INGESTION][LOCK] Error releasing ingestion lock: {e}")
            finally:
                self._lock_fp = None
                self._is_owner = False
                logger.info(f"[INGESTION][RELEASE] Released camera ingestion lock (PID: {os.getpid()}).")

    def get_owner_pid(self) -> Optional[int]:
        """Reads lock file to determine current owner PID (advisory only)."""
        if not os.path.exists(self.lock_file_path):
            return None
        try:
            with open(self.lock_file_path, "rb") as f:
                if sys.platform == "win32":
                    # On Windows, offset 0 is locked by msvcrt.locking (mandatory byte lock).
                    # Seeking past byte 0 avoids PermissionError while reading advisory PID metadata.
                    f.seek(1)
                else:
                    f.seek(0)
                content = f.read().decode("utf-8", errors="ignore").strip()
                for line in content.splitlines():
                    if line.startswith("pid="):
                        val = line.split("=")[1].strip()
                        if val.isdigit():
                            return int(val)
        except Exception:
            pass
        return None


# Global coordinator instance
ingestion_coordinator = IngestionCoordinator()
