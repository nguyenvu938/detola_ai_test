# Đề xuất KOC – run `final-haiku`

> **Dữ liệu đã lưu (cache).** Run chạy lúc 2026-11-17 20:32 với screen=claude-haiku-5-5, video=claude-haiku-5-5, rationale=claude-sonnet-5-5; 12 lần gọi model, chi phí $0.0466. Đọc file này không gọi model. Chạy lại: `uv run koc run --run-id final-haiku` (cần ANTHROPIC_API_KEY).

## Phễu xử lý

272 creator (gộp các danh sách Kalodata) → lọc luật 161 → lấy chi tiết 60 → đạt khán giả/loại tài khoản 36 → LLM sàng lọc 16 (đạt cổng 13) → phân tích video 9 → đạt ngưỡng điểm 5 → **chọn 4**

## Tóm tắt

Đầu vào chỉ có 4 KOC (không đủ bộ 5): nhóm này phủ khán giả nữ 18–30 tuổi qua các ngách skincare review và beauty makeup, trong đó reviewkemchongnang có độ liên quan kem chống nắng cao nhất (9/10). Tổng chi phí ước tính của 4 KOC là 27,25 triệu VNĐ, còn khoảng 2,75 triệu VNĐ trong ngân sách 30 triệu cho vị trí thứ 5, và ngân sách dồn vào 3 KOC mức 8 triệu cùng 1 KOC mức 3,25 triệu.

## 5 KOC đề xuất

