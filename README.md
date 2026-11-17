# AI KOC Discovery

Hệ thống tìm KOC TikTok phù hợp một chiến dịch, dựa trên dữ liệu hiệu suất (Kalodata), nội dung và **phân tích video
bằng AI**, với chi phí AI tối ưu và khả năng chạy tiếp khi bị gián đoạn.

Bài toán demo: thương hiệu kem chống nắng Việt Nam, khách hàng nữ 18–30, ngân sách 30 triệu VNĐ, cần 5 KOC.

> **Chỉ cần đọc file này là chạy được.** Mục [Hướng dẫn chạy](#hướng-dẫn-chạy-trên-máy-bất-kỳ) đi từ máy trống đến
> lúc xem được kết quả trên trình duyệt. Xem kết quả có sẵn **không cần API key**.

## Dành cho người kiểm tra

**Toàn bộ kết quả đã được chạy sẵn và lưu kèm repo (dữ liệu cache).** Không cần API key để xem đủ thông tin:
đề xuất KOC, bằng chứng, chi phí AI, benchmark 9 model, bảng đề xuất model và đo mở rộng 50–500 KOC. Mọi trang/báo cáo đều ghi rõ
"Dữ liệu đã lưu (cache)", thời điểm chạy, số lần gọi model và số tiền đã tiêu; xem không gọi model, không tốn tiền.

| Cách xem | Cần gì |
|---|---|
| **Mở `results/report.html`** (bấm đúp, hoặc tải file về rồi mở bằng trình duyệt) | Không cần gì: 1 file tự chứa, dữ liệu nhúng sẵn |
| Đọc trên GitHub: [`results/final/recommendation.md`](results/final/recommendation.md), [`results/benchmark_models.md`](results/benchmark_models.md), [`results/scale_test.md`](results/scale_test.md) | Không cần gì |
| Trang web đầy đủ `uv run koc serve` (các bước dưới) | uv; thêm tab **Tiến độ** trực tiếp và phát video khi đã chạy pipeline |

**5 phút, không cần API key** – trang web từ mã nguồn:

```bash
# 1 lần: cài uv (Windows PowerShell: powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex")
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone https://github.com/nguyenvu938/detola_ai_test.git koc-discovery && cd koc-discovery
uv sync
uv run koc serve          # mở http://127.0.0.1:8000
```

| Tab | Nên xem gì | Ứng với tiêu chí |
|---|---|---|
| **Đề xuất** | Phễu 272 → KOC được chọn; mỗi KOC có lý do, rủi ro, gợi ý brief, điểm thành phần, quan sát trong video theo mốc thời gian; ghi chú ngân sách | 1. Chất lượng |
| **Chi phí AI** | Token, USD, độ trễ theo bước và model: cả run $0.023, chỉ 3 bước gọi model; số lần dùng lại kết quả cũ và tiền tiết kiệm | 2. Tối ưu token |
| **Benchmark model** | **Đề xuất model cho từng bước** (rẻ nhất đạt ≥ 90% khớp tham chiếu) kèm lý do, chi phí dự phóng 500 KOC, bảng 9 model, độ ổn định của bộ KOC | 2. Tối ưu token (và độ chính xác) |
| **Mở rộng 50–500 KOC** | Mô phỏng 5 / 50 / 500 KOC trên nguyên pipeline: phễu, số lần gọi, chi phí, thời gian, điểm nghẽn, phục hồi | 3. Khả năng mở rộng |
| **Tiến độ** | Checkpoint từng stage, các lần gọi model gần nhất (dùng khi tự chạy pipeline) | Phục hồi khi gián đoạn |

**10 phút, cần `ANTHROPIC_API_KEY` (~$0.01–0.05)** – tự chạy và thử phục hồi. Chỉ có key Anthropic thì mọi bước
dùng Claude Haiku; thêm `GEMINI_API_KEY` thì bước xem video và viết lý do dùng Gemini 3.1 Flash-Lite theo đề xuất benchmark:

```bash
cp .env.example .env      # điền ANTHROPIC_API_KEY (Windows: copy .env.example .env)
uv run koc run --run-id demo --crash-after 3    # "sập" giữa chừng
uv run koc run --run-id demo                    # chạy lại: tiếp tục đúng chỗ, không gọi lặp model
```
Trong lúc chạy, mở tab **Tiến độ** và chọn run `demo`. Đọc thêm: [`ARCHITECTURE.md`](ARCHITECTURE.md) (các quyết định và lý do).

## Đáp ứng 3 tiêu chí của đề

| Tiêu chí | Kết quả | Xem ở đâu |
|---|---|---|
| [**1. Chất lượng**](#1-chất-lượng-đề-xuất-dựa-trên-bằng-chứng-có-phân-tích-video-bằng-ai) | 5 KOC, mỗi người có 3 lớp bằng chứng; AI xem video gốc có tiếng của cả 5; code kiểm 15/15 trích dẫn hợp lệ; model đang dùng khớp 94–98% với đồng thuận của 3 model mạnh nhất | Tab **Đề xuất**, [`results/final/recommendation.md`](results/final/recommendation.md) |
| [**2. Tối ưu token**](#2-tối-ưu-token-và-chi-phí) | **$0.023** cho cả run (12 lần gọi model); quét lại dữ liệu không đổi **$0**; định tuyến theo benchmark 9 model rẻ hơn toàn Opus ~18 lần | Tab **Chi phí AI**, **Benchmark model**, [`results/benchmark_models.md`](results/benchmark_models.md) |
| [**3. Khả năng mở rộng**](#3-khả-năng-mở-rộng-50500-koc) | Mô phỏng 500 KOC trên nguyên pipeline: chọn đủ 500, chi phí AI dự phóng **$2.36**, code chạy 18 giây; "sập" giữa chừng rồi chạy tiếp không gọi lặp item nào | Tab **Mở rộng 50–500 KOC**, [`results/scale_test.md`](results/scale_test.md) |

### 1. Chất lượng: đề xuất dựa trên bằng chứng, có phân tích video bằng AI

**Kết quả** (run `final`, định tuyến theo benchmark):

| | |
|---|---|
| Phễu | 272 creator (4 nguồn Kalodata) → lọc luật 161 → lấy chi tiết 60 → đúng khán giả/loại tài khoản 36 → LLM sàng lọc 16 (đạt cổng 13) → AI xem video 9 → đạt ngưỡng điểm 8 → **chọn 5** |
| 5 KOC | `@reviewkemchongnang` (0.79) · `@_huongdaily` (0.73) · `@lapiszuzu` (0.69) · `@emlylynguyen` (0.66) · `@trangriviuuu_01` (0.63) |
| Ngân sách | Booking ước tính 26,25 tr / 30 tr, còn 3,75 tr chạy Spark Ads (thấp hơn mức khuyến nghị 7,5 tr; báo cáo nêu cách đàm phán theo hoa hồng) |
| Mỗi KOC có | Lý do, rủi ro, gợi ý brief, điểm thành phần, quan sát trong video theo mốc thời gian (trên web bấm mốc để tua tới đúng đoạn) |
| Token / chi phí / thời gian | 64.417 token vào, 13.730 token ra · **$0.023** (12 lần gọi model) · **93 giây** xử lý (cộng các stage, kể cả lần chạy tiếp sau khi "sập") |

**3 lớp bằng chứng.** Code gộp điểm theo trọng số trong `config/campaign.toml`; LLM không tự chọn KOC.

| Lớp | Nguồn và nội dung | Trọng số |
|---|---|---|
| Số liệu | Kalodata: khán giả đúng giới/tuổi, doanh thu ngành (chỉ so khi cùng cơ sở), chuyển đổi, view/follower, engagement, tỷ lệ view organic | 45% |
| Hồ sơ | LLM đọc bio, tiêu đề video, shop: loại tài khoản (cá nhân / brand / shop / agency), ngách, mức phù hợp, thương hiệu đối thủ đã quảng bá, rủi ro | 20% |
| Video | AI xem 1 video đúng chủ đề (Gemini: video gốc có tiếng; Claude: 6 khung hình + phụ đề): lộ mặt, thử trên da, kết cấu, hook, claim rủi ro, người dẫn | 35% |

**Cơ chế giữ chất lượng:**
- **Kiểm trích dẫn bằng code:** lời giải thích phải trích mã bằng chứng (`M:gmv`, `S:screen`, `V:<video_id>`...). Code kiểm từng mã có thật trong input của đúng KOC đó: 15/15 hợp lệ.
- **Thà thiếu còn hơn chọn sai:** dưới ngưỡng điểm 0.5 thì không chọn bù (`@mai.trinh.h` 0.46 bị loại). Khi thiếu KOC, báo cáo nói rõ do thiếu người đạt ngưỡng hay do vượt ngân sách, kèm phương án gần nhất.
- **Loại sớm sai đối tượng:** tài khoản brand/shop/agency, khán giả lệch giới. Tối đa 1 KOC mỗi nhóm dùng chung liên hệ (cùng agency), tránh trùng độ phủ.
- **Đo độ chính xác của model:** so với đồng thuận đa số của Opus 5.5, Gemini 4 Carbon, DeepSeek V4 Pro (effort high). Model đang dùng khớp 94% ở bước sàng lọc và 98% ở bước xem video.
- **Đo độ ổn định:** đếm % biến thể model chọn mỗi KOC. `@reviewkemchongnang`, `@lapiszuzu`, `@_huongdaily` 90% (chắc chắn); `@trangriviuuu_01` 80%; `@emlylynguyen` 50% (sát ngưỡng).
- **Nhãn của người:** `eval/golden_labels_TEMPLATE.csv` để tự gán nhãn rồi đo độ khớp giữa model và người (chưa gán).

**Báo cáo nêu rõ các điểm yếu:**
- 3/5 KOC có cờ view/follower thấp hơn chuẩn (dấu hiệu follower ảo hoặc kênh giảm tương tác).
- Video AI xem của `@emlylynguyen` là quảng cáo sữa tắm, không phải kem chống nắng. KOC này được chọn nhờ khán giả và cách thể hiện; báo cáo ghi rủi ro, cần brief chặt.

### 2. Tối ưu token và chi phí

**Kết quả:** $0.023 cho cả run (12 lần gọi: 2 sàng lọc, 9 xem video, 1 viết lý do) ≈ 600 VNĐ; 64.417 token vào,
13.730 token ra; 93 giây xử lý. Chi tiết từng stage: mục "Chi phí AI và thời gian" trong [`results/final/recommendation.md`](results/final/recommendation.md).

| Kỹ thuật | Tác dụng |
|---|---|
| Phễu rẻ trước, đắt sau | 4/7 bước là code thuần (0 token). 272 creator, chỉ 16 người được LLM đọc hồ sơ, 9 người được AI xem video |
| Phễu thích ứng | Sàng lọc từng đợt theo thứ tự điểm, dừng khi đủ 2 × số KOC ứng viên đạt cổng (dùng 16/40 suất) |
| Gom batch, thu gọn input | 8 creator/lần gọi dùng chung 1 prompt hệ thống; bio cắt 200 ký tự, tiêu đề video 100 ký tự |
| Xem video tiết kiệm | 1 video đúng chủ đề mỗi creator, 60 giây đầu, độ phân giải thấp |
| Định tuyến theo benchmark | Mỗi bước dùng model rẻ nhất đạt ≥ 90% khớp tham chiếu (bảng dưới) |
| Dùng lại kết quả | Cache theo nội dung + sổ đăng ký creator: chỉ phần mới hoặc phần thay đổi mới gọi model (mục dưới) |
| Chặn ngân sách | Run vượt `max_usd_per_run` thì dừng, tránh hóa đơn bất ngờ |

#### Benchmark 9 model và đề xuất (dữ liệu đã lưu, chạy 2026-11-17, tốn $2.11)

Cùng input của run `final-haiku`, so Claude (Haiku/Sonnet/Opus 5.5), Gemini (3.5 Flash-Lite, 3.1 Flash-Lite, 3.8 Flash,
4 Carbon), DeepSeek (Flash, V4 Pro). Tham chiếu = đồng thuận của Opus 5.5, Gemini 4 Carbon, DeepSeek V4 Pro (effort high).

| Bước | Model đề xuất | Khớp tham chiếu | Lý do |
|---|---|---|---|
| Sàng lọc | **Claude Haiku 5.5** | 94% | Rẻ nhất đạt ≥ 90%. Model khớp 100% (Gemini 3.8 Flash) đắt hơn 6 lần |
| Xem video | **Gemini 3.1 Flash-Lite** | 98% | Xem video gốc có tiếng; hơn Haiku (91%, chỉ thấy khung hình) 7 điểm % mà chỉ thêm $1.27/500 KOC |
| Viết lý do | **Gemini 3.1 Flash-Lite** | 100% trích dẫn hợp lệ | Cả 9 model đều trích đúng; rẻ nhất, rẻ hơn Sonnet ~17 lần |

| Chi phí AI dự phóng cho 500 KOC | USD |
|---|---|
| Đề xuất (Haiku + Gemini Flash-Lite + Gemini Flash-Lite) | **2.90** |
| Chỉ dùng Anthropic (Haiku cả 3 bước; xem video chỉ khớp 91%) | 1.65 |
| Chỉ dùng Google (3.8 Flash sàng lọc + Flash-Lite) / bản rẻ nhất (Flash-Lite cả 3 bước, sàng lọc chỉ khớp 88%) | 6.67 / 2.98 |
| Chỉ dùng DeepSeek (Flash cả 3 bước) | 5.23 |
| Định tuyến lúc chạy run `final-haiku` (Haiku + Haiku + Sonnet) | 5.77 |
| Toàn Claude Opus 5.5 | 52.25 |

**So sánh theo hãng** (model rẻ nhất đạt ngưỡng của mỗi hãng, chi phí cho 500 KOC):

| Bước | Anthropic | Google | DeepSeek | Vì sao chọn |
|---|---|---|---|---|
| Sàng lọc (text) | **Haiku: 94%, $0.71** | 3.8 Flash: 100%, $4.48 (Flash-Lite: 88%, $0.79) | Flash: 91%, $2.21 | Haiku rẻ nhất trong các model đạt 90%. Trường loại tài khoản (dùng ở cổng lọc) cả 3 hãng đều đúng 100%; khác nhau ở trường ngách |
| Xem video | Haiku: 91%, $0.68 | **3.1 Flash-Lite: 98%, $1.95** | Flash: 91%, $2.13 | Chỉ Gemini xem được video gốc có tiếng. Claude và DeepSeek chỉ thấy 6 khung hình + phụ đề nên hay sai "có thoa sản phẩm lên da không" (71% so với 100%) và "kết cấu" (83% so với 100%). Đổi lại Gemini lệch 1/9 video ở trường "đúng chủ đề" |
| Viết lý do | Haiku: 100%, $0.26 | **3.1 Flash-Lite: 100%, $0.24** | Flash: 100%, $0.89 | Cả 3 hãng trích dẫn đúng 100%; Gemini rẻ nhất và nhanh nhất (3,8 giây so với 14 giây của Haiku) |

Tỷ lệ chi phí trong phương án đề xuất: **Anthropic 25%, Google 75%**. DeepSeek không được chọn ở bước nào: ở mỗi bước
đều có model khác khớp bằng hoặc cao hơn với giá thấp hơn. DeepSeek V4 Pro không đọc được ảnh nên không xem được video.
Mẫu đo nhỏ (16 creator, 9 video: 1 lần lệch ≈ 6–11 điểm % của một trường), nên chênh vài điểm % chỉ là tín hiệu, chưa phải
kết luận chắc chắn. Bảng đầy đủ: tab **Benchmark model** hoặc [`results/benchmark_models.md`](results/benchmark_models.md).

**Định tuyến mặc định đã đổi theo đề xuất** (`config/models.toml`) và run `final` chạy bằng định tuyến này. Máy không có
`GEMINI_API_KEY` thì bước video và viết lý do **tự dùng Claude Haiku** (dự phòng).

Run `final-haiku` (định tuyến cũ, chạy trước benchmark và là input của benchmark) chỉ chọn được 4 KOC và giữ
`@ngoc.matcha.review`, KOC mà bảng độ ổn định chỉ đánh giá 40%. Đổi bước xem video sang Gemini (nghe được lời nói) đưa
`@trangriviuuu_01` (ổn định 80%) và `@emlylynguyen` vào bộ chọn. Cách đo: [`BENCHMARK_PLAN.md`](BENCHMARK_PLAN.md).

#### Dùng lại kết quả, chỉ quét lại phần thay đổi

- **Cache theo nội dung:** khóa = hash của model + prompt + input. Input chỉ chứa thứ không đổi theo ngày (mô tả video,
  bậc follower rộng 25%, tỷ lệ doanh thu làm tròn), nên video đã phân tích được dùng lại mãi theo ID video.
- **Sổ đăng ký creator** (SQLite): mỗi lần quét xếp mỗi creator vào 1 trong 4 loại:
  - **mới**;
  - **thay đổi**, có ghi thay đổi gì: "2 video mới", "bậc follower 57k–71k → 71k–89k", bio, shop, khán giả;
  - **không đổi**;
  - **quá hạn**: quá 14 ngày không có thay đổi, nên lấy lại dữ liệu nguồn.

  Xem bằng `uv run koc changes`.
- **Đo thật trên cùng dữ liệu:** lần 1 tốn $0.0235 và 92 giây; **lần 2 tốn $0 và 23 giây**, 12/12 lần gọi dùng kết quả cũ,
  ra đúng 5 KOC như lần 1. Tab Chi phí AI có cột "Dùng lại kết quả cũ" và "Tiết kiệm".

### 3. Khả năng mở rộng 50–500 KOC

Đề chỉ cần demo 5 KOC. Để kiểm tra thiết kế có chạy được 50–500 KOC không, lệnh `uv run koc scale-test` chạy
**nguyên pipeline thật** (đủ 7 stage, checkpoint, cache, phễu thích ứng, chọn trong ngân sách) trên dữ liệu Kalodata giả
lập với model giả. Lệnh không gọi mạng, không tốn tiền, chạy ~25 giây. Phễu, số lần gọi, thời gian code và phục hồi là
**đo thật**. Token, USD và thời gian chờ model là **dự phóng**: số lần gọi × số đo thật mỗi item ở run `final`.
Ngân sách giữ tỷ lệ của đề (6 tr/KOC). Mô phỏng không đo chất lượng; chất lượng đã đo ở benchmark.

| | 5 KOC | 50 KOC | 500 KOC |
|---|---|---|---|
| Creator đầu vào (giả lập) | 125 | 1.250 | 12.500 |
| Lấy chi tiết Kalodata | 60 | 600 | 6.000 |
| LLM sàng lọc: người / lần gọi | 16 / 2 | 120 / 15 | 1.232 / 154 |
| AI xem video (người = lần gọi) | 10 | 100 | 1.000 |
| Viết lý do (lần gọi, 10 KOC/lần) | 1 | 5 | 50 |
| **Chọn được** | **5** | **50** | **500** |
| **Chi phí AI (dự phóng)** | **$0.03** | **$0.23** | **$2.36** ($0.0047/KOC) |
| Chờ model, song song 4 / 16 | 49 giây / 33 giây | 5 phút / 86 giây | 49 phút / 13 phút |
| Kalodata API ở giới hạn 10 request/10 giây | 1 phút, 6 điểm | 10 phút, 60 điểm | 1,7 giờ, 600 điểm |
| Thời gian phần code (đo thật) | < 0,1 giây | 1,1 giây | 18 giây |
| Giải bài chọn trong ngân sách (đo thật) | < 1 ms | 1 ms | 2 ms |
| SQLite (checkpoint + cache) | 0,4 MB | 3,2 MB | 31 MB |

**Phục hồi ở quy mô 50 KOC:** cho "sập" sau 60/120 lần gọi model rồi chạy lại cùng run: **0 item bị gọi lặp**, ra đúng
bộ 50 KOC như khi chạy liền một mạch. Bảng đầy đủ: [`results/scale_test.md`](results/scale_test.md).

$2.36 thấp hơn mức $2.90 của benchmark vì 2 cách tính dùng tỷ lệ phễu khác nhau. Benchmark theo tỷ lệ của run `final-haiku`,
khi đó nhiều người phải xem video hơn; mô phỏng theo tỷ lệ đạt cổng của run `final`. Hai con số cùng cỡ ~$0.005/KOC.

**Thiết kế giúp mở rộng:**

| Cơ chế | Vì sao |
|---|---|
| Mỗi tầng phễu tỷ lệ với số KOC | `enrich_per_koc = 12`, `screen_per_koc = 8`, `video_per_koc = 2`: chi phí AI tăng tuyến tính theo số KOC, không theo số creator đầu vào (chỉ ~10% creator đầu vào phải gọi model) |
| Song song có giới hạn | Sàng lọc, xem video, viết lý do chạy `concurrency` luồng; tăng theo hạn mức RPM của tài khoản |
| Chia lô | 8 creator/lần sàng lọc; 10 KOC/lần viết lý do (1 lần gọi cho 500 KOC sẽ vượt giới hạn token ra) |
| Checkpoint từng item + cache theo nội dung | Sập ở đâu chạy tiếp ở đó; lần quét sau chỉ trả tiền phần mới |
| Bài chọn trong ngân sách | n ≤ 6: vét cạn (chính xác). n lớn: nhân tử Lagrange + đổi chỗ, 2 ms cho 500 KOC; so với vét cạn trên 1.000 bài nhỏ ngẫu nhiên, trùng đáp án 99,4%, tệ nhất đạt 97,5% |
| Chặn ngân sách mỗi run | `max_usd_per_run` mặc định $1; run 500 KOC cần đặt ~$5 |

**Điểm nghẽn mà mô phỏng phát hiện, đã sửa:**

| Điểm nghẽn | Nếu không sửa | Đã sửa |
|---|---|---|
| Bước chọn chỉ xét 12 người điểm cao nhất | Không bao giờ chọn quá 12 KOC | Thuật toán riêng cho n lớn (trên) |
| Ngưỡng phễu là số cố định 60/40/10 | 500 KOC vẫn chỉ 10 người được xem video | Ngưỡng = hệ số × số KOC (5 KOC vẫn là 60/40/10) |
| Mỗi checkpoint SQLite chờ ghi đĩa (103 ms/lần trên máy đo) | 50 KOC mất 193 giây chỉ để ghi; 500 KOC ~30 phút | Chế độ WAL: 0,2 ms/lần (193 giây → 1,3 giây). Vẫn an toàn khi process bị tắt ngang |
| Xếp hạng phần trăm O(N²) | Hàng trăm triệu phép so sánh ở 12.500 creator | Tìm nhị phân O(N log N) |
| Sàng lọc tuần tự | 154 lần gọi × ~20 giây ≈ 50 phút | Song song theo đợt, mỗi đợt gửi số batch vừa đủ phần còn thiếu |
| Viết lý do 1 lần gọi cho cả bộ | 500 KOC vượt giới hạn token ra | Chia lô 10 KOC, chạy song song |

Sau khi sửa, chạy lại pipeline trên dữ liệu thật: phễu giống hệt run `final` và ra đúng 5 KOC cũ. Với 5 KOC, hành vi không đổi.

**Nút thắt còn lại ở 500 KOC (chưa làm):**
- **Lấy chi tiết Kalodata:** 6.000 lần gọi = 1,7 giờ. Có thể lấy chi tiết theo đợt như bước sàng lọc: mô phỏng cho thấy chỉ
  1.232/4.837 người qua chỉ số cần được sàng lọc, nên chỉ cần ~1.500 lần gọi (~25 phút). Lần quét sau chỉ lấy lại creator
  mới hoặc có thay đổi trên bảng xếp hạng.
- **Chờ model:** 49 phút ở 4 luồng. Tăng `concurrency` lên 16 thì còn 13 phút (cần hạn mức RPM tương ứng). Chiến dịch không
  gấp có thể dùng Batch API, rẻ hơn ~50%.
- **Tải 1.000 video:** dùng link mp4 trực tiếp từ Kalodata API (`video/url`) thay cho yt-dlp.
- **Nhiều chiến dịch:** tách phân tích video thành tầng dùng chung cho mọi chiến dịch và tầng chấm theo brief (rẻ). Thiết
  kế 2 tầng trong [`ARCHITECTURE.md`](ARCHITECTURE.md).

Đọc thêm: [`ARCHITECTURE.md`](ARCHITECTURE.md) (các quyết định và lý do) · [`data/market/research.md`](data/market/research.md) (nghiên cứu thị trường, giá booking)

---

## Hướng dẫn chạy trên máy bất kỳ

Áp dụng cho Windows 10/11, macOS và Linux. Cần Internet. Không cần cài Python hay ffmpeg trước: `uv` tự tải Python 3.12,
ffmpeg đi kèm thư viện `imageio-ffmpeg`.

### Bước 0. Cài Git và uv

- **Git:** https://git-scm.com/downloads (macOS có sẵn sau `xcode-select --install`).
- **uv** (quản lý Python và thư viện):

  Windows (PowerShell):
  ```powershell
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
  macOS / Linux:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
  Đóng và mở lại terminal, kiểm tra: `uv --version`.

### Bước 1. Lấy code và cài thư viện

```bash
git clone https://github.com/nguyenvu938/detola_ai_test.git koc-discovery
cd koc-discovery
uv sync
```

`uv sync` tạo môi trường ảo `.venv/` trong thư mục dự án (~200 MB) và tự tải Python 3.12 nếu máy chưa có.
**Mọi lệnh bên dưới chạy từ thư mục `koc-discovery`.**

### Bước 2. Xem kết quả trên trình duyệt (không cần API key)

```bash
uv run koc serve
```

Mở **http://127.0.0.1:8000**. Trang có 5 tab:
- **Đề xuất:** phễu, các KOC được chọn, lý do, rủi ro, gợi ý brief, quan sát trong video theo mốc thời gian.
- **Tiến độ:** checkpoint từng stage và các lần gọi model, tự cập nhật mỗi 2 giây khi đang chạy pipeline.
- **Chi phí AI:** token, USD, độ trễ theo stage và model.
- **Benchmark model:** so sánh 9 model.
- **Mở rộng 50–500 KOC:** mô phỏng 5 / 50 / 500 KOC (chi phí, thời gian, điểm nghẽn).

Server chỉ mở cho máy của bạn (127.0.0.1) và chỉ đọc dữ liệu. Dừng bằng `Ctrl+C`.
Video gốc không nằm trong repo (dung lượng lớn), nên trang hiện link TikTok. Sau khi chạy pipeline (Bước 4), video tải về
máy và trang phát được video, **bấm mốc thời gian để tua tới đúng đoạn AI nhận xét**.

### Bước 3. Chạy test (không tốn tiền)

```bash
uv run pytest
```

37 test, phần gọi API được giả lập. Có test chứng minh pipeline "sập" giữa chừng rồi chạy lại không gọi lặp model,
và test chạy nguyên pipeline trên 500 creator giả lập (20 KOC).

Đo khả năng mở rộng (0 đồng, không cần API key, ~25 giây):

```bash
uv run koc scale-test          # ghi results/scale_test.md, tab "Mở rộng 50–500 KOC"
```

### Bước 4. Chạy lại pipeline với AI thật (cần API key)

1. Tạo API key:
   - **Anthropic** (bắt buộc với cấu hình mặc định): https://console.anthropic.com → *API Keys*.
   - **Gemini** (cho benchmark, hoặc nếu chuyển bước video sang Gemini): https://aistudio.google.com → *Get API key*.
   - **DeepSeek** (cho benchmark): https://platform.deepseek.com → *API keys*.
2. Tạo file `.env` từ mẫu rồi điền key (file này không được commit):
   ```bash
   cp .env.example .env          # Windows PowerShell: copy .env.example .env
   ```
   ```
   ANTHROPIC_API_KEY=...
   GEMINI_API_KEY=...
   DEEPSEEK_API_KEY=...
   ```
3. Chạy (~1,5 phút nếu máy đã có video; 4–7 phút trên máy mới vì phải tải video từ TikTok; ~$0.03):
   ```bash
   uv run koc run --run-id demo
   ```
   Kết quả ở `results/demo/recommendation.md` và trên web (chọn run `demo` ở góc phải).
   Mở tab **Tiến độ** trong lúc chạy để xem từng stage hoàn thành.

4. Thử khả năng phục hồi:
   ```bash
   uv run koc run --run-id demo2 --crash-after 3   # "sập" sau 3 lần gọi model
   uv run koc status --run-id demo2                # xem các item đã lưu
   uv run koc run --run-id demo2                   # chạy lại: chỉ làm phần còn thiếu
   ```

5. Benchmark nhiều model trên cùng input (đo được 39 phút, ~$2, cần đủ 3 key):
   ```bash
   uv run koc bench --run-id demo
   ```
   Kết quả: `results/benchmark_models.md` và tab **Benchmark model**. Lệnh cũng tạo `eval/golden_labels_TEMPLATE.csv`
   để bạn tự gán nhãn (xem video, điền 3 cột), lưu thành `eval/golden_labels.csv` rồi chạy lại để đo độ khớp với người.

> Kết quả lần chạy của bạn có thể lệch nhẹ so với `final` vì 2 lý do: LLM có dao động giữa các lần chạy, và repo không
> kèm video. Pipeline tự tải lại video từ TikTok, nhưng TikTok giấu luồng video của bài gắn giỏ hàng với người xem không
> đăng nhập; bài nào không tải được thì chỉ được phân tích qua ảnh bìa (báo cáo ghi rõ). Xem mục Giới hạn.

### Lệnh và tuỳ chọn

| Lệnh | Việc làm |
|---|---|
| `uv run koc run --run-id X` | Chạy (hoặc tiếp tục) pipeline, ghi `results/X/` |
| `... --video-model gemini-4-carbon` | Đổi model một bước (cũng có `--screen-model`, `--rationale-model`); danh sách model trong `config/models.toml` |
| `... --no-cache` | Không dùng cache LLM, để đo chi phí/thời gian chạy nguội |
| `... --redo-stage video` | Làm lại một stage khi dữ liệu đầu vào đã đổi |
| `... --crash-after N` | Giả lập sự cố sau N lần gọi model |
| `uv run koc status --run-id X` | Số item xong/lỗi từng stage, chi phí |
| `uv run koc shortlist` | Ai sẽ được lấy chi tiết Kalodata, đã có snapshot chưa |
| `uv run koc changes` | Sổ đăng ký creator: ai mới, ai thay đổi gì (video mới, đổi bio/shop/khán giả/bậc follower), ai quá hạn cần lấy lại dữ liệu |
| `uv run koc bench --run-id X` | So 9 model trên input của run X |
| `uv run koc serve [--port 8000]` | Trang web xem kết quả |
| `uv run koc fetch-videos` | Tải mp4 từ link Kalodata trong `data/kalodata/video_urls.json` (link hết hạn nhanh) |
| `uv run koc sanitize-data` | Xoá số điện thoại/email khỏi bio trong snapshot, thay mã băm liên hệ bằng mã vô nghĩa `lh-N` (mã băm số điện thoại dò ngược được); đã chạy trước khi commit |
| `uv run koc export-html` | Ghi `results/report.html` (1 file tự chứa từ run `final` + benchmark) để xem không cần cài gì |
| `uv run koc bench --render-only` | Dựng lại báo cáo benchmark + bảng đề xuất từ số đã đo, không gọi model |
| `uv run koc scale-test [--sizes 5,50,500]` | Mô phỏng nguyên pipeline ở nhiều quy mô (dữ liệu giả lập, model giả, 0 đồng) |

**Đổi chiến dịch:** sửa `config/campaign.toml` (sản phẩm, ngách, giới tính, độ tuổi, ngân sách, số KOC, ngưỡng phễu).
Số người ở mỗi tầng phễu tự nhân theo số KOC. Với 50–500 KOC, nâng `max_usd_per_run` và `concurrency` trong `config/models.toml`.
Prompt, cách chấm khán giả và câu chữ bằng chứng tự sinh từ đó. Dữ liệu Kalodata cho danh mục khác cần thu thập lại
(xem `data/kalodata/README.md`, hoặc dùng Kalodata API theo `ARCHITECTURE.md`).

### Lỗi thường gặp

| Hiện tượng | Cách xử lý |
|---|---|
| `uv: command not found` | Mở terminal mới sau khi cài; vẫn lỗi thì xem https://docs.astral.sh/uv/getting-started/installation/ |
| Cổng 8000 đã bị dùng | `uv run koc serve --port 8080` rồi mở http://127.0.0.1:8080 |
| `Chưa có GEMINI_API_KEY` / `DEEPSEEK_API_KEY` | Chỉ cần khi benchmark hoặc định tuyến sang model đó; điền vào `.env` |
| `authentication_error` / 401 | Key sai hoặc hết hạn; kiểm tra `.env` (không có khoảng trắng, không có dấu nháy) |
| `DỪNG: Run đã tiêu ≥ $1.0` | Chặn ngân sách an toàn; tăng `max_usd_per_run` trong `config/models.toml` nếu cần |
| `404 ... no longer available` (Gemini) | Google đã ngừng model đó; đổi tên model trong `config/models.toml` |
| Nhiều video báo "không có luồng video" | Bình thường với bài gắn giỏ hàng/quảng cáo; bài đó được phân tích qua ảnh bìa và bị trừ điểm |
| Chữ tiếng Việt lỗi trong terminal Windows | Dùng Windows Terminal; hoặc chạy `set PYTHONIOENCODING=utf-8` trước |
| Muốn chạy lại từ đầu một run | Dùng `--run-id` mới (trạng thái nằm trong `state/koc.db`, có thể xoá thư mục `state/`) |

---

## Kiến trúc tóm tắt

Phễu "rẻ trước, đắt sau" (chi tiết và lý do: [`ARCHITECTURE.md`](ARCHITECTURE.md)):

| Stage | Làm gì | Chi phí AI |
|---|---|---|
| S0 ingest | Gộp 4 nguồn Kalodata: bảng doanh thu, Top Video Creators, video organic nhiều view, danh sách nghiên cứu web đã kiểm chứng | 0 |
| S1 prefilter | Follower 10k–500k, loại tên brand/shop, chọn 12 × số KOC người theo hạn mức từng nguồn | 0 |
| S2 enrich | Chi tiết Kalodata: nhãn khán giả, video, shop, sản phẩm | 0 |
| S3 metrics | 6 chỉ số định lượng, loại khán giả lệch giới, cờ view/follower thấp | 0 |
| S4 screen | LLM phân loại tài khoản, ngách, mức phù hợp; 8 creator/lần gọi, song song, **dừng sớm khi đủ ứng viên** | rất thấp |
| S5 video | AI xem 1 video/creator cho 2 × số KOC ứng viên (khung hình + phụ đề, hoặc video gốc có tiếng với Gemini) | phần lớn |
| S6 select | Ngưỡng điểm + tối ưu tổ hợp trong ngân sách + tối đa 1 KOC mỗi nhóm agency | 0 |
| S7 rationale | LLM viết lý do, 1 lần gọi mỗi 10 KOC; code kiểm từng mã bằng chứng | thấp |

Trạng thái trong SQLite (`state/koc.db`, chế độ WAL): checkpoint từng item, cache kết quả LLM theo hash input,
sổ token/chi phí/độ trễ, sổ đăng ký creator.

## Cấu trúc thư mục

```
config/   campaign.toml (brief, phễu, trọng số) · models.toml (9 model, giá, định tuyến, benchmark) · market.toml (giá booking)
prompts/  prompt có phiên bản: screen_v1→v4, video_v1→v2, rationale_v1→v2 (giữ bản cũ để so sánh)
data/     kalodata/ snapshot (đã xoá SĐT/email) · market/research.md · videos/ (không commit)
src/koc/  cli.py · pipeline.py · stages/ · llm/ (adapter Anthropic, Gemini, DeepSeek) · store.py · media.py
          audience.py · registry.py · benchmark.py · scale.py (koc scale-test) · web/ (koc serve)
results/  final/ (run nộp bài) · benchmark_models.md/.json · scale_test.md/.json · report.html
tests/    37 test pytest
```

## Giới hạn hiện tại

- **Dữ liệu Kalodata là snapshot thu qua giao diện web** (tài khoản được cấp chưa có API key): 272 creator, 56 trang chi tiết.
  17/60 suất trong shortlist chưa có snapshot nên bị bỏ qua (báo cáo ghi rõ). Bản production dùng Kalodata Open API.
- **Nhân khẩu học follower:** tài khoản được cấp chỉ hiện biểu đồ mẫu giống nhau cho mọi creator. Hệ thống dùng nhãn thô
  Kalodata (`Majority Female`, nhóm tuổi đông nhất), thiếu nữa thì suy từ người dẫn trong video; báo cáo ghi nguồn.
- **Video:** TikTok giấu luồng video của bài gắn giỏ hàng/quảng cáo với người xem không đăng nhập. Prototype lấy mp4 từ CDN
  Kalodata (link hết hạn nhanh); bài không lấy được thì chỉ dùng ảnh bìa và bị trừ điểm.
- **Giá booking KOC là ước tính theo tier follower** (nguồn trong `data/market/research.md`, do Gemini tổng hợp từ web, cần kiểm chứng).
- **Doanh thu có nhiều cơ sở** tuỳ nguồn (danh mục kem chống nắng / mọi ngành hàng / vài video organic). Chỉ so với nhau khi
  cùng cơ sở, khác cơ sở thì coi là trung tính.
- **Video AI xem của `@emlylynguyen` không phải kem chống nắng** (quảng cáo sữa tắm): KOC này được chọn nhờ khán giả và
  cách thể hiện; báo cáo nêu rủi ro và cần brief chặt. Hệ thống chỉ xem 1 video mỗi creator.
- **Mô phỏng 500 KOC dùng dữ liệu và model giả:** đo được cơ chế, số lần gọi, thời gian code; chi phí và thời gian chờ model
  là dự phóng từ số đo thật của run `final`. Chưa chạy 500 KOC thật (chưa có Kalodata API key).
- **LLM có dao động:** chạy lại từ đầu có thể đổi 1–2 KOC sát ngưỡng. Benchmark đo việc này.
- Run `final-haiku` (input của benchmark) thiếu thời gian của stage video bị ngắt ở lần demo sập; lỗi đã sửa trước khi chạy `final`.
- Chưa phân tích bình luận (chất lượng khán giả, tương tác ảo).

## Hướng mở rộng

- Kalodata Open API thay snapshot: `creator/rank`, `video/rank`, `creator/detail`, `video/url` (đã thiết kế trong `ARCHITECTURE.md`).
- Batch API cho bước sàng lọc/video khi quét hàng trăm creator (giảm ~50% chi phí).
- Lấy chi tiết Kalodata theo đợt như bước sàng lọc (500 KOC: ~1.500 thay vì 6.000 lần gọi, xem mục Khả năng mở rộng).
- Xem thêm video khi model chưa chắc (`confidence` thấp), chỉ cho người sát ngưỡng.
- Phân tích bình luận để phát hiện tương tác ảo; học trọng số từ kết quả chiến dịch thật (GMV sau booking).
- Dùng lại phân tích cho **chiến dịch khác** (vd sữa rửa mặt): tách phân tích video thành phần chung (mô tả nội dung, sản phẩm xuất hiện, lộ mặt, thử trên da...) và phần theo chiến dịch (chấm độ phù hợp, rẻ) – thiết kế trong `ARCHITECTURE.md`.
