"""Schema output của từng bước LLM. Model bắt buộc trả đúng cấu trúc này (structured output),
nên code phía sau đọc thẳng các trường, không phải đoán định dạng."""
from typing import Literal

from pydantic import BaseModel, Field


# ---------- Stage 4: screen (text) ----------
class CreatorScreen(BaseModel):
    handle: str
    account_kind: Literal["individual_creator", "brand_official", "shop_seller", "agency_team", "unknown"]
    primary_niche: Literal["skincare_review", "beauty_makeup", "deal_affiliate", "lifestyle", "other"]
    topic_relevance: int = Field(description="0-10: mức nội dung xoay quanh sản phẩm của chiến dịch")
    content_signals: list[str] = Field(description="tối đa 4 tag ngắn về phong cách nội dung")
    competitor_brands: list[str] = Field(description="các thương hiệu CÙNG LOẠI SẢN PHẨM với chiến dịch mà creator đã quảng bá")
    brand_safety_flags: list[str] = Field(description="rủi ro: claim y tế, nói quá, nội dung nhạy cảm... rỗng nếu không có")
    fit_note: str = Field(description="1 câu tiếng Việt <= 25 từ")


class ScreenBatch(BaseModel):
    creators: list[CreatorScreen]


# ---------- Stage 5: video ----------
class Evidence(BaseModel):
    at: str = Field(description="mốc thời gian (vd '00:04') hoặc số khung (vd 'frame 3')")
    observation: str


class VideoAnalysis(BaseModel):
    is_on_topic: bool
    face_on_camera: bool
    product_demo_on_skin: bool = Field(description="có thoa/test sản phẩm trên da thật không")
    shows_texture_or_finish: bool
    hook_strength: int = Field(description="1-5: 3 giây đầu có giữ chân người xem không")
    production_quality: int = Field(description="1-5")
    presenter_gender: Literal["female", "male", "unclear"]
    presenter_age_band: Literal["under_18", "18_24", "25_34", "35_plus", "unclear"]
    risky_claims: list[str] = Field(description="claim có thể vi phạm quảng cáo mỹ phẩm, vd 'trị nám dứt điểm'")
    style_tags: list[str] = Field(description="tối đa 4 tag")
    summary_vi: str = Field(description="2 câu tiếng Việt")
    evidence: list[Evidence] = Field(description="2-4 bằng chứng cụ thể quan sát được")
    confidence: float = Field(description="0-1: độ chắc chắn của phân tích")


# ---------- Stage 7: rationale ----------
class KocRationale(BaseModel):
    handle: str
    reason_vi: str = Field(description="2-3 câu: vì sao hợp chiến dịch")
    evidence_refs: list[str] = Field(description="mã bằng chứng lấy từ input, vd 'M:audience', 'V:7671645419348266261'")
    risks_vi: str
    brief_suggestion_vi: str = Field(description="1 câu gợi ý góc nội dung cho KOC này")


class RationaleSet(BaseModel):
    summary_vi: str = Field(description="2 câu tổng quan về các KOC trong danh sách được gửi")
    kocs: list[KocRationale]
