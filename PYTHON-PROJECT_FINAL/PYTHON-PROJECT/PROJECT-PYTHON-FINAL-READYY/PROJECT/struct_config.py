import struct

# Fixed-length equipment record: 67 bytes
# < = Little-Endian
# 6s ID, 32s name, 10s category, i year, f daily rate,
# i condition, 6s borrower ID, B deleted flag
EQUIP_FMT = "<6s32s10sifi6sB"
EQUIP_SIZE = struct.calcsize(EQUIP_FMT)

# Borrower master record: 39 bytes
BORROWER_FMT = "<6s32sB"
BORROWER_SIZE = struct.calcsize(BORROWER_FMT)

# Activity/request record: exactly 24 bytes
# timestamp, operation code, equipment id, borrower number, days/status value, rate
ACTIVITY_FMT = "<I B 3x I I I f"
ACTIVITY_SIZE = struct.calcsize(ACTIVITY_FMT)

MAGIC = b"MPS1"
VERSION = 1
HEADER_FMT = "<4sBBH"  # magic, version, reserved, record_size
HEADER_SIZE = struct.calcsize(HEADER_FMT)  # 8 bytes

OP_ADD = 1
OP_UPDATE = 2
OP_DELETE = 3
OP_VIEW = 4
OP_BORROW_REQUEST = 5
OP_BORROW_APPROVE = 6
OP_BORROW_REJECT = 7
OP_RETURN = 8
OP_BORROW = 9
OP_RESERVE = 10

OP_NAMES = {
    OP_ADD: "ADD",
    OP_UPDATE: "UPDATE",
    OP_DELETE: "DELETE",
    OP_VIEW: "VIEW",
    OP_BORROW_REQUEST: "REQUEST",
    OP_BORROW_APPROVE: "APPROVE",
    OP_BORROW_REJECT: "REJECT",
    OP_RETURN: "RETURN",
    OP_BORROW: "BORROW",
    OP_RESERVE: "RESERVE",
}

CONDITION_NAMES = {0: "Bad", 1: "Fair", 2: "Good"}

CATEGORIES = (
    "Camera", "Lens", "Lighting", "Audio", "Support",
    "Power", "Monitor", "Set", "Comms"
)


def pack_str(text: str, length: int) -> bytes:
    raw = text.encode("cp874")
    if len(raw) > length:
        raise ValueError(f"text is longer than {length} bytes")
    return raw.ljust(length, b"\x00")


def unpack_str(data: bytes) -> str:
    return data.rstrip(b"\x00").decode("cp874", errors="replace")


def pack_equipment(rec: dict) -> bytes:
    return struct.pack(
        EQUIP_FMT,
        pack_str(rec["equip_id"], 6),
        pack_str(rec["name"], 32),
        pack_str(rec["category"], 10),
        int(rec["year"]),
        float(rec["rate_per_day_thb"]),
        int(rec["condition"]),
        pack_str(rec.get("borrower_id", ""), 6),
        int(bool(rec.get("is_deleted", False))),
    )


def unpack_equipment(data: bytes) -> dict:
    if len(data) != EQUIP_SIZE:
        raise ValueError("invalid equipment record size")
    u = struct.unpack(EQUIP_FMT, data)
    return {
        "equip_id": unpack_str(u[0]),
        "name": unpack_str(u[1]),
        "category": unpack_str(u[2]),
        "year": u[3],
        "rate_per_day_thb": u[4],
        "condition": u[5],
        "borrower_id": unpack_str(u[6]),
        "is_deleted": bool(u[7]),
    }


def pack_borrower(borrower_id: str, name: str, active: bool = True) -> bytes:
    return struct.pack(BORROWER_FMT, pack_str(borrower_id, 6), pack_str(name, 32), int(active))


def unpack_borrower(data: bytes) -> dict:
    if len(data) != BORROWER_SIZE:
        raise ValueError("invalid borrower record size")
    u = struct.unpack(BORROWER_FMT, data)
    return {"borrower_id": unpack_str(u[0]), "name": unpack_str(u[1]), "active": bool(u[2])}


def borrower_number(borrower_id: str) -> int:
    digits = "".join(ch for ch in borrower_id if ch.isdigit())
    return int(digits or 0)


def pack_activity(timestamp: int, op_code: int, equip_id: str, borrower_id: str, value: int, rate: float) -> bytes:
    equip_no = int(equip_id) if equip_id.isdigit() else 0
    return struct.pack(ACTIVITY_FMT, int(timestamp), int(op_code), equip_no,
                       borrower_number(borrower_id), int(value), float(rate))


def unpack_activity(data: bytes) -> dict:
    if len(data) != ACTIVITY_SIZE:
        raise ValueError("invalid activity record size")
    ts, op, equip_no, borrower_no, value, rate = struct.unpack(ACTIVITY_FMT, data)
    return {"timestamp": ts, "op_code": op, "equip_id": str(equip_no),
            "borrower_no": borrower_no, "value": value, "rate": rate}


def make_header(record_size: int) -> bytes:
    return struct.pack(HEADER_FMT, MAGIC, VERSION, 0, record_size)


def validate_header(data: bytes, record_size: int) -> bool:
    if len(data) != HEADER_SIZE:
        return False
    magic, version, _reserved, stored_size = struct.unpack(HEADER_FMT, data)
    return magic == MAGIC and version == VERSION and stored_size == record_size
