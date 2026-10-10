import os
from datetime import datetime, timedelta
from data import *
from table_utils import fit_text, table_line, table_row

# Reports are stored beside the program and always regenerate from the
# current Binary files. Paths do not depend on the terminal working folder.
REPORT_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_FILES = {
    "equipment": os.path.join(REPORT_DIR, "report_equipment.txt"),
    "borrowing": os.path.join(REPORT_DIR, "report_borrowing.txt"),
    "activity": os.path.join(REPORT_DIR, "report_activity.txt"),
}

# Friendly labels used only in reports so the activity history is easy to read.
# Internal operation codes remain unchanged for the program logic.
ACTION_LABELS = {
    "REQUEST": "Requested",
    "APPROVE": "Approved",
    "BORROW": "Borrowed",
    "RETURN": "Returned",
    "REJECT": "Rejected",
    "RESERVE": "Reserved",
    "UPDATE": "Updated",
    "ADD": "Added",
    "DELETE": "Deleted",
    "VIEW": "Viewed",
}


def ask(prompt, validator, allow_q=True):
    while True:
        value = input(prompt).strip()
        if allow_q and value.lower() == "q":
            return None
        try:
            return validator(value)
        except (ValueError, TypeError) as exc:
            print(f"Invalid input: {exc}")


def validate_id(v):
    if not v.isdigit():
        raise ValueError("รหัสอุปกรณ์ต้องเป็นตัวเลข เช่น 10001")
    if len(v) != 5:
        raise ValueError("รหัสอุปกรณ์ต้องมี 5 หลัก เช่น 10001")
    return v


def validate_name(v):
    if not v:
        raise ValueError("ห้ามว่าง")
    if len(v.encode()) > 32:
        raise ValueError("ชื่อยาวเกิน 32 bytes")
    return v


def validate_category(v):
    if v not in CATEGORIES:
        raise ValueError("เลือกจาก: " + ", ".join(CATEGORIES))
    if len(v.encode()) > 10:
        raise ValueError("หมวดหมู่ยาวเกิน 10 bytes")
    return v


def validate_year(v):
    try:
        n = int(v)
    except (ValueError, TypeError):
        raise ValueError("ปีต้องเป็นจำนวนเต็ม 2021-2026")
    if not 2021 <= n <= 2026:
        raise ValueError("ปีต้องอยู่ระหว่าง 2021-2026")
    return n


def validate_rate(v):
    n = float(v)
    if n < 0:
        raise ValueError("ค่าเช่าห้ามติดลบ")
    return n


def validate_condition(v):
    n = int(v)
    if n not in (0, 1, 2):
        raise ValueError("0=Bad, 1=Fair, 2=Good")
    return n


def print_table(items):
    widths = [14, 30, 18, 8, 12, 14]
    line = table_line(widths)

    print("\n" + line)
    print(table_row(
        ["Equipment ID", "Equipment Name", "Category", "Year", "Rate/Day", "Status"],
        widths,
        ["left", "left", "left", "center", "right", "center"]
    ))
    print(line)

    groups = {}
    for r in items:
        groups.setdefault(r["equip_id"], []).append(r)
    for eid, group in groups.items():
        r = group[0]
        total = len(group)
        borrowed = sum(bool(x["borrower_id"]) for x in group)
        if r["is_deleted"]:
            status = "Deleted"
        elif borrowed:
            status = f"Borrowed {borrowed}/{total}"
        else:
            status = f"Available {total}/{total}"
        print(table_row(
            [r["equip_id"], r["name"], r["category"], r["year"], f"{r['rate_per_day_thb']:.2f}", status],
            widths,
            ["left", "left", "left", "center", "right", "center"]
        ))

    print(line)
    print(f"Total Equipment Units: {len(items)} | Equipment IDs: {len(groups)}")


def validate_quantity(v):
    n = int(v)
    if n <= 0:
        raise ValueError("จำนวนต้องเป็นจำนวนเต็มมากกว่า 0")
    if n > 100:
        raise ValueError("เพิ่มได้ครั้งละไม่เกิน 100 ชิ้น")
    return n


