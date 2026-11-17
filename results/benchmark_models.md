# Benchmark model – input của run `final-haiku`

> **Dữ liệu đã lưu (cache).** Benchmark chạy lúc 2026-11-17 21:15, tốn $2.11 cho 31 biến thể (bước × model × effort). Đọc file này không gọi model, không cần API key. Chạy lại: `uv run koc bench --run-id final-haiku` (cần key Anthropic, Gemini, DeepSeek; ~$2, ~40 phút).

## Đề xuất model cho từng bước

Luật: (1) chọn model **rẻ nhất** có độ khớp tham chiếu ≥ 90% và không lỗi; (2) **nâng cấp** lên model khớp cao hơn nếu hơn ≥ 5 điểm % mà chỉ tốn thêm ≤ $2 cho 500 KOC; (3) bước viết lý do: rẻ nhất có 100% trích dẫn hợp lệ. Vì chi phí nhân lên theo số KOC, model đắt chỉ đáng dùng khi chất lượng tăng tương xứng.

| Bước | Đề xuất | Khớp tham chiếu | USD/item | USD cho 500 KOC | Độ trễ TB | Đang dùng | Lý do |
|---|---|---|---|---|---|---|---|
| Sàng lọc (text) | **claude-haiku-5-5** (low) | 94% | 0.00036 | 0.71 | 17.5s | claude-haiku-5-5 | rẻ nhất trong các model khớp tham chiếu ≥ 90%: khớp 94%, 0.00036 USD/item. Model khớp cao nhất là gemini-3.8-flash (100%), đắt hơn 6 lần nhưng chỉ hơn 6 điểm %; không model nào vừa hơn ≥ 5 điểm % vừa tốn thêm ≤ $2/500 KOC |
| Xem video | **gemini-3.1-flash-lite** (low) | 98% | 0.00173 | 1.95 | 8.9s | gemini-3.1-flash-lite | khớp 98%, cao hơn model rẻ nhất đạt ngưỡng (claude-haiku-5-5, 91%) 7 điểm % mà chỉ tốn thêm $1.27 cho 500 KOC (ngưỡng nâng cấp: ≥ 5 điểm %, ≤ $2). |
| Viết lý do | **gemini-3.1-flash-lite** (medium) | – | 0.00195 | 0.24 | 3.8s | gemini-3.1-flash-lite | rẻ nhất trong 9 model có 100% mã bằng chứng hợp lệ (kiểm bằng code). Văn phong không đo tự động được: nên đọc 1 bản mẫu trước khi đổi (results/benchmark_outputs.json). |

**Chi phí AI dự phóng cho 500 KOC** (theo tỷ lệ phễu thực tế của run):

| Phương án | Sàng lọc | Xem video | Viết lý do | USD cho 500 KOC |
|---|---|---|---|---|
| Đề xuất (theo benchmark) | claude-haiku-5-5 | gemini-3.1-flash-lite | gemini-3.1-flash-lite | 2.90 |
| Lúc chạy run final-haiku | claude-haiku-5-5 | claude-haiku-5-5 | claude-sonnet-5-5 | 5.77 |
| Toàn Claude Opus 5.5 | claude-opus-5-5 | claude-opus-5-5 | claude-opus-5-5 | 52.25 |
| Chỉ dùng Anthropic (Claude) | claude-haiku-5-5 | claude-haiku-5-5 | claude-haiku-5-5 | 1.65 |
| Chỉ dùng Google (Gemini) | gemini-3.8-flash | gemini-3.1-flash-lite | gemini-3.1-flash-lite | 6.67 |
| Chỉ dùng Google (Gemini), model rẻ nhất mỗi bước (có bước chưa đạt ngưỡng) | gemini-3.1-flash-lite | gemini-3.1-flash-lite | gemini-3.1-flash-lite | 2.98 |
| Chỉ dùng DeepSeek | deepseek-flash | deepseek-flash | deepseek-flash | 5.23 |

## So sánh theo hãng: Anthropic, Google, DeepSeek

Mỗi ô: model **rẻ nhất đạt ngưỡng** của hãng đó (không có thì model khớp cao nhất), độ khớp tham chiếu, chi phí cho 500 KOC, độ trễ mỗi lần gọi; dòng dưới: vì sao không dùng hãng đó so với model đề xuất.

