"""
Polymarket "Both-Sides" Arbitrage Bot — Skeleton / Architecture Draft
======================================================================

Ý tưởng cốt lõi:
    Trên mỗi thị trường binary (YES/NO), nếu:
        best_ask(YES) + best_ask(NO) < 1.00 - phi_giao_dich
    thì mua cả 2 phía với đúng số lượng bằng nhau sẽ đảm bảo lãi
    (bằng 1.00 - tong_chi_phi) khi thị trường resolve, bất kể bên nào thắng.

Bot này CHƯA đặt lệnh thật — nó mới dừng ở bước quét + tính edge +
log cơ hội. Phần đặt lệnh (execute_both_sides) để trống, bạn cần:
    1. Đăng ký API key trên Polymarket (CLOB API)
    2. Cài đặt py-clob-client
    3. Tự điền logic ký lệnh + gửi lệnh vào chỗ TODO

Cấu trúc file:
    1. Config
    2. Lấy danh sách market đang mở (Gamma API - public, không cần key)
    3. Lấy order book cho từng market (CLOB API - public)
    4. Tính edge sau phí
    5. Lọc theo thanh khoản đủ để fill cả 2 chân
    6. Log / cảnh báo cơ hội (chưa tự động đặt lệnh)
"""

import time
import json
import sys
import requests
from dataclasses import dataclass, asdict
from typing import Optional

# ---------------------------------------------------------------------
# 1. CONFIG
# ---------------------------------------------------------------------

GAMMA_API = "https://gamma-api.polymarket.com"
CLOB_API = "https://clob.polymarket.com"

FEE_RATE = 0.02          # phí ước tính mỗi bên, tự điều chỉnh theo thực tế
MIN_EDGE = 0.015         # chỉ báo cơ hội khi lãi ròng ước tính > 1.5%
MIN_LIQUIDITY_USD = 50   # bỏ qua market có order book quá mỏng
SCAN_INTERVAL_SEC = 15   # quét lại sau mỗi X giây
MAX_MARKETS_PER_SCAN = 200


@dataclass
class Opportunity:
    market_question: str
    condition_id: str
    yes_ask: float
    no_ask: float
    total_cost: float
    net_edge: float
    max_size_usd: float


# ---------------------------------------------------------------------
# 2. LẤY DANH SÁCH MARKET ĐANG MỞ
# ---------------------------------------------------------------------

