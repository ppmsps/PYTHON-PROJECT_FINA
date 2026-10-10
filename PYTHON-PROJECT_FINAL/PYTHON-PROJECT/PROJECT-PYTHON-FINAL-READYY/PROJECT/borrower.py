from data import *
from datetime import datetime, timedelta


def borrower_menu():
    while True:
        print("\n=== BORROWER / ผู้ยืม ===")
        print("1) View Available Equipment")
        print("2) Register Borrower")
        print("3) Request Borrow / Reserve")
        print("4) Return Equipment")
        print("0) Back")
        c = input("เลือกเมนู: ").strip()
        if c == "1":
            show_equipment_status()
        elif c == "2":
            register_borrower()
        elif c == "3":
            request_borrow()
        elif c == "4":
            return_equipment()
        elif c == "0":
            break
        else:
            print("กรุณาเลือก 0-4")


def validate_borrower_id(v):
    import re
    if not re.fullmatch(r"P\d{3}", v.upper()):
        raise ValueError("รหัสผู้ยืมต้องอยู่ในรูปแบบ P001-P999")
    return v.upper()


def register_borrower():
    bid = input("รหัสผู้ยืม (เช่น P001): ").strip().upper()
    try:
        bid = validate_borrower_id(bid)
    except ValueError as exc:
        print(exc)
        return
    if find_borrower(bid):
        print("มีผู้ยืมนี้อยู่แล้ว")
        return
    name = input("ชื่อผู้ยืม: ").strip()
    if not name or len(name.encode("cp874")) > 32:
        print("ชื่อไม่ถูกต้อง: ต้องไม่ว่างและไม่เกิน 32 bytes")
        return
    append_borrower(bid, name)
    print("ลงทะเบียนผู้ยืมสำเร็จ")


def _equipment_category(eid):
    _, rec = find_equipment(eid)
    return rec["category"] if rec else None


def _borrowed_records_in_category(category):
    return [r for r in read_equipment()
            if not r["is_deleted"]
            and r["category"].lower() == category.lower()
            and r["borrower_id"]]


def _active_request_for(bid, eid):
    """Unresolved request/reservation for this exact physical equipment."""
    borrower_no = borrower_number(bid)
    current = None
    for a in read_activities():
        if a["borrower_no"] != borrower_no or a["equip_id"] != eid:
            continue
        if a["op_code"] in (OP_BORROW_REQUEST, OP_RESERVE):
            current = a
        elif a["op_code"] in (OP_BORROW_APPROVE, OP_BORROW_REJECT, OP_RETURN):
            # An approve/reject resolves the request. A later reservation can
            # be created after a completed cycle.
            current = None
    return current


def _borrower_has_category(bid, category, include_pending=True):
    """Return an active borrowed/requested item in the same category.

    The 1-item-per-category rule belongs to the borrower, not to the equipment.
    Therefore another borrower may reserve the same physical item and form a queue.
    ``include_pending`` is kept configurable so reservation logic can distinguish
    an actual current loan from a future queue entry.
    """
    for rec in _borrowed_records_in_category(category):
        if rec["borrower_id"].lower() == bid.lower():
            return rec

    if not include_pending:
        return None

    borrower_no = borrower_number(bid)
    pending = None
    for a in read_activities():
        if a["borrower_no"] != borrower_no or a["op_code"] not in (OP_BORROW_REQUEST, OP_RESERVE):
            continue
        if _equipment_category(a["equip_id"]) == category:
            pending = a
    return pending


def _current_borrow_due(eid):
    last_borrow = None
    for a in read_activities():
        if a["equip_id"] == eid and a["op_code"] == OP_BORROW:
            last_borrow = a
        elif a["equip_id"] == eid and a["op_code"] == OP_RETURN:
            last_borrow = None
    if last_borrow is None:
        return None
    # BORROW timestamp is the actual start date/time; value is duration.
    return datetime.fromtimestamp(last_borrow["timestamp"]) + timedelta(days=last_borrow["value"])


