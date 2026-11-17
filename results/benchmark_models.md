# Benchmark model – input của run `final-haiku`

> **Dữ liệu đã lưu (cache).** Benchmark chạy lúc 2026-11-18 06:31, tốn $2.60 cho 31 biến thể (bước × model × effort), cộng $0.48 cho các lần gọi hỏng mà hãng vẫn tính tiền. Đọc file này không gọi model, không cần API key. Chạy lại: `uv run koc bench --run-id final-haiku` (cần key Anthropic, Gemini, DeepSeek; ~$3, ~1 giờ).

## Đề xuất model cho từng bước

Luật: (1) chọn model **rẻ nhất** có độ khớp tham chiếu ≥ 90% và không lỗi; (2) **nâng cấp** lên model khớp cao hơn nếu hơn ≥ 5 điểm % mà chỉ tốn thêm ≤ $2 cho 500 KOC; (3) bước viết lý do: rẻ nhất có 100% trích dẫn hợp lệ. Vì chi phí nhân lên theo số KOC, model đắt chỉ đáng dùng khi chất lượng tăng tương xứng.

| Bước | Đề xuất | Khớp tham chiếu | USD/item | USD cho 500 KOC | Độ trễ TB | Đang dùng | Lý do |
|---|---|---|---|---|---|---|---|
| Sàng lọc (text) | **gemini-3.8-flash** (low) | 91% | 0.00104 | 2.08 | 9.9s | gemini-3.8-flash | rẻ nhất trong các model khớp tham chiếu ≥ 90%: khớp 91%, 0.00104 USD/item. Model khớp cao nhất là gemini-4-carbon (94%), đắt hơn 3 lần nhưng chỉ hơn 3 điểm %; không model nào vừa hơn ≥ 5 điểm % vừa tốn thêm ≤ $2/500 KOC |
| Xem video | **gemini-3.5-flash-lite** (low) | 97% | 0.00220 | 2.47 | 9.4s | gemini-3.5-flash-lite | khớp 97%, cao hơn model rẻ nhất đạt ngưỡng (claude-haiku-5-5, 91%) 6 điểm % mà chỉ tốn thêm $1.79 cho 500 KOC (ngưỡng nâng cấp: ≥ 5 điểm %, ≤ $2). |
| Viết lý do | **gemini-3.1-flash-lite** (medium) | – | 0.00210 | 0.26 | 3.7s | gemini-3.1-flash-lite | rẻ nhất trong 9 model có 100% mã bằng chứng hợp lệ (kiểm bằng code). Văn phong không đo tự động được: nên đọc 1 bản mẫu trước khi đổi (results/benchmark_outputs.json). |

**Chi phí AI dự phóng cho 500 KOC** (theo tỷ lệ phễu thực tế của run):

| Phương án | Sàng lọc | Xem video | Viết lý do | USD cho 500 KOC |
|---|---|---|---|---|
| Đề xuất (theo benchmark) | gemini-3.8-flash | gemini-3.5-flash-lite | gemini-3.1-flash-lite | 4.81 |
| Lúc chạy run final-haiku | claude-haiku-5-5 | claude-haiku-5-5 | claude-sonnet-5-5 | 4.82 |
| Toàn Claude Opus 5.5 | claude-opus-5-5 | claude-opus-5-5 | claude-opus-5-5 | 51.05 |
| Chỉ dùng Anthropic (Claude) | claude-opus-5-5 | claude-haiku-5-5 | claude-haiku-5-5 | 17.87 |
| Chỉ dùng Anthropic (Claude), model rẻ nhất mỗi bước (có bước chưa đạt ngưỡng) | claude-haiku-5-5 | claude-haiku-5-5 | claude-haiku-5-5 | 1.83 |
| Chỉ dùng Google (Gemini) | gemini-3.8-flash | gemini-3.5-flash-lite | gemini-3.1-flash-lite | 4.81 |
| Chỉ dùng Google (Gemini), model rẻ nhất mỗi bước (có bước chưa đạt ngưỡng) | gemini-3.1-flash-lite | gemini-3.5-flash-lite | gemini-3.1-flash-lite | 3.63 |
| Chỉ dùng DeepSeek | deepseek-flash | deepseek-flash | deepseek-flash | 6.11 |

## So sánh theo hãng: Anthropic, Google, DeepSeek