| Bước | Anthropic (Claude) | Google (Gemini) | DeepSeek |
|---|---|---|---|
| Sàng lọc | claude-haiku-5-5<br>khớp 94% · $0.71 · 17.5s<br>**được chọn** | gemini-3.8-flash<br>khớp 100% · $4.48 · 29.2s<br>rẻ nhất: gemini-3.1-flash-lite 88%, $0.79, 3.8s<br>*đắt hơn 6.3 lần; chậm hơn 1.7 lần* | deepseek-flash<br>khớp 91% · $2.21 · 26.5s<br>khớp cao nhất: deepseek-v4-pro 97%, $8.11<br>*khớp thấp hơn 3 điểm %; đắt hơn 3.1 lần; chậm hơn 1.5 lần* |
| Xem video | claude-haiku-5-5<br>khớp 91% · $0.68 · 3.8s<br>6 khung hình + phụ đề<br>khớp cao nhất: claude-sonnet-5-5 97%, $13.92<br>*khớp thấp hơn 7 điểm %; rẻ hơn 2.9 lần; nhanh hơn 2.3 lần* | gemini-3.1-flash-lite<br>khớp 98% · $1.95 · 8.9s<br>video gốc có tiếng<br>khớp cao nhất: gemini-4-carbon 100%, $22.83<br>**được chọn** | deepseek-flash<br>khớp 91% · $2.13 · 7.0s<br>6 khung hình + phụ đề<br>*khớp thấp hơn 7 điểm %; chi phí ngang nhau* |
| Viết lý do | claude-haiku-5-5<br>trích dẫn 100% · $0.26 · 14.3s<br>*chi phí ngang nhau; chậm hơn 3.8 lần* | gemini-3.1-flash-lite<br>trích dẫn 100% · $0.24 · 3.8s<br>**được chọn** | deepseek-flash<br>trích dẫn 100% · $0.89 · 25.0s<br>*đắt hơn 3.7 lần; chậm hơn 6.6 lần* |
| **Chỉ dùng hãng này, 500 KOC** | **$1.65** | **$6.67** | **$5.23** |

**Sàng lọc: độ khớp từng trường** (model ở bảng trên, 16 creator; 1 lần lệch ≈ 6 điểm % của trường đó):

| Trường | Anthropic (Claude): claude-haiku-5-5 | Google (Gemini): gemini-3.8-flash | DeepSeek: deepseek-flash |
|---|---|---|---|
| Loại tài khoản | 100% | 100% | 100% |
| Ngách | 88% | 100% | 81% |

**Xem video: độ khớp từng trường** (model ở bảng trên, 9 video; 1 lần lệch ≈ 11 điểm % của trường đó):

| Trường | Anthropic (Claude): claude-haiku-5-5 | Google (Gemini): gemini-3.1-flash-lite | DeepSeek: deepseek-flash |
|---|---|---|---|
| Đúng chủ đề | 100% | 89% | 100% |
| Lộ mặt | 100% | 100% | 100% |
| Thử sản phẩm trên da | 71% | 100% | 71% |
| Kết cấu / độ hoàn thiện | 83% | 100% | 83% |
| Giới tính người dẫn | 100% | 100% | 100% |

**Tỷ lệ chi phí theo hãng trong phương án đề xuất (500 KOC):** Anthropic (Claude) 25% ($0.71) · Google (Gemini) 75% ($2.19). DeepSeek không được chọn ở bước nào (lý do từng bước ở bảng trên).


**Độ ổn định của bộ KOC** – mỗi KOC được bao nhiêu % biến thể chọn (mỗi biến thể dùng 1 model cho cả sàng lọc + xem video; phần định lượng giữ nguyên). KOC được ≥ 80% biến thể chọn là lựa chọn chắc chắn; thấp hơn là nhóm sát ngưỡng, kết quả phụ thuộc model:

| KOC | Tỷ lệ biến thể chọn | Có trong đề xuất của run `final-haiku` (input benchmark) |
|---|---|---|
| @_huongdaily | 90% | có |
| @lapiszuzu | 90% | có |
| @reviewkemchongnang | 90% | có |
| @trangriviuuu_01 | 80% | – |
| @emlylynguyen | 50% | – |
| @ngoc.matcha.review | 40% | có |
| @beobeo.21 | 10% | – |
| @mai.trinh.h | 10% | – |

