# Polymarket Both-Sides Arbitrage Scanner (skeleton)

Bot quét thị trường Polymarket tìm cơ hội mua cả 2 phía (YES + NO) khi
tổng giá < $1 trừ phí. **Chỉ quét và log — chưa tự động đặt lệnh thật.**

## Chạy local

```bash
pip install -r requirements.txt
python polymarket_arb_bot.py          # chạy vòng lặp liên tục
python polymarket_arb_bot.py --once   # quét 1 lần, ghi ra opportunities.json
```

## Đưa lên GitHub để chạy tự động (miễn phí)

Máy chạy code của Claude không gọi được API Polymarket (giới hạn mạng),
nhưng GitHub Actions runner thì gọi được — nên cách nhanh nhất để có
kết quả "live" là đẩy repo này lên GitHub và để Actions tự chạy.

1. Tạo repo mới trên GitHub (trống, không cần README/gitignore mặc định).
2. Trong thư mục này, chạy:
   ```bash
   git init
   git add .
   git commit -m "Initial commit: Polymarket arb scanner skeleton"
   git branch -M main
   git remote add origin https://github.com/<username>/<ten-repo>.git
   git push -u origin main
   ```
3. Vào tab **Actions** trên GitHub → workflow "Quét cơ hội Polymarket" sẽ
   tự chạy mỗi 15 phút (chỉnh trong `.github/workflows/scan.yml`), hoặc
   bấm **Run workflow** để chạy ngay.
4. Sau mỗi lần chạy, vào phần **Artifacts** của run đó để tải
   `opportunities.json` — danh sách thị trường có edge dương tại thời
   điểm quét.

## Bước tiếp theo (nếu muốn tiến tới đặt lệnh thật)

- Cài `py-clob-client`, tạo API key trên Polymarket.
- Điền logic vào hàm `execute_both_sides()` trong `polymarket_arb_bot.py`.
- Bắt đầu với size rất nhỏ, có cơ chế hủy/hedge khi 1 chân lệnh không khớp.
- **Không** commit private key vào repo — dùng GitHub Secrets nếu chạy qua Actions.