def add_equipment():
    print("\n--- ADD: เพิ่มอุปกรณ์ ---")
    print("กรอกข้อมูลอุปกรณ์ 1 ครั้ง แล้วระบุจำนวนที่ต้องการเพิ่มได้เลย")

    equip_id = ask("รหัสอุปกรณ์: ", validate_id)
    if equip_id is None: return
    name = ask("ชื่ออุปกรณ์: ", validate_name)
    if name is None: return
    category = ask("หมวดหมู่: ", validate_category)
    if category is None: return
    year = ask("ปี: ", validate_year)
    if year is None: return
    rate = ask("ค่าเช่าต่อวัน (บาท): ", validate_rate)
    if rate is None: return
    condition = ask("สภาพ (0=Bad, 1=Fair, 2=Good): ", validate_condition)
    if condition is None: return
    quantity = ask("จำนวนที่ต้องการเพิ่ม: ", validate_quantity)
    if quantity is None: return

    # One ID may represent multiple identical physical units.
    # If the ID already exists, add more units to that same ID/group.
    existing = find_equipment_records(equip_id, include_deleted=True)
    if existing:
        # Reuse soft-deleted slots first, then append the remaining units.
        free_slots = [idx for idx, rec in existing if rec["is_deleted"]]
        remaining = quantity
        for idx in free_slots[:quantity]:
            rec = dict(equip_id=equip_id, name=name, category=category, year=year,
                       rate_per_day_thb=rate, condition=condition, borrower_id="", is_deleted=False)
            write_equipment_at(idx, rec)
            remaining -= 1
        for _ in range(remaining):
            append_equipment(dict(equip_id=equip_id, name=name, category=category, year=year,
                                  rate_per_day_thb=rate, condition=condition, borrower_id="", is_deleted=False))
        total = len([r for _, r in find_equipment_records(equip_id)])
        print(f"เพิ่มสำเร็จ: {name} | ID {equip_id} | เพิ่ม {quantity} ชิ้น | มีทั้งหมด {total} ชิ้น")
    else:
        remaining = quantity
        # Use any deleted slots, not only one.
        for idx, old in enumerate(read_equipment()):
            if remaining <= 0: break
            if old["is_deleted"]:
                rec = dict(equip_id=equip_id, name=name, category=category, year=year,
                           rate_per_day_thb=rate, condition=condition, borrower_id="", is_deleted=False)
                write_equipment_at(idx, rec)
                remaining -= 1
        for _ in range(remaining):
            append_equipment(dict(equip_id=equip_id, name=name, category=category, year=year,
                                  rate_per_day_thb=rate, condition=condition, borrower_id="", is_deleted=False))
        print(f"เพิ่มสำเร็จ: {name} | ID {equip_id} | จำนวน {quantity} ชิ้น")

    # Store quantity in the activity value so the activity report records the batch size.
    append_activity(OP_ADD, equip_id, "", quantity, rate)


def _ask_optional(prompt, current, validator):
    """Read an optional update field without ever crashing on bad input.

    Empty input keeps the current value. q cancels the whole update.
    Validation is retried field-by-field so one bad value cannot terminate the program.
    """
    while True:
        value = input(prompt).strip()
        if value.lower() == "q":
            return current, True
        if value == "":
            return current, False
        try:
            return validator(value), False
        except (ValueError, TypeError) as exc:
            print(f"Invalid input: {exc}")