def _reservation_queue(eid):
    """Return unresolved RESERVE entries for one exact equipment ID with a projected schedule."""
    acts = read_activities()
    resolved = set()
    for a in acts:
        if a["equip_id"] != eid:
            continue
        key = (a["borrower_no"], a["value"])
        if a["op_code"] in (OP_BORROW_APPROVE, OP_BORROW_REJECT):
            resolved.add(key)

    reservations = [
        a for a in acts
        if a["equip_id"] == eid
        and a["op_code"] == OP_RESERVE
        and (a["borrower_no"], a["value"]) not in resolved
    ]
    reservations.sort(key=lambda a: a["timestamp"])

    slot = _current_borrow_due(eid) or datetime.fromtimestamp(0)
    result = []
    for a in reservations:
        requested = datetime.fromtimestamp(a["timestamp"])
        scheduled = max(slot, requested)
        end = scheduled + timedelta(days=a["value"])
        result.append({
            "borrower_no": a["borrower_no"],
            "requested": requested,
            "days": a["value"],
            "scheduled": scheduled,
            "end": end,
        })
        slot = end
    return result


def _exact_item_reservation_start(eid, desired_start):
    """
    Schedule the exact physical item.
    The first possible slot is after its current borrower returns. Then
    unresolved reservations for the same exact ID are processed in request order.
    """
    slot = desired_start
    due = _current_borrow_due(eid)
    if due and due > slot:
        slot = due

    acts = read_activities()
    resolved = set()
    for a in acts:
        if a["equip_id"] != eid:
            continue
        key = (a["borrower_no"], a["value"])
        if a["op_code"] in (OP_BORROW_APPROVE, OP_BORROW_REJECT):
            resolved.add(key)

    reservations = [
        a for a in acts
        if a["equip_id"] == eid
        and a["op_code"] == OP_RESERVE
        and (a["borrower_no"], a["value"]) not in resolved
    ]
    reservations.sort(key=lambda a: a["timestamp"])

    for a in reservations:
        requested = datetime.fromtimestamp(a["timestamp"])
        scheduled = max(slot, requested)
        slot = scheduled + timedelta(days=a["value"])

    return slot


def _category_items(category):
    return [r for r in read_equipment()
            if not r["is_deleted"] and r["category"].lower() == category.lower()]


def show_equipment_status():
    items = [r for r in read_equipment() if not r["is_deleted"]]
    if not items:
        print("ไม่พบอุปกรณ์")
        return

    print("\n=== EQUIPMENT STATUS / สถานะอุปกรณ์ ===")
    print("หมายเหตุ: ระบบจะแสดงสถานะของ ID จริง และไม่สุ่มเปลี่ยนอุปกรณ์ให้ผู้ยืม")

    # Fixed-width columns make every equipment row start/end at the same position.
    ID_W = 8
    NAME_W = 32
    STATUS_W = 58
    SEP = "  " + "-" * ID_W + "+" + "-" * NAME_W + "+" + "-" * STATUS_W
    HEADER = "  " + f"{'ID':<{ID_W}}|{'Equipment Name':<{NAME_W}}|{'Status / รายละเอียด':<{STATUS_W}}"

    for cat in CATEGORIES:
        group = [r for r in items if r["category"].lower() == cat.lower()]
        if not group:
            continue

        available = sum(1 for r in group if not r["borrower_id"])
        print(f"\n[{cat}] เหลือว่าง {available}/{len(group)} ชิ้น")
        print(SEP)
        print(HEADER)
        print(SEP)

        for r in group:
            eid = str(r["equip_id"])
            name = r["name"]

            if not r["borrower_id"]:
                print(f"  {eid:<{ID_W}}|{name:<{NAME_W}}|ว่าง")
                continue

            # Find the current BORROW record for this exact equipment.
            due = _current_borrow_due(r["equip_id"])
            start = None
            for a in read_activities():
                if a["equip_id"] == r["equip_id"] and a["op_code"] == OP_BORROW:
                    start = datetime.fromtimestamp(a["timestamp"])

            status = f"ถูกยืมโดย {r['borrower_id']}"
            print(f"  {eid:<{ID_W}}|{name:<{NAME_W}}|{status}")
            if due and start:
                print(f"  {'':<{ID_W}}|{'':<{NAME_W}}|เริ่ม {start:%d/%m/%Y} | สิ้นสุด/คืน {due:%d/%m/%Y}")

            # Show the existing reservation queue below the same equipment ID.
            queue = _reservation_queue(r["equip_id"])
            if queue:
                print(f"  {'':<{ID_W}}|{'':<{NAME_W}}|คิวจองล่วงหน้า:")
                for qno, q in enumerate(queue, 1):
                    print(f"  {'':<{ID_W}}|{'':<{NAME_W}}|  คิว {qno}: P{q['borrower_no']:03d} | ต้องการเริ่ม {q['requested']:%d/%m/%Y} | {q['days']} วัน | คาดว่า {q['scheduled']:%d/%m/%Y}-{q['end']:%d/%m/%Y}")

        print(SEP)


