import asyncio
import logging
import re
from datetime import datetime
from typing import List, Dict
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


class SocialMediaScraper:

    def detect_platform(self, url: str) -> str:
        if "facebook.com" in url:
            return "Facebook"
        elif "instagram.com" in url:
            return "Instagram"
        elif "twitter.com" in url or "x.com" in url:
            return "X/Twitter"
        return "Unknown"

    async def fetch_posts(self, url: str) -> List[Dict]:
        platform = self.detect_platform(url)
        try:
            if platform == "Facebook":
                return await self._fetch_facebook(url)
            elif platform == "Instagram":
                return await self._fetch_instagram(url)
            elif platform == "X/Twitter":
                return await self._fetch_twitter(url)
        except Exception as e:
            logger.error(f"Scrape error [{platform}] {url}: {e}")
            return []
        return []

    async def _fetch_facebook(self, url: str) -> List[Dict]:
        """
        Fetch Facebook page posts.
        Uses mobile version for better text accessibility.
        For production, use facebook-scraper library or FB Graph API.
        """
        posts = []
        try:
            # Try facebook-scraper library first (most reliable)
            from facebook_scraper import get_posts
            loop = asyncio.get_event_loop()

            def _scrape():
                results = []
                page_id = self._extract_fb_page_id(url)
                try:
                    for post in get_posts(page_id, pages=3, options={"allow_extra_requests": False}):
                        results.append({
                            "text": post.get("text", "") or post.get("post_text", ""),
                            "time": str(post.get("time", datetime.now())),
                            "post_id": post.get("post_id", ""),
                            "url": post.get("post_url", url),
                        })
                        if len(results) >= 10:
                            break
                except Exception as e:
                    logger.warning(f"facebook-scraper failed: {e}")
                return results

            posts = await loop.run_in_executor(None, _scrape)
        except ImportError:
            logger.warning("facebook-scraper not installed, falling back to mobile scrape")
            posts = await self._fetch_facebook_mobile(url)

        return posts

    def _extract_fb_page_id(self, url: str) -> str:
        """Extract page name or numeric ID from Facebook URL."""
        # Handle /people/Name/ID format
        people_match = re.search(r'/people/[^/]+/(\d+)', url)
        if people_match:
            return people_match.group(1)

        # Handle /pg/pagename or /pagename
        name_match = re.search(r'facebook\.com/(?:pg/)?([^/?]+)', url)
        if name_match:
            candidate = name_match.group(1)
            if candidate not in ("profile.php", "people", "groups"):
                return candidate

        return url

    async def _fetch_facebook_mobile(self, url: str) -> List[Dict]:
        """Fallback: scrape m.facebook.com"""
        posts = []
        mobile_url = url.replace("www.facebook.com", "m.facebook.com")
        try:
            async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=20) as client:
                resp = await client.get(mobile_url)
                soup = BeautifulSoup(resp.text, "html.parser")

                # Mobile FB posts are in div[data-ft] or article tags
                for article in soup.find_all(["article", "div"], attrs={"data-ft": True})[:10]:
                    text_el = article.find("p") or article.find("span")
                    text = text_el.get_text(" ", strip=True) if text_el else ""
                    if text:
                        posts.append({
                            "text": text,
                            "time": datetime.now().isoformat(),
                            "url": url
                        })
        except Exception as e:
            logger.error(f"Mobile FB scrape failed: {e}")
        return posts

    async def _fetch_instagram(self, url: str) -> List[Dict]:
        """
        Fetch Instagram posts.
        Uses instaloader for public profiles.
        """
        posts = []
        try:
            import instaloader
            import re as _re

            username_match = _re.search(r'instagram\.com/([^/?]+)', url)
            if not username_match:
                return []
            username = username_match.group(1).strip("/")

            loop = asyncio.get_event_loop()

            def _scrape():
                results = []
                L = instaloader.Instaloader()
                profile = instaloader.Profile.from_username(L.context, username)
                for post in profile.get_posts():
                    results.append({
                        "text": post.caption or "",
                        "time": str(post.date_utc),
                        "post_id": post.shortcode,
                        "url": f"https://www.instagram.com/p/{post.shortcode}/"
                    })
                    if len(results) >= 10:
                        break
                return results

            posts = await loop.run_in_executor(None, _scrape)
        except ImportError:
            logger.warning("instaloader not installed")
        except Exception as e:
            logger.error(f"Instagram scrape failed: {e}")
        return posts

    async def _fetch_twitter(self, url: str) -> List[Dict]:
        """
        Fetch X/Twitter posts.
        Uses snscrape or nitter instances.
        """
        posts = []
        try:
            import snscrape.modules.twitter as sntwitter

            username_match = re.search(r'(?:twitter|x)\.com/([^/?]+)', url)
            if not username_match:
                return []
            username = username_match.group(1).strip("/")

            loop = asyncio.get_event_loop()

            def _scrape():
                results = []
                for tweet in sntwitter.TwitterUserScraper(username).get_items():
                    results.append({
                        "text": tweet.rawContent or "",
                        "time": str(tweet.date),
                        "post_id": str(tweet.id),
                        "url": tweet.url
                    })
                    if len(results) >= 10:
                        break
                return results

            posts = await loop.run_in_executor(None, _scrape)
        except ImportError:
            logger.warning("snscrape not installed, trying nitter")
            posts = await self._fetch_nitter(url)
        except Exception as e:
            logger.error(f"Twitter scrape failed: {e}")
        return posts

    async def _fetch_nitter(self, url: str) -> List[Dict]:
        """Fallback: use public Nitter instance for Twitter."""
        posts = []
        username_match = re.search(r'(?:twitter|x)\.com/([^/?]+)', url)
        if not username_match:
            return []
        username = username_match.group(1).strip("/")

        nitter_instances = [
            "https://nitter.net",
            "https://nitter.privacydev.net",
            "https://nitter.poast.org",
        ]

        for instance in nitter_instances:
            try:
                nitter_url = f"{instance}/{username}"
                async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=15) as client:
                    resp = await client.get(nitter_url)
                    if resp.status_code != 200:
                        continue
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for tweet_div in soup.find_all("div", class_="tweet-content")[:10]:
                        text = tweet_div.get_text(" ", strip=True)
                        if text:
                            posts.append({
                                "text": text,
                                "time": datetime.now().isoformat(),
                                "url": url
                            })
                    if posts:
                        break
            except Exception as e:
                logger.warning(f"Nitter {instance} failed: {e}")
                continue

        return posts
