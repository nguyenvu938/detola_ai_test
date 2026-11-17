"""Đo độ khớp khán giả với brief (giới tính + khoảng tuổi bất kỳ), dùng chung cho mọi nguồn dữ liệu.

3 mức dữ liệu, từ tốt đến kém:
  1. Số liệu phân bố follower (giới %, tuổi %)        -> share_numeric()
  2. Nhãn thô Kalodata ("Majority Female", "25-34")    -> score_from_labels()
  3. Người dẫn trong video (giới, nhóm tuổi ước lượng) -> score_from_presenter()
"""
import re

GENDER_WORDS = {"female": "nữ", "male": "nam", "all": "mọi giới"}
OPPOSITE = {"female": "male", "male": "female"}


def bucket_range(label: str) -> tuple[int, int] | None:
    """'18-24' / '18_24' -> (18, 24); '55+' / '35_plus' -> (55, 64); 'under_18' -> (13, 17)."""
    s = (label or "").strip().lower()
    if s.startswith("under"):
        return 13, 17
    m = re.match(r"(\d+)\s*[-_]\s*(\d+)", s)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.match(r"(\d+)\s*(\+|_?plus)", s)
    if m:
        return int(m.group(1)), int(m.group(1)) + 9
    return None


def age_overlap(label: str, lo: int, hi: int) -> float | None:
    """Tỷ lệ nhóm tuổi nằm trong khoảng mục tiêu, giả định tuổi phân bố đều trong nhóm."""
    r = bucket_range(label)
    if r is None:
        return None
    b_lo, b_hi = r
    inter = min(b_hi, hi) - max(b_lo, lo) + 1
    return max(0, inter) / (b_hi - b_lo + 1)


class Target:
    def __init__(self, campaign: dict):
        self.gender = campaign.get("target_gender", "all")
        self.age_min = campaign.get("target_age_min", 0)
        self.age_max = campaign.get("target_age_max", 200)

    def describe(self) -> str:
        return f"{GENDER_WORDS.get(self.gender, self.gender)} {self.age_min}–{self.age_max} tuổi"

    def gender_share(self, gender_dist: dict | None) -> float | None:
        if not gender_dist:
            return None
        if self.gender == "all":
            return 1.0
        return gender_dist.get(self.gender)

    def share_numeric(self, gender_dist: dict | None, age_dist: dict | None) -> float | None:
        """Ước tính tỷ lệ follower đúng giới VÀ đúng tuổi (giả định giới và tuổi độc lập)."""
        g = self.gender_share(gender_dist)
        if g is None or not age_dist:
            return None
        in_range = sum(share * (age_overlap(b, self.age_min, self.age_max) or 0) for b, share in age_dist.items())
        return g * in_range

    def is_wrong_majority(self, sex_label: str | None) -> bool:
        opp = OPPOSITE.get(self.gender)
        return bool(opp) and (sex_label or "").strip().lower() == f"majority {opp}"

    def score_from_labels(self, sex_label: str | None, age_top: str | None) -> float | None:
        sex = (sex_label or "").strip().lower()
        if not sex and not age_top:
            return None
        if self.gender == "all":
            g = 1.0
        elif sex == f"majority {self.gender}":
            g = 1.0
        elif self.is_wrong_majority(sex_label):
            g = 0.3
        else:
            g = 0.6                     # balanced hoặc không rõ
        ov = age_overlap(age_top, self.age_min, self.age_max) if age_top else None
        a = 0.5 if ov is None else max(ov, 0.2)   # nhãn chỉ là nhóm ĐÔNG NHẤT, các nhóm khác vẫn có người -> sàn 0.2
        return g * a

    def score_from_presenter(self, presenter_gender: str, presenter_age_band: str) -> float:
        if self.gender == "all":
            g = 1.0
        else:
            g = {self.gender: 1.0, "unclear": 0.5}.get(presenter_gender, 0.3)
        ov = age_overlap(presenter_age_band, self.age_min, self.age_max)
        a = 0.5 if ov is None else max(ov, 0.2)
        return g * a
