"""
CrewAI multi-agent social media post generation service.

Agent Pipeline (sequential):
    1. ContentStrategist  → Analyzes topic, identifies best content angle & key messages
    2. SocialMediaWriter  → Drafts the raw post based on the strategy
    3. ContentEditor      → Refines tone, hooks, and enforces character limits
    4. HashtagExpert      → Selects optimal hashtags and assembles the final post

Each platform/topic combination runs its own Crew, producing `num_posts` variants.
"""

import os
import re
import json

from crewai import Agent, Task, Crew, Process, LLM

from src.models import PLATFORM_LIMITS, LLMProvider, Platform
from src.exceptions import GenerationError, APIKeyError
from src.logger import get_logger

logger = get_logger(__name__)


# ─── LLM Factory ─────────────────────────────────────────────────────────────

def _build_llm(config: dict) -> LLM:
    provider = config.get("llm_provider", LLMProvider.OPENAI)
    api_key = config.get("api_key", "").strip()
    model = config.get("model", "gpt-4o-mini")

    if not api_key:
        raise APIKeyError(f"API key is required for provider '{provider}'.")

    if provider == LLMProvider.OPENAI:
        os.environ["OPENAI_API_KEY"] = api_key
        return LLM(model=f"openai/{model}", api_key=api_key, temperature=0.7)
    elif provider == LLMProvider.ANTHROPIC:
        os.environ["ANTHROPIC_API_KEY"] = api_key
        return LLM(model=f"anthropic/{model}", api_key=api_key, temperature=0.7)
    elif provider == LLMProvider.GOOGLE:
        os.environ["GEMINI_API_KEY"] = api_key
        return LLM(model=f"gemini/{model}", api_key=api_key, temperature=0.7)
    else:
        raise GenerationError(f"Unsupported LLM provider: {provider}")


# ─── Agents ───────────────────────────────────────────────────────────────────

