# Kế hoạch benchmark model

Mục tiêu: với mỗi bước dùng AI, tìm model **rẻ nhất mà chất lượng vẫn đủ**, bằng số đo chứ không đoán.
Kết quả: [`results/benchmark_models.md`](results/benchmark_models.md). Chạy lại: `uv run koc bench --run-id final`.

## 1. Ba bước được đo

| Bước | Việc model làm | Input | Output (JSON có schema) |
|---|---|---|---|
| **Screen** (Stage 4) | Phân loại creator: cá nhân hay shop/brand/team, ngách, mức phù hợp với sản phẩm, rủi ro | bio + 12 tiêu đề video + shop + sản phẩm, 8 creator/lần gọi | `account_kind`, `primary_niche`, `topic_relevance` 0–10, `brand_safety_flags`, `competitor_brands` |
| **Video** (Stage 5) | Xem 1 video/creator: có lộ mặt, có dùng thử trên da, hook, claim rủi ro | Claude, DeepSeek Flash: 6 khung hình 384px + phụ đề. Gemini: 60 giây video gốc có tiếng | `is_on_topic`, `face_on_camera`, `product_demo_on_skin`, `hook_strength`, bằng chứng theo mốc thời gian |
| **Rationale** (Stage 7) | Viết lý do đề xuất bộ KOC, trích mã bằng chứng | JSON điểm + bằng chứng của bộ KOC | lý do, mã bằng chứng, rủi ro, gợi ý brief |

Bước chọn KOC (Stage 6) là **thuật toán tất định** (điểm + ràng buộc ngân sách + đa dạng), không dùng LLM.
Mọi model nhận **cùng input** lấy từ run `final` (cùng danh sách creator, cùng video).

## 2. Ma trận model

| Hãng | Model | Giá in/out ($/1M) | Bước tham gia |
|---|---|---|---|
| Anthropic | claude-haiku-5-5 | 0.10 / 0.50 | cả 3 |
| Anthropic | claude-sonnet-5-5 | 2.00 / 10.00 | cả 3 |
| Anthropic | claude-opus-5-5 | 4.00 / 20.00 | cả 3 (+ tham chiếu) |
| Google | gemini-3.5-flash-lite | 0.30 / 2.50 | cả 3 (thay gemini-2.5-flash-lite: Google báo không còn mở cho tài khoản mới) |
| Google | gemini-3.1-flash-lite | 0.25 / 1.50 | cả 3 |
| Google | gemini-3.8-flash | 0.75 / 3.75 | cả 3 |
| Google | gemini-4-carbon | 2.00 / 10.00 | cả 3 (+ tham chiếu) |
| DeepSeek | deepseek-flash (V4.1) | 0.30 / 1.20 | cả 3 |
| DeepSeek | deepseek-v4-pro | 1.32 / 3.96 | screen, rationale (không đọc ảnh) (+ tham chiếu) |

Tất cả chạy effort `low` (rationale: `medium`); tham chiếu chạy effort `high`.

## 3. Số đo

**Chi phí và tốc độ** (tự động, bảng `llm_calls` trong SQLite): token vào/ra (gồm thinking), USD mỗi item,
USD dự phóng cho 500 KOC theo tỷ lệ phễu thực tế, thời gian chạy.

**Chất lượng:**
- *Độ khớp với nhãn tham chiếu.* Tham chiếu = **đồng thuận** của model mạnh nhất mỗi hãng (Opus 5.5, Gemini 4 Carbon,
  DeepSeek V4 Pro) ở effort `high`: trường phân loại lấy đa số, trường điểm lấy trung vị. Dùng đồng thuận nhiều hãng
  để không thiên vị một hãng. Trường phân loại tính % trùng; trường điểm tính sai số tuyệt đối trung bình (MAE).
- *Nhãn vàng do người gán:* `koc bench` tạo `eval/golden_labels_TEMPLATE.csv` (handle + link video, cột nhãn trống).
  Người học xem kênh/video, điền `account_kind`, `face_on_camera`, `product_demo_on_skin`, lưu thành
  `eval/golden_labels.csv` rồi chạy lại bench. **Nhãn phải do người gán, không để AI gán.**
- *Rationale:* tỷ lệ trích dẫn hợp lệ (code kiểm mã bằng chứng có thật trong input của đúng KOC), độ dài.
- *Ảnh hưởng tới quyết định:* nếu dùng model X cho cả screen + video, bộ KOC được chọn trùng bao nhiêu với pipeline (Jaccard).

## 4. Luật chọn model

Với mỗi bước (`koc.benchmark.recommend`, tham số trong `config/models.toml` mục `[benchmark]`):
1. Chọn model **rẻ nhất** có độ khớp ≥ 90% so với tham chiếu và 0 lỗi.
2. **Nâng cấp** lên model khớp cao hơn nếu hơn ≥ 5 điểm % mà chỉ tốn thêm ≤ $2 cho 500 KOC.
3. Bước viết lý do: rẻ nhất có 100% mã bằng chứng hợp lệ (văn phong cần người đọc mẫu).

Không model rẻ nào đạt thì dùng model đắt hơn **chỉ cho bước đó** (định tuyến theo bước, có `fallback` khi thiếu API key).

**Kết quả (đo lại 2026-11-18):** sàng lọc = Gemini 3.8 Flash (91%; Claude Haiku 84%), xem video = Gemini 3.5 Flash-Lite
(97%, nâng cấp từ Haiku 91% với +$1.79/500 KOC), viết lý do = Gemini 3.1 Flash-Lite. Chi phí dự phóng $4.81 / 500 KOC
(định tuyến của run `final-haiku` $4.82, toàn Opus $51.05). Đo lại toàn bộ vì lần đo đầu (2026-11-17: Haiku 94%,
3.1 Flash-Lite 98%) có 2 lỗi: adapter Gemini bỏ qua `effort`, và cache của lần đo cũ được tạo trước khi code đổi định dạng input.
Gemini 4 Carbon ở effort high cần chừa chỗ cho token suy nghĩ (đã sửa trong adapter), nếu không sẽ hết token ra trước khi viết JSON.

## 5. Giới hạn của cách đo

- Nhãn tham chiếu là của model, không phải sự thật: hữu ích để so tương đối giữa các model, cần nhãn người để kết luận tuyệt đối.
- Bước video không hoàn toàn công bằng: Gemini nghe được tiếng, Claude/DeepSeek chỉ thấy 6 khung hình (+ phụ đề nếu có).
  Đây là khác biệt thật về năng lực mà hệ thống phải tính đến, nên vẫn so trên cùng bài đăng.
- 1 lần chạy mỗi biến thể: chưa đo độ dao động giữa các lần chạy của cùng model.
