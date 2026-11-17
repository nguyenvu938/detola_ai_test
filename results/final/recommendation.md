# Đề xuất KOC – run `final`

> **Dữ liệu đã lưu (cache).** Run chạy lúc 2026-11-18 06:32 với screen=gemini-3.8-flash, video=gemini-3.5-flash-lite, rationale=gemini-3.1-flash-lite; 12 lần gọi model, chi phí $0.0372. Đọc file này không gọi model. Chạy lại: `uv run koc run --run-id final` (cần GEMINI_API_KEY; chỉ có ANTHROPIC_API_KEY thì mọi bước tự dùng Claude Haiku).

## Phễu xử lý

272 creator (gộp các danh sách Kalodata) → lọc luật 161 → lấy chi tiết 60 → đạt khán giả/loại tài khoản 36 → LLM sàng lọc 16 (đạt cổng 11) → phân tích video 9 → đạt ngưỡng điểm 8 → **chọn 5**

## Tóm tắt

Danh sách 5 KOC được chọn giúp tối ưu hóa ngân sách 30 triệu VNĐ, tập trung vào đối tượng nữ giới 18-30 tuổi với sự cân bằng giữa các KOC chuyên sâu về skincare và KOC có khả năng chuyển đổi doanh số. Phân bổ ngân sách đảm bảo độ phủ rộng, kết hợp giữa các kênh chuyên gia uy tín và các kênh có khả năng kéo traffic mạnh cho chiến dịch.

## 5 KOC đề xuất

