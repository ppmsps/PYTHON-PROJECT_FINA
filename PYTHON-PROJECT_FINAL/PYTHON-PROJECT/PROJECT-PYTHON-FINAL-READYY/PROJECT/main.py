import os
from data import initialize_files, set_change_hook
from staff import staff_menu, generate_report, generate_reports
from borrower import borrower_menu
from approver import approver_menu

SEED = [
('10001', 'Camera Sony FX6', 'Camera', 2025, 2500, 2),
('10002', 'Camera ARRI Alexa Mini', 'Camera', 2024, 4500, 1),
('10003', 'Camera Canon C70', 'Camera', 2024, 2200, 2),
('10004', 'Camera Sony FX3', 'Camera', 2024, 2000, 2),
('10005', 'Camera BMD Pocket 6K', 'Camera', 2024, 1800, 2),
('10006', 'Camera Blackmagic 6K Pro', 'Camera', 2025, 1900, 2),
('20001', 'Lens Cooke S4 35mm', 'Lens', 2025, 1800, 2),
('20002', 'Lens Sigma Cine 50mm T1.5', 'Lens', 2024, 1500, 1),
('20003', 'Zoom Lens 24-70mm', 'Lens', 2024, 1200, 2),
('20004', 'Lens Canon CN-E 85mm', 'Lens', 2024, 1600, 2),
('20005', 'Lens Sony 24-105mm', 'Lens', 2024, 1100, 2),
('20006', 'Lens Sigma 18-35mm', 'Lens', 2025, 1300, 2),
('30001', 'Light Aputure 600d Pro', 'Lighting', 2025, 1800, 2),
('30002', 'Light LED Panel 1x1', 'Lighting', 2024, 900, 1),
('30003', 'Softbox 120 cm', 'Lighting', 2024, 300, 2),
('30004', 'Light Aputure 300x', 'Lighting', 2024, 1200, 2),
('30005', 'Light RGB Tube', 'Lighting', 2024, 700, 2),
('30006', 'Light LED Fresnel', 'Lighting', 2025, 1000, 2),
('40001', 'Boom Mic Sennheiser MKH416', 'Audio', 2025, 900, 2),
('40002', 'Wireless Lavalier Mic', 'Audio', 2024, 800, 1),
('40003', 'Recorder Zoom F8', 'Audio', 2024, 1200, 2),
('40004', 'Shotgun Mic NTG5', 'Audio', 2024, 850, 2),
('40005', 'Wireless Mic Set 2-Ch', 'Audio', 2024, 1000, 2),
('40006', 'Boom Mic RODE NTG3', 'Audio', 2025, 950, 2),
('50001', 'Tripod Fluid Head', 'Support', 2025, 500, 2),
('50002', 'Dolly Track 3 m', 'Support', 2024, 1000, 1),
('50003', 'Gimbal DJI RS 3 Pro', 'Support', 2024, 1200, 2),
('50004', 'Light Stand Heavy Duty', 'Support', 2024, 450, 2),
('50005', 'C-Stand', 'Support', 2024, 550, 2),
('50006', 'Tripod Carbon Fiber', 'Support', 2025, 750, 2),
('60001', 'V-Mount Battery 150Wh', 'Power', 2025, 500, 2),
('60002', 'Battery Charger 4-Ch', 'Power', 2024, 450, 1),
('60003', 'V-Mount Battery 98Wh', 'Power', 2024, 400, 2),
('60004', 'Power Station', 'Power', 2024, 900, 2),
('60005', 'AC Power Kit', 'Power', 2024, 600, 2),
('70001', 'Monitor SmallHD 17in', 'Monitor', 2025, 1500, 2),
('70002', 'Wireless Video Teradek', 'Monitor', 2024, 2500, 1),
('70003', 'Monitor Feelworld 7in', 'Monitor', 2024, 800, 2),
('70004', 'Monitor Atomos Ninja', 'Monitor', 2024, 1400, 2),
('70005', 'Video Transmitter', 'Monitor', 2024, 1800, 2),
('80001', 'Green Screen', 'Set', 2025, 700, 2),
('80002', 'White Backdrop 3x6 m', 'Set', 2024, 600, 1),
('80003', 'Black Backdrop 3x6 m', 'Set', 2024, 600, 2),
('80004', 'Product Shooting Table', 'Set', 2024, 400, 2),
('80005', 'Reflector 5-in-1 Set', 'Set', 2024, 350, 2),
('90001', 'Walkie-Talkie', 'Comms', 2025, 400, 2),
('90002', 'Radio Headset', 'Comms', 2024, 150, 1),
('90003', 'Intercom Set', 'Comms', 2024, 900, 2),
('90004', 'Long-Range Radio', 'Comms', 2024, 500, 2),
('90005', 'Production Headset Set', 'Comms', 2024, 350, 2)
]


def seed_equipment():
    from data import read_equipment, append_equipment, append_borrower
    if read_equipment(): return
    for eid,name,cat,year,rate,cond in SEED:
        append_equipment({"equip_id":eid,"name":name,"category":cat,"year":year,
                          "rate_per_day_thb":rate,"condition":cond,"borrower_id":"","is_deleted":False})
    from data import read_borrowers
    if not read_borrowers():
        for bid,name in [("P001","ฝ่ายกล้อง"),("P002","ฝ่ายเสียง"),("P003","ฝ่ายไฟ"),("P004","ฝ่าย Production")]:
            append_borrower(bid,name)


def main():
    initialize_files()
    seed_equipment()
    generate_reports(verbose=False)
    # Every write to a .bin file refreshes all 3 TXT reports automatically.
    set_change_hook(lambda: generate_reports(verbose=False))
    while True:
        print("\n==================================================")
        print("      MOVIE PRODUCTION EQUIPMENT SYSTEM")
        print("==================================================")
        print("1) Staff / Admin  - จัดการอุปกรณ์ + CRUD + รายงาน")
        print("2) Borrower       - ดูอุปกรณ์ + ยื่นคำขอ + คืน")
        print("3) Approver       - พิจารณาคำขอยืม/จอง")
        print("0) Exit")
        c = input("เลือกเมนู: ").strip()
        if c == "1": staff_menu()
        elif c == "2": borrower_menu()
        elif c == "3": approver_menu()
        elif c == "0":
            try: generate_report()
            finally: print("ปิดโปรแกรมอย่างปลอดภัย")
            break
        else: print("กรุณาเลือก 0-3")

if __name__ == "__main__": main()
