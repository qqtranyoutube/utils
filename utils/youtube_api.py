import os
import time
from typing import List, Any, Optional
from datetime import datetime
import requests
import pandas as pd
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

load_dotenv()
API_KEY_DEFAULT = os.getenv("YOUTUBE_API_KEY")

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"


def _safe_get(url: str, params: dict, max_retries: int = 3, backoff: float = 0.3) -> dict:
    headers = {"Accept": "application/json"}
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=10)
        except requests.RequestException as e:
            if attempt == max_retries:
                raise
            time.sleep(backoff * attempt)
            continue

        if resp.status_code == 200:
            return resp.json()

        # parse error body
        try:
            body = resp.json()
        except Exception:
            body = {}

        err = body.get("error", {})
        reasons = [e.get("reason") for e in err.get("errors", [])] if isinstance(err, dict) else []

        if resp.status_code in (403, 429) or "quotaExceeded" in reasons or "rateLimitExceeded" in reasons:
            # raise HttpError so upstream can catch and display
            raise HttpError(resp, resp.text, uri=resp.url)

        if resp.status_code >= 500:
            if attempt == max_retries:
                resp.raise_for_status()
            time.sleep(backoff * attempt)
            continue

        resp.raise_for_status()

    raise RuntimeError("HTTP request failed")


def _batch(iterable: List[Any], n: int):
    for i in range(0, len(iterable), n):
        yield iterable[i : i + n]


def search_meditation_videos_today(api_key: Optional[str]) -> pd.DataFrame:
    if not api_key:
        api_key = API_KEY_DEFAULT
    if not api_key:
        raise RuntimeError("YOUTUBE_API_KEY not provided")

    today = datetime.utcnow().date()
    published_after = f"{today.isoformat()}T00:00:00Z"
    published_before = f"{today.isoformat()}T23:59:59Z"

    items = []
    page_token = None

    while True:
        params = {
            "part": "snippet",
            "q": "meditation",
            "type": "video",
            "order": "date",
            "publishedAfter": published_after,
            "publishedBefore": published_before,
            "maxResults": 50,
            "key": api_key,
        }
        if page_token:
            params["pageToken"] = page_token

        data = _safe_get(SEARCH_URL, params)
        for it in data.get("items", []):
            sn = it.get("snippet", {})
            items.append({
                "videoId": it.get("id", {}).get("videoId"),
                "title": sn.get("title"),
                "channelId": sn.get("channelId"),
                "channelTitle": sn.get("channelTitle"),
                "publishedAt": sn.get("publishedAt"),
                "thumbnail": (sn.get("thumbnails") or {}).get("medium", {}).get("url"),
                "liveBroadcastContent": sn.get("liveBroadcastContent", "none"),
            })

        page_token = data.get("nextPageToken")
        if not page_token:
            break
        time.sleep(0.08)

    return pd.DataFrame(items)


def enrich_videos_with_stats(api_key: str, df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame([])

    video_ids = [v for v in df["videoId"].tolist() if v]
    rows = []
    for batch in _batch(video_ids, 50):
        params = {"part": "snippet,statistics,liveStreamingDetails", "id": ",".join(batch), "key": api_key}
        data = _safe_get(VIDEOS_URL, params)
        for it in data.get("items", []):
            sn = it.get("snippet", {})
            st = it.get("statistics", {})
            live = it.get("liveStreamingDetails", {})
            rows.append({
                "videoId": it.get("id"),
                "viewCount": int(st.get("viewCount", 0)),
                "likeCount": int(st.get("likeCount", 0)) if st.get("likeCount") else 0,
                "commentCount": int(st.get("commentCount", 0)) if st.get("commentCount") else 0,
                "actualStartTime": live.get("actualStartTime"),
                "liveDetailsPresent": bool(live),
                "defaultAudioLanguage": sn.get("defaultAudioLanguage"),
            })
        time.sleep(0.08)

    stats_df = pd.DataFrame(rows)
    merged = df.merge(stats_df, on="videoId", how="left")
    for c in ["viewCount", "likeCount", "commentCount"]:
        if c in merged.columns:
            merged[c] = merged[c].fillna(0).astype(int)
    return merged


def enrich_channels(api_key: str, df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df

    channel_ids = df["channelId"].dropna().unique().tolist()
    ch_rows = []
    for batch in _batch(channel_ids, 50):
        params = {"part": "snippet,statistics", "id": ",".join(batch), "key": api_key}
        data = _safe_get(CHANNELS_URL, params)
        for it in data.get("items", []):
            sn = it.get("snippet", {})
            st = it.get("statistics", {})
            ch_rows.append({
                "channelId": it.get("id"),
                "subscriberCount": int(st.get("subscriberCount", 0)) if st.get("subscriberCount") else 0,
                "channelVideoCount": int(st.get("videoCount", 0)) if st.get("videoCount") else 0,
                "country": sn.get("country") or "Unknown",
            })
        time.sleep(0.08)

    ch_df = pd.DataFrame(ch_rows)
    merged = df.merge(ch_df, on="channelId", how="left")
    merged["subscriberCount"] = merged.get("subscriberCount", 0).fillna(0).astype(int)
    merged["channelVideoCount"] = merged.get("channelVideoCount", 0).fillna(0).astype(int)
    merged["country"] = merged.get("country").fillna("Unknown")
    return merged


def estimate_rpm_from_views(views: int) -> float:
    if not views or int(views) <= 0:
        return 0.0
    v = int(views)
    if v < 1000:
        return 0.0
    if v < 5000:
        return round(v * 0.5 / 1000, 2)
    if v < 10000:
        return round(v * 1.5 / 1000, 2)
    return round(v * 3.5 / 1000, 2)


def final_pipeline(api_key: Optional[str] = None) -> pd.DataFrame:
    if not api_key:
        api_key = API_KEY_DEFAULT
    if not api_key:
        raise RuntimeError("YOUTUBE_API_KEY is required")

    df_search = search_meditation_videos_today(api_key)
    if df_search is None or df_search.empty:
        return pd.DataFrame([])

    df_stats = enrich_videos_with_stats(api_key, df_search)
    df_full = enrich_channels(api_key, df_stats)

    df_full["estimatedRPM_USD"] = df_full["viewCount"].apply(estimate_rpm_from_views)
    df_full["Monetizable"] = df_full["viewCount"].apply(lambda v: bool(v and int(v) >= 1000))
    df_full["publishedAt"] = pd.to_datetime(df_full["publishedAt"])
    df_full = df_full.sort_values("publishedAt", ascending=False).reset_index(drop=True)
    return df_full