Mỗi ô: model **rẻ nhất đạt ngưỡng** của hãng đó (không có thì model khớp cao nhất), độ khớp tham chiếu, chi phí cho 500 KOC, độ trễ mỗi lần gọi; dòng dưới: vì sao không dùng hãng đó so với model đề xuất.

| Bước | Anthropic (Claude) | Google (Gemini) | DeepSeek |
|---|---|---|---|
| Sàng lọc | claude-opus-5-5<br>khớp 94% · $16.89 · 12.2s<br>rẻ nhất: claude-haiku-5-5 84%, $0.85, 21.0s<br>*đắt hơn 8.1 lần* | gemini-3.8-flash<br>khớp 91% · $2.08 · 9.9s<br>khớp cao nhất: gemini-4-carbon 94%, $6.15<br>rẻ nhất: gemini-3.1-flash-lite 88%, $0.90, 4.2s<br>**được chọn** | deepseek-flash<br>khớp 91% · $2.10 · 26.4s<br>*chi phí ngang nhau; chậm hơn 2.7 lần* |
| Xem video | claude-haiku-5-5<br>khớp 91% · $0.68 · 3.4s<br>6 khung hình + phụ đề<br>khớp cao nhất: claude-sonnet-5-5 97%, $13.67<br>*khớp thấp hơn 6 điểm %; rẻ hơn 3.7 lần; nhanh hơn 2.7 lần* | gemini-3.5-flash-lite<br>khớp 97% · $2.47 · 9.4s<br>video gốc có tiếng<br>khớp cao nhất: gemini-4-carbon 100%, $18.75<br>**được chọn** | deepseek-flash<br>khớp 94% · $3.14 · 10.4s<br>6 khung hình + phụ đề<br>*khớp thấp hơn 3 điểm %; đắt hơn 1.3 lần* |
| Viết lý do | claude-haiku-5-5<br>trích dẫn 100% · $0.30 · 16.8s<br>*chi phí ngang nhau; chậm hơn 4.6 lần* | gemini-3.1-flash-lite<br>trích dẫn 100% · $0.26 · 3.7s<br>**được chọn** | deepseek-flash<br>trích dẫn 100% · $0.87 · 22.1s<br>*đắt hơn 3.3 lần; chậm hơn 6.0 lần* |
| **Chỉ dùng hãng này, 500 KOC** | **$17.87** | **$4.81** | **$6.11** |

**Sàng lọc: độ khớp từng trường** (model ở bảng trên, 16 creator; 1 lần lệch ≈ 6 điểm % của trường đó):

| Trường | Anthropic (Claude): claude-opus-5-5 | Google (Gemini): gemini-3.8-flash | DeepSeek: deepseek-flash |
|---|---|---|---|
| Loại tài khoản | 100% | 100% | 100% |
| Ngách | 88% | 81% | 81% |

**Xem video: độ khớp từng trường** (model ở bảng trên, 9 video; 1 lần lệch ≈ 11 điểm % của trường đó):

| Trường | Anthropic (Claude): claude-haiku-5-5 | Google (Gemini): gemini-3.5-flash-lite | DeepSeek: deepseek-flash |
|---|---|---|---|
| Đúng chủ đề | 100% | 100% | 100% |
| Lộ mặt | 100% | 100% | 100% |
| Thử sản phẩm trên da | 71% | 100% | 100% |
| Kết cấu / độ hoàn thiện | 86% | 86% | 71% |
| Giới tính người dẫn | 100% | 100% | 100% |

**Tỷ lệ chi phí theo hãng trong phương án đề xuất (500 KOC):** Google (Gemini) 100% ($4.81). Anthropic (Claude) không được chọn ở bước nào (lý do từng bước ở bảng trên). DeepSeek không được chọn ở bước nào (lý do từng bước ở bảng trên).


**Độ ổn định của bộ KOC** – mỗi KOC được bao nhiêu % biến thể chọn (mỗi biến thể dùng 1 model cho cả sàng lọc + xem video; phần định lượng giữ nguyên). KOC được ≥ 80% biến thể chọn là lựa chọn chắc chắn; thấp hơn là nhóm sát ngưỡng, kết quả phụ thuộc model:

| KOC | Tỷ lệ biến thể chọn | Có trong đề xuất của run `final-haiku` (input benchmark) |
|---|---|---|
| @_huongdaily | 100% | có |
| @lapiszuzu | 100% | có |
| @reviewkemchongnang | 100% | có |
| @trangriviuuu_01 | 60% | – |
| @emlylynguyen | 50% | – |
| @beobeo.21 | 30% | – |
| @mai.trinh.h | 20% | – |

