import os
import time
import datetime
import requests
import pandas as pd
from dotenv import load_dotenv
from googleapiclient.errors import HttpError

# Load environment (supports .env for local dev)
load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY") or os.environ.get("YOUTUBE_API_KEY")

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


def _raise_http_error(resp: requests.Response):
    """Convert a requests.Response into a googleapiclient.errors.HttpError
    so the rest of the app (which may catch HttpError) can handle it.
    """
    raise HttpError(resp, resp.text, uri=resp.url)


def _safe_get(url, params, max_retries=3, backoff_factor=1.0):
    headers = {"Accept": "application/json"}
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=10)
        except requests.exceptions.RequestException as e:
            # network error or timeout
            if attempt == max_retries:
                raise
            time.sleep(backoff_factor * attempt)
            continue

        # Successful
        if resp.status_code == 200:
            return resp

        # Try to parse error body
        try:
            j = resp.json()
        except ValueError:
            j = {}

        error = j.get("error", {})
        errors = error.get("errors", []) if isinstance(error, dict) else []
        reasons = [err.get("reason") for err in errors if isinstance(err, dict)]

        # If quota exceeded or rate-limited -> raise HttpError so caller can handle
        if "quotaExceeded" in reasons or resp.status_code in (403, 429):
            _raise_http_error(resp)

        # Server error -> retry
        if resp.status_code >= 500:
            if attempt == max_retries:
                resp.raise_for_status()
            time.sleep(backoff_factor * attempt)
            continue

        # Other client error -> raise
        resp.raise_for_status()

    # If we exit loop without returning
    raise RuntimeError("Failed to complete HTTP request")


def search_meditation_videos_today(query: str = "meditation", max_results: int = 50) -> pd.DataFrame:
    """Search YouTube for `query` videos published *today* (UTC), return a
    pandas.DataFrame with video metadata + statistics (if available).

    This implementation uses plain HTTP requests (no google-auth / service
    account), so it will not attempt to contact the GCE metadata server and
    avoids the metadata TransportError.

    If the API returns a quota error, a googleapiclient.errors.HttpError is
    raised (so existing app code that catches HttpError will handle it).
    """
    if not API_KEY:
        raise RuntimeError("YOUTUBE_API_KEY not set. Please set environment variable or Streamlit secret.")

    # Today's UTC bounds
    today = datetime.datetime.utcnow().date()
    published_after = f"{today.isoformat()}T00:00:00Z"
    published_before = f"{today.isoformat()}T23:59:59Z"

    items = []
    page_token = None

    while True:
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "order": "date",
            "publishedAfter": published_after,
            "publishedBefore": published_before,
            "maxResults": max_results,
            "key": API_KEY,
        }
        if page_token:
            params["pageToken"] = page_token

        resp = _safe_get(SEARCH_URL, params)
        data = resp.json()

        for it in data.get("items", []):
            vid = it["id"].get("videoId")
            sn = it.get("snippet", {})
            items.append({
                "videoId": vid,
                "title": sn.get("title"),
                "channelId": sn.get("channelId"),
                "channelTitle": sn.get("channelTitle"),
                "publishedAt": sn.get("publishedAt"),
            })

        page_token = data.get("nextPageToken")
        if not page_token:
            break

        # be gentle with the API
        time.sleep(0.1)

    if not items:
        return pd.DataFrame([])

    # Enrich with statistics using videos.list (batch up to 50 ids)
    video_ids = [x["videoId"] for x in items if x.get("videoId")]
    stats = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i : i + 50]
        params = {
            "part": "snippet,statistics,liveStreamingDetails",
            "id": ",".join(batch),
            "key": API_KEY,
        }
        resp = _safe_get(VIDEOS_URL, params)
        data = resp.json()

        for it in data.get("items", []):
            sn = it.get("snippet", {})
            st = it.get("statistics", {})
            live = it.get("liveStreamingDetails", {})

            stats.append({
                "videoId": it.get("id"),
                "title": sn.get("title"),
                "channelId": sn.get("channelId"),
                "channelTitle": sn.get("channelTitle"),
                "publishedAt": sn.get("publishedAt"),
                "viewCount": int(st.get("viewCount", 0)),
                "likeCount": int(st.get("likeCount", 0)) if st.get("likeCount") else 0,
                "commentCount": int(st.get("commentCount", 0)) if st.get("commentCount") else 0,
                "liveBroadcastContent": sn.get("liveBroadcastContent", "none"),
                "actualStartTime": live.get("actualStartTime"),
            })

        time.sleep(0.1)

    df = pd.DataFrame(stats)

    # If videos.list returned nothing (e.g. invalid ids), return basic search results
    if df.empty:
        return pd.DataFrame(items)

    # Add estimated RPM and monetizable flag (simple proxy: monetizable if >=1000 views)
    def _estimate_rpm(v):
        if v is None or v <= 0:
            return 0.0
        v = int(v)
        if v < 1000:
            return 0.0
        if v < 5000:
            return round(v * 0.5 / 1000, 2)
        if v < 10000:
            return round(v * 1.5 / 1000, 2)
        return round(v * 3.5 / 1000, 2)

    df["estimated_rpm"] = df["viewCount"].apply(_estimate_rpm)
    df["monetizable"] = df["viewCount"].apply(lambda x: bool(x and int(x) >= 1000))

    return df
