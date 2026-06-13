from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import markdown

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


def _parse_front_matter(md_text: str) -> Tuple[dict, str]:

    lines = md_text.splitlines()

    if len(lines) < 3 or lines[0].strip() != "---":
        return {}, md_text

    # find closing ---
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, md_text  # malformed; treat as no front-matter

    fm_lines = lines[1:end]
    body = "\n".join(lines[end + 1 :]).lstrip("\n")

    meta: dict = {}
    current_key: Optional[str] = None

    def _strip_quotes(s: str) -> str:
        s = s.strip()
        if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
            return s[1:-1]
        return s

    for raw in fm_lines:
        line = raw.rstrip()
        if not line.strip():
            continue

        # list item (for tags: - foo)
        if line.lstrip().startswith("-") and current_key:
            item = line.split("-", 1)[1].strip()
            meta.setdefault(current_key, [])
            if isinstance(meta[current_key], list):
                meta[current_key].append(_strip_quotes(item))
            continue

        if ":" not in line:
            continue

        key, val = line.split(":", 1)
        key = key.strip()
        val = val.strip()

        current_key = key

        # empty value => maybe a list block starts next lines
        if val == "":
            meta[key] = []
            continue

        # tags: ["a","b"]
        if val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            if not inner:
                meta[key] = []
            else:
                parts = [p.strip() for p in inner.split(",")]
                meta[key] = [_strip_quotes(p) for p in parts]
            continue

        meta[key] = _strip_quotes(val)

    return meta, body


def load_posts() -> List[BlogPost]:
    posts: List[BlogPost] = []
    if not POSTS_DIR.exists():
        return posts

    for md_file in POSTS_DIR.glob("*.md"):
        slug = md_file.stem
        text = md_file.read_text(encoding="utf-8")

        meta, body = _parse_front_matter(text)

        title = str(meta.get("title") or slug)
        date_raw = str(meta.get("date") or "")
        summary = str(meta.get("summary") or "")
        cover = meta.get("cover")

        tags_raw = meta.get("tags") or []
        if isinstance(tags_raw, list):
            tags = [str(t) for t in tags_raw]
        else:
            tags = [str(tags_raw)]

        # date parse (expects "YYYY-MM-DD")
        try:
            dt = datetime.fromisoformat(date_raw)
        except Exception:
            dt = datetime.fromtimestamp(md_file.stat().st_mtime)

        date_str = dt.strftime("%b %d, %Y")

        body_html = markdown.markdown(
            body,
            extensions=["fenced_code", "tables", "toc"],
            output_format="html5",
        )

        posts.append(
            BlogPost(
                slug=slug,
                title=title,
                date=dt,
                date_str=date_str,
                tags=tags,
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