def update_equipment():
    print("\n--- UPDATE: แก้ไขอุปกรณ์ ---")
    target = ask("รหัสอุปกรณ์: ", validate_id)
    if target is None:
        return
    matches = find_equipment_records(target)
    if not matches:
        print("ไม่พบรหัสอุปกรณ์")
        return

    original = matches[0][1]
    rec = dict(original)
    print(f"พบ ID {target} จำนวน {len(matches)} ชิ้น — การแก้ไขจะใช้กับอุปกรณ์ ID นี้ทั้งหมด")
    print(f"ปัจจุบัน: {rec['name']} | {rec['category']} | {rec['rate_per_day_thb']:.2f} | {rec['condition']}")
    print("กด Enter เพื่อคงค่าเดิม | พิมพ์ q เพื่อยกเลิกการแก้ไขทั้งหมด")

    rec["name"], cancelled = _ask_optional(f"ชื่อ [{rec['name']}]: ", rec["name"], validate_name)
    if cancelled: print("ยกเลิกการแก้ไข"); return
    rec["category"], cancelled = _ask_optional(f"หมวดหมู่ [{rec['category']}]: ", rec["category"], validate_category)
    if cancelled: print("ยกเลิกการแก้ไข"); return
    rec["year"], cancelled = _ask_optional(f"ปี [{rec['year']}]: ", rec["year"], validate_year)
    if cancelled: print("ยกเลิกการแก้ไข"); return
    rec["rate_per_day_thb"], cancelled = _ask_optional(f"ค่าเช่า [{rec['rate_per_day_thb']}]: ", rec["rate_per_day_thb"], validate_rate)
    if cancelled: print("ยกเลิกการแก้ไข"); return
    rec["condition"], cancelled = _ask_optional(f"สภาพ [{rec['condition']}]: ", rec["condition"], validate_condition)
    if cancelled: print("ยกเลิกการแก้ไข"); return

    changed = 0
    for idx, old in matches:
        updated = dict(old)
        for key in ("name", "category", "year", "rate_per_day_thb", "condition"):
            updated[key] = rec[key]
        write_equipment_at(idx, updated)
        changed += 1
    append_activity(OP_UPDATE, target, "", rec["condition"], rec["rate_per_day_thb"])
    print(f"แก้ไขสำเร็จ {changed} ชิ้น")


def delete_equipment():
    print("\n--- DELETE: ลบอุปกรณ์แบบ Soft Delete ---")
    target = ask("รหัสอุปกรณ์: ", validate_id)
    if target is None: return
    matches = find_equipment_records(target)
    if not matches:
        print("ไม่พบรหัสอุปกรณ์")
        return
    if any(rec["borrower_id"] for _, rec in matches):
        print("ลบไม่ได้: อุปกรณ์ ID นี้มีบางชิ้นกำลังถูกยืม")
        return
    for idx, rec in matches:
        rec = dict(rec)
        rec["is_deleted"] = True
        write_equipment_at(idx, rec)
    append_activity(OP_DELETE, target, "", len(matches), matches[0][1]["rate_per_day_thb"])
    print(f"ลบแบบ Soft Delete สำเร็จ — ID {target} จำนวน {len(matches)} ชิ้น")


def view_equipment_menu(log_view=True):
    while True:
        items = [r for r in read_equipment() if not r["is_deleted"]]
        print("\n--- VIEW: Equipment Information ---")
        print("1) View One")
        print("2) View All")
        print("3) Filter")
        print("4) Summary Statistics")
        print("0) Back")
        c = input("Select: ").strip()
        if c == "1":
            target = input("Equipment ID: ").strip()
            found = [r for r in items if r["equip_id"].lower() == target.lower()]
            print_table(found)
            if found and log_view: append_activity(OP_VIEW, target)
        elif c == "2":
            print_table(items)
            if log_view: append_activity(OP_VIEW, "0", value=len(items))
        elif c == "3":
            print("Categories:", ", ".join(CATEGORIES))
            cat = input("Category: ").strip()
            found = [r for r in items if r["category"].lower() == cat.lower()]
            print_table(found)
            if found and log_view: append_activity(OP_VIEW, "0", value=len(found))
        elif c == "4":
            borrowed = sum(bool(r["borrower_id"]) for r in items)
            rates = [r["rate_per_day_thb"] for r in items]
            print(f"Active         : {len(items)}")
            print(f"Available      : {len(items)-borrowed}")
            print(f"Borrowed       : {borrowed}")
            print(f"Minimum rate   : {min(rates) if rates else 0:.2f}")
            print(f"Maximum rate   : {max(rates) if rates else 0:.2f}")
            print(f"Average rate   : {sum(rates)/len(rates) if rates else 0:.2f}")
        elif c == "0": break
        else: print("Select 0-4 only")


