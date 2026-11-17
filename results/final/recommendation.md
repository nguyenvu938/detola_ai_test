# Đề xuất KOC – run `final`

> **Dữ liệu đã lưu (cache).** Run chạy lúc 2026-11-17 21:32 với screen=claude-haiku-5-5, video=gemini-3.1-flash-lite, rationale=gemini-3.1-flash-lite; 12 lần gọi model, chi phí $0.0234. Đọc file này không gọi model. Chạy lại: `uv run koc run --run-id final` (cần ANTHROPIC_API_KEY).

## Phễu xử lý

272 creator (gộp các danh sách Kalodata) → lọc luật 161 → lấy chi tiết 60 → đạt khán giả/loại tài khoản 36 → LLM sàng lọc 16 (đạt cổng 13) → phân tích video 9 → đạt ngưỡng điểm 8 → **chọn 5**

## Tóm tắt

Bộ 5 KOC được chọn tập trung vào tệp khán giả nữ 18-30 tuổi với tổng ngân sách 26.25 triệu VNĐ, đảm bảo tối ưu chi phí và bám sát nhóm khách hàng tiềm năng. Sự kết hợp giữa các KOC chuyên review mỹ phẩm và KOC phong cách sống tạo ra độ phủ đa dạng, từ trải nghiệm thực tế đến tối ưu hóa hiệu quả làm đẹp.

## 5 KOC đề xuất