Lưu ý về độ chính xác: tham chiếu là đồng thuận của 3 model mạnh (chưa phải nhãn người). Model thuộc nhóm tham chiếu (Opus, Gemini 4 Carbon, DeepSeek V4 Pro) có lợi thế khi so ở effort thấp. Cột "Khớp người" có số sau khi người gán nhãn `eval/golden_labels.csv`.

## Số liệu chi tiết

Cùng input, đổi model. **Tham chiếu** = đồng thuận (đa số / trung vị) của claude-opus-5-5, gemini-4-carbon, deepseek-v4-pro ở effort `high`. Chi phí cho 500 KOC = chi phí mỗi item × số item phải xử lý cho mỗi KOC được chọn theo phễu thực tế (screen 4.0, video 2.2 item/KOC). Claude và DeepSeek xem video qua 6 khung hình + phụ đề; Gemini xem video gốc có tiếng.

### screen

| Model | Effort | Lỗi | Thời gian (s) | Token vào | Token ra | USD | USD/item | USD cho 500 KOC | Khớp tham chiếu | MAE điểm | Khớp người |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-haiku-5-5 | low | 0 | 42.1 | 21,122 | 9,768 | 0.0068 | 0.00043 | 0.85 | 84% | topic_relevance=0.9 | – |
| gemini-3.1-flash-lite | low | 0 | 8.4 | 10,783 | 2,995 | 0.0072 | 0.00045 | 0.90 | 88% | topic_relevance=0.8 | – |
| gemini-3.5-flash-lite | low | 0 | 5.3 | 10,783 | 1,671 | 0.0074 | 0.00046 | 0.93 | 88% | topic_relevance=0.9 | – |
| gemini-3.8-flash | low | 0 | 19.8 | 10,783 | 2,286 | 0.0167 | 0.00104 | 2.08 | 91% | topic_relevance=0.7 | – |
| deepseek-flash | low | 0 | 52.7 | 14,453 | 11,150 | 0.0168 | 0.00105 | 2.10 | 91% | topic_relevance=0.4 | – |
| gemini-4-carbon | low | 0 | 29.5 | 11,764 | 2,569 | 0.0492 | 0.00308 | 6.15 | 94% | topic_relevance=0.2 | – |
| deepseek-v4-pro | low | 0 | 74.8 | 14,397 | 11,007 | 0.0587 | 0.00367 | 7.33 | 91% | topic_relevance=0.6 | – |
| deepseek-v4-pro *(ref)* | high | 0 | 96.9 | 14,555 | 13,459 | 0.0683 | 0.00427 | 8.53 | 94% | topic_relevance=0.4 | – |
| claude-sonnet-5-5 | low | 0 | 20.1 | 21,122 | 2,986 | 0.0748 | 0.00467 | 9.35 | 88% | topic_relevance=0.8 | – |
| claude-opus-5-5 | low | 0 | 24.3 | 21,122 | 2,883 | 0.1352 | 0.00845 | 16.89 | 94% | topic_relevance=0.2 | – |
| claude-opus-5-5 *(ref)* | high | 0 | 62.5 | 21,122 | 6,977 | 0.2047 | 0.01279 | 25.58 | 100% | topic_relevance=0.1 | – |
| gemini-4-carbon *(ref)* | high | 0 | 521.7 | 11,764 | 29,311 | 0.3166 | 0.01979 | 39.58 | 97% | topic_relevance=0.2 | – |

### video

