from data import *
from table_utils import table_line, table_row
from datetime import datetime, timedelta


def pending_requests():
    acts = read_activities()
    result = []
    resolved = set()
    for a in acts:
        key = (a["equip_id"], a["borrower_no"], a["value"])
        if a["op_code"] in (OP_BORROW_APPROVE, OP_BORROW_REJECT):
            resolved.add(key)
    for a in acts:
        if a["op_code"] in (OP_BORROW_REQUEST, OP_RESERVE):
            key = (a["equip_id"], a["borrower_no"], a["value"])
            if key not in resolved:
                result.append(a)
    return result


def _borrow_actions():
    return {
        OP_BORROW_REQUEST, OP_RESERVE, OP_BORROW_APPROVE, OP_BORROW_REJECT,
        OP_BORROW, OP_RETURN
    }


def show_borrow_return_history():
    acts = [a for a in read_activities() if a["op_code"] in _borrow_actions()]
    items = {r["equip_id"]: r for r in read_equipment()}
    borrowers = {b["borrower_id"].upper(): b for b in read_borrowers()}

    print("\n--- Borrow / Return History ---")
    if not acts:
        print("ยังไม่มีประวัติการยืม-คืน")
        return

    widths = [18, 12, 12, 22, 22, 12]
    line = table_line(widths)
    print(line)
    print(table_row(
        ["Date / Time", "Operation", "Equip ID", "Equipment", "Borrower", "Value"],
        widths, ["left", "left", "left", "left", "left", "right"]
    ))
    print(line)

    for a in acts:
        dt = datetime.fromtimestamp(a["timestamp"]).strftime("%Y-%m-%d %H:%M")
        bid = f"P{a['borrower_no']:03d}" if a["borrower_no"] else "-"
        borrower = borrowers.get(bid.upper(), {}).get("name", bid)
        equipment = items.get(a["equip_id"], {}).get("name", "Unknown")
        op = OP_NAMES.get(a["op_code"], "UNKNOWN")
        print(table_row(
            [dt, op, a["equip_id"], equipment, borrower, a["value"]],
            widths, ["left", "left", "left", "left", "left", "right"]
        ))

    print(line)
    print(f"Total Borrow / Return Activities: {len(acts)}")


def _return_status_records():
    items = {r["equip_id"]: r for r in read_equipment()}
    acts = read_activities()

    # Last BORROW/RETURN event per equipment + borrower.
    last_event = {}
    for a in acts:
        if a["op_code"] in (OP_BORROW, OP_RETURN):
            key = (a["equip_id"], a["borrower_no"])
            last_event[key] = a

    result = []
    for (eid, borrower_no), event in last_event.items():
        rec = items.get(eid)
        if rec is None:
            continue
        bid = f"P{borrower_no:03d}" if borrower_no else "-"
        if event["op_code"] == OP_RETURN:
            status = "RETURNED"
        elif rec["borrower_id"]:
            status = "WAITING"
        else:
            status = "RETURNED"
        result.append((eid, rec, bid, status, event))

    return result


def show_return_status():
    records = _return_status_records()

    print("\n--- Check Return Status ---")
    print("1) Waiting for Return")
    print("2) Returned Equipment")
    print("3) All Return Records")
    print("0) Back")
    choice = input("Select: ").strip()

    if choice == "0":
        return
    if choice not in {"1", "2", "3"}:
        print("Select 0-3 only")
        return

    if choice == "1":
        records = [x for x in records if x[3] == "WAITING"]
        title = "WAITING FOR RETURN"
    elif choice == "2":
        records = [x for x in records if x[3] == "RETURNED"]
        title = "RETURNED EQUIPMENT"
    else:
        title = "ALL RETURN RECORDS"

    print(f"\n--- {title} ---")
    if not records:
        print("ไม่พบข้อมูล")
        return

    widths = [10, 28, 14, 14, 12, 12]
    line = table_line(widths)
    print(line)
    print(table_row(
        ["Equip ID", "Equipment", "Borrower", "Last Action", "Status", "Days"],
        widths, ["left", "left", "center", "left", "center", "right"]
    ))
    print(line)

    for eid, rec, bid, status, event in records:
        action = OP_NAMES.get(event["op_code"], "UNKNOWN")
        print(table_row(
            [eid, rec["name"], bid, action, status, event["value"]],
            widths, ["left", "left", "center", "left", "center", "right"]
        ))

    print(line)
    waiting = sum(x[3] == "WAITING" for x in records)
    returned = sum(x[3] == "RETURNED" for x in records)
    print(f"Waiting for Return: {waiting}")
    print(f"Returned: {returned}")
    print(f"Total Records: {len(records)}")


