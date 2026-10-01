#!/usr/bin/env python3
"""
終端機記帳系統
用法：
  python3 k账.py          → 互動式選單
  python3 帳.py add       → 快速新增
  python3 帳.py list      → 查看記錄
  python3 帳.py summary   → 月份統計
  python3 帳.py export    → 匯出 CSV
"""

import json
import os
import sys
import csv
from datetime import datetime, date
from pathlib import Path

# ── 資料檔案位置 ──────────────────────────────────────────────
DATA_FILE = Path.home() / ".accounting" / "records.json"
DATA_FILE.parent.mkdir(exist_ok=True)

# ── 分類與選項 ────────────────────────────────────────────────
CATEGORIES = {
    "支出": ["餐飲", "交通", "住房", "購物", "娛樂", "醫療", "教育", "旅遊", "其他支出"],
    "收入": ["薪資", "投資收益", "其他收入"],
}
PAYMENT_METHODS = ["現金", "信用卡", "LINE Pay", "街口支付", "轉帳", "其他"]
BANKS           = ["台銀", "國泰", "玉山", "台新", "元大", "富邦", "星展", "聯邦", "（略過）"]

# ── ANSI 顏色 ─────────────────────────────────────────────────
R  = "\033[0m"       # reset
B  = "\033[1m"       # bold
GR = "\033[32m"      # green
RD = "\033[31m"      # red
YL = "\033[33m"      # yellow
CY = "\033[36m"      # cyan
BL = "\033[34m"      # blue
DM = "\033[2m"       # dim
BG_DARK = "\033[40m" # dark bg

def clr():
    os.system("clear" if os.name == "posix" else "cls")

def banner():
    print(f"""
{BL}{B}╔══════════════════════════════════════╗
║         💰  終端機記帳系統           ║
╚══════════════════════════════════════╝{R}
{DM}資料存於：{DATA_FILE}{R}
""")

def hr(char="─", width=42):
    print(f"{DM}{char * width}{R}")

# ── 資料讀寫 ──────────────────────────────────────────────────
def load() -> list:
    if not DATA_FILE.exists():
        return []
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))

def save(records: list):
    DATA_FILE.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

# ── 輸入工具 ──────────────────────────────────────────────────
def pick(prompt: str, options: list, allow_skip=False) -> str:
    """方向鍵選單"""
    print(f"\n{B}{prompt}{R}")
    for i, opt in enumerate(options, 1):
        print(f"  {CY}{i:2}.{R} {opt}")
    if allow_skip:
        print(f"  {DM} 0.  略過{R}")
    while True:
        raw = input(f"\n{YL}請輸入編號：{R}").strip()
        if allow_skip and raw == "0":
            return ""
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        print(f"{RD}請輸入 1~{len(options)} 的數字{R}")

def ask(prompt: str, default="") -> str:
    hint = f"{DM}（直接 Enter 略過）{R}" if not default else f"{DM}（預設：{default}）{R}"
    val = input(f"{B}{prompt}{R} {hint}：").strip()
    return val if val else default

def ask_amount() -> float:
    while True:
        raw = input(f"\n{B}金額（NT$）{R}：").strip().replace(",", "")
        try:
            amt = float(raw)
            if amt > 0:
                return amt
        except ValueError:
            pass
        print(f"{RD}請輸入有效數字{R}")