Lưu ý về độ chính xác: tham chiếu là đồng thuận của 3 model mạnh (chưa phải nhãn người). Model thuộc nhóm tham chiếu (Opus, Gemini 4 Carbon, DeepSeek V4 Pro) có lợi thế khi so ở effort thấp. Cột "Khớp người" có số sau khi người gán nhãn `eval/golden_labels.csv`.

## Số liệu chi tiết

Cùng input, đổi model. **Tham chiếu** = đồng thuận (đa số / trung vị) của claude-opus-5-5, gemini-4-carbon, deepseek-v4-pro ở effort `high`. Chi phí cho 500 KOC = chi phí mỗi item × số item phải xử lý cho mỗi KOC được chọn theo phễu thực tế (screen 4.0, video 2.2 item/KOC). Claude và DeepSeek xem video qua 6 khung hình + phụ đề; Gemini xem video gốc có tiếng.

### screen

| Model | Effort | Lỗi | Thời gian (s) | Token vào | Token ra | USD | USD/item | USD cho 500 KOC | Khớp tham chiếu | MAE điểm | Khớp người |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-haiku-5-5 | low | 0 | 35.3 | 21,074 | 8,159 | 0.0057 | 0.00036 | 0.71 | 94% | topic_relevance=0.6 | – |
| gemini-3.1-flash-lite | low | 0 | 7.9 | 10,757 | 2,398 | 0.0063 | 0.00039 | 0.79 | 88% | topic_relevance=0.8 | – |
| gemini-3.5-flash-lite | low | 0 | 7.8 | 10,757 | 2,499 | 0.0095 | 0.00059 | 1.18 | 88% | topic_relevance=0.9 | – |
| deepseek-flash | low | 0 | 53.1 | 21,734 | 11,761 | 0.0177 | 0.00111 | 2.21 | 91% | topic_relevance=0.3 | – |
| gemini-3.8-flash | low | 0 | 58.7 | 10,757 | 7,396 | 0.0358 | 0.00224 | 4.48 | 100% | topic_relevance=0.1 | – |
| deepseek-v4-pro | low | 0 | 152.9 | 14,349 | 12,595 | 0.0649 | 0.00406 | 8.11 | 97% | topic_relevance=0.7 | – |
| claude-sonnet-5-5 | low | 0 | 19.6 | 21,074 | 2,961 | 0.0683 | 0.00427 | 8.53 | 88% | topic_relevance=0.8 | – |
| gemini-4-carbon | low | 0 | 296.0 | 11,738 | 4,561 | 0.0691 | 0.00432 | 8.64 | 97% | topic_relevance=0.2 | – |
| deepseek-v4-pro *(ref)* | high | 0 | 187.1 | 14,507 | 14,227 | 0.0712 | 0.00445 | 8.91 | 97% | topic_relevance=0.2 | – |
| gemini-4-carbon *(ref)* | high | 0 | 266.3 | 11,738 | 4,837 | 0.0718 | 0.00449 | 8.98 | 97% | topic_relevance=0.2 | – |
| claude-opus-5-5 | low | 0 | 24.2 | 21,074 | 2,838 | 0.1341 | 0.00838 | 16.76 | 91% | topic_relevance=0.4 | – |
| claude-opus-5-5 *(ref)* | high | 0 | 59.4 | 21,074 | 6,718 | 0.2117 | 0.01323 | 26.46 | 97% | topic_relevance=0.1 | – |

### video

