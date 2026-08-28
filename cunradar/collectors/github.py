"""GitHub Trending + Repository commit tracker."""

import re
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from .base import BaseCollector, CollectedItem


class GitHubTrendingCollector(BaseCollector):
    """Collect today's trending repositories from github.com/trending."""

    TRENDING_URL = "https://github.com/trending"

    def __init__(self, language: str = "", limit: int = 15) -> None:
        self.language = language
        self.limit = limit

    def collect(self) -> list[CollectedItem]:
        url = self.TRENDING_URL
        if self.language:
            url += f"/{self.language}"
        url += "?since=daily"

        try:
            resp = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=15,
            )
            resp.raise_for_status()
        except Exception as e:
            print(f"  [GitHub Trending] Failed to fetch: {e}")
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        articles = soup.select("article.Box-row")
        items: list[CollectedItem] = []

        for article in articles[: self.limit]:
            h2 = article.select_one("h2 a")
            if not h2:
                continue

            # Extract repo name (owner/name)
            repo_href = h2.get("href", "").strip("/")
            repo_name = repo_href  # e.g. "owner/repo"

            # Description
            desc_el = article.select_one("p")
            description = desc_el.get_text(strip=True) if desc_el else ""

            # Language
            lang_el = article.select_one("[itemprop='programmingLanguage']")
            language = lang_el.get_text(strip=True) if lang_el else ""

            # Stars today
            stars_el = article.select_one(".float-sm-right")
            stars_text = stars_el.get_text(strip=True) if stars_el else ""

            items.append(CollectedItem(
                source="github_trending",
                source_name=repo_name,
                # 按仓库去重：同一仓库只要推送过一次就不再重复推送，
                # 不再带日期，避免「每天都是新内容」导致重复推送。
                item_id=f"gh-trend:{repo_name}",
                title=f"{repo_name} ({language})",
                url=f"https://github.com/{repo_name}",
                published=datetime.now(timezone.utc),
                description=description,
                extra={
                    "language": language,
                    "stars_today": stars_text,
                    "repo": repo_href,
                },
            ))

        print(f"  [GitHub Trending]: {len(items)} trending repos found")
        return items


class GitHubRepoCollector(BaseCollector):
    """Collect recent commits from specific GitHub repositories."""

    API_BASE = "https://api.github.com"

    def __init__(self, repos: list[dict], token: str = "") -> None:
        self.repos = repos
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "CunRadar/1.0",
            "Accept": "application/vnd.github.v3+json",
        })
        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})

    def collect(self) -> list[CollectedItem]:
        items: list[CollectedItem] = []
        for repo_cfg in self.repos:
            name = repo_cfg.get("name", repo_cfg["repo"])
            repo_full = repo_cfg["repo"]

            try:
                resp = self.session.get(
                    f"{self.API_BASE}/repos/{repo_full}/commits",
                    params={"per_page": 10},
                    timeout=15,
                )
                if resp.status_code == 403:
                    print(f"  [GitHub] Rate limited for '{name}'. Add GITHUB_TOKEN for higher limits.")
                    continue
                resp.raise_for_status()
                commits = resp.json()
            except Exception as e:
                print(f"  [GitHub] Failed to fetch commits for '{name}': {e}")
                continue

            for commit in commits:
                sha = commit.get("sha", "")[:7]
                info = commit.get("commit", {})
                author_info = info.get("author", {})
                published = None
                if author_info.get("date"):
                    published = datetime.fromisoformat(author_info["date"].replace("Z", "+00:00"))

                message = info.get("message", "").split("\n")[0]  # first line only

                items.append(CollectedItem(
                    source="github",
                    source_name=name,
                    item_id=f"gh-commit:{repo_full}:{sha}",
                    title=f"[{repo_full}] {message}",
                    url=f"https://github.com/{repo_full}/commit/{sha}",
                    published=published,
                    description="",
                    extra={
                        "repo": repo_full,
                        "sha": sha,
                        "author": info.get("author", {}).get("name", ""),
                    },
                ))

            print(f"  [GitHub] '{name}': {len(commits)} recent commits")

        return items
