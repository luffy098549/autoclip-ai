"""Store public YouTube metadata only, without granting reuse rights."""
from datetime import datetime, timezone
from ..models import db, Streamer, CompetitorVideo
from ..sources.youtube import fetch_channel, fetch_recent_videos


def sync_youtube_channel(streamer_id: int, api_key: str, max_videos: int = 10):
    creator = db.session.get(Streamer, streamer_id)
    if not creator:
        raise ValueError("Unknown streamer")
    if creator.platform != "youtube":
        raise ValueError("Only YouTube is supported")
    channel = fetch_channel(creator.channel_identifier, api_key)
    incoming = fetch_recent_videos(channel, api_key, limit=max_videos)
    for item in incoming:
        video = CompetitorVideo.query.filter_by(
            streamer_id=creator.id, video_id=item["video_id"]
        ).first()
        if not video:
            video = CompetitorVideo(streamer_id=creator.id, video_id=item["video_id"])
            db.session.add(video)
        video.title = item["title"] or "(Untitled)"
        video.published_at = (datetime.fromisoformat(item["published_at"].replace("Z", "+00:00"))
                              if item["published_at"] else None)
        video.view_count = item["views"]
        video.like_count = item["likes"]
        video.comment_count = item["comments"]
        video.duration_iso8601 = item["duration"]
        video.fetched_at = datetime.now(timezone.utc)
    db.session.commit()
    return {"streamer_id": creator.id, "channel": channel["title"],
            "videos_updated": len(incoming)}
