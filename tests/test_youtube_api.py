from app.sources import youtube
from app.intelligence.competitive_patterns import relative_performance


def test_youtube_metadata_client_mocks(monkeypatch):
    requests=[]
    def fake_request(resource, params, key):
        requests.append((resource,params))
        if resource=="channels":
            return {"items":[{"id":"UC123","snippet":{"title":"Canal Demo"},
                "statistics":{"subscriberCount":"1200"},
                "contentDetails":{"relatedPlaylists":{"uploads":"UU123"}}}]}
        if resource=="playlistItems":
            return {"items":[{"contentDetails":{"videoId":"vid1"}}]}
        return {"items":[{"id":"vid1","snippet":{"title":"Video prueba","publishedAt":"2026-10-01T00:00:00Z"},
            "statistics":{"viewCount":"7000","likeCount":"77","commentCount":"5"},
            "contentDetails":{"duration":"PT1M23S"}}]}
    monkeypatch.setattr(youtube,"_request",fake_request)
    channel=youtube.fetch_channel("@creador_demo","fake-testing-key")
    videos=youtube.fetch_recent_videos(channel,"fake-testing-key",limit=5)
    assert channel["subscriber_count"]==1200
    assert videos[0]["views"]==7000
    assert requests[0][1]["forHandle"]=="creador_demo"
    assert [x[0] for x in requests]==["channels","playlistItems","videos"]


def test_public_relative_performance():
    assert relative_performance(1000,[500,1000,1500])==1.0
    assert relative_performance(1000,[0,0])==0.0