| Model | Effort | Lỗi | Thời gian (s) | Token vào | Token ra | USD | USD/item | USD cho 500 KOC | Khớp tham chiếu | MAE điểm | Khớp người |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-haiku-5-5 | low | 0 | 14.4 | 40,782 | 5,767 | 0.0054 | 0.00060 | 0.68 | 91% | hook_strength=0.4, production_quality=0.6 | – |
| gemini-3.5-flash-lite | low | 0 | 28.3 | 43,244 | 2,714 | 0.0198 | 0.00220 | 2.47 | 97% | hook_strength=0.7, production_quality=0.4 | – |
| gemini-3.1-flash-lite | low | 0 | 38.5 | 43,244 | 5,998 | 0.0201 | 0.00224 | 2.52 | 89% | hook_strength=0.6, production_quality=0.6 | – |
| deepseek-flash | low | 0 | 35.9 | 23,738 | 17,545 | 0.0251 | 0.00279 | 3.14 | 94% | hook_strength=0.3, production_quality=0.6 | – |
| gemini-3.8-flash | low | 0 | 34.3 | 43,244 | 3,264 | 0.0447 | 0.00496 | 5.58 | 95% | hook_strength=0.2, production_quality=0.3 | – |
| claude-sonnet-5-5 | low | 0 | 19.9 | 40,782 | 5,897 | 0.1094 | 0.01216 | 13.67 | 97% | hook_strength=0.3, production_quality=0.2 | – |
| gemini-4-carbon | low | 0 | 38.7 | 56,718 | 3,656 | 0.1500 | 0.01667 | 18.75 | 100% | hook_strength=0.4, production_quality=0.4 | – |
| claude-opus-5-5 | low | 0 | 23.1 | 40,782 | 5,517 | 0.2112 | 0.02347 | 26.40 | 95% | hook_strength=0.2, production_quality=0.2 | – |
| claude-opus-5-5 *(ref)* | high | 0 | 39.6 | 40,782 | 10,423 | 0.2990 | 0.03322 | 37.38 | 100% | hook_strength=0.2, production_quality=0.2 | – |
| gemini-4-carbon *(ref)* | high | 0 | 1351.8 | 56,718 | 41,590 | 0.5293 | 0.05882 | 66.17 | 100% | hook_strength=0.2, production_quality=0.2 | – |

### rationale

| Model | Effort | Thời gian (s) | Token vào | Token ra | USD | Trích dẫn hợp lệ | Độ dài lý do TB |
|---|---|---|---|---|---|---|---|
| claude-haiku-5-5 | medium | 16.8 | 4,635 | 3,773 | 0.0024 | 100% | 312 |
| claude-sonnet-5-5 | medium | 10.7 | 4,635 | 1,634 | 0.0263 | 100% | 215 |
| claude-opus-5-5 | medium | 18.2 | 4,635 | 2,107 | 0.0621 | 100% | 231 |
| gemini-3.5-flash-lite | medium | 3.0 | 2,270 | 887 | 0.0029 | 100% | 198 |
| gemini-3.1-flash-lite | medium | 3.7 | 2,270 | 1,022 | 0.0021 | 100% | 230 |
| gemini-3.8-flash | medium | 22.3 | 2,270 | 3,180 | 0.0136 | 100% | 268 |
| gemini-4-carbon | medium | 72.0 | 2,739 | 5,614 | 0.0616 | 100% | 419 |
| deepseek-flash | medium | 22.1 | 3,218 | 5,126 | 0.0070 | 100% | 377 |
| deepseek-v4-pro | medium | 58.7 | 3,269 | 9,493 | 0.0419 | 100% | 230 |

### Bộ KOC có đổi theo model không?

Nếu dùng cùng một model cho cả bước sàng lọc và bước video (phần định lượng giữ nguyên):

| Model | Effort | KOC được chọn | Jaccard so với pipeline |
|---|---|---|---|
| claude-haiku-5-5 | low | _huongdaily, beobeo.21, lapiszuzu, reviewkemchongnang | 60% |
| claude-sonnet-5-5 | low | _huongdaily, beobeo.21, lapiszuzu, reviewkemchongnang | 60% |
| claude-opus-5-5 | low | _huongdaily, lapiszuzu, mai.trinh.h, reviewkemchongnang | 60% |
| gemini-3.5-flash-lite | low | _huongdaily, emlylynguyen, lapiszuzu, reviewkemchongnang, trangriviuuu_01 | 50% |
| gemini-3.1-flash-lite | low | _huongdaily, emlylynguyen, lapiszuzu, reviewkemchongnang, trangriviuuu_01 | 50% |
| gemini-3.8-flash | low | _huongdaily, emlylynguyen, lapiszuzu, reviewkemchongnang, trangriviuuu_01 | 50% |
| gemini-4-carbon | low | _huongdaily, emlylynguyen, lapiszuzu, reviewkemchongnang, trangriviuuu_01 | 50% |
| deepseek-flash | low | _huongdaily, beobeo.21, lapiszuzu, reviewkemchongnang, trangriviuuu_01 | 50% |
| claude-opus-5-5 | high | _huongdaily, lapiszuzu, mai.trinh.h, reviewkemchongnang | 60% |
| gemini-4-carbon | high | _huongdaily, emlylynguyen, lapiszuzu, reviewkemchongnang, trangriviuuu_01 | 50% |