# ── 新增記錄 ──────────────────────────────────────────────────
def add_record(quick_args=None):
    clr()
    banner()
    print(f"{B}✏️  新增記帳{R}")
    hr()

    # 快速指令模式：帳.py add 支出 餐飲 早餐 85 現金 玉山
    if quick_args:
        try:
            typ, cat, desc, amt = quick_args[0], quick_args[1], quick_args[2], float(quick_args[3])
            pay   = quick_args[4] if len(quick_args) > 4 else "現金"
            bank  = quick_args[5] if len(quick_args) > 5 else ""
            note  = quick_args[6] if len(quick_args) > 6 else ""
        except (IndexError, ValueError):
            print(f"{RD}格式：add 類型 分類 說明 金額 [付款方式] [銀行] [備註]{R}")
            print(f"例：add 支出 餐飲 早餐 85 現金 玉山")
            return
    else:
        typ  = pick("類型", ["支出", "收入"])
        cat  = pick("分類", CATEGORIES[typ])
        desc = ask("項目說明")
        amt  = ask_amount()
        pay  = pick("付款方式", PAYMENT_METHODS)
        bank_choice = pick("銀行", BANKS, allow_skip=False)
        bank = "" if bank_choice == "（略過）" else bank_choice
        note = ask("備註")

    record = {
        "id":       len(load()) + 1,
        "日期":     date.today().isoformat(),
        "類型":     typ,
        "分類":     cat,
        "項目說明": desc,
        "金額":     amt,
        "付款方式": pay,
        "銀行":     bank,
        "備註":     note,
    }

    records = load()
    records.append(record)
    save(records)

    sign = f"{GR}+{R}" if typ == "收入" else f"{RD}-{R}"
    print(f"""
{GR}{B}✅ 已記錄！{R}
  {DM}日期{R}  {record['日期']}
  {DM}分類{R}  {record['分類']}  {DM}|{R}  {record['項目說明']}
  {DM}金額{R}  {sign} NT$ {record['金額']:,.0f}
  {DM}銀行{R}  {record['銀行'] or '—'}  {DM}|{R}  {record['付款方式']}
""")

# ── 查看記錄 ──────────────────────────────────────────────────
def list_records(n=20):
    clr()
    banner()
    records = load()
    if not records:
        print(f"{YL}尚無記錄。{R}")
        return

    # 預設顯示最近 n 筆
    recent = records[-n:][::-1]
    print(f"{B}📋 最近 {len(recent)} 筆記錄{R}  {DM}（共 {len(records)} 筆）{R}\n")

    print(f"{DM}{'ID':>4}  {'日期':<12} {'類型':<4} {'分類':<8} {'說明':<16} {'金額':>8}  {'銀行':<6}{R}")
    hr()

    for r in recent:
        color = GR if r["類型"] == "收入" else RD
        sign  = "+" if r["類型"] == "收入" else "-"
        bank  = r.get("銀行", "") or "—"
        desc  = r["項目說明"][:14] + ("…" if len(r["項目說明"]) > 14 else "")
        print(
            f"{DM}{r['id']:>4}{R}  "
            f"{r['日期']:<12} "
            f"{color}{r['類型']:<4}{R} "
            f"{r['分類']:<8} "
            f"{desc:<16} "
            f"{color}{sign}NT${r['金額']:>7,.0f}{R}  "
            f"{DM}{bank:<6}{R}"
        )
    hr()

# ── 月份統計 ──────────────────────────────────────────────────
def summary(month: str = None):
    clr()
    banner()
    records = load()
    if not records:
        print(f"{YL}尚無記錄。{R}")
        return

    if not month:
        month = date.today().strftime("%Y-%m")

    filtered = [r for r in records if r["日期"].startswith(month)]
    if not filtered:
        print(f"{YL}本月（{month}）尚無記錄。{R}")
        return

    income  = sum(r["金額"] for r in filtered if r["類型"] == "收入")
    expense = sum(r["金額"] for r in filtered if r["類型"] == "支出")
    balance = income - expense
    rate    = (balance / income * 100) if income > 0 else 0

    print(f"{B}📊 {month} 月份統計{R}\n")
    hr()
    print(f"  {GR}{B}總收入{R}   NT$ {income:>10,.0f}")
    print(f"  {RD}{B}總支出{R}   NT$ {expense:>10,.0f}")
    print(f"  {CY}{B}結　餘{R}   NT$ {balance:>10,.0f}")
    print(f"  {YL}{B}儲蓄率{R}   {rate:>10.1f}%")
    hr()

    # 各分類加總
    print(f"\n{B}支出分類明細{R}")
    cats = {}
    for r in filtered:
        if r["類型"] == "支出":
            cats[r["分類"]] = cats.get(r["分類"], 0) + r["金額"]
    for cat, amt in sorted(cats.items(), key=lambda x: -x[1]):
        bar_len = int(amt / max(cats.values()) * 20) if cats else 0
        bar = "█" * bar_len + "░" * (20 - bar_len)
        pct = amt / expense * 100 if expense > 0 else 0
        print(f"  {cat:<8} {RD}{bar}{R} NT${amt:>8,.0f}  {DM}{pct:.1f}%{R}")

    # 各銀行加總
    print(f"\n{B}銀行使用統計{R}")
    banks = {}
    for r in filtered:
        b = r.get("銀行") or "未指定"
        banks[b] = banks.get(b, 0) + r["金額"]
    for bank, amt in sorted(banks.items(), key=lambda x: -x[1]):
        print(f"  {BL}{bank:<6}{R}  NT$ {amt:>8,.0f}")
    hr()

