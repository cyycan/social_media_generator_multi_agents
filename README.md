# 📣 Social Media Generator

An AI-powered, step-by-step social media content generator built with **LangChain**, **Streamlit**, and a clean wizard-style UI inspired by professional agentic apps.

## ✨ Features

- **4-Step Wizard**: Configure → Upload Data → Review Posts → Publish
- **Multi-Platform Support**: Twitter/X, LinkedIn, Instagram, Facebook
- **Multi-Provider LLM**: OpenAI, Anthropic (Claude), Google (Gemini)
- **LangChain LCEL Chains**: Platform-aware prompt chains with structured JSON output
- **Data Ingestion**: CSV upload, text paste, or manual entry
- **Review & Edit**: Per-post editing, regeneration, approval workflow
- **Publishing**: Mock mode (safe test) + Live API (Twitter, LinkedIn stubs)
- **Clean Architecture**: Service layer, centralized state, modular wizard steps

---

## 🏗️ Project Structure

```
social-media-generator/
├── streamlit_app.py          # Entry point
├── src/
│   ├── app.py                # Main Streamlit app + stepper UI
│   ├── state_manager.py      # Centralized session state
│   ├── models.py             # Domain models & enums
│   ├── logger.py             # Structured logging
│   ├── exceptions.py         # Custom exceptions
│   ├── services/
│   │   ├── generator_service.py   # LangChain LCEL generation
│   │   ├── data_service.py        # CSV / text parsing
│   │   └── publisher_service.py   # Mock + real publish
│   └── steps/
│       ├── step_configure.py  # Step 1: LLM + brand config
│       ├── step_upload.py     # Step 2: Data ingestion
│       ├── step_review.py     # Step 3: Review & edit posts
│       └── step_publish.py    # Step 4: Publish to platforms
├── sample_data/
│   └── sample_topics.csv      # Example CSV for testing
├── .streamlit/
│   └── config.toml            # Theme configuration
├── .env.example               # Environment variables template
└── requirements.txt
```

---

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/cyycan/social_media_generator_multi_agents.git
cd social-media-generator
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate        # macOS/Linux
.\venv\Scripts\activate         # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment (optional)

```bash
cp .env.example .env
# Edit .env with your API keys
```

> You can also enter your API key directly in the app UI — it's stored only in your browser session.

### 5. Run the App

```bash
streamlit run streamlit_app.py
```

Visit **http://localhost:8501** in your browser.

---

## 📋 Workflow

### Step 1 — ⚙️ Configure
- Choose your LLM provider (OpenAI / Anthropic / Google)
- Enter your API key
- Select target platforms (Twitter/X, LinkedIn, Instagram, Facebook)
- Set brand name, description, tone, and posts-per-topic

### Step 2 — 📂 Upload Data
- Upload a **CSV** file with columns: `topic`, `keywords`, `context`
- Or **paste text** (each line = a topic, `#hashtags` → keywords)
- Or use the **manual entry** form
- Download the included `sample_topics.csv` template to get started

### Step 3 — ✍️ Review Posts
- Click **Generate Posts** to run the LangChain generation pipeline
- Review all generated posts per platform
- Edit content inline (with live character counter)
- **Regenerate** individual posts
- **Approve** posts you want to publish
- Use **Approve All** for bulk approval

### Step 4 — 🚀 Publish
- Choose **Mock Mode** (safe — no real posts) or **Live API Mode**
- Preview approved posts before publishing
- View detailed publish results with post links
- Start a new campaign from scratch

---

## 🤖 Multi-Agent Architecture (CrewAI)

Each post is produced by a **4-agent sequential crew**:

```
ContentStrategist → SocialMediaWriter → ContentEditor → HashtagExpert
```

| Agent | Role | Output |
|-------|------|--------|
| 🧠 **Content Strategist** | Analyzes topic, picks best angle for the platform, defines key messages & emotional hook | Strategy brief |
| ✍️ **Social Media Writer** | Drafts the post with a scroll-stopping hook, platform-native format | Raw draft |
| 🔍 **Content Editor** | Polishes tone, enforces character limits, cuts filler & clichés | Refined post text |
| #️⃣ **Hashtag Expert** | Selects platform-optimal hashtags, assembles the final post as JSON | `{"content": "...", "hashtags": [...]}` |

Each `platform × topic × variant` combination runs its own independent Crew.
For example: 2 platforms × 3 topics × 2 variants = **12 crews × 4 agents = 48 LLM calls**.

```python
crew = Crew(
    agents=[strategist, writer, editor, hashtag_expert],
    tasks=[t_strategy, t_writing, t_editing, t_hashtag],
    process=Process.sequential,
    verbose=True,
)
result = crew.kickoff()
```

---

## 🌐 Deploying to Streamlit Cloud

1. Push your repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo, set **main file**: `streamlit_app.py`
4. Add your API key under **Secrets**:

```toml
# .streamlit/secrets.toml (DO NOT commit this file)
OPENAI_API_KEY = "sk-..."
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Streamlit |
| **Multi-Agent Framework** | **CrewAI** |
| AI Framework | LangChain (used by CrewAI) |
| LLM Providers | OpenAI, Anthropic, Google Gemini |
| Data | Pandas |
| Publishing | Tweepy (Twitter), Requests (LinkedIn) |
| Logging | Python `logging` |

---