def request_borrow():
    bid = input("รหัสผู้ยืม: ").strip()
    borrower = find_borrower(bid)
    if not borrower:
        print("ไม่พบผู้ยืม กรุณาลงทะเบียนก่อน")
        return

    eid = input("รหัสอุปกรณ์ที่ต้องการ (เช่น 90005): ").strip()
    # Same ID can represent multiple identical physical units.
    # Prefer an available unit for an immediate borrow; otherwise use the first unit for reservation details.
    _, rec = find_available_equipment(eid)
    if rec is None:
        _, rec = find_equipment(eid)
    if rec is None:
        print("ไม่พบอุปกรณ์ตาม ID ที่ระบุ")
        return

    category = rec["category"]

    # If the exact item is already occupied, this is a queue/reservation case.
    # First reject only a duplicate request for the same physical item.
    existing = _active_request_for(bid, eid)
    if existing:
        print(f"ไม่สามารถยื่นซ้ำได้: {bid} มีคำขอของอุปกรณ์ {eid} อยู่แล้ว")
        return

    # 1 borrower may actively hold/request only 1 physical item per category.
    # This restriction is per borrower; it must NOT block other borrowers from
    # reserving the same occupied equipment.
    existing_cat = _borrower_has_category(bid, category)
    if existing_cat:
        if isinstance(existing_cat, dict) and "op_code" in existing_cat:
            print(f"ไม่สามารถยื่นซ้ำได้: {bid} มีคำขอ/คิวจองในหมวด {category} อยู่แล้ว (อุปกรณ์ {existing_cat['equip_id']})")
        else:
            print(f"ไม่สามารถยืมซ้ำได้: {bid} มีอุปกรณ์หมวด {category} อยู่แล้ว ({existing_cat['equip_id']} - {existing_cat['name']})")
        print("กติกา: ผู้ยืม 1 รหัส ยืม/จองได้ 1 ชิ้นต่อ 1 หมวด")
        return

    group = _category_items(category)
    id_group = [r for r in group if r["equip_id"].lower() == eid.lower()]
    available = [r for r in group if not r["borrower_id"]]
    same_id_available = [r for r in id_group if not r["borrower_id"]]

    print(f"\n=== {category} ===")
    print(f"อุปกรณ์ในหมวดนี้ทั้งหมด: {len(group)} ชิ้น | ว่าง: {len(available)} ชิ้น | ถูกยืม: {len(group)-len(available)} ชิ้น")
    print(f"ID {eid}: {rec['name']} | ทั้งหมด {len(id_group)} ชิ้น | ว่าง {len(same_id_available)} ชิ้น")

    if rec["borrower_id"]:
        # Exact item is unavailable. Show alternatives, but NEVER silently assign one.
        print(f"\n❌ {rec['equip_id']} ไม่ว่างในขณะนี้ (ผู้ยืม: {rec['borrower_id']})")
        if available:
            print("\nอุปกรณ์อื่นในหมวดเดียวกันที่ยังว่าง:")
            for r in available:
                print(f"  {r['equip_id']} | {r['name']} | ว่าง")
            print("\nหากต้องการของตาม ID ที่เลือก กรุณาเลือก 'จองล่วงหน้า'")
        else:
            print(f"❌ อุปกรณ์ทั้ง {len(group)} ชิ้นในหมวดนี้ถูกยืมครบแล้ว")

        choice = input("ต้องการจองอุปกรณ์ ID นี้โดยตรงหรือไม่? (y/n): ").strip().lower()
        if choice != "y":
            print("ยกเลิกการทำรายการ — ไม่มีการเปลี่ยนอุปกรณ์ให้โดยอัตโนมัติ")
            return

        is_reservation = True
    else:
        is_reservation = False

    # Let the customer specify the intended start date. This makes the appointment
    # explicit instead of silently using today's date.
    raw_date = input("วันที่ต้องการเริ่มยืม/เริ่มจอง (DD/MM/YYYY, Enter=วันนี้): ").strip()
    if raw_date:
        try:
            desired_start = datetime.strptime(raw_date, "%d/%m/%Y").replace(hour=9, minute=0, second=0)
            if desired_start.date() < datetime.now().date():
                print("วันที่ต้องการต้องไม่ย้อนหลัง")
                return
        except ValueError:
            print("รูปแบบวันที่ไม่ถูกต้อง ใช้ DD/MM/YYYY")
            return
    else:
        desired_start = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)

    days_raw = input("จำนวนวันที่ขอยืม/จอง: ").strip()
    try:
        days = int(days_raw)
        if days <= 0:
            raise ValueError
    except ValueError:
        print("จำนวนวันต้องเป็นจำนวนเต็มมากกว่า 0")
        return

    if is_reservation:
        projected = _exact_item_reservation_start(eid, desired_start)
        if projected > desired_start:
            print("\n=== รายละเอียดคิวจอง ===")
            print(f"อุปกรณ์ที่จอง: {eid} | {rec['name']}")
            print(f"วันที่ยื่นจอง: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            print(f"วันที่ลูกค้าต้องการ: {desired_start.strftime('%d/%m/%Y')}")
            print(f"วันที่เร็วที่สุดที่คาดว่าจะรับได้: {projected.strftime('%d/%m/%Y')}")
            print("ระบบจะไม่เปลี่ยนอุปกรณ์ให้ และจะรออุปกรณ์ ID นี้โดยตรง")
            confirm = input("ยืนยันคิวจองหรือไม่? (y/n): ").strip().lower()
            if confirm != "y":
                print("ยกเลิกการจอง")
                return
        else:
            print(f"\nอุปกรณ์ {eid} คาดว่าจะพร้อมรับได้ตั้งแต่ {projected.strftime('%d/%m/%Y')}")
            confirm = input("ยืนยันการจองหรือไม่? (y/n): ").strip().lower()
            if confirm != "y":
                print("ยกเลิกการจอง")
                return

    op = OP_RESERVE if is_reservation else OP_BORROW_REQUEST
    # Timestamp stores the requested start date so reservation scheduling is deterministic.
    append_activity(op, eid, bid, days, rec["rate_per_day_thb"], timestamp=int(desired_start.timestamp()))

    if is_reservation:
        projected = _exact_item_reservation_start(eid, desired_start)
        print(f"จองสำเร็จ: {eid} | {rec['name']} | วันที่เริ่มที่ต้องการ {desired_start.strftime('%d/%m/%Y')} | วันที่เร็วที่สุด {projected.strftime('%d/%m/%Y')}")
    else:
        print(f"ส่งคำขอยืมแล้ว: {eid} | {rec['name']} | วันที่เริ่ม {desired_start.strftime('%d/%m/%Y')}")
        print("ผู้อนุมัติจะอนุมัติ 'อุปกรณ์ ID นี้' เท่านั้น")


def return_equipment():
    bid = input("รหัสผู้ยืม: ").strip()
    eid = input("รหัสอุปกรณ์ที่คืน: ").strip()
    idx, rec = find_equipment_for_borrower(eid, bid)
    if rec is None:
        print("ไม่พบอุปกรณ์ที่ผู้ยืมรหัสนี้กำลังถืออยู่")
        return
        print("ผู้ยืมไม่ตรงกับข้อมูลในระบบ")
        return
    rec["borrower_id"] = ""
    write_equipment_at(idx, rec)
    append_activity(OP_RETURN, eid, bid, 0, rec["rate_per_day_thb"])
    print(f"คืนสำเร็จ: {eid} | {rec['name']}")