# ── 匯出 CSV ──────────────────────────────────────────────────
def export_csv():
    records = load()
    if not records:
        print(f"{YL}尚無記錄可匯出。{R}")
        return
    out = Path.home() / "Desktop" / f"記帳_{date.today()}.csv"
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["id","日期","類型","分類","項目說明","金額","付款方式","銀行","備註"])
        w.writeheader()
        w.writerows(records)
    print(f"{GR}✅ 已匯出至桌面：{out.name}{R}")

# ── 刪除記錄 ──────────────────────────────────────────────────
def delete_record():
    list_records()
    raw = input(f"\n{YL}輸入要刪除的 ID（輸入 0 取消）：{R}").strip()
    if raw == "0" or not raw.isdigit():
        return
    target_id = int(raw)
    records = load()
    new = [r for r in records if r["id"] != target_id]
    if len(new) == len(records):
        print(f"{RD}找不到 ID {target_id}{R}")
        return
    save(new)
    print(f"{GR}✅ 已刪除 ID {target_id}{R}")

# ── 主選單 ────────────────────────────────────────────────────
def main_menu():
    while True:
        clr()
        banner()
        today_records = [r for r in load() if r["日期"] == date.today().isoformat()]
        today_expense = sum(r["金額"] for r in today_records if r["類型"] == "支出")
        today_income  = sum(r["金額"] for r in today_records if r["類型"] == "收入")

        print(f"  今日支出  {RD}NT$ {today_expense:,.0f}{R}   今日收入  {GR}NT$ {today_income:,.0f}{R}\n")
        hr()
        print(f"  {CY}1.{R}  ✏️   新增記帳")
        print(f"  {CY}2.{R}  📋  查看記錄")
        print(f"  {CY}3.{R}  📊  月份統計")
        print(f"  {CY}4.{R}  📤  匯出 CSV")
        print(f"  {CY}5.{R}  🗑️   刪除記錄")
        print(f"  {CY}0.{R}  {DM}離開{R}")
        hr()

        choice = input(f"\n{YL}請選擇：{R}").strip()
        if   choice == "1": add_record()
        elif choice == "2": list_records(); input(f"\n{DM}按 Enter 返回...{R}")
        elif choice == "3": summary();       input(f"\n{DM}按 Enter 返回...{R}")
        elif choice == "4": export_csv();    input(f"\n{DM}按 Enter 返回...{R}")
        elif choice == "5": delete_record(); input(f"\n{DM}按 Enter 返回...{R}")
        elif choice == "0": print(f"\n{DM}掰掰！{R}\n"); break

# ── 進入點 ────────────────────────────────────────────────────
if __name__ == "__main__":
    args = sys.argv[1:]

    if not args:
        main_menu()
    elif args[0] == "add":
        add_record(args[1:] if len(args) > 1 else None)
    elif args[0] == "list":
        list_records()
    elif args[0] == "summary":
        month = args[1] if len(args) > 1 else None
        summary(month)
    elif args[0] == "export":
        export_csv()
    else:
        print(f"""
{B}用法：{R}
  python3 帳.py              互動式選單
  python3 帳.py add          新增（互動）
  python3 帳.py add 支出 餐飲 早餐 85 現金 玉山
  python3 帳.py list         查看最近記錄
  python3 帳.py summary      本月統計
  python3 帳.py summary 2025-03   指定月份
  python3 帳.py export       匯出 CSV 到桌面
""")