def approver_menu():
    while True:
        print("\n=== APPROVER / ผู้อนุมัติ ===")
        print("1) View Pending Requests / Reservations")
        print("2) Approve / Reject Request")
        print("3) View Reservation Queues")
        print("4) View Borrow / Return Information")
        print("0) Back")
        c = input("Select: ").strip()
        if c == "1":
            show_requests()
        elif c == "2":
            while True:
                print("\n--- PROCESS REQUEST ---")
                print("1) Approve")
                print("2) Reject")
                print("0) Cancel")
                action = input("Select: ").strip()
                if action == "1":
                    process_request(True)
                    break
                elif action == "2":
                    process_request(False)
                    break
                elif action == "0":
                    break
                else:
                    print("Select 0-2 only")
        elif c == "3":
            show_reservation_queues()
        elif c == "4":
            while True:
                print("\n--- BORROW / RETURN INFORMATION ---")
                print("1) Borrow / Return History")
                print("2) Return Status")
                print("0) Back")
                sub = input("Select: ").strip()
                if sub == "1":
                    show_borrow_return_history()
                elif sub == "2":
                    show_return_status()
                elif sub == "0":
                    break
                else:
                    print("Select 0-2 only")
        elif c == "0":
            break
        else:
            print("Select 0-4 only")


def _reservation_queue(eid):
    """Return unresolved reservation queue for one exact physical equipment ID."""
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

    # Current borrower blocks the physical item until this due date.
    current_due = None
    for a in acts:
        if a["equip_id"] == eid and a["op_code"] == OP_BORROW:
            current_due = datetime.fromtimestamp(a["timestamp"]) + timedelta(days=a["value"])
        elif a["equip_id"] == eid and a["op_code"] == OP_RETURN:
            current_due = None

    slot = current_due or datetime.fromtimestamp(0)
    result = []
    for a in reservations:
        requested = datetime.fromtimestamp(a["timestamp"])
        scheduled = max(slot, requested)
        end = scheduled + timedelta(days=a["value"])
        result.append((a, requested, scheduled, end))
        slot = end
    return current_due, result


def show_reservation_queues():
    items = {r["equip_id"]: r for r in read_equipment() if not r["is_deleted"]}
    acts = read_activities()
    eids = sorted({a["equip_id"] for a in acts if a["op_code"] == OP_RESERVE})

    print("\n--- RESERVATION QUEUES / คิวจองล่วงหน้า ---")
    print("แสดงคิวของอุปกรณ์ ID เดิมโดยเรียงตามลำดับการจอง")
    if not eids:
        print("ยังไม่มีคิวจอง")
        return

    borrowers = {b["borrower_id"].upper(): b for b in read_borrowers()}
    for eid in eids:
        rec = items.get(eid)
        if not rec:
            continue
        current_due, queue = _reservation_queue(eid)
        if not queue:
            continue

        print(f"\n{eid} | {rec['name']} | หมวด {rec['category']}")
        if rec["borrower_id"]:
            start = None
            for a in acts:
                if a["equip_id"] == eid and a["op_code"] == OP_BORROW:
                    start = datetime.fromtimestamp(a["timestamp"])
            if start and current_due:
                print(f"  ผู้ยืมปัจจุบัน: {rec['borrower_id']} | เริ่ม {start:%d/%m/%Y} | สิ้นสุด/คืน {current_due:%d/%m/%Y}")
            else:
                print(f"  ผู้ยืมปัจจุบัน: {rec['borrower_id']}")
        else:
            print("  สถานะปัจจุบัน: ว่าง")

        for no, (a, requested, scheduled, end) in enumerate(queue, 1):
            bid = f"P{a['borrower_no']:03d}"
            borrower_name = borrowers.get(bid.upper(), {}).get("name", "")
            label = f"{bid} ({borrower_name})" if borrower_name else bid
            print(f"  คิว {no}: {label} | ต้องการเริ่ม {requested:%d/%m/%Y} | {a['value']} วัน | คาดว่าเริ่ม {scheduled:%d/%m/%Y} | สิ้นสุด/คืน {end:%d/%m/%Y}")

    print("\nหมายเหตุ: คิวจองจะยึดอุปกรณ์ ID ที่ลูกค้าเลือก ไม่สลับไปใช้อุปกรณ์ตัวอื่น")


