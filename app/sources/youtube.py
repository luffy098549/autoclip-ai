"""Official YouTube Data API metadata-only client. No third-party media downloading."""
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_ROOT = "https://www.googleapis.com/youtube/v3"


class YouTubeMetadataError(RuntimeError):
    pass


def _request(resource: str, params: dict, api_key: str) -> dict:
    if resource not in {"channels", "playlistItems", "videos"}:
        raise ValueError("Unknown YouTube Data API resource")
    if not api_key:
        raise YouTubeMetadataError("YouTube API key is not configured")
    query = urlencode({**params, "key": api_key})
    url = f"{API_ROOT}/{resource}?{query}"
    try:
        req = Request(url, headers={"User-Agent": "AutoClipAI/0.3 (metadata-only)"})
        with urlopen(req, timeout=20) as response:
            return json.load(response)
    except HTTPError as exc:
        # Never expose the request URL, which contains the API key.
        raise YouTubeMetadataError(f"YouTube API returned HTTP {exc.code}") from exc
    except (URLError, TimeoutError, ValueError) as exc:
        raise YouTubeMetadataError("Could not fetch YouTube metadata") from exc


def fetch_channel(handle: str, api_key: str) -> dict:
    normalized = handle.strip().lstrip("@")
    if not normalized or "/" in normalized or " " in normalized:
        raise ValueError("Invalid channel handle")
    selector = "id" if normalized.startswith("UC") and len(normalized) == 24 else "forHandle"
    data = _request("channels",
        {"part": "snippet,statistics,contentDetails", selector: normalized},
        api_key)
    items = data.get("items") or []
    if not items:
        raise YouTubeMetadataError("Channel not found")
    item = items[0]
    return {
        "channel_id": item.get("id"),
        "title": item.get("snippet", {}).get("title", normalized),
        "subscriber_count": int(item.get("statistics", {}).get("subscriberCount") or 0),
        "uploads_playlist_id": item.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads"),
    }


def fetch_recent_videos(channel: dict, api_key: str, limit: int = 10) -> list[dict]:
    if not 1 <= limit <= 50:
        raise ValueError("limit must be 1..50")
    playlist_id = channel.get("uploads_playlist_id")
    if not playlist_id:
        return []
    items = _request("playlistItems", {
        "part": "contentDetails", "playlistId": playlist_id, "maxResults": limit
    }, api_key).get("items", [])
    ids = [x.get("contentDetails", {}).get("videoId") for x in items]
    ids = [v for v in ids if v]
    if not ids:
        return []
    data = _request("videos", {"part": "snippet,statistics,contentDetails",
                               "id": ",".join(ids)}, api_key)
    results = []
    for item in data.get("items", []):
        snippet = item.get("snippet", {})
        statistics = item.get("statistics", {})
        results.append({
            "video_id": item["id"],
            "title": str(snippet.get("title", ""))[:400],
            "published_at": snippet.get("publishedAt"),
            "views": int(statistics.get("viewCount") or 0),
            "likes": int(statistics.get("likeCount") or 0),
            "comments": int(statistics.get("commentCount") or 0),
            "duration": item.get("contentDetails", {}).get("duration"),
        })
    return results