| Model | Effort | Lỗi | Thời gian (s) | Token vào | Token ra | USD | USD/item | USD cho 500 KOC | Khớp tham chiếu | MAE điểm | Khớp người |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-haiku-5-5 | low | 0 | 15.8 | 41,392 | 5,747 | 0.0055 | 0.00061 | 0.68 | 91% | hook_strength=0.3, production_quality=0.7 | – |
| gemini-3.1-flash-lite | low | 0 | 27.3 | 43,852 | 3,081 | 0.0156 | 0.00173 | 1.95 | 98% | hook_strength=0.4, production_quality=0.3 | – |
| deepseek-flash | low | 0 | 27.7 | 24,231 | 12,175 | 0.0170 | 0.00189 | 2.13 | 91% | hook_strength=0.4, production_quality=0.3 | – |
| gemini-3.5-flash-lite | low | 0 | 28.3 | 43,852 | 3,016 | 0.0207 | 0.00230 | 2.59 | 98% | hook_strength=0.6, production_quality=0.2 | – |
| gemini-3.8-flash | low | 0 | 67.4 | 43,852 | 9,801 | 0.0696 | 0.00774 | 8.71 | 97% | hook_strength=0.4, production_quality=0.3 | – |
| claude-sonnet-5-5 | low | 0 | 18.9 | 41,392 | 5,975 | 0.1114 | 0.01238 | 13.92 | 97% | hook_strength=0.3, production_quality=0.2 | – |
| gemini-4-carbon *(ref)* | high | 0 | 225.7 | 57,326 | 4,778 | 0.1624 | 0.01805 | 20.30 | 100% | hook_strength=0.3, production_quality=0.2 | – |
| gemini-4-carbon | low | 0 | 355.2 | 57,326 | 6,799 | 0.1826 | 0.02029 | 22.83 | 100% | hook_strength=0.4, production_quality=0.3 | – |
| claude-opus-5-5 | low | 0 | 21.8 | 41,392 | 5,539 | 0.2141 | 0.02379 | 26.76 | 95% | hook_strength=0.3, production_quality=0.2 | – |
| claude-opus-5-5 *(ref)* | high | 0 | 39.0 | 41,392 | 10,511 | 0.3135 | 0.03484 | 39.19 | 100% | hook_strength=0.3, production_quality=0.2 | – |

### rationale

| Model | Effort | Thời gian (s) | Token vào | Token ra | USD | Trích dẫn hợp lệ | Độ dài lý do TB |
|---|---|---|---|---|---|---|---|
| claude-haiku-5-5 | medium | 14.3 | 4,603 | 3,141 | 0.0021 | 100% | 234 |
| claude-sonnet-5-5 | medium | 17.5 | 4,603 | 2,508 | 0.0350 | 100% | 218 |
| claude-opus-5-5 | medium | 23.2 | 4,603 | 2,502 | 0.0698 | 100% | 232 |
| gemini-3.5-flash-lite | medium | 3.3 | 2,270 | 905 | 0.0029 | 100% | 214 |
| gemini-3.1-flash-lite | medium | 3.8 | 2,270 | 922 | 0.0020 | 100% | 224 |
| gemini-3.8-flash | medium | 31.2 | 2,270 | 4,115 | 0.0171 | 100% | 338 |
| gemini-4-carbon | medium | 83.2 | 2,736 | 5,350 | 0.0590 | 100% | 335 |
| deepseek-flash | medium | 25.0 | 3,212 | 5,293 | 0.0071 | 100% | 336 |
| deepseek-v4-pro | medium | 105.7 | 3,263 | 9,187 | 0.0407 | 100% | 273 |

### Bộ KOC có đổi theo model không?

Nếu dùng cùng một model cho cả bước sàng lọc và bước video (phần định lượng giữ nguyên):

| Model | Effort | KOC được chọn | Jaccard so với pipeline |
|---|---|---|---|
| claude-haiku-5-5 | low | _huongdaily, beobeo.21, lapiszuzu, reviewkemchongnang, trangriviuuu_01 | 50% |
| claude-sonnet-5-5 | low | _huongdaily, lapiszuzu, ngoc.matcha.review, reviewkemchongnang | 100% |
| claude-opus-5-5 | low | _huongdaily, lapiszuzu, ngoc.matcha.review, trangriviuuu_01 | 60% |
| gemini-3.5-flash-lite | low | _huongdaily, emlylynguyen, lapiszuzu, reviewkemchongnang, trangriviuuu_01 | 50% |
| gemini-3.1-flash-lite | low | _huongdaily, emlylynguyen, lapiszuzu, reviewkemchongnang, trangriviuuu_01 | 50% |
| gemini-3.8-flash | low | _huongdaily, emlylynguyen, mai.trinh.h, reviewkemchongnang, trangriviuuu_01 | 29% |
| gemini-4-carbon | low | _huongdaily, emlylynguyen, lapiszuzu, reviewkemchongnang, trangriviuuu_01 | 50% |
| deepseek-flash | low | lapiszuzu, ngoc.matcha.review, reviewkemchongnang, trangriviuuu_01 | 60% |
| claude-opus-5-5 | high | _huongdaily, lapiszuzu, ngoc.matcha.review, reviewkemchongnang | 100% |
| gemini-4-carbon | high | _huongdaily, emlylynguyen, lapiszuzu, reviewkemchongnang, trangriviuuu_01 | 50% |