def show_requests():
    reqs = pending_requests()
    if not reqs:
        print("ไม่มีคำขอที่รออนุมัติ")
        return

    widths = [5, 10, 28, 10, 10, 12, 18]
    line = table_line(widths)

    print("\n--- Pending Requests ---")
    print(line)
    print(table_row(
        ["No.", "Equip ID", "Equipment", "Type", "Borrower", "Days", "Start Date"],
        widths, ["center", "left", "left", "center", "center", "right", "left"]
    ))
    print(line)

    items = {r["equip_id"]: r for r in read_equipment()}
    for n, r in enumerate(reqs, 1):
        borrower = f"P{r['borrower_no']:03d}"
        request_type = "RESERVE" if r["op_code"] == OP_RESERVE else "BORROW"
        start_date = datetime.fromtimestamp(r["timestamp"]).strftime("%d/%m/%Y")
        equipment = items.get(r["equip_id"], {}).get("name", "Unknown")
        print(table_row(
            [n, r["equip_id"], equipment, request_type, borrower, r["value"], start_date],
            widths, ["center", "left", "left", "center", "center", "right", "left"]
        ))
        if r["op_code"] == OP_RESERVE:
            print(f"    ↳ จองตรง ID {r['equip_id']} เท่านั้น | ไม่เปลี่ยนอุปกรณ์อัตโนมัติ")

    print(line)
    print(f"Total Pending Requests: {len(reqs)}")


def process_request(approve):
    reqs = pending_requests()
    if not reqs:
        print("ไม่มีคำขอที่รออนุมัติ")
        return
    show_requests()
    try:
        n = int(input("เลือกหมายเลขคำขอ (0=ยกเลิก): "))
        if n == 0:
            return
        req = reqs[n - 1]
    except (ValueError, IndexError):
        print("หมายเลขไม่ถูกต้อง")
        return

    requested_eid = req["equip_id"]
    bid = f"P{req['borrower_no']:03d}"
    _, requested_rec = find_equipment(requested_eid)
    if requested_rec is None:
        print("ไม่พบอุปกรณ์ที่ใช้ระบุหมวดในคำขอแล้ว")
        append_activity(OP_BORROW_REJECT, requested_eid, bid, req["value"], req["rate"])
        return

    category = requested_rec["category"]
    available = [r for r in read_equipment()
                 if not r["is_deleted"] and r["category"].lower() == category.lower() and not r["borrower_id"]]
    is_reservation = req["op_code"] == OP_RESERVE

    if not available:
        if is_reservation:
            print(f"หมวด {category} ยังเต็ม — คิวจองยังคงรออยู่")
            return
        print(f"หมวด {category} ไม่มีอุปกรณ์ว่างแล้ว")
        append_activity(OP_BORROW_REJECT, requested_eid, bid, req["value"], req["rate"])
        return

    # One ID may represent multiple identical physical units.
    # For an immediate approval, assign any available unit under the requested ID.
    assigned_idx, assigned_rec = find_available_equipment(requested_eid)
    if assigned_rec is None:
        if is_reservation:
            print(f"ยังไม่ว่าง: {requested_eid} | {requested_rec['name']} — คงคิวจองไว้ได้")
            return
        print(f"อุปกรณ์ ID {requested_eid} ไม่มีชิ้นว่าง ไม่สามารถอนุมัติคำขอนี้ได้")
        append_activity(OP_BORROW_REJECT, requested_eid, bid, req["value"], req["rate"])
        return

    if approve:
        assigned_rec["borrower_id"] = bid
        write_equipment_at(assigned_idx, assigned_rec)
        requested_rec = assigned_rec
        append_activity(OP_BORROW_APPROVE, requested_eid, bid, req["value"], requested_rec["rate_per_day_thb"])
        append_activity(OP_BORROW, requested_eid, bid, req["value"], requested_rec["rate_per_day_thb"], timestamp=req["timestamp"])
        print(f"อนุมัติแล้ว — {requested_eid} ({requested_rec['name']}) ให้ {bid}")
    else:
        append_activity(OP_BORROW_REJECT, requested_eid, bid, req["value"], req["rate"])
        print("ปฏิเสธคำขอ/การจองแล้ว")