| # | KOC | Follower | Khán giả mục tiêu | Doanh thu 30 ngày (cơ sở) | Điểm | Chi phí ước tính |
|---|---|---|---|---|---|---|
| 1 | [@reviewkemchongnang](https://www.tiktok.com/@reviewkemchongnang) | 37,800 | suy từ video (1.00) | 714.3 tr (danh mục kem chống nắng, mọi kênh bán) | 0.704 | 3.2 tr |
| 2 | [@lapiszuzu](https://www.tiktok.com/@lapiszuzu) | 102,600 | kalodata: nhãn (Majority Female, tuổi 18-24) | 224.6 tr (mọi ngành hàng) | 0.609 | 8.0 tr |
| 3 | [@ngoc.matcha.review](https://www.tiktok.com/@ngoc.matcha.review) | 145,800 | kalodata: nhãn (Majority Female, tuổi 18-24) | 524.4 tr (danh mục kem chống nắng, mọi kênh bán) | 0.602 | 8.0 tr |
| 4 | [@_huongdaily](https://www.tiktok.com/@_huongdaily) | 164,800 | kalodata: nhãn (Majority Female, tuổi 18-24) | 1.8 tr (từ các video kem chống nắng organic trong bảng xếp hạng) | 0.558 | 8.0 tr |

Chi phí ước tính = phí review + phí cấp mã Spark Ads theo tier follower (`config/market.toml`). Tổng booking **27.2 tr**, còn **2.8 tr** để chạy Spark Ads cho 2–3 video tốt nhất sau 48 giờ (khuyến nghị 7.5 tr). Hoa hồng affiliate 12–18% tính trên doanh số, không nằm trong ngân sách cố định.

> Còn 2.75 tr cho Spark Ads, thấp hơn mức khuyến nghị 7.5 tr: có thể đàm phán phí theo hoa hồng (12–18%) để giữ ngân sách boost.

> 5 KOC đạt ngưỡng nhưng không bộ 5 người nào vừa 30 tr (bộ 5 tốt nhất tốn 30.50 tr, vượt 0.50 tr). Đề xuất 4 KOC; muốn đủ 5 thì thêm @beobeo.21 và đàm phán giảm 0.50 tr (vd bỏ phí cấp mã Spark Ads của 1 KOC, hoặc trả theo hoa hồng).

Đã phân tích video nhưng dưới ngưỡng điểm: @trangriviuuu_01 (0.48), @milohongg (0.44), @mai.trinh.h (0.43), @emlylynguyen (0.39)

### @reviewkemchongnang

Đây là KOC chuyên kem chống nắng, được chấm liên quan 9/10, khán giả suy ra từ video khớp nữ 18–30 tuổi (1.00). Doanh thu 30 ngày của danh mục kem chống nắng ≈ 714 triệu VNĐ và 100% lượt xem không đến từ quảng cáo, cho thấy tăng trưởng tự nhiên. Chi phí 3,25 triệu VNĐ là thấp nhất bộ.

- **Rủi ro:** View/follower chỉ 2%, thấp hơn chuẩn 20%, và chưa có engagement rate. KOC đã quảng bá nhiều nhãn đối thủ (Meiking, Sunplay, Anessa, L'Oreal Paris UV Defender...) nên cần điều khoản độc quyền hoặc giãn thời gian. Video mẫu chưa có phụ đề và phần so sánh còn mơ hồ.
- **Gợi ý brief:** Dùng format soi UV camera và thoa thử lên da để cho thấy độ phủ của sản phẩm, bổ sung phụ đề và kết luận so sánh rõ ràng.
- **Điểm thành phần:** định lượng 0.78, sàng lọc 0.75, video 0.58 (audience=0.5, category_gmv=0.833, conversion=0.929, views_per_follower=0.157, engagement=0.5, organic=1.0)
- **Video đã phân tích** (keyframes): [7697843645805858056](https://www.tiktok.com/@reviewkemchongnang/video/7697843645805858056) – Creator nữ trẻ dùng UV camera và đối chiếu 11 sản phẩm kem chống nắng, có thoa thử sản phẩm lên cánh tay và mặt. Hook dựa vào hình ảnh soi UV gây tò mò, nhưng chưa có phụ đề và phần so sánh còn mơ hồ.
  - `frame 1 @ 0.5s` Hình ảnh UV camera đen trắng soi khuôn mặt kèm nhãn 'SOI RÕ LỚP KEM BẢO VỆ DA' và dãy 11 sản phẩm đánh số
  - `frame 2 @ 2.5s` Creator lộ mặt cầm chai kem chống nắng L'Oréal trước camera
  - `frame 5 @ 20.5s` Thoa kem thử lên cánh tay, kết cấu kem trắng hiện rõ trên da
  - `frame 6 @ 27.3s` Tiếp tục thoa kem lên cánh tay và đưa tuýp kem về phía camera
- Bằng chứng trích dẫn: M:audience, M:gmv, M:organic, S:screen, V:7697843645805858056

### @lapiszuzu

Khán giả theo Kalodata nghiêng về nữ, tuổi 18–24, đúng tệp mục tiêu, và engagement rate đạt 3,80%. Ngách makeup có video dùng kem chống nắng nâng tone thay kem lót, liên quan 7/10, thoa thử trực tiếp lên da và có thẻ thử UV SPF 50+ PA++++.

- **Rủi ro:** 0% lượt xem không đến từ quảng cáo, nghĩa là phụ thuộc nhiều vào quảng cáo trả phí. Doanh thu 225 triệu VNĐ tính mọi ngành hàng chứ không riêng kem chống nắng. Video mẫu có câu như "không trôi" và so sánh cần kiểm soát claim.
- **Gợi ý brief:** Làm video kem chống nắng như bước lót nền: thoa thử, so sánh lớp nền trước và sau, nhấn mạnh hiệu ứng lì và mịn nhưng tránh claim tuyệt đối.
- **Điểm thành phần:** định lượng 0.63, sàng lọc 0.55, video 0.62 (audience=1.0, category_gmv=0.5, conversion=0.5, views_per_follower=0.357, engagement=0.976, organic=0.003)
- **Video đã phân tích** (keyframes): [7694655061888224564](https://www.tiktok.com/@lapiszuzu/video/7694655061888224564) – Creator nữ trẻ giới thiệu cách dùng kem chống nắng nâng tone thay kem lót để nền không trôi và kiềm dầu, có thoa thử sản phẩm lên da và cho thấy hiệu ứng bóng/lì trên mặt. Nội dung liên quan trực tiếp đến kem chống nắng, nhưng có vài câu quảng cáo "không trôi" và so sánh cần kiểm soát.
  - `00:00` Tiêu đề chữ trên màn hình "1 tuýp kem chống nắng nâng tone = kem lót + nền mịn ráo" với người nói cầm hai tuýp sản phẩm, lộ mặt rõ.
  - `00:02` Thoa sản phẩm màu trắng lên da mặt, kết cấu sữa tạo lớp mỏng trên má.
  - `00:24` Cận cảnh da mặt sau khi thoa cho thấy độ bóng/ẩm và chữ "Giúp lớp nền trông đẹp hơn á chó".
  - `00:36` Thẻ thử UV hiển thị trên màn hình khi bóp tuýp kem chống nắng ghi SPF 50+ PA++++, minh họa thử nghiệm sản phẩm.
  - `00:48` Thoa tay lên mặt người mẫu thứ hai, lớp nền hiển thị với chữ "chính là do dùng kem chống nắng nâng tone chưa phù hợp".
- Bằng chứng trích dẫn: M:audience, M:engagement, S:screen, V:7694655061888224564

### @ngoc.matcha.review

Khán giả theo Kalodata nghiêng về nữ, tuổi 18–24, và doanh thu 30 ngày của danh mục kem chống nắng ≈ 524 triệu VNĐ, cho thấy tiềm năng chuyển đổi. KOC có quy mô lớn (145.800 follower) và lộ mặt, swatch sản phẩm trên da rõ ràng.

- **Rủi ro:** Độ liên quan kem chống nắng chỉ 5/10 và chưa thấy video kem chống nắng nào. Engagement rate chỉ 0,60%, 0% lượt xem không đến từ quảng cáo nên phụ thuộc quảng cáo. Video mẫu là review son, ánh sáng và khung hình ở mức trung bình.
- **Gợi ý brief:** Đặt kem chống nắng vào routine makeup hằng ngày, tận dụng kỹ năng swatch và thoa thử lên da để thể hiện kết cấu.
- **Điểm thành phần:** định lượng 0.58, sàng lọc 0.50, video 0.69 (audience=1.0, category_gmv=0.548, conversion=0.31, views_per_follower=0.614, engagement=0.31, organic=0.0)
- **Video đã phân tích** (keyframes): [7699089843313184008](https://www.tiktok.com/@ngoc.matcha.review/video/7699089843313184008) – Bài đăng review son 2 đầu (son dưỡng và son màu) chứ không phải kem chống nắng nên không đúng chủ đề chiến dịch. Creator lộ mặt, swatch son lên da tay và cho thấy độ bám màu đỏ hồng, nhưng ánh sáng và khung hình ở mức trung bình.
  - `frame 1 @ 0.5s` Creator lộ mặt, cầm một cây son màu đỏ hồng hướng về camera, có chữ hoặc sản phẩm trên kệ phía sau.
  - `frame 4 @ 20.3s` Cầm đầu son hai đầu đưa lên, có vệt swatch màu đỏ hồng trên mu bàn tay.
  - `frame 6 @ 40.7s` Swatch màu đỏ san hô đậm trên mu bàn tay, bóng nước, cho thấy kết cấu sau khi thoa.
- Bằng chứng trích dẫn: M:audience, M:gmv, M:engagement, S:screen, V:7699089843313184008

### @_huongdaily

Khán giả theo Kalodata nghiêng về nữ, tuổi 18–24, ngách skincare review liên quan 7/10 và đã có nội dung chống nắng La Roche-Posay, AHC. 95% lượt xem không đến từ quảng cáo, cho thấy nội dung được xem tự nhiên.

- **Rủi ro:** View/follower 0% (chuẩn 10%), chưa có engagement rate và doanh thu kem chống nắng organic chỉ ≈ 2 triệu VNĐ. Đã quảng bá La Roche-Posay Anthelios và AHC, và 4/5 bài đã kiểm không xem được hình. Video mẫu là deal Hasaki, không thoa thử hay cho thấy kết cấu.
- **Gợi ý brief:** Làm video review kem chống nắng thật tại nhà hoặc tại cửa hàng, có thoa thử lên da, mô tả kết cấu và cảm giác sau thoa, thay vì dạng săn sale.
- **Điểm thành phần:** định lượng 0.63, sàng lọc 0.70, video 0.39 (audience=1.0, category_gmv=0.5, conversion=0.5, views_per_follower=0.043, engagement=0.5, organic=0.948)
- **Video đã phân tích** (keyframes): [7693938530099285268](https://www.tiktok.com/@_huongdaily/video/7693938530099285268) – Bài đăng là video quảng bá deal 10.10 tại Hasaki, nhấn mạnh các sản phẩm Kiss My Body và giá sale, không phải nội dung về kem chống nắng. Creator lộ mặt, cầm và xem sản phẩm trong cửa hàng nhưng không thoa thử lên da và không cho thấy kết cấu hay hiệu ứng.
  - `0:00` Khung hình đầu có tiêu đề 'Săn gì ở Hasaki?' và creator đứng trước cửa hàng, giơ tay chỉ lên, tạo hook bằng câu hỏi về deal.
  - `frame 4` Creator cầm một chai sản phẩm trước kệ hàng Kiss My Body, quan sát nhãn nhưng không thoa lên da.
  - `frame 5` Creator xoa tay có sản phẩm trắng nhưng khung hình không rõ kết cấu, đang hiển thị nhãn giá 89K.
  - `frame 6` Creator quay bằng camera cầm tay trước gương trong cửa hàng, không có cảnh thử sản phẩm trên da.
- Bằng chứng trích dẫn: M:audience, M:organic, S:screen, V:7693938530099285268

Kiểm tra trích dẫn bằng code: 18 mã, sai 0, khớp danh sách KOC: True.

## Chi phí AI và thời gian

| Stage | Model | Lần gọi | Cache hit | Token vào | Token ra | USD | Độ trễ TB (ms) |
|---|---|---|---|---|---|---|---|
| screen | claude-haiku-5-5 | 2 | 0 | 21,074 | 8,679 | 0.0063 | 18751 |
| video | claude-haiku-5-5 | 9 | 0 | 41,392 | 5,800 | 0.0057 | 4176 |
| rationale | claude-sonnet-5-5 | 1 | 0 | 4,603 | 2,472 | 0.0346 | 16929 |

**Tổng chi phí AI: $0.0466** (≈ 1,212 VNĐ, tỷ giá tham khảo 26.000).

| Stage | Thời gian xử lý cộng dồn (s) |
|---|---|
| enrich | 15.1 |
| ingest+prefilter | 0.0 |
| rationale | 17.3 |
| screen | 42.0 |
| video | 21.1 |

Thời gian lần chạy này: 2.5s.

Định tuyến model: screen=claude-haiku-5-5, video=claude-haiku-5-5, rationale=claude-sonnet-5-5

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