def get_active_markets(limit: int = MAX_MARKETS_PER_SCAN) -> list[dict]:
    """Lấy các market binary đang active + chưa đóng từ Gamma API."""
    params = {
        "active": "true",
        "closed": "false",
        "limit": limit,
    }
    resp = requests.get(f"{GAMMA_API}/markets", params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------
# 3. LẤY ORDER BOOK CHO 1 MARKET
# ---------------------------------------------------------------------

def get_order_book(token_id: str) -> Optional[dict]:
    """Lấy order book (bids/asks) cho 1 token (YES hoặc NO) từ CLOB API."""
    try:
        resp = requests.get(f"{CLOB_API}/book", params={"token_id": token_id}, timeout=5)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None


def best_ask_and_depth(book: dict, target_usd: float) -> tuple[Optional[float], float]:
    """
    Trả về (giá ask tốt nhất, tổng USD có thể fill ở mức giá đó trở xuống
    cho tới khi đạt target_usd). Đơn giản hóa: chỉ nhìn vào vài mức đầu.
    """
    asks = book.get("asks", [])
    if not asks:
        return None, 0.0
    asks_sorted = sorted(asks, key=lambda x: float(x["price"]))
    best_price = float(asks_sorted[0]["price"])
    filled_usd = 0.0
    for level in asks_sorted:
        price = float(level["price"])
        size = float(level["size"])
        filled_usd += price * size
        if filled_usd >= target_usd:
            break
    return best_price, filled_usd


# ---------------------------------------------------------------------
# 4 + 5. TÍNH EDGE VÀ LỌC THEO THANH KHOẢN
# ---------------------------------------------------------------------

def scan_for_opportunities() -> list[Opportunity]:
    opportunities = []
    markets = get_active_markets()

    for m in markets:
        try:
            tokens = m.get("clobTokenIds")
            if not tokens or len(tokens) != 2:
                continue  # chỉ xử lý market binary YES/NO

            yes_token_id, no_token_id = tokens

            yes_book = get_order_book(yes_token_id)
            no_book = get_order_book(no_token_id)
            if not yes_book or not no_book:
                continue

            yes_ask, yes_depth = best_ask_and_depth(yes_book, MIN_LIQUIDITY_USD)
            no_ask, no_depth = best_ask_and_depth(no_book, MIN_LIQUIDITY_USD)

            if yes_ask is None or no_ask is None:
                continue

            total_cost = yes_ask + no_ask
            net_edge = 1.0 - total_cost - (2 * FEE_RATE * total_cost)

            if net_edge > MIN_EDGE:
                max_size = min(yes_depth, no_depth)
                if max_size >= MIN_LIQUIDITY_USD:
                    opportunities.append(Opportunity(
                        market_question=m.get("question", "?"),
                        condition_id=m.get("conditionId", "?"),
                        yes_ask=yes_ask,
                        no_ask=no_ask,
                        total_cost=total_cost,
                        net_edge=net_edge,
                        max_size_usd=max_size,
                    ))

        except (KeyError, ValueError, TypeError):
            continue  # bỏ qua market lỗi dữ liệu, không crash cả vòng quét

    return sorted(opportunities, key=lambda o: o.net_edge, reverse=True)


# ---------------------------------------------------------------------
# 6. THỰC THI (CHƯA BẬT — CẦN BẠN TỰ ĐIỀN)
# ---------------------------------------------------------------------

def execute_both_sides(opp: Opportunity, size_usd: float):
    """
    TODO — chỗ này cần py-clob-client để ký và gửi lệnh thật:

        from py_clob_client.client import ClobClient
        client = ClobClient(host=CLOB_API, key=PRIVATE_KEY, chain_id=137)
        client.create_and_post_order(...)  # cho cả yes_token và no_token

    Lưu ý rủi ro "leg risk": nếu chân 1 khớp mà chân 2 trượt giá/không khớp,
    bạn cần logic hủy/hedge lại ngay, không được để lệnh treo 1 chân.
    """
    print(f"[SẼ ĐẶT LỆNH] {opp.market_question[:60]}... "
          f"| edge={opp.net_edge:.2%} | size=${size_usd:.2f}")
    # KHÔNG gửi lệnh thật ở bản skeleton này.


# ---------------------------------------------------------------------
# MAIN LOOP
# ---------------------------------------------------------------------

def run_single_scan(output_file: Optional[str] = None):
    """Quét 1 lần rồi thoát — dùng cho GitHub Actions (không chạy vòng lặp vô hạn)."""
    opps = scan_for_opportunities()
    if opps:
        print(f"--- Tìm thấy {len(opps)} cơ hội (edge > {MIN_EDGE:.1%}) ---")
        for o in opps[:20]:
            print(f"  {o.market_question[:55]:55s} "
                  f"edge={o.net_edge:6.2%}  cost={o.total_cost:.3f}  "
                  f"depth=${o.max_size_usd:.0f}")
    else:
        print("Không có cơ hội nào đạt ngưỡng lúc này.")

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump([asdict(o) for o in opps], f, ensure_ascii=False, indent=2)
        print(f"\nĐã ghi kết quả vào {output_file}")

    return opps


def main():
    if "--once" in sys.argv:
        # dùng cho GitHub Actions: quét 1 lần, ghi kết quả ra file, rồi thoát
        run_single_scan(output_file="opportunities.json")
        return

    print("Bắt đầu quét cơ hội arbitrage Polymarket (chế độ chỉ log, vòng lặp)...\n")
    while True:
        run_single_scan()
        print(f"\nChờ {SCAN_INTERVAL_SEC}s rồi quét lại...\n")
        time.sleep(SCAN_INTERVAL_SEC)


if __name__ == "__main__":
    main()
