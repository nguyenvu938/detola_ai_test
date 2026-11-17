# Đo khả năng mở rộng: 5 → 50 → 500 KOC

> **Dữ liệu đã lưu (cache)**, tạo lúc 2026-11-17 22:17 bằng `uv run koc scale-test` (0 đồng, không cần API key).
> Chạy NGUYÊN pipeline thật trên dữ liệu Kalodata **giả lập** với model **giả** (không gọi mạng). Số người qua phễu, số lần gọi model, thời gian code, bài chọn, SQLite, phục hồi là **đo thật**. Token, USD, thời gian chờ model là **dự phóng** = số lần gọi × số đo thật mỗi item ở run `final` (screen: claude-haiku-5-5, video: gemini-3.1-flash-lite, rationale: gemini-3.1-flash-lite). Kết quả giả không đo chất lượng (xem benchmark).

| | **5 KOC** | **50 KOC** | **500 KOC** |
|---|---|---|---|
| Ngân sách booking | 30 tr | 300 tr | 3,000 tr |
| Creator đầu vào (giả lập) | 125 | 1,250 | 12,500 |
| S1 qua luật (0 đồng) | 80 | 781 | 7,764 |
| S2 lấy chi tiết Kalodata (12 × n) | 60 | 600 | 6,000 |
| S3 qua chỉ số khán giả (0 đồng) | 46 | 487 | 4,837 |
| S4 LLM sàng lọc: người / lần gọi | 16 / 2 | 120 / 15 | 1,232 / 154 |
| S5 AI xem video: người = lần gọi | 10 | 100 | 1,000 |
| S7 viết lý do: lần gọi (10 KOC/lần) | 1 | 5 | 50 |
| **Chọn được** / chi phí booking | **5** / 29.2 tr | **50** / 298.0 tr | **500** / 2,814.0 tr |
| Tổng lần gọi model | 13 (10% số creator đầu vào) | 120 (10% số creator đầu vào) | 1,204 (10% số creator đầu vào) |
| Token vào / ra (dự phóng) | 0.07M / 0.01M | 0.64M / 0.12M | 6.41M / 1.19M |
| **Chi phí AI (dự phóng)** | **$0.03** ($0.0050/KOC) | **$0.23** ($0.0047/KOC) | **$2.36** ($0.0047/KOC) |
| Chờ model, song song 4 / 16 (dự phóng) | 49 giây / 33 giây | 5 phút / 86 giây | 49 phút / 13 phút |
| Kalodata API: lần gọi / điểm / thời gian ở 1 req/s | 60 / 6.0 / 60 giây | 600 / 60.0 / 10 phút | 6,000 / 600.0 / 1.7 giờ |
| Thời gian phần code (đo thật) | < 0.1 giây | 1.1 giây | 18.0 giây |
| Giải bài chọn trong ngân sách (đo thật) | < 1 ms | 1 ms | 2 ms |
| SQLite (checkpoint + cache) | 0.4 MB | 3.2 MB | 31.0 MB |

**Phục hồi ở quy mô 50 KOC:** cho "sập" sau 60 lần gọi model rồi chạy lại cùng run: 120 lần gọi trả tiền (chạy liền một lèo: 120), **0 item bị gọi lặp**, chọn ra 50 KOC (trùng bộ chọn của lần chạy liền).

Cách đọc:
- Mọi tầng phễu tỷ lệ với số KOC (`*_per_koc` trong `config/campaign.toml`), nên chi phí AI tăng **tuyến tính** theo số KOC, không theo số creator đầu vào: phần lớn creator bị loại ở các bước 0 đồng.
- Nút thắt thời gian ở 500 KOC là **lấy chi tiết Kalodata** (giới hạn 10 request/10 giây) và **chờ model** (tăng `concurrency` trong `config/models.toml` theo hạn mức RPM của tài khoản). Code chỉ chiếm vài chục giây.
- Run 500 KOC cần nâng `max_usd_per_run` (mặc định $1, chặn hóa đơn bất ngờ) lên trên mức dự phóng.
- Bài chọn: n ≤ 6 vét cạn (chính xác); n lớn dùng nhân tử Lagrange + đổi chỗ (test so với vét cạn ở cỡ nhỏ).
