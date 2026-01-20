from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import markdown

try:
    import frontmatter
except ModuleNotFoundError:
    frontmatter = None

BASE_DIR = Path(__file__).resolve().parent
POSTS_DIR = BASE_DIR / "posts"


@dataclass
class BlogPost:
    slug: str
    title: str
    date: datetime
    date_str: str
    tags: List[str]
    summary: str
    cover: Optional[str]
    html: str


def load_posts() -> List[BlogPost]:
    if frontmatter is None:
        return []

    posts: List[BlogPost] = []

    if not POSTS_DIR.exists():
        return posts

    for md_file in POSTS_DIR.glob("*.md"):
        fm = frontmatter.load(md_file)
        slug = md_file.stem

        title = str(fm.get("title") or slug)
        date_raw = str(fm.get("date") or "")
        tags = fm.get("tags") or []
        summary = str(fm.get("summary") or "")
        cover = fm.get("cover")

        # date parse (expects "YYYY-MM-DD")
        try:
            dt = datetime.fromisoformat(date_raw)
        except Exception:
            # fallback: file modified time
            dt = datetime.fromtimestamp(md_file.stat().st_mtime)

        date_str = dt.strftime("%b %d, %Y")

        body_html = markdown.markdown(
            fm.content,
            extensions=["fenced_code", "tables", "toc"],
            output_format="html5",
        )

        posts.append(
            BlogPost(
                slug=slug,
                title=title,
                date=dt,
                date_str=date_str,
                tags=list(tags) if isinstance(tags, (list, tuple)) else [str(tags)],
                summary=summary,
                cover=str(cover) if cover else None,
                html=body_html,
            )
        )

    posts.sort(key=lambda p: p.date, reverse=True)
    return posts


def get_post_by_slug(slug: str) -> Optional[BlogPost]:
    for p in load_posts():
        if p.slug == slug:
            return p
    return None
