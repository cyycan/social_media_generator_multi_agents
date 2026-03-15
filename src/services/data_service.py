"""
Data I/O service — handles CSV, TXT, and manual topic input.
Extracts topics, keywords, and context for post generation.
"""

import io
import csv
import re
from typing import Optional

import pandas as pd

from src.exceptions import DataParsingError
from src.logger import get_logger

logger = get_logger(__name__)


def parse_csv(file_bytes: bytes) -> dict:
    """
    Parse an uploaded CSV file.
    Looks for columns: topic, keywords, context (flexible naming).
    Returns dict with topics, keywords, extra_context.
    """
    try:
        df = pd.read_csv(io.BytesIO(file_bytes))
    except Exception as exc:
        raise DataParsingError(f"Could not parse CSV: {exc}") from exc

    df.columns = [c.strip().lower() for c in df.columns]

    # Flexible column detection
    topic_col = _find_col(df, ["topic", "topics", "subject", "title", "idea"])
    keyword_col = _find_col(df, ["keywords", "keyword", "tags", "tag"])
    context_col = _find_col(df, ["context", "description", "notes", "extra", "info"])

    topics: list[str] = []
    keywords: list[str] = []
    context_parts: list[str] = []

    if topic_col:
        topics = df[topic_col].dropna().astype(str).str.strip().tolist()
        topics = [t for t in topics if t]

    if keyword_col:
        raw_kws = df[keyword_col].dropna().astype(str).str.strip().tolist()
        for kw_str in raw_kws:
            keywords.extend([k.strip() for k in re.split(r"[,;|]", kw_str) if k.strip()])
        keywords = list(dict.fromkeys(keywords))  # deduplicate preserving order

    if context_col:
        context_parts = df[context_col].dropna().astype(str).str.strip().tolist()

    if not topics:
        # Fallback: use first column as topics
        topics = df.iloc[:, 0].dropna().astype(str).str.strip().tolist()
        logger.info("No 'topic' column found; using first column as topics")

    logger.info(
        f"Parsed CSV: {len(topics)} topics, {len(keywords)} keywords, "
        f"{len(context_parts)} context rows"
    )

    return {
        "topics": topics[:20],  # cap at 20 topics
        "keywords": keywords[:30],
        "extra_context": " | ".join(context_parts[:5]),
        "raw_text": df.to_string(index=False),
    }


def parse_text(raw_text: str) -> dict:
    """
    Parse plain text input.
    Splits on newlines/bullets for topics.
    Extracts #hashtags as keywords.
    """
    if not raw_text.strip():
        raise DataParsingError("Text input is empty.")

    lines = [l.strip().lstrip("-•*>") for l in raw_text.splitlines() if l.strip()]
    topics = [l for l in lines if l][:20]

    # Extract hashtags as keywords
    keywords = re.findall(r"#(\w+)", raw_text)
    keywords = list(dict.fromkeys(keywords))

    logger.info(f"Parsed text: {len(topics)} topics, {len(keywords)} hashtag keywords")

    return {
        "topics": topics,
        "keywords": keywords,
        "extra_context": "",
        "raw_text": raw_text,
    }


def parse_manual(
    topics_str: str,
    keywords_str: str,
    extra_context: str,
) -> dict:
    """Parse manually entered topics/keywords."""
    topics = [t.strip() for t in topics_str.split("\n") if t.strip()]
    keywords = [k.strip().lstrip("#") for k in re.split(r"[,\n]", keywords_str) if k.strip()]

    if not topics:
        raise DataParsingError("Please enter at least one topic.")

    return {
        "topics": topics[:20],
        "keywords": keywords[:30],
        "extra_context": extra_context.strip(),
        "raw_text": topics_str,
    }


def get_sample_csv() -> str:
    """Return sample CSV content for download."""
    rows = [
        ["topic", "keywords", "context"],
        ["New product launch", "launch, innovation, tech", "Launching our AI-powered analytics dashboard"],
        ["Customer success story", "success, testimonial, results", "Client achieved 40% cost reduction"],
        ["Industry trend", "trend, future, insights", "AI adoption in enterprise is accelerating"],
        ["Team spotlight", "team, culture, people", "Highlighting our engineering team's achievements"],
        ["Tips & how-to", "tips, tutorial, guide", "5 ways to improve your workflow"],
    ]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerows(rows)
    return output.getvalue()


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _find_col(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    return None