def _status(rec):
    return "Deleted" if rec["is_deleted"] else ("Borrowed" if rec["borrower_id"] else "Available")


def _write_report(filename, lines):
    with open(filename, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# Report helpers
# Table cells are ASCII-only so every column is exactly the same width in any
# text editor / font. Thai text (which has zero-width vowels/tone marks and is
# rendered with different font widths) is listed OUTSIDE the tables instead.
# ---------------------------------------------------------------------------
def _is_ascii(text):
    return all(ord(ch) < 128 for ch in str(text))


def _name_cell(rec, thai_notes):
    """ASCII name for table; Thai names are replaced by 'Item <ID>' + note."""
    if _is_ascii(rec["name"]):
        return rec["name"]
    thai_notes.append((rec["equip_id"], rec["name"]))
    return f"Item {rec['equip_id']}"


def _bid(borrower_no):
    return f"P{borrower_no:03d}" if borrower_no else "-"


def _borrower_name(borrower_no, borrower_map):
    if not borrower_no:
        return "-"
    return borrower_map.get(borrower_no, f"P{borrower_no:03d}")


def _activity_detail(a):
    op = a["op_code"]
    value = a["value"]
    if op in (OP_BORROW_REQUEST, OP_RESERVE, OP_BORROW_APPROVE, OP_BORROW_REJECT, OP_BORROW):
        return "-"
    if op == OP_UPDATE:
        return CONDITION_NAMES.get(value, f"Condition {value}")
    if op == OP_VIEW:
        return f"{value} records"
    if op == OP_DELETE:
        return "1 item"
    if op == OP_RETURN:
        return "Returned"
    if op == OP_ADD:
        return f"Added {value} item(s)" if value else "Added"
    return str(value)


def _build_table(headers, rows, widths, aligns, empty_text):
    """Build a terminal table with Unicode-safe cell widths.

    ``widths`` are maximum widths. Each column expands when needed, up to
    its maximum, so Thai/English/multilingual text cannot shift the borders.
    ``table_utils`` measures terminal cells rather than bytes/characters.
    """
    from table_utils import display_width

    actual = []
    for i, header in enumerate(headers):
        max_width = widths[i]
        values = [header] + [r[i] for r in rows]
        needed = max(display_width(v) for v in values) if values else 1
        actual.append(max(1, min(max_width, needed)))

    line = table_line(actual)
    out = [line, table_row(headers, actual, ["center"] * len(actual)), line]
    if rows:
        out += [table_row(r, actual, aligns) for r in rows]
    else:
        cells = [""] * len(actual)
        cells[1] = empty_text
        out.append(table_row(cells, actual, ["center"] * len(actual)))
    out.append(line)
    return out


def _compose_report(title, details, table_lines, notes, summary):
    width = len(table_lines[0])
    bar = "=" * width
    out = [bar, title, bar, *details, "", *table_lines]
    if notes:
        out += ["", *notes]
    out += ["", "-" * width, "SUMMARY", *summary, bar]
    return out


def _thai_note_lines(thai_notes):
    if not thai_notes:
        return []
    seen, lines = set(), ["NOTE: ชื่ออุปกรณ์ภาษาไทยที่แสดงเป็น 'Item <ID>' ในตาราง"]
    for eid, name in thai_notes:
        if eid not in seen:
            seen.add(eid)
            lines.append(f"  {eid} = {name}")
    return lines


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _borrow_cycles(activities):
    """Rebuild every request/reservation and its outcome from activity.bin.

    Status flow: PENDING -> APPROVED -> RETURNED, or PENDING -> REJECTED.
    """
    cycles = []
    for a in activities:
        op = a["op_code"]
        if op in (OP_BORROW_REQUEST, OP_RESERVE):
            cycles.append({
                "type": "RESERVE" if op == OP_RESERVE else "BORROW",
                "equip_id": a["equip_id"], "borrower_no": a["borrower_no"],
                "days": a["value"], "rate": a["rate"],
                "start_ts": a["timestamp"], "update_ts": a["timestamp"],
                "status": "PENDING",
            })
        elif op in (OP_BORROW_APPROVE, OP_BORROW_REJECT):
            for c in cycles:
                if (c["status"] == "PENDING" and c["equip_id"] == a["equip_id"]
                        and c["borrower_no"] == a["borrower_no"] and c["days"] == a["value"]):
                    c["status"] = "APPROVED" if op == OP_BORROW_APPROVE else "REJECTED"
                    c["update_ts"] = a["timestamp"]
                    break
        elif op == OP_RETURN:
            for c in reversed(cycles):
                if (c["status"] == "APPROVED" and c["equip_id"] == a["equip_id"]
                        and c["borrower_no"] == a["borrower_no"]):
                    c["status"] = "RETURNED"
                    c["update_ts"] = a["timestamp"]
                    break
    return cycles


def generate_equipment_report():
    items = read_equipment()
    activities = read_activities()
    borrowers = read_borrowers()
    active = [r for r in items if not r["is_deleted"]]
    deleted = [r for r in items if r["is_deleted"]]
    available = [r for r in active if not r["borrower_id"]]
    borrowed = [r for r in active if r["borrower_id"]]
    borrower_map = {borrower_number(b["borrower_id"]): b["name"] for b in borrowers}

    # Group identical equipment IDs into one row. One ID can represent many physical units.
    groups = {}
    for r in active:
        groups.setdefault(r["equip_id"], []).append(r)
    display_items = list(groups.values())

    rows = []
    for eid, group in groups.items():
        r = group[0]
        free = sum(not x["borrower_id"] for x in group)
        borrowed_group = [x for x in group if x["borrower_id"]]
        if borrowed_group:
            status = "Borrowed"
            borrower_names = []
            for x in borrowed_group:
                bid = x["borrower_id"]
                name = borrower_map.get(borrower_number(bid), "")
                if name and name not in borrower_names:
                    borrower_names.append(name)
            borrower = ", ".join(borrower_names) if borrower_names else "-"
        else:
            status = "Available"
            borrower = "-"
        rows.append([
            r["equip_id"], _name_cell(r, []), r["category"], status, borrower,
            CONDITION_NAMES.get(r["condition"], "?"), len(group)
        ])

    widths = [12, 28, 12, 15, 24, 12, 8]
    table = _build_table(
        ["Equipment ID", "Equipment Name", "Category", "Status", "Borrower", "Condition", "Qty"],
        rows, widths,
        ["left", "left", "left", "center", "center", "center", "center"],
        "No active equipment")

    by_cat = []
    for cat in CATEGORIES:
        group = [r for r in active if r["category"] == cat]
        if group:
            free = sum(not r["borrower_id"] for r in group)
            ids = len({r["equip_id"] for r in group})
            by_cat.append(f"  {cat:<10}: {ids:>2} IDs | {len(group):>2} units | Available {free:>2} | Borrowed {len(group)-free:>2}")
    use_pct = (len(borrowed) / len(active) * 100) if active else 0.0

    details = [
        f"Generated At : {_now()}",
        "Source Files : inventory.bin + borrowers.bin + activity.bin",
        f"Equipment Records : {len(items)} | Borrowers : {len(borrowers)} | Activity Records : {len(activities)}",
        "",
        "DETAILS",
        "แสดงสถานะอุปกรณ์ Active ครบทุกชิ้น เพื่อให้ข้อมูลที่เพิ่ม/แก้ไขล่าสุดมองเห็นได้ทันที",
        "Borrower ใช้ชื่อจาก borrowers.bin และ Status/Condition ใช้ข้อมูลจาก inventory.bin",
        "",
        "TABLE: EQUIPMENT STATUS (ALL ACTIVE ITEMS)",
    ]
    summary = [
        f"Total records : {len(items)}  (Active {len(active)} | Deleted/Free slot {len(deleted)})",
        f"Displayed in table : {len(display_items)} equipment IDs / {len(active)} physical units",
        f"Available : {len(available)}",
        f"Borrowed : {len(borrowed)} ({use_pct:.1f}% of active equipment in use)",
        "By category:",
        *by_cat,
    ]
    _write_report(REPORT_FILES["equipment"],
                  _compose_report("📦 สรุปสถานะอุปกรณ์", details, table, [], summary))


def generate_borrowing_report():
    items = read_equipment()
    borrowers = read_borrowers()
    activities = read_activities()
    item_map = {r["equip_id"]: r for r in items}
    borrower_map = {borrower_number(b["borrower_id"]): b["name"] for b in borrowers}
    cycles = _borrow_cycles(activities)

    rows = []
    for n, c in enumerate(cycles, 1):
        rec = item_map.get(c["equip_id"])
        equip = rec["name"] if rec else "Unknown"
        start_dt = datetime.fromtimestamp(c["start_ts"])
        end_dt = start_dt + timedelta(days=c["days"])
        rows.append([
            n,
            _borrower_name(c["borrower_no"], borrower_map),
            equip,
            start_dt.strftime("%Y-%m-%d"),
            end_dt.strftime("%Y-%m-%d"),
            c["status"],
        ])

    widths = [5, 16, 30, 12, 12, 11]
    table = _build_table(
        ["No.", "Borrower", "Equipment", "Start Date", "End Date", "Status"],
        rows, widths,
        ["center", "left", "left", "center", "center", "center"],
        "No borrowing history yet")

    count = lambda status: sum(c["status"] == status for c in cycles)
    borrowed_now = sum(bool(r["borrower_id"]) and not r["is_deleted"] for r in items)
    decided = count("APPROVED") + count("RETURNED") + count("REJECTED")
    approve_rate = ((count("APPROVED") + count("RETURNED")) / decided * 100) if decided else 0.0

    details = [
        f"Generated At : {_now()}",
        "Source Files : inventory.bin + borrowers.bin + activity.bin",
        f"Equipment Records : {len(items)} | Borrowers : {len(borrowers)} | Requests : {len(cycles)}",
        "",
        "DETAILS",
        "แสดงรายการยืม/จอง โดยใช้ชื่อผู้ยืมและชื่ออุปกรณ์เพื่อให้อ่านง่าย",
        "Start Date = วันที่เริ่มยืม | End Date = วันที่สิ้นสุดตามจำนวนวันที่ยืม",
        "",
        "TABLE: BORROWING SUMMARY",
    ]
    summary = [
        f"Total requests : {len(cycles)}",
        f"Pending : {count('PENDING')} | Approved : {count('APPROVED')} | Returned : {count('RETURNED')} | Rejected : {count('REJECTED')}",
        f"Approval rate : {approve_rate:.1f}% of decided requests",
        f"Equipment currently borrowed : {borrowed_now}",
    ]
    _write_report(REPORT_FILES["borrowing"],
                  _compose_report("📋 สรุปการยืม", details, table, [], summary))


def generate_activity_report():
    activities = read_activities()
    items = read_equipment()
    borrowers = read_borrowers()
    item_map = {r["equip_id"]: r for r in items}
    borrower_map = {borrower_number(b["borrower_id"]): b["name"] for b in borrowers}
    cycles = _borrow_cycles(activities)

    def period_for_activity(a):
        op = a["op_code"]
        if op in (OP_BORROW_REQUEST, OP_RESERVE):
            start_ts = a["timestamp"]
            end_ts = start_ts + (a["value"] * 86400)
            return (datetime.fromtimestamp(start_ts).strftime("%Y-%m-%d"),
                    datetime.fromtimestamp(end_ts).strftime("%Y-%m-%d"))

        candidates = [
            c for c in cycles
            if c["equip_id"] == a["equip_id"]
            and c["borrower_no"] == a["borrower_no"]
            and c["days"] == a["value"]
        ]
        if candidates:
            exact = [c for c in candidates
                     if c["start_ts"] == a["timestamp"] or c["update_ts"] == a["timestamp"]]
            c = exact[-1] if exact else candidates[-1]
            start_ts = c["start_ts"]
            end_ts = start_ts + (c["days"] * 86400)
            return (datetime.fromtimestamp(start_ts).strftime("%Y-%m-%d"),
                    datetime.fromtimestamp(end_ts).strftime("%Y-%m-%d"))
        return "-", "-"

    # แสดง Activity ครบทุก record ไม่ตัดเหลือ 30 รายการ
    rows = []
    for a in sorted(activities, key=lambda x: x["timestamp"], reverse=True):
        rec = item_map.get(a["equip_id"])
        equip = rec["name"] if rec else ("-" if a["equip_id"] == "0" else "Not in inventory")
        bid = _borrower_name(a["borrower_no"], borrower_map)
        start_date, end_date = period_for_activity(a)
        rows.append([
            datetime.fromtimestamp(a["timestamp"]).strftime("%Y-%m-%d %H:%M"),
            ACTION_LABELS.get(OP_NAMES.get(a["op_code"], "UNKNOWN"), "Unknown"),
            equip, bid, start_date, end_date, _activity_detail(a)
        ])

    widths = [17, 10, 30, 16, 12, 12, 18]
    table = _build_table(
        ["Date / Time", "Action", "Equipment", "Borrower", "Start Date", "End Date", "Details"],
        rows, widths,
        ["center", "center", "left", "left", "center", "center", "center"],
        "No activity yet")

    op_counts = {}
    for a in activities:
        code = OP_NAMES.get(a["op_code"], "UNKNOWN")
        name = ACTION_LABELS.get(code, code.title())
        op_counts[name] = op_counts.get(name, 0) + 1
    breakdown = " | ".join(f"{k} {v}" for k, v in sorted(op_counts.items()))
    stamps = [a["timestamp"] for a in activities]
    first = datetime.fromtimestamp(min(stamps)).strftime("%Y-%m-%d %H:%M") if stamps else "-"
    last = datetime.fromtimestamp(max(stamps)).strftime("%Y-%m-%d %H:%M") if stamps else "-"

    details = [
        f"Generated At : {_now()}",
        "Source Files : activity.bin + inventory.bin + borrowers.bin",
        f"Activity Records : {len(activities)} | Equipment Records : {len(items)} | Borrowers : {len(borrowers)}",
        "",
        "DETAILS",
        "แสดงประวัติการทำงานครบทุกกิจกรรม พร้อมวันที่เริ่มยืมและวันที่สิ้นสุด",
        "ไม่แสดงจำนวนวัน เพื่อให้ดูวันเริ่มต้นและวันสิ้นสุดได้โดยตรง",
        "Borrower แสดงเป็นชื่อ และ Equipment แสดงเป็นชื่ออุปกรณ์",
        "",
        "TABLE: ACTIVITY LOG",
    ]
    summary = [
        f"Total activity records : {len(activities)}",
        f"Period covered : {first} to {last}",
        f"By action : {breakdown if breakdown else '-'}",
    ]
    _write_report(REPORT_FILES["activity"],
                  _compose_report("📝 สรุปประวัติการทำงาน", details, table, [], summary))


def generate_reports(verbose=True):
    # Every report is regenerated from the current Binary files.
    # This is the single source of truth for all TXT reports.
    generate_equipment_report()
    generate_borrowing_report()
    generate_activity_report()
    if verbose:
        print("สร้างรายงานสำเร็จ 3 ไฟล์:")
        for path in REPORT_FILES.values():
            print(f"- {path}")


def generate_report():
    # Backward-compatible name used by main.py.
    generate_reports()


def staff_menu():
    while True:
        print("\n=== STAFF / ADMIN ===")
        print("1) Add Equipment")
        print("2) Update Equipment")
        print("3) Delete Equipment")
        print("4) View Equipment")
        print("5) Generate Reports")
        print("0) Back")
        c = input("Select: ").strip()
        if c == "1": add_equipment()
        elif c == "2": update_equipment()
        elif c == "3": delete_equipment()
        elif c == "4": view_equipment_menu()
        elif c == "5":
            generate_reports()
        elif c == "0": break
        else: print("Select 0-5 only")
