import os
import time
from struct_config import *
from storage import ensure_binary_file, sync_file

# Keep all Binary data beside the Python source files, regardless of the
# directory from which main.py is launched. This prevents the program from
# accidentally reading/writing a second copy of inventory.bin/report files.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INVENTORY_FILE = os.path.join(BASE_DIR, "inventory.bin")
BORROWERS_FILE = os.path.join(BASE_DIR, "borrowers.bin")
ACTIVITY_FILE = os.path.join(BASE_DIR, "activity.bin")

_change_hook = None


def set_change_hook(fn):
    """Register a callback (e.g. regenerate TXT reports) run after any binary write."""
    global _change_hook
    _change_hook = fn


def _notify_change():
    if _change_hook is not None:
        try:
            _change_hook()
        except Exception as exc:  # a report problem must never break CRUD
            print(f"[REPORT WARNING] {exc}")


def initialize_files():
    ensure_binary_file(INVENTORY_FILE, EQUIP_SIZE)
    ensure_binary_file(BORROWERS_FILE, BORROWER_SIZE)
    ensure_binary_file(ACTIVITY_FILE, ACTIVITY_SIZE)


def read_records(path, record_size, unpacker):
    result = []
    with open(path, "rb") as f:
        f.seek(HEADER_SIZE)
        while True:
            chunk = f.read(record_size)
            if not chunk:
                break
            if len(chunk) != record_size:
                raise ValueError(f"Corrupt record in {path}")
            result.append(unpacker(chunk))
    return result


def append_activity(op_code, equip_id="0", borrower_id="", value=0, rate=0.0, timestamp=None):
    initialize_files()
    with open(ACTIVITY_FILE, "ab") as f:
        ts = int(time.time()) if timestamp is None else int(timestamp)
        f.write(pack_activity(ts, op_code, equip_id, borrower_id, value, rate))
        sync_file(f)
    _notify_change()


def read_equipment():
    return read_records(INVENTORY_FILE, EQUIP_SIZE, unpack_equipment)


def write_equipment_at(index, rec):
    with open(INVENTORY_FILE, "r+b") as f:
        f.seek(HEADER_SIZE + index * EQUIP_SIZE)
        f.write(pack_equipment(rec))
        sync_file(f)
    _notify_change()


def append_equipment(rec):
    with open(INVENTORY_FILE, "ab") as f:
        f.write(pack_equipment(rec))
        sync_file(f)
    _notify_change()


def find_equipment(equip_id, include_deleted=False):
    """Return the first matching equipment record (kept for compatibility)."""
    for idx, rec in enumerate(read_equipment()):
        if rec["equip_id"].lower() == equip_id.lower() and (include_deleted or not rec["is_deleted"]):
            return idx, rec
    return -1, None


def find_equipment_records(equip_id, include_deleted=False):
    """Return every physical unit sharing the same equipment ID."""
    return [
        (idx, rec) for idx, rec in enumerate(read_equipment())
        if rec["equip_id"].lower() == equip_id.lower()
        and (include_deleted or not rec["is_deleted"])
    ]


def find_available_equipment(equip_id):
    """Return one available physical unit for a shared equipment ID."""
    for idx, rec in find_equipment_records(equip_id):
        if not rec["borrower_id"]:
            return idx, rec
    return -1, None


def find_equipment_for_borrower(equip_id, borrower_id):
    """Find the physical unit of an ID currently held by this borrower."""
    for idx, rec in find_equipment_records(equip_id):
        if rec["borrower_id"].lower() == borrower_id.lower():
            return idx, rec
    return -1, None


def find_free_slot():
    for idx, rec in enumerate(read_equipment()):
        if rec["is_deleted"]:
            return idx
    return -1


def read_borrowers():
    return read_records(BORROWERS_FILE, BORROWER_SIZE, unpack_borrower)


def find_borrower(borrower_id):
    for rec in read_borrowers():
        if rec["borrower_id"].lower() == borrower_id.lower() and rec["active"]:
            return rec
    return None


def append_borrower(borrower_id, name):
    with open(BORROWERS_FILE, "ab") as f:
        f.write(pack_borrower(borrower_id, name, True))
        sync_file(f)
    _notify_change()


def read_activities():
    return read_records(ACTIVITY_FILE, ACTIVITY_SIZE, unpack_activity)