def _make_strategist(llm: LLM) -> Agent:
    return Agent(
        role="Content Strategist",
        goal=(
            "Analyze the given topic and brand context to identify the single most "
            "compelling content angle for the target social media platform. "
            "Define clear key messages and the emotional hook that will drive engagement."
        ),
        backstory=(
            "You are a senior social media strategist with 10+ years of experience "
            "across B2B and B2C brands. You understand that what resonates on LinkedIn "
            "is very different from what goes viral on Instagram. You think about audience "
            "psychology first, content second. You distill complex topics into one clear, "
            "powerful angle that makes the audience care."
            "New article to promote:\n"
            "URL: {url}\n\n"
            "Write ONE LinkedIn post (no numbering, no extra lines). "
            "Include the phrase: based on the content from {url}. "
            "Use up to two natural hashtags inline "
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )


def _make_writer(llm: LLM) -> Agent:
    return Agent(
        role="Social Media Copywriter",
        goal=(
            "Transform the strategist's content brief into a compelling, platform-native "
            "social media post draft. Hook readers in the first line, communicate the key "
            "message clearly, and match the brand's voice exactly."
        ),
        backstory=(
            "You are an award-winning social media copywriter who has crafted viral posts "
            "for Fortune 500 companies and high-growth startups alike. You obsess over the "
            "opening line — because that is the only line most people read. You write with "
            "specificity, energy, and purpose. You never use corporate jargon or clichés."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )


def _make_editor(llm: LLM, char_limit: int, platform: str) -> Agent:
    return Agent(
        role="Content Editor",
        goal=(
            f"Polish the draft post for {platform}. Strictly enforce the {char_limit}-character "
            "limit. Sharpen the hook, improve readability, cut filler words, ensure the tone "
            "matches the brand. Return ONLY the final post text — no labels, no commentary."
        ),
        backstory=(
            "You are a meticulous editor who has spent years perfecting social media copy. "
            "You have a ruthless eye for weak verbs, redundant phrases, and missed opportunities. "
            f"You know {platform}'s algorithm preferences and audience expectations inside out. "
            "Every word must earn its place. You make the post tighter, sharper, and more human."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )


def _make_hashtag_expert(llm: LLM, platform: str) -> Agent:
    return Agent(
        role="Hashtag & Discoverability Specialist",
        goal=(
            f"Select the optimal hashtag set for {platform} to maximize reach and "
            "discoverability. Combine brand, trending, and niche community hashtags. "
            "Return a valid JSON object with keys 'content' and 'hashtags'."
        ),
        backstory=(
            "You are a social media SEO specialist who tracks hashtag trends daily. "
            "You know that on Instagram, 5-10 tightly relevant hashtags beat 30 generic ones; "
            "on LinkedIn, 3-5 professional tags drive the most reach; on Twitter, 1-2 trending "
            "tags boost impressions most. You never recommend hashtags just for volume — "
            "only for genuine relevance and discoverability."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )


# ─── Tasks ────────────────────────────────────────────────────────────────────

def _make_strategy_task(agent, topic, platform, tone, brand_name,
                         brand_description, keywords, extra_context, variant) -> Task:
    return Task(
        description=f"""
Produce a content strategy brief for the following:

Topic: {topic}
Platform: {platform}
Brand: {brand_name}
Brand Description: {brand_description}
Tone: {tone}
Keywords: {', '.join(keywords) if keywords else 'none'}
Extra Context: {extra_context or 'none'}
Post Variant #{variant} — choose a distinct angle from other variants.

Your brief must cover:
1. The single best content angle for {platform}
2. Primary audience insight driving this angle
3. 2-3 key messages
4. The emotional hook or call-to-action
5. Platform-specific format/style notes
""",
        expected_output=(
            "A structured content strategy brief (100-200 words) with: "
            "content angle, audience insight, key messages, hook, and platform notes."
        ),
        agent=agent,
    )


def _make_writing_task(agent, strategy_task, platform, tone, char_limit) -> Task:
    return Task(
        description=f"""
Using the Content Strategist's brief, write a social media post draft for {platform}.

- Tone: {tone}
- Character limit: {char_limit} (aim for 80-90% of limit)
- Open with a strong hook — the first line must stop the scroll
- Include appropriate line breaks and emojis for {platform}
- Do NOT include hashtags (the Hashtag Specialist handles those)
- Return ONLY the post text — no labels, no preamble
""",
        expected_output=(
            f"A complete {platform} post draft (no hashtags), "
            f"under {char_limit} characters, starting with a compelling hook."
        ),
        agent=agent,
        context=[strategy_task],
    )


def _make_editing_task(agent, writing_task, platform, char_limit, tone, brand_name) -> Task:
    return Task(
        description=f"""
Edit and polish the draft post for {platform}.

- Strictly enforce {char_limit}-character limit (hashtags excluded)
- Brand: {brand_name} | Tone: {tone}
- Sharpen the opening hook if it's weak
- Remove filler words, passive voice, and clichés
- Ensure line breaks and formatting suit {platform}'s feed
- Do NOT add hashtags
- Return ONLY the final post text — nothing else
""",
        expected_output=(
            f"Polished final {platform} post text under {char_limit} characters, "
            "no hashtags, no preamble, no labels."
        ),
        agent=agent,
        context=[writing_task],
    )


def _make_hashtag_task(agent, editing_task, platform, topic, keywords) -> Task:
    platform_guide = {
        Platform.TWITTER: "1-2 highly relevant trending hashtags",
        Platform.LINKEDIN: "3-5 professional industry hashtags",
        Platform.INSTAGRAM: "5-10 relevant niche and community hashtags",
        Platform.FACEBOOK: "2-3 broad topic hashtags",
    }
    guide = platform_guide.get(platform, "3-5 relevant hashtags")

    return Task(
        description=f"""
Select optimal hashtags for {platform} and assemble the final post.

Topic: {topic}
Seed keywords: {', '.join(keywords) if keywords else 'none'}
Platform guide: use {guide}

Return ONLY a valid JSON object (no markdown fences, no extra text):
{{
  "content": "<the full edited post text>",
  "hashtags": ["tag1", "tag2", "tag3"]
}}

Rules:
- "content" = the polished post text from the editor (without hashtags embedded)
- "hashtags" = list of strings WITHOUT the # symbol
""",
        expected_output=(
            'Valid JSON object with "content" (string) and "hashtags" (list of strings). '
            "No markdown, no preamble."
        ),
        agent=agent,
        context=[editing_task],
    )


# ─── Crew Builder ─────────────────────────────────────────────────────────────

def _build_crew(llm, topic, platform, brand_name, brand_description,
                tone, keywords, extra_context, char_limit, post_variant) -> Crew:
    strategist    = _make_strategist(llm)
    writer        = _make_writer(llm)
    editor        = _make_editor(llm, char_limit, platform)
    hashtag_expert = _make_hashtag_expert(llm, platform)

    t_strategy = _make_strategy_task(strategist, topic, platform, tone,
                                      brand_name, brand_description,
                                      keywords, extra_context, post_variant)
    t_writing  = _make_writing_task(writer, t_strategy, platform, tone, char_limit)
    t_editing  = _make_editing_task(editor, t_writing, platform, char_limit, tone, brand_name)
    t_hashtag  = _make_hashtag_task(hashtag_expert, t_editing, platform, topic, keywords)

    return Crew(
        agents=[strategist, writer, editor, hashtag_expert],
        tasks=[t_strategy, t_writing, t_editing, t_hashtag],
        process=Process.sequential,
        verbose=True,
    )


# ─── Output Parser ────────────────────────────────────────────────────────────

def _parse_output(raw: str, platform: str, topic: str) -> dict:
    import uuid
    clean = re.sub(r"```(?:json)?", "", str(raw)).strip().rstrip("`").strip()

    try:
        data = json.loads(clean)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", clean, re.DOTALL)
        data = json.loads(match.group()) if match else {}

    content  = data.get("content", clean)
    hashtags = data.get("hashtags", [])
    if not isinstance(hashtags, list):
        hashtags = []
    hashtags = [str(h).lstrip("#").strip() for h in hashtags if h]

    return {
        "id":             str(uuid.uuid4())[:8],
        "platform":       platform,
        "topic":          topic,
        "content":        content,
        "hashtags":       hashtags,
        "status":         "draft",
        "char_count":     len(content),
        "edited_content": None,
    }


# ─── Public API ───────────────────────────────────────────────────────────────

def generate_posts(config: dict, sample_data: dict) -> list[dict]:
    """Run the 4-agent CrewAI pipeline for every platform × topic combination."""
    llm           = _build_llm(config)
    platforms     = config.get("platforms", ["Twitter/X"])
    topics        = sample_data.get("topics", ["General"])
    keywords      = sample_data.get("keywords", [])
    extra_context = sample_data.get("extra_context", "")
    num_posts     = config.get("num_posts", 2)
    brand_name    = config.get("brand_name", "Our Brand")
    brand_desc    = config.get("brand_description", "")
    tone          = config.get("tone", "Professional")

    all_posts: list[dict] = []

    for platform in platforms:
        char_limit = PLATFORM_LIMITS.get(platform, 2000)
        for topic in topics:
            for variant in range(1, num_posts + 1):
                logger.info(f"Crew → {platform} | {topic} | variant {variant}/{num_posts}")
                try:
                    crew   = _build_crew(llm, topic, platform, brand_name, brand_desc,
                                         tone, keywords, extra_context, char_limit, variant)
                    result = crew.kickoff()
                    post   = _parse_output(str(result), platform, topic)
                    all_posts.append(post)
                    logger.info(f"✅ {platform}/{topic} variant {variant} — {post['char_count']} chars")
                except Exception as exc:
                    logger.error(f"Crew failed: {platform}/{topic} v{variant}: {exc}")
                    raise GenerationError(
                        f"Agent crew failed for {platform} / {topic} (variant {variant}): {exc}"
                    ) from exc

    return all_posts


def regenerate_single_post(config: dict, sample_data: dict, post: dict) -> dict:
    """Re-run the full 4-agent crew for a single post."""
    llm    = _build_llm(config)
    plat   = post["platform"]
    topic  = post.get("topic", "General")
    crew   = _build_crew(llm, topic, plat,
                          config.get("brand_name", "Our Brand"),
                          config.get("brand_description", ""),
                          config.get("tone", "Professional"),
                          sample_data.get("keywords", []),
                          sample_data.get("extra_context", ""),
                          PLATFORM_LIMITS.get(plat, 2000), 1)
    result   = crew.kickoff()
    new_post = _parse_output(str(result), plat, topic)
    new_post["id"]     = post["id"]
    new_post["status"] = post["status"]
    return new_post
