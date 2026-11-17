"""Test server xem kết quả: chạy thật trên cổng ngẫu nhiên, dữ liệu tạm trong tmp_path."""
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from koc import config
from koc.store import Store
from koc.web import server


def fake_result(run_id="demo"):
    row = {"handle": "a", "nickname": "A", "followers": 1000, "metric_score": 0.5, "screen_score": 0.5,
           "video_score": 0.5, "final_score": 0.5, "est_cost_vnd": 3_000_000, "category_gmv_vnd": 1e8,
           "gmv_basis": "creators_list", "metric_parts": {"audience": 1.0}}
    return {
        "run_id": run_id, "campaign": {"product": "kem chống nắng"},
        "funnel": {"ingested": 10, "selected": 1},
        "choice": {"selected": [row], "total_cost_vnd": 3_000_000, "ads_reserve_vnd": 1, "recommended_ads_vnd": 2},
        "videos": {"a": {"video_id": "123456", "url": "u", "kind": "video", "analysis": {"evidence": []}}},
        "screens": {"a": {"account_kind": "individual_creator", "primary_niche": "skincare_review",
                          "topic_relevance": 8, "fit_note": "ok"}},
        "final": {"rationale": {"summary_vi": "tóm tắt", "kocs": [{"handle": "a", "reason_vi": "vì"}]},
                  "packs": [{"handle": "a", "evidence": {"M:gmv": "x"}}], "citation_check": {"valid_rate": 1.0}},
        "dropped": {"metrics": []}, "usage": [], "timings": [], "cost_usd": 0.01,
    }


@pytest.fixture
def live(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "RESULTS_DIR", tmp_path / "results")
    monkeypatch.setattr(server, "VIDEO_DIR", tmp_path / "videos")
    (tmp_path / "results" / "demo").mkdir(parents=True)
    (tmp_path / "results" / "demo" / "result.json").write_text(json.dumps(fake_result()), encoding="utf-8")
    (tmp_path / "videos" / "123456").mkdir(parents=True)
    (tmp_path / "videos" / "123456" / "123456.mp4").write_bytes(b"0123456789")
    store = Store(tmp_path / "t.db")
    store.start_run("demo", {})
    store.save_item("demo", "screen", "a", "done", {"x": 1})
    server.Handler.store = store
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


def get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.status, r.headers, r.read()


def test_index_and_apis(live):
    assert b"KOC Discovery" in get(live + "/")[2]
    res = json.loads(get(live + "/api/result?run=demo")[2])
    assert res["kocs"][0]["row"]["handle"] == "a" and res["kocs"][0]["has_local_video"]
    prog = json.loads(get(live + "/api/progress?run=demo")[2])
    assert prog["stages"]["screen"]["done"] == 1
    assert any(r["run_id"] == "demo" for r in json.loads(get(live + "/api/runs")[2]))


def test_video_range_request(live):
    status, headers, body = get(live + "/video/123456.mp4", {"Range": "bytes=2-4"})
    assert status == 206 and body == b"234" and headers["Content-Range"] == "bytes 2-4/10"


def test_rejects_bad_run_id_and_missing_result(live):
    with pytest.raises(urllib.error.HTTPError) as e:
        get(live + "/api/result?run=../../etc")
    assert e.value.code == 400
    with pytest.raises(urllib.error.HTTPError) as e:
        get(live + "/api/result?run=khongco")
    assert e.value.code == 404


def test_export_static_embeds_data(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "RESULTS_DIR", tmp_path / "results")
    monkeypatch.setattr(server, "VIDEO_DIR", tmp_path / "videos")
    (tmp_path / "results" / "demo").mkdir(parents=True)
    r = fake_result()
    r["videos"]["a"]["analysis"]["summary_vi"] = "có </script> trong chữ"     # không được đóng nhầm thẻ script
    (tmp_path / "results" / "demo" / "result.json").write_text(json.dumps(r), encoding="utf-8")
    out = server.export_static("demo", tmp_path / "report.html")
    html = out.read_text(encoding="utf-8")
    assert "window.__KOC_STATIC__" in html and "</script> trong" not in html
    blob = html.split("window.__KOC_STATIC__ = ", 1)[1].split(";</script>", 1)[0]
    data = json.loads(blob)
    assert data["results"]["demo"]["kocs"][0]["has_local_video"] is False