| # | KOC | Follower | Khán giả mục tiêu | Doanh thu 30 ngày (cơ sở) | Điểm | Chi phí ước tính |
|---|---|---|---|---|---|---|
| 1 | [@reviewkemchongnang](https://www.tiktok.com/@reviewkemchongnang) | 37,800 | suy từ video (1.00) | 714.3 tr (danh mục kem chống nắng, mọi kênh bán) | 0.874 | 3.2 tr |
| 2 | [@lapiszuzu](https://www.tiktok.com/@lapiszuzu) | 102,600 | kalodata: nhãn (Majority Female, tuổi 18-24) | 224.6 tr (mọi ngành hàng) | 0.724 | 8.0 tr |
| 3 | [@trangriviuuu_01](https://www.tiktok.com/@trangriviuuu_01) | 22,200 | kalodata: nhãn (Majority Female, tuổi 18-24) | 57.6 tr (từ các video kem chống nắng organic trong bảng xếp hạng) | 0.713 | 3.2 tr |
| 4 | [@anhonanngon](https://www.tiktok.com/@anhonanngon) | 33,500 | kalodata: nhãn (Majority Female, tuổi 18-24) | 280.2 tr (danh mục kem chống nắng, mọi kênh bán) | 0.614 | 3.2 tr |
| 5 | [@_huongdaily](https://www.tiktok.com/@_huongdaily) | 164,800 | kalodata: nhãn (Majority Female, tuổi 18-24) | 1.8 tr (từ các video kem chống nắng organic trong bảng xếp hạng) | 0.586 | 8.0 tr |

Chi phí ước tính = phí review + phí cấp mã Spark Ads theo tier follower (`config/market.toml`). Tổng booking **25.8 tr**, còn **4.2 tr** để chạy Spark Ads cho 2–3 video tốt nhất sau 48 giờ (khuyến nghị 7.5 tr). Hoa hồng affiliate 12–18% tính trên doanh số, không nằm trong ngân sách cố định.

> Còn 4.25 tr cho Spark Ads, thấp hơn mức khuyến nghị 7.5 tr: có thể đàm phán phí theo hoa hồng (12–18%) để giữ ngân sách boost.

Đã phân tích video nhưng dưới ngưỡng điểm: @linhnhirv.68 (0.49)

### @reviewkemchongnang

Kênh chuyên sâu 10/10 về kem chống nắng với doanh thu 30 ngày đạt khoảng 714 triệu VNĐ. Nội dung minh bạch, sử dụng camera UV để chứng minh hiệu quả bảo vệ da, rất phù hợp để xây dựng lòng tin sản phẩm.

- **Rủi ro:** Tỉ lệ view/follower thấp, đã quảng bá cho nhiều nhãn hàng đối thủ trực tiếp trong ngành kem chống nắng.
- **Gợi ý brief:** Sử dụng camera UV để kiểm chứng khả năng bảo vệ của sản phẩm một cách trực quan nhất.
- **Điểm thành phần:** định lượng 0.78, sàng lọc 1.00, video 0.92 (audience=0.5, category_gmv=0.841, conversion=0.932, views_per_follower=0.157, engagement=0.5, organic=1.0)
- **Video đã phân tích** (native_video): [7697843645805858056](https://www.tiktok.com/@reviewkemchongnang/video/7697843645805858056) – Creator giới thiệu và tư vấn các loại kem chống nắng khác nhau, sử dụng camera UV để kiểm tra khả năng bảo vệ da. Video có hình ảnh test sản phẩm trực tiếp trên tay và khuôn mặt của người nói.
  - `00:00` Creator cầm tuýp kem chống nắng L'Oreal trên tay, phía trên có khung hình từ camera UV soi lớp kem.
  - `00:13` Creator chỉ tay lên má để chỉ vị trí đã test kem chống nắng trên mặt.
  - `00:33` Creator thoa và test sản phẩm kem chống nắng trực tiếp lên vùng da tay.
- Bằng chứng trích dẫn: M:audience, M:gmv, S:screen, V:7697843645805858056

### @lapiszuzu

KOC có tệp khán giả nữ 18-24 tuổi đông đảo và tỷ lệ tương tác ổn định 3.8%. Thế mạnh là nội dung review kem chống nắng kết hợp làm lớp lót nền giúp sản phẩm tiếp cận khách hàng làm đẹp hiệu quả.

- **Rủi ro:** 100% lượt xem đến từ quảng cáo, cần lưu ý về tính bền vững của nội dung khi ngừng chạy ads.
- **Gợi ý brief:** Demo sản phẩm như một lớp lót (primer) hoàn hảo cho lớp nền trang điểm mịn màng.
- **Điểm thành phần:** định lượng 0.63, sàng lọc 0.60, video 0.92 (audience=1.0, category_gmv=0.5, conversion=0.5, views_per_follower=0.357, engagement=0.976, organic=0.003)
- **Video đã phân tích** (native_video): [7694655061888224564](https://www.tiktok.com/@lapiszuzu/video/7694655061888224564) – Video chia sẻ bí kíp chọn kem chống nắng nâng tông thay thế kem lót giúp lớp nền mịn ráo, không bị trượt nền. Creator review chi tiết dòng Peacholic Fresh Calming Sun Gel và test trực tiếp lên da.
  - `00:01` Creator xuất hiện và giới thiệu về kem chống nắng nâng tông thay kem lót.
  - `00:17` Review và test chất kem Peacholic Fresh Calming Sun Gel trên tay.
  - `00:30` Thoa trực tiếp kem chống nắng lên mặt để demo khả năng làm lớp lót và nâng tông.
- Bằng chứng trích dẫn: M:audience, M:engagement, S:screen, V:7694655061888224564

### @trangriviuuu_01

KOC tập trung vào dòng skincare bình dân, phù hợp với đối tượng khách hàng nữ 18-24 tuổi quan tâm đến giá cả. Kênh có độ phủ organic tốt (19%) giúp tăng tính chân thực cho nội dung.

- **Rủi ro:** Đã quảng bá sản phẩm đối thủ (YOQQ), cần làm rõ USP của nhãn hàng để tạo sự khác biệt.
- **Gợi ý brief:** Tập trung review kết cấu và độ nâng tông tự nhiên trên da một cách gần gũi.
- **Điểm thành phần:** định lượng 0.67, sàng lọc 0.70, video 0.77 (audience=1.0, category_gmv=0.5, conversion=0.5, views_per_follower=0.871, engagement=0.5, organic=0.191)
- **Video đã phân tích** (native_video): [7691676006473534740](https://www.tiktok.com/@trangriviuuu_01/video/7691676006473534740) – Video review kem chống nắng kiêm dưỡng trắng và nâng tông tự nhiên với bảng thành phần hoạt chất. Creator thực hiện thao tác thoa sản phẩm trực tiếp lên da để minh họa kết cấu và độ nâng tông.
  - `00:03` Nặn kem chống nắng ra tay để test sản phẩm.
  - `00:05` Thoa và tán kem chống nắng lên vùng da tay để cho thấy độ nâng tông.
  - `00:08` Quay cận cảnh vỏ hộp kem chống nắng có in thông tin SPF và các hoạt chất.
- Bằng chứng trích dẫn: M:audience, M:organic, S:screen, V:7691676006473534740

### @anhonanngon

Đạt doanh thu 280 triệu VNĐ từ danh mục kem chống nắng trong 30 ngày, chứng tỏ khả năng chuyển đổi đơn hàng tốt dù là kênh đa dạng nội dung. Có kinh nghiệm test sản phẩm trực tiếp với thẻ cảm ứng tia UV.

- **Rủi ro:** Mức độ chuyên môn về làm đẹp chưa cao, đã quảng bá sản phẩm đối thủ (YOQQ).
- **Gợi ý brief:** Thực hiện bài test khả năng chống tia UV bằng thẻ cảm ứng để tạo điểm nhấn thị giác mạnh.
- **Điểm thành phần:** định lượng 0.59, sàng lọc 0.40, video 0.77 (audience=1.0, category_gmv=0.25, conversion=0.386, views_per_follower=0.9, engagement=0.452, organic=0.0)
- **Video đã phân tích** (native_video): [7700984589732318482](https://www.tiktok.com/@anhonanngon/video/7700984589732318482) – Video review kem chống nắng kết hợp test thử khả năng chống tia UV bằng thẻ cảm ứng và thoa trực tiếp lên da tay. Sản phẩm cho thấy khả năng nâng tông rõ rệt và chất kem dễ tán.
  - `00:02` Dùng tăm lấy kem chống nắng test lên thẻ cảm ứng tia UV
  - `00:16` Bơm kem chống nắng trực tiếp lên cổ tay và thoa đều
  - `00:35` So sánh hai tay trước và sau khi bôi kem chống nắng để thấy hiệu quả nâng tông
- Bằng chứng trích dẫn: M:gmv, V:7700984589732318482, S:competitors

### @_huongdaily

KOC làm đẹp uy tín với tệp khán giả 18-24 tuổi, có khả năng xây dựng nội dung chuyên nghiệp. 95% lượt xem tự nhiên cho thấy cộng đồng người theo dõi chất lượng.

- **Rủi ro:** Nhiều video là bài quảng cáo, đã hợp tác với các ông lớn (La Roche-Posay, AHC), cần đầu tư nội dung sáng tạo để tránh bão hòa.
- **Gợi ý brief:** Lồng ghép sản phẩm vào chu trình chăm sóc da hàng ngày tại các cửa hàng mỹ phẩm uy tín.
- **Điểm thành phần:** định lượng 0.63, sàng lọc 0.70, video 0.47 (audience=1.0, category_gmv=0.5, conversion=0.5, views_per_follower=0.043, engagement=0.5, organic=0.948)
- **Video đã phân tích** (native_video): [7693938530099285268](https://www.tiktok.com/@_huongdaily/video/7693938530099285268) – Video ghi lại hành trình dạo cửa hàng Hasaki để săn sale các sản phẩm body mist và lotion thơm ngát của hãng Kiss My Body. Creator có test thử texture sản phẩm lên da và chia sẻ các khung giờ săn deal hấp dẫn.
  - `00:00` Creator đứng trước cửa hàng Hasaki giới thiệu chương trình 10.10.
  - `00:28` Test thử kết cấu lotion lên mu bàn tay.
  - `00:40` Giới thiệu chương trình giảm giá lotion và body mist.
- Bằng chứng trích dẫn: M:audience, M:organic, S:screen, V:7693938530099285268

Kiểm tra trích dẫn bằng code: 19 mã, sai 0, khớp danh sách KOC: True.

## So với lần quét trước

Mới 0 · thay đổi 0 · không đổi 43 · quá hạn 0 (sổ đăng ký creator, `koc changes`). Creator không đổi được dùng lại kết quả phân tích cũ; chỉ phần mới (video mới, hồ sơ đổi) mới gọi model.


## Chi phí AI và thời gian

| Stage | Model | Lần gọi | Dùng lại kết quả cũ | Token vào | Token ra | USD | Tiết kiệm nhờ dùng lại | Độ trễ TB (ms) |
|---|---|---|---|---|---|---|---|---|
| screen | gemini-3.8-flash | 2 | 0 | 10,710 | 2,164 | 0.0161 | 0.0000 | 9380 |
| video | gemini-3.5-flash-lite | 9 | 0 | 39,140 | 2,835 | 0.0188 | 0.0000 | 4184 |
| rationale | gemini-3.1-flash-lite | 1 | 0 | 2,353 | 1,077 | 0.0022 | 0.0000 | 3360 |

**Tổng chi phí AI: $0.0372** (≈ 967 VNĐ, tỷ giá tham khảo 26.000).

| Stage | Thời gian xử lý cộng dồn (s) |
|---|---|
| enrich | 0.0 |
| ingest+prefilter | 0.0 |
| rationale | 3.4 |
| screen | 10.1 |
| video | 16.7 |

**Tổng thời gian xử lý: 30 giây** (cộng các stage qua mọi lần chạy/resume; lần chạy cuối mất 30.2s). **Token: 52,203 vào / 6,076 ra.**

Định tuyến model: screen=gemini-3.8-flash, video=gemini-3.5-flash-lite, rationale=gemini-3.1-flash-lite

## Ứng viên bị loại ở các bước sau (trích)

- @hagiangreview1: Kalodata: Majority Male (lệch giới mục tiêu)
- @hoaivan6868: creator_type=BELONGED_TO_SELLER
- @truonghienthehigh: creator_type=BELONGED_TO_SELLER
- @tuyentanuytin2: chưa có dữ liệu chi tiết
- @thuongtone: Kalodata: Majority Male (lệch giới mục tiêu)
- @linhsan1029: chưa có dữ liệu chi tiết
- @quenhii.pham: chưa có dữ liệu chi tiết
- @chunhungne: chưa có dữ liệu chi tiết
- @phuong_phuong999: chưa có dữ liệu chi tiết
- @danquynh.daily: Kalodata: Majority Male (lệch giới mục tiêu)
