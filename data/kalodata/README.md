# Snapshot dữ liệu Kalodata

Prototype không gọi API Kalodata trực tiếp. Dữ liệu được thu thập một lần qua giao diện web Kalodata
(tài khoản DETOLA cấp, thị trường Việt Nam) và lưu thành JSON ở đây. Lớp `koc.sources.kalodata`
đọc các file này; bản production thay lớp đó bằng Kalodata Open API mà không phải sửa các stage.

| File | Nội dung | Trang Kalodata |
|---|---|---|
| `creators_list.json` | 150 creator đầu bảng xếp hạng doanh thu, lọc danh mục *Facial Sunscreen & Sun Care* + *Body Sunscreen*, 30 ngày (2026-10-18 → 2026-11-16) | Creator → Filters → Category |
| `creators_list_video.json` | Như trên + preset *Top Video Creators* (bán qua video, không phải livestream) | Creator → My Custom Filters |
| `videos_sunscreen.json` | 100 video kem chống nắng nhiều view nhất 30 ngày, chỉ video **không chạy quảng cáo** (Ad View Ratio = No-ad) | Video & Ad |
| `creators_list_content.json` | 87 creator đứng sau 100 video trên (gộp bằng script), xếp theo tổng view organic. `revenue_vnd` = tổng doanh thu của các video đó, không phải doanh thu cả ngành | suy ra từ `videos_sunscreen.json` |
| `creators_list_research.json` | 24 handle (trong 31 handle Gemini đề xuất từ nghiên cứu web, `data/market/research.md` Mục 5) tìm thấy trên Kalodata VN; 7 handle không tìm thấy (`not_found`). `revenue_vnd` là doanh thu mọi ngành hàng | tìm từng handle ở Creator search |
| `creators/<handle>.json` | Chi tiết 1 creator: nhãn khán giả, 10 video gần đây, shop đã hợp tác, sản phẩm | Creator Detail |

Pipeline gộp mọi file `creators_list*.json` và bỏ trùng theo handle.

Lưu ý:
- Doanh thu, số bán là **ước tính của Kalodata** (họ tự ghi chú "for reference only").
- Số liệu là giá trị hiển thị đã làm tròn (261.8k → 261800).
- **Nhân khẩu học follower:** với tài khoản được cấp, biểu đồ giới tính/tuổi trên trang chi tiết là biểu đồ mẫu,
  giống hệt nhau cho mọi creator (nữ 60% / nam 40%; 18-24 30,5%...). Không dùng số này: `follower_gender` và
  `follower_age` để `null`. API của trang vẫn trả **nhãn thô thật** cho từng creator: `follower_sex_label`
  (vd `Majority Female`) và `follower_age_top` (nhóm tuổi đông nhất, vd `25-34`). Hệ thống dùng nhãn này.
- Phần lớn bài trong danh sách video có cờ quảng cáo (`is_ad`): là bài đăng thật được boost (Spark Ads).
  Nhiều bài của tài khoản affiliate là **bài ảnh (slideshow)**, không có luồng video; hệ thống tự nhận diện.
- Bio đã được lọc số điện thoại/email trước khi đưa vào LLM (`scrub_pii`).

## Schema `creators/<handle>.json`

```json
{
  "handle": "hannahteam.review",
  "kalodata_id": "7549097228750406663",
  "nickname": "hannahteam.review",
  "collected_at": "2026-11-17",
  "date_range": {"start": "2026-10-18", "end": "2026-11-16"},
  "region": "Vietnam",
  "creator_type": "INDEPENDENT",
  "mcn_name": "Olala MCN",
  "bio": "...",
  "followers": 64200,
  "debut_date": "2025-09-28",
  "follower_gender": null,
  "follower_age": null,
  "follower_sex_label": "Majority Female",
  "follower_age_top": "25-34",
  "demographics_note": "biểu đồ chi tiết là placeholder; dùng nhãn thô",
  "core_metrics": {"revenue_vnd": 6700000000, "live_revenue_vnd": 2480000000, "video_revenue_vnd": 3870000000,
                   "video_views": 2690000, "live_views": 141460, "follower_change": 2900},
  "videos": [
    {"video_id": "7671645419348266261", "url": "https://www.tiktok.com/@hannahteam.review/video/7671645419348266261",
     "description": "...", "duration_s": 37.1, "views": 116860, "revenue_vnd": 373430000, "items_sold": 485,
     "is_ad": true, "ad_revenue_ratio": 0.80, "ad_view_ratio": ">90%", "publish_date": "2026-08-08"}
  ],
  "shops": [{"name": "AHC Vietnam", "revenue_vnd": 708670000, "product_count": 11, "items_sold": 948}],
  "products": [{"title": "...", "revenue_vnd": 443740000, "items_sold": 577, "avg_price_vnd": 769050}]
}
```
