"""Domain models for the Social Media Generator."""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import uuid


class Platform(str, Enum):
    TWITTER = "Twitter/X"
    LINKEDIN = "LinkedIn"
    INSTAGRAM = "Instagram"
    FACEBOOK = "Facebook"


class Tone(str, Enum):
    PROFESSIONAL = "Professional"
    CASUAL = "Casual"
    HUMOROUS = "Humorous"
    INSPIRATIONAL = "Inspirational"
    EDUCATIONAL = "Educational"
    PROMOTIONAL = "Promotional"


class PostStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    PUBLISHED = "published"
    FAILED = "failed"


class LLMProvider(str, Enum):
    OPENAI = "OpenAI"
    ANTHROPIC = "Anthropic"
    GOOGLE = "Google (Gemini)"


PLATFORM_LIMITS: dict[str, int] = {
    Platform.TWITTER: 280,
    Platform.LINKEDIN: 3000,
    Platform.INSTAGRAM: 2200,
    Platform.FACEBOOK: 63206,
}

PLATFORM_ICONS: dict[str, str] = {
    Platform.TWITTER: "🐦",
    Platform.LINKEDIN: "💼",
    Platform.INSTAGRAM: "📸",
    Platform.FACEBOOK: "👥",
}

PLATFORM_COLORS: dict[str, str] = {
    Platform.TWITTER: "#1DA1F2",
    Platform.LINKEDIN: "#0A66C2",
    Platform.INSTAGRAM: "#E1306C",
    Platform.FACEBOOK: "#1877F2",
}

PROVIDER_MODELS: dict[str, list[str]] = {
    LLMProvider.OPENAI: ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
    LLMProvider.ANTHROPIC: ["claude-3-haiku-20240307", "claude-3-5-sonnet-20241022"],
    LLMProvider.GOOGLE: ["gemini-1.5-flash", "gemini-1.5-pro"],
}


@dataclass
class AppConfig:
    llm_provider: str = LLMProvider.OPENAI
    api_key: str = ""
    model: str = "gpt-4o-mini"
    platforms: list = field(default_factory=lambda: ["Twitter/X", "LinkedIn"])
    tone: str = Tone.PROFESSIONAL
    brand_name: str = ""
    brand_description: str = ""
    num_posts: int = 3


@dataclass
class SampleData:
    topics: list = field(default_factory=list)
    keywords: list = field(default_factory=list)
    extra_context: str = ""
    raw_text: str = ""


@dataclass
class GeneratedPost:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    platform: str = Platform.TWITTER
    topic: str = ""
    content: str = ""
    hashtags: list = field(default_factory=list)
    status: str = PostStatus.DRAFT
    char_count: int = 0
    edited_content: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "platform": self.platform,
            "topic": self.topic,
            "content": self.content,
            "hashtags": self.hashtags,
            "status": self.status,
            "char_count": self.char_count,
            "edited_content": self.edited_content,
        }

    @property
    def final_content(self) -> str:
        return self.edited_content if self.edited_content is not None else self.content