| # | KOC | Follower | Khán giả mục tiêu | Doanh thu 30 ngày (cơ sở) | Điểm | Chi phí ước tính |
|---|---|---|---|---|---|---|
| 1 | [@reviewkemchongnang](https://www.tiktok.com/@reviewkemchongnang) | 37,800 | suy từ video (1.00) | 714.3 tr (danh mục kem chống nắng, mọi kênh bán) | 0.790 | 3.2 tr |
| 2 | [@_huongdaily](https://www.tiktok.com/@_huongdaily) | 164,800 | kalodata: nhãn (Majority Female, tuổi 18-24) | 1.8 tr (từ các video kem chống nắng organic trong bảng xếp hạng) | 0.730 | 8.0 tr |
| 3 | [@lapiszuzu](https://www.tiktok.com/@lapiszuzu) | 102,600 | kalodata: nhãn (Majority Female, tuổi 18-24) | 224.6 tr (mọi ngành hàng) | 0.689 | 8.0 tr |
| 4 | [@emlylynguyen](https://www.tiktok.com/@emlylynguyen) | 87,900 | kalodata: nhãn (Majority Female, tuổi 18-24) | 1.8 tr (từ các video kem chống nắng organic trong bảng xếp hạng) | 0.657 | 3.8 tr |
| 5 | [@trangriviuuu_01](https://www.tiktok.com/@trangriviuuu_01) | 22,200 | kalodata: nhãn (Majority Female, tuổi 18-24) | 57.6 tr (từ các video kem chống nắng organic trong bảng xếp hạng) | 0.631 | 3.2 tr |

Chi phí ước tính = phí review + phí cấp mã Spark Ads theo tier follower (`config/market.toml`). Tổng booking **26.2 tr**, còn **3.8 tr** để chạy Spark Ads cho 2–3 video tốt nhất sau 48 giờ (khuyến nghị 7.5 tr). Hoa hồng affiliate 12–18% tính trên doanh số, không nằm trong ngân sách cố định.

> Còn 3.75 tr cho Spark Ads, thấp hơn mức khuyến nghị 7.5 tr: có thể đàm phán phí theo hoa hồng (12–18%) để giữ ngân sách boost.

Đã phân tích video nhưng dưới ngưỡng điểm: @mai.trinh.h (0.46)

### @reviewkemchongnang

Đây là KOC chuyên biệt về kem chống nắng với doanh thu ngành hàng đạt 714 triệu VNĐ/tháng. Nội dung video sử dụng công nghệ camera UV trực quan giúp khách hàng tin tưởng tuyệt đối vào khả năng bảo vệ của sản phẩm.

- **Rủi ro:** Đã quảng bá cho nhiều nhãn hàng đối thủ trực tiếp và có tỷ lệ view/follower thấp so với chuẩn.
- **Gợi ý brief:** Sử dụng camera UV để chứng minh hiệu quả chống nắng thực tế trên nền da có khuyết điểm.
- **Điểm thành phần:** định lượng 0.78, sàng lọc 0.85, video 0.77 (audience=0.5, category_gmv=0.833, conversion=0.929, views_per_follower=0.157, engagement=0.5, organic=1.0)
- **Video đã phân tích** (native_video): [7697843645805858056](https://www.tiktok.com/@reviewkemchongnang/video/7697843645805858056) – Creator sử dụng công nghệ camera UV để kiểm chứng khả năng bảo vệ của kem chống nắng trên da thực tế. Video trình bày trực quan giúp người xem tin tưởng vào sản phẩm nhờ vào hình ảnh so sánh rõ ràng.
  - `00:00` Người dùng sử dụng camera UV để soi lớp kem trên mặt, hiển thị rõ vùng được bảo vệ bởi kem chống nắng dưới dạng màu đen.
  - `00:03` Creator thoa trực tiếp kem chống nắng lên cánh tay để demo kết cấu và độ thẩm thấu của sản phẩm.
  - `00:13` Creator thoa kem trực tiếp lên vùng da mặt để minh họa hiệu quả bảo vệ và finish trên da.
- Bằng chứng trích dẫn: M:audience, M:gmv, V:7697843645805858056, S:screen

### @_huongdaily

Sở hữu tệp khán giả nữ 18-24 tuổi phù hợp với mục tiêu nhãn hàng. Nội dung phong cách săn sale và review tại cửa hàng như Hasaki rất gần gũi với người dùng phổ thông.

- **Rủi ro:** Tỷ lệ view/follower thấp, phần lớn các bài đăng trước đây là dạng bài khó kiểm định chất lượng hình ảnh.
- **Gợi ý brief:** Thực hiện nội dung dạng 'mua sắm tại quầy' nhấn mạnh vào kết cấu kem và ưu đãi độc quyền.
- **Điểm thành phần:** định lượng 0.63, sàng lọc 0.70, video 0.88 (audience=1.0, category_gmv=0.5, conversion=0.5, views_per_follower=0.043, engagement=0.5, organic=0.948)
- **Video đã phân tích** (native_video): [7693938530099285268](https://www.tiktok.com/@_huongdaily/video/7693938530099285268) – Creator giới thiệu các sản phẩm Kiss My Body tại Hasaki, bao gồm cả kem chống nắng có tích hợp dưỡng da. Video tập trung vào việc săn deal khuyến mãi hấp dẫn dịp 10.10.
  - `00:16` Creator xịt thử sản phẩm lên cổ tay.
  - `00:28` Creator bóp kem dưỡng thể/chống nắng ra mu bàn tay để test kết cấu.
  - `00:53` Cận cảnh tuýp kem có ghi chỉ số SPF 50.
- Bằng chứng trích dẫn: M:audience, V:7693938530099285268, S:screen

### @lapiszuzu

KOC có tỷ lệ tương tác ổn định 3.8% và thế mạnh trong việc kết hợp kem chống nắng với quy trình trang điểm. Đây là nhân tố quan trọng để mở rộng tệp khách hàng quan tâm đến tính thẩm mỹ của sản phẩm.

- **Rủi ro:** Lượt xem phụ thuộc hoàn toàn vào quảng cáo (0% organic) và chưa chuyên sâu về mảng chống nắng.
- **Gợi ý brief:** Xây dựng nội dung kem chống nắng nâng tông thay thế kem lót giúp nền trang điểm bền màu.
- **Điểm thành phần:** định lượng 0.63, sàng lọc 0.55, video 0.85 (audience=1.0, category_gmv=0.5, conversion=0.5, views_per_follower=0.357, engagement=0.976, organic=0.003)
- **Video đã phân tích** (native_video): [7694655061888224564](https://www.tiktok.com/@lapiszuzu/video/7694655061888224564) – Video hướng dẫn mẹo chọn kem chống nắng nâng tông thay kem lót để nền bền và mịn màng. Người làm nội dung test sản phẩm trên da thật và chia sẻ hiệu quả khi trang điểm dưới trời mưa.
  - `00:03` Người dùng so sánh hiệu ứng kem chống nắng lên da mặt.
  - `00:16` Thử nghiệm kết cấu sản phẩm kem chống nắng trên lòng bàn tay.
  - `00:23` Test chỉ số chống nắng bằng thẻ chuyên dụng và đèn tia UV.
  - `00:30` Thao tác thoa kem chống nắng trực tiếp lên toàn bộ gương mặt.
- Bằng chứng trích dẫn: M:audience, M:engagement, V:7694655061888224564

### @emlylynguyen

Tệp khán giả trẻ trung, năng động và có khả năng lan tỏa nội dung lifestyle mạnh mẽ. Dù là KOC đa ngành, kinh nghiệm review sản phẩm nâng tone sẽ là bước đệm tốt cho chiến dịch.

- **Rủi ro:** Đã từng nhầm lẫn nội dung sản phẩm (review sữa tắm thay vì chống nắng) và có tỷ lệ view/follower chưa đạt chuẩn.
- **Gợi ý brief:** Tạo video lifestyle gắn kem chống nắng vào quy trình chuẩn bị trang điểm trước khi ra ngoài.
- **Điểm thành phần:** định lượng 0.64, sàng lọc 0.50, video 0.77 (audience=1.0, category_gmv=0.5, conversion=0.5, views_per_follower=0.1, engagement=0.5, organic=1.0)
- **Video đã phân tích** (native_video): [7701307939755232530](https://www.tiktok.com/@emlylynguyen/video/7701307939755232530) – Video quảng cáo sữa tắm Hazeline tập trung vào khả năng làm sáng, thơm da và chương trình khuyến mãi rinh nhẫn kim cương. Nội dung không liên quan đến kem chống nắng nên không phù hợp với chiến dịch yêu cầu.
  - `00:03` Người làm nội dung xuất hiện giới thiệu sản phẩm sữa tắm Hazeline.
  - `00:27` Demo sản phẩm sữa tắm thoa lên tay để cho thấy chất gel và bọt.
  - `00:58` Nhãn sản phẩm ghi rõ là sữa tắm, không phải kem chống nắng.
- Bằng chứng trích dẫn: M:audience, V:7701307939755232530

### @trangriviuuu_01

KOC có doanh thu ổn định từ các video review chống nắng (58 triệu VNĐ/tháng) và thế mạnh về visual sản phẩm. Khả năng làm nổi bật tính năng nâng tone da là điểm cộng lớn cho chiến dịch.

- **Rủi ro:** Đã từng quảng bá cho nhãn hàng đối thủ và lượt xem organic còn ở mức khiêm tốn.
- **Gợi ý brief:** Tập trung vào quay cận cảnh chất kem và so sánh độ nâng tone tự nhiên trên hai vùng da tay.
- **Điểm thành phần:** định lượng 0.67, sàng lọc 0.55, video 0.62 (audience=1.0, category_gmv=0.5, conversion=0.5, views_per_follower=0.871, engagement=0.5, organic=0.191)
- **Video đã phân tích** (native_video): [7691676006473534740](https://www.tiktok.com/@trangriviuuu_01/video/7691676006473534740) – Video review kem chống nắng kết hợp dưỡng trắng và nâng tông da với kết cấu mỏng nhẹ. Sản phẩm được test trực tiếp trên da tay để người xem dễ dàng quan sát hiệu ứng.
  - `00:02` Người dùng thoa kem chống nắng trực tiếp lên lòng bàn tay và mu bàn tay.
  - `00:05` So sánh phần da đã thoa kem (nâng tông rõ rệt) với vùng da bên cạnh.
  - `00:24` Cận cảnh chất kem trắng mịn được tán đều trên da tay.
- Bằng chứng trích dẫn: M:audience, M:gmv, V:7691676006473534740

Kiểm tra trích dẫn bằng code: 15 mã, sai 0, khớp danh sách KOC: True.

## So với lần quét trước

Mới 0 · thay đổi 0 · không đổi 43 · quá hạn 0 (sổ đăng ký creator, `koc changes`). Creator không đổi được dùng lại kết quả phân tích cũ; chỉ phần mới (video mới, hồ sơ đổi) mới gọi model.


## Chi phí AI và thời gian

| Stage | Model | Lần gọi | Dùng lại kết quả cũ | Token vào | Token ra | USD | Tiết kiệm nhờ dùng lại | Độ trễ TB (ms) |
|---|---|---|---|---|---|---|---|---|
| screen | claude-haiku-5-5 | 2 | 0 | 21,122 | 9,606 | 0.0064 | 0.0000 | 20476 |
| video | gemini-3.1-flash-lite | 9 | 0 | 40,884 | 3,091 | 0.0149 | 0.0000 | 8193 |
| rationale | gemini-3.1-flash-lite | 1 | 0 | 2,411 | 1,033 | 0.0022 | 0.0000 | 3976 |

**Tổng chi phí AI: $0.0234** (≈ 609 VNĐ, tỷ giá tham khảo 26.000).

| Stage | Thời gian xử lý cộng dồn (s) |
|---|---|
| enrich | 8.9 |
| ingest+prefilter | 0.0 |
| rationale | 4.3 |
| screen | 45.4 |
| video | 34.0 |

**Tổng thời gian xử lý: 93 giây** (cộng các stage qua mọi lần chạy/resume; lần chạy cuối mất 36.7s). **Token: 64,417 vào / 13,730 ra.**

Định tuyến model: screen=claude-haiku-5-5, video=gemini-3.1-flash-lite, rationale=gemini-3.1-flash-lite

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
