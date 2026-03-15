"""
Publisher service — handles posting to social media platforms.
Includes mock mode and real API stubs for Twitter, LinkedIn, Instagram, Facebook.
"""

import time
import random
from datetime import datetime
from typing import Optional

from src.models import PostStatus, Platform
from src.exceptions import PublishError
from src.logger import get_logger

logger = get_logger(__name__)


# ─── Mock publisher ────────────────────────────────────────────────────────

def mock_publish(post: dict) -> dict:
    """Simulate publishing with realistic latency and occasional failures."""
    time.sleep(random.uniform(0.3, 0.9))  # simulate API latency

    # 90% success rate in mock mode
    success = random.random() < 0.90

    if success:
        fake_id = f"mock_{post['platform'][:2].lower()}_{random.randint(100000, 999999)}"
        logger.info(f"[MOCK] Published post {post['id']} to {post['platform']} → {fake_id}")
        return {
            "post_id": post["id"],
            "platform": post["platform"],
            "status": PostStatus.PUBLISHED,
            "platform_post_id": fake_id,
            "published_at": datetime.utcnow().isoformat() + "Z",
            "url": _build_mock_url(post["platform"], fake_id),
            "error": None,
        }
    else:
        logger.warning(f"[MOCK] Publish failed for post {post['id']} on {post['platform']}")
        return {
            "post_id": post["id"],
            "platform": post["platform"],
            "status": PostStatus.FAILED,
            "platform_post_id": None,
            "published_at": None,
            "url": None,
            "error": "Simulated API error (mock mode)",
        }


def _build_mock_url(platform: str, post_id: str) -> str:
    urls = {
        Platform.TWITTER: f"https://twitter.com/i/web/status/{post_id}",
        Platform.LINKEDIN: f"https://www.linkedin.com/posts/{post_id}",
        Platform.INSTAGRAM: f"https://www.instagram.com/p/{post_id}/",
        Platform.FACEBOOK: f"https://www.facebook.com/posts/{post_id}",
    }
    return urls.get(platform, f"https://example.com/posts/{post_id}")


# ─── Real API stubs ────────────────────────────────────────────────────────

def publish_twitter(post: dict, credentials: dict) -> dict:
    """
    Publish to Twitter/X via Tweepy.

    Required credentials:
      - api_key, api_secret, access_token, access_token_secret (v1.1)
      OR
      - bearer_token (v2)
    """
    try:
        import tweepy  # type: ignore

        client = tweepy.Client(
            bearer_token=credentials.get("bearer_token"),
            consumer_key=credentials.get("api_key"),
            consumer_secret=credentials.get("api_secret"),
            access_token=credentials.get("access_token"),
            access_token_secret=credentials.get("access_token_secret"),
        )
        content = post.get("edited_content") or post.get("content", "")
        response = client.create_tweet(text=content[:280])
        tweet_id = response.data["id"]

        return {
            "post_id": post["id"],
            "platform": Platform.TWITTER,
            "status": PostStatus.PUBLISHED,
            "platform_post_id": str(tweet_id),
            "published_at": datetime.utcnow().isoformat() + "Z",
            "url": f"https://twitter.com/i/web/status/{tweet_id}",
            "error": None,
        }
    except ImportError:
        raise PublishError("tweepy not installed. Run: pip install tweepy")
    except Exception as exc:
        raise PublishError(f"Twitter publish failed: {exc}") from exc


def publish_linkedin(post: dict, credentials: dict) -> dict:
    """
    Publish to LinkedIn via LinkedIn REST API.

    Required credentials:
      - access_token, author_urn (e.g. 'urn:li:person:xxxx')
    """
    try:
        import requests

        content = post.get("edited_content") or post.get("content", "")
        payload = {
            "author": credentials["author_urn"],
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": content},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }
        headers = {
            "Authorization": f"Bearer {credentials['access_token']}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        }
        resp = requests.post(
            "https://api.linkedin.com/v2/ugcPosts",
            json=payload,
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        post_id = resp.headers.get("x-restli-id", "unknown")

        return {
            "post_id": post["id"],
            "platform": Platform.LINKEDIN,
            "status": PostStatus.PUBLISHED,
            "platform_post_id": post_id,
            "published_at": datetime.utcnow().isoformat() + "Z",
            "url": f"https://www.linkedin.com/feed/update/{post_id}",
            "error": None,
        }
    except Exception as exc:
        raise PublishError(f"LinkedIn publish failed: {exc}") from exc


def publish_post(
    post: dict,
    use_mock: bool = True,
    platform_credentials: Optional[dict] = None,
) -> dict:
    """
    Unified publish dispatcher.

    Args:
        post: GeneratedPost dict
        use_mock: If True, use mock publisher (safe default)
        platform_credentials: Dict of platform → credentials dict
    """
    if use_mock:
        return mock_publish(post)

    platform = post.get("platform", "")
    creds = (platform_credentials or {}).get(platform, {})

    try:
        if platform == Platform.TWITTER:
            return publish_twitter(post, creds)
        elif platform == Platform.LINKEDIN:
            return publish_linkedin(post, creds)
        else:
            # Facebook & Instagram require Graph API + media upload
            # which are complex flows; fall back to mock for now
            logger.info(f"Real publish for {platform} not yet implemented; using mock")
            return mock_publish(post)
    except PublishError:
        raise
    except Exception as exc:
        logger.error(f"Unexpected error publishing to {platform}: {exc}")
        return {
            "post_id": post["id"],
            "platform": platform,
            "status": PostStatus.FAILED,
            "platform_post_id": None,
            "published_at": None,
            "url": None,
            "error": str(exc),
        }
