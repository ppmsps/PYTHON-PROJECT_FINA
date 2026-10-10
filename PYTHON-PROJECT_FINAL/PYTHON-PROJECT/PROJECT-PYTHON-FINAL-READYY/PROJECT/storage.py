import os
import shutil
from struct_config import HEADER_SIZE, make_header, validate_header


def ensure_binary_file(path: str, record_size: int) -> None:
    if not os.path.exists(path):
        with open(path, "wb") as f:
            f.write(make_header(record_size))
            f.flush()
            os.fsync(f.fileno())
        return

    try:
        size = os.path.getsize(path)
        if size < HEADER_SIZE or (size - HEADER_SIZE) % record_size != 0:
            raise ValueError("file size is not aligned to fixed records")
        with open(path, "rb") as f:
            if not validate_header(f.read(HEADER_SIZE), record_size):
                raise ValueError("invalid header")
    except (OSError, ValueError) as exc:
        print(f"\n[FILE ERROR] {path}: {exc}")
        choice = input("Backup as .bak and recreate the file? (y/n): ").strip().lower()
        if choice != "y":
            raise
        backup = path + ".bak"
        if os.path.exists(backup):
            os.remove(backup)
        shutil.copy2(path, backup)
        with open(path, "wb") as f:
            f.write(make_header(record_size))
            f.flush()
            os.fsync(f.fileno())
        print(f"Backed up to {backup} and recreated {path}.")


def sync_file(f) -> None:
    f.flush()
    os.fsync(f.fileno())
