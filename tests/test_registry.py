"""Test sổ đăng ký creator (phát hiện mới / thay đổi / quá hạn) và việc dùng lại kết quả LLM cũ."""
from koc.llm.base import LLM
from koc.registry import Registry, follower_bucket
from koc.schemas import ScreenBatch
from koc.store import Store


def detail(videos=("v1", "v2"), followers=64_200, bio="review mỹ phẩm"):
    return {"videos": [{"video_id": v} for v in videos], "followers": followers, "bio": bio,
            "creator_type": "INDEPENDENT", "shops": [{"name": "A"}], "follower_sex_label": "Majority Female"}


def test_follower_bucket_ignores_small_moves():
    assert follower_bucket(64_200) == follower_bucket(64_900)          # dao động nhỏ: cùng bậc
    assert follower_bucket(64_200) != follower_bucket(100_000)         # tăng ~55%: khác bậc


def test_registry_new_unchanged_changed_stale(tmp_path):
    reg = Registry(Store(tmp_path / "s.db"), max_age_days=14)
    t0 = 1_000_000.0
    assert reg.observe("a", detail(), now=t0)["status"] == "new"
    # follower nhích nhẹ, cùng video -> không đổi (không phải quét lại)
    assert reg.observe("a", detail(followers=64_800), now=t0 + 86400)["status"] == "unchanged"
    # có video mới -> thay đổi, nói rõ thay đổi gì
    r = reg.observe("a", detail(videos=("v1", "v2", "v3")), now=t0 + 2 * 86400)
    assert r["status"] == "changed" and "1 video mới" in r["changes"]
    # 15 ngày không có thay đổi -> quá hạn, nên lấy lại dữ liệu nguồn
    assert reg.observe("a", detail(videos=("v1", "v2", "v3")), now=t0 + 17 * 86400)["status"] == "stale"


class Fake:
    def complete(self, **kw):
        return {"creators": []}, 1000, 100, 0.0123


def test_reuse_records_money_saved(tmp_path):
    store = Store(tmp_path / "s.db")
    models = {"models": {"m": {"provider": "fake", "input_per_m": 1, "output_per_m": 1}},
              "limits": {"max_usd_per_run": 1.0}}
    for run in ("lan1", "lan2"):
        llm = LLM(models, store, run)
        llm._adapters["fake"] = Fake()
        llm.call(stage="screen", model="m", system="s", parts=[{"type": "text", "text": "x"}],
                 schema=ScreenBatch, item_ids=["a"])
    u1, u2 = store.usage_by_stage("lan1")[0], store.usage_by_stage("lan2")[0]
    assert u1["cost_usd"] == 0.0123 and u1["cache_hits"] == 0
    assert u2["cost_usd"] == 0 and u2["cache_hits"] == 1 and u2["saved_usd"] == 0.0123   # lần 2 dùng lại, ghi tiền tiết kiệm
