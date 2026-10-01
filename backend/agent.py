import os
import json
import re
import asyncio
import urllib.parse
import ipaddress
import logging
import httpx
from dotenv import load_dotenv
from anthropic import AsyncAnthropic
import google.generativeai as genai

try:
    from groq import AsyncGroq
except ImportError:
    AsyncGroq = None

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables from .env file
env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(env_path, override=True)

# SSRF and Safe Host Checking
RESERVED_IP_RANGES = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("fc00::/7"),
]

YOUTUBE_ID_REGEX = re.compile(r'^[a-zA-Z0-9_-]{11}$')

def normalize_url(url: str) -> str | None:
    if not url or not isinstance(url, str):
        return None
    
    url = url.strip().strip("'\"`")
    if not url:
        return None
        
    # Remove obvious trailing punctuation accidentally included in AI output
    url = re.sub(r'[\.,\)\]"\']+$', '', url)
    
    # Prepend scheme if missing
    if url.startswith("//"):
        url = "https:" + url
    elif not re.match(r'^[a-zA-Z][a-zA-Z0-9+\-.]*://', url):
        if re.match(r'^(www\.|[a-zA-Z0-9-]+\.[a-zA-Z]{2,})', url):
            url = "https://" + url
        else:
            return None
            
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme.lower() not in ("http", "https"):
            return None
        if not parsed.hostname:
            return None
        return urllib.parse.urlunparse(parsed)
    except Exception:
        return None

def is_safe_url(url: str) -> bool:
    normalized = normalize_url(url)
    if not normalized:
        return False
    try:
        parsed = urllib.parse.urlparse(normalized)
        hostname = (parsed.hostname or "").lower()
        if not hostname:
            return False
            
        if hostname in ("localhost", "0.0.0.0", "127.0.0.1", "::1") or hostname.endswith((".local", ".internal", ".lan", ".localhost")):
            return False
            
        try:
            ip = ipaddress.ip_address(hostname)
            for rng in RESERVED_IP_RANGES:
                if ip in rng:
                    return False
        except ValueError:
            pass
            
        return True
    except Exception:
        return False

def extract_clean_text_and_url(title_or_text: str, candidate_url: str | None = None) -> tuple[str, str | None]:
    title = (title_or_text or "").strip()
    url = candidate_url or ""
    
    # Check markdown link [Title](https://...)
    md_match = re.search(r'\[([^\]]+)\]\((https?://[^\)]+)\)', title)
    if md_match:
        title = md_match.group(1).strip()
        url = md_match.group(2).strip()
        
    # Check raw URL inside title
    raw_url_match = re.search(r'(https?://[^\s\)]+)', title)
    if raw_url_match and not url:
        url = raw_url_match.group(1).strip()
        title = re.sub(r'https?://[^\s\)]+', '', title).strip(" :-")
        
    return title, normalize_url(url)

async def verify_youtube_video_id(client: httpx.AsyncClient, video_id: str, timeout: float = 4.0) -> bool:
    if not video_id or not YOUTUBE_ID_REGEX.match(video_id):
        return False
    try:
        oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        res = await client.get(oembed_url, timeout=timeout)
        if res.status_code == 200:
            return True
    except Exception as e:
        logger.debug(f"[LINK] oEmbed verification error for video ID {video_id}: {e}")
    return False

async def resolve_youtube_resource(client: httpx.AsyncClient, item: dict, topic: str, youtube_api_key: str | None = None, timeout: float = 8.0) -> dict:
    title, ai_url = extract_clean_text_and_url(item.get("title", ""), item.get("url", ""))
    channel = item.get("channel", "") or item.get("source", "")
    description = item.get("why", "")
    
    query = f"{topic} {title} {channel}".strip()
    logger.info(f"[LINK] Resolving YouTube: '{title}' (Channel: '{channel}', Topic: '{topic}')")
    
    candidate_video_ids = []
    
    # Check if AI provided a direct watch URL with a valid video ID
    if ai_url and "watch?v=" in ai_url:
        parsed = urllib.parse.urlparse(ai_url)
        qs = urllib.parse.parse_qs(parsed.query)
        v_param = qs.get("v", [None])[0]
        if v_param and YOUTUBE_ID_REGEX.match(v_param):
            candidate_video_ids.append(v_param)
            
    # Method 1: YouTube Data API v3 if API key available
    if youtube_api_key and youtube_api_key != "your_youtube_api_key_here":
        try:
            yt_api_url = "https://www.googleapis.com/youtube/v3/search"
            params = {
                "part": "snippet",
                "type": "video",
                "maxResults": 5,
                "regionCode": "IN",
                "relevanceLanguage": "en",
                "q": query,
                "key": youtube_api_key
            }
            res = await client.get(yt_api_url, params=params, timeout=timeout)
            if res.status_code == 200:
                data = res.json()
                for yt_item in data.get("items", []):
                    v_id = yt_item.get("id", {}).get("videoId")
                    if v_id and YOUTUBE_ID_REGEX.match(v_id) and v_id not in candidate_video_ids:
                        candidate_video_ids.append(v_id)
                logger.info(f"[LINK] YouTube API candidate IDs: {candidate_video_ids}")
        except Exception as e:
            logger.warning(f"[LINK] YouTube API error: {e}")

    # Method 2: HTML search scraping fallback if no candidate IDs
    if not candidate_video_ids:
        try:
            encoded_query = urllib.parse.quote(query)
            search_url = f"https://www.youtube.com/results?search_query={encoded_query}"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
            res = await client.get(search_url, headers=headers, timeout=timeout)
            if res.status_code == 200:
                scraped_ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', res.text)
                for v_id in scraped_ids:
                    if v_id not in candidate_video_ids:
                        candidate_video_ids.append(v_id)
                logger.info(f"[LINK] YouTube Scraper candidate IDs: {candidate_video_ids[:5]}")
        except Exception as e:
            logger.warning(f"[LINK] YouTube Scraper error: {e}")

    # Verify candidate video IDs (up to 3 attempts)
    for v_id in candidate_video_ids[:3]:
        is_valid = await verify_youtube_video_id(client, v_id, timeout=min(4.0, timeout))
        if is_valid:
            verified_url = f"https://www.youtube.com/watch?v={v_id}"
            logger.info(f"[LINK] Verified YouTube video: {verified_url}")
            return {
                "title": title,
                "channel": channel,
                "url": verified_url,
                "why": description,
                "resource_type": "video",
                "verified": True,
                "is_search_fallback": False
            }
        else:
            logger.info(f"[LINK] Rejected candidate video ID: {v_id}")

    # Fallback to safe search URL if verification failed
    search_fallback = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
    logger.info(f"[LINK] YouTube verification failed. Returning search fallback: {search_fallback}")
    return {
        "title": title,
        "channel": channel,
        "url": search_fallback,
        "why": description,
        "resource_type": "video",
        "verified": False,
        "is_search_fallback": True
    }

async def verify_web_url(client: httpx.AsyncClient, candidate_url: str, resource_type: str = "notes", timeout: float = 8.0) -> str | None:
    if not is_safe_url(candidate_url):
        return None
    try:
        # Try HEAD request first
        try:
            res = await client.head(candidate_url, follow_redirects=True, timeout=timeout)
            if 200 <= res.status_code < 400:
                final_url = str(res.url)
                if is_safe_url(final_url):
                    return final_url
        except Exception:
            pass

        # Fallback to GET stream
        async with client.stream("GET", candidate_url, follow_redirects=True, timeout=timeout) as res:
            if 200 <= res.status_code < 400:
                final_url = str(res.url)
                if is_safe_url(final_url):
                    return final_url
    except Exception as e:
        logger.debug(f"[LINK] Verification failed for {candidate_url}: {e}")
    return None

async def resolve_web_resource(client: httpx.AsyncClient, item: dict, topic: str, resource_type: str = "notes", timeout: float = 8.0) -> dict:
    title, ai_url = extract_clean_text_and_url(item.get("title", ""), item.get("url", ""))
    source = item.get("source", "")
    item_type = item.get("type", resource_type.capitalize())
    
    query = f"{topic} {title} {source}".strip()
    logger.info(f"[LINK] Resolving Web Resource ({resource_type}): '{title}' (Source: '{source}')")
    
    candidates = []
    if ai_url and is_safe_url(ai_url) and not any(blocked in ai_url for blocked in ["google.com/search", "youtube.com", "example.com", "placeholder"]):
        candidates.append(ai_url)
        
    # Search DuckDuckGo lite
    try:
        ddg_url = "https://lite.duckduckgo.com/lite/"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = await client.post(ddg_url, data={"q": query}, headers=headers, timeout=timeout)
        if res.status_code == 200:
            extracted_links = re.findall(r'href="(https?://[^"]+)"', res.text)
            for link in extracted_links:
                norm_link = normalize_url(link)
                if norm_link and is_safe_url(norm_link):
                    if not any(blocked in norm_link for blocked in ["duckduckgo.com", "bing.com", "google.com", "youtube.com", "yandex.com"]):
                        if norm_link not in candidates:
                            candidates.append(norm_link)
    except Exception as e:
        logger.warning(f"[LINK] DuckDuckGo search error for '{query}': {e}")
        
    # Verify candidate URLs (up to 3 attempts)
    for cand in candidates[:3]:
        logger.info(f"[LINK] Verifying web candidate: {cand}")
        verified_url = await verify_web_url(client, cand, resource_type=resource_type, timeout=timeout)
        if verified_url:
            logger.info(f"[LINK] Verified web resource: {verified_url}")
            return {
                "title": title,
                "url": verified_url,
                "source": source,
                "type": item_type,
                "resource_type": resource_type,
                "verified": True,
                "is_search_fallback": False
            }
        else:
            logger.info(f"[LINK] Rejected web candidate: {cand}")
            
    # Safe search fallback if verification failed
    search_fallback = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
    logger.info(f"[LINK] Web resource verification failed. Returning search fallback: {search_fallback}")
    return {
        "title": title,
        "url": search_fallback,
        "source": source,
        "type": item_type,
        "resource_type": resource_type,
        "verified": False,
        "is_search_fallback": True
    }

async def enrich_study_pack(pack: dict, topic: str = "") -> dict:
    if not pack or not isinstance(pack, dict):
        return pack

    link_timeout = float(os.getenv("LINK_TIMEOUT", "8.0"))
    youtube_api_key = os.getenv("YOUTUBE_API_KEY") or os.getenv("YOUTUBE_DATA_API_KEY")
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    
    async with httpx.AsyncClient(follow_redirects=True, timeout=link_timeout, headers=headers) as client:
        # Process videos
        if "videos" in pack and isinstance(pack.get("videos"), list):
            video_tasks = [resolve_youtube_resource(client, v, topic, youtube_api_key=youtube_api_key, timeout=link_timeout) for v in pack["videos"]]
            resolved_videos = await asyncio.gather(*video_tasks, return_exceptions=True)
            
            clean_videos = []
            seen_video_urls = set()
            for res in resolved_videos:
                if isinstance(res, dict) and res.get("title"):
                    url = res.get("url")
                    if url and url in seen_video_urls:
                        continue
                    if url:
                        seen_video_urls.add(url)
                    clean_videos.append(res)
            pack["videos"] = clean_videos

        # Process web resources
        category_map = {
            "notes_links": "notes",
            "question_papers": "paper",
            "marking_schemes": "scheme"
        }
        for key, res_type in category_map.items():
            if key in pack and isinstance(pack.get(key), list):
                tasks = [resolve_web_resource(client, item, topic, resource_type=res_type, timeout=link_timeout) for item in pack[key]]
                resolved_items = await asyncio.gather(*tasks, return_exceptions=True)
                
                clean_items = []
                seen_urls = set()
                for res in resolved_items:
                    if isinstance(res, dict) and res.get("title"):
                        url = res.get("url")
                        if url and url in seen_urls:
                            continue
                        if url:
                            seen_urls.add(url)
                        clean_items.append(res)
                pack[key] = clean_items

    return pack

async def generate_study_pack(board: str, class_level: str, subject: str, topic: str) -> dict:
    load_dotenv(env_path, override=True)
    groq_api_key = os.getenv("GROQ_API_KEY")
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    gemini_api_key = os.getenv("GEMINI_API_KEY")

    system_prompt = """You are an expert academic assistant helping school students in India prepare for exams.
You will receive: Board, Class, Subject, and Topic.
Your job is to generate a complete, reliable, age-appropriate study pack.

Always respond in this EXACT JSON format (no extra text, no markdown fences):
{
  "what_to_learn": ["point 1", "point 2", "point 3", "point 4", "point 5"],
  "question_papers": [
    {"title": "Paper title", "url": "", "source": "Source name"},
    {"title": "Paper title", "url": "", "source": "Source name"}
  ],
  "marking_schemes": [
    {"title": "Scheme title", "url": "", "source": "Source name"},
    {"title": "Scheme title", "url": "", "source": "Source name"}
  ],
  "topic_summary": {
    "overview": "2-3 sentence overview of the topic",
    "key_concepts": ["concept 1", "concept 2", "concept 3", "concept 4"],
    "important_formulas": ["formula 1", "formula 2"],
    "common_mistakes": ["mistake 1", "mistake 2"]
  },
  "videos": [
    {"title": "Video title", "url": "", "channel": "Channel name", "why": "Why this video helps"},
    {"title": "Video title", "url": "", "channel": "Channel name", "why": "Why this video helps"}
  ],
  "notes_links": [
    {"title": "Notes title", "url": "", "source": "Source name", "type": "Resource"},
    {"title": "Notes title", "url": "", "source": "Source name", "type": "Resource"}
  ]
}

Rules:
- Give accurate video titles and channel names (e.g. Khan Academy, Vedantu, Physics Wallah, Unacademy, Sunlike study)
- Keep language simple for school students
- important_formulas can be empty array [] if subject has no formulas"""

    user_message = f"Board: {board}, Class: {class_level}, Subject: {subject}, Topic: {topic}\nPlease generate the complete study pack using real and helpful resources."

    async def get_groq_response():
        if not groq_api_key or groq_api_key == "your_groq_api_key_here":
            return None
        if not AsyncGroq:
            return None
        client = AsyncGroq(api_key=groq_api_key)
        for model_name in ["openai/gpt-oss-120b", "qwen/qwen3.8-27b", "openai/gpt-oss-20b", "allam-2-7b"]:
            try:
                response = await client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.2,
                    max_tokens=4096
                )
                content = response.choices[0].message.content
                return json.loads(content)
            except Exception as e:
                logger.error(f"Groq ({model_name}) error: {e}")
        return None

    async def get_gemini_response():
        if not gemini_api_key or gemini_api_key == "your_api_key_here":
            return None
        genai.configure(api_key=gemini_api_key)
        for model_name in ['gemini-2.5-flash', 'gemini-flash-latest', 'gemini-2.5-pro', 'gemini-1.5-flash']:
            try:
                model = genai.GenerativeModel(model_name, system_instruction=system_prompt)
                response = await model.generate_content_async(
                    user_message,
                    generation_config=genai.types.GenerationConfig(
                        response_mime_type="application/json",
                        temperature=0.2,
                    )
                )
                return json.loads(response.text)
            except Exception as e:
                logger.error(f"Gemini ({model_name}) error: {e}")
        return None

    groq_res, gemini_res = await asyncio.gather(get_groq_response(), get_gemini_response())

    # Fallback to Anthropic if both failed and anthropic key is present
    if not groq_res and not gemini_res and anthropic_api_key and anthropic_api_key != "your_api_key_here":
        try:
            client = AsyncAnthropic(api_key=anthropic_api_key)
            response = await client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=system_prompt,
                tools=[{"type": "web_search_20250305", "name": "web_search"}],
                messages=[{"role": "user", "content": user_message}]
            )
            response_text = "".join([block.text for block in response.content if hasattr(block, "text")])
            cleaned_text = response_text.strip()
            if cleaned_text.startswith("```"):
                cleaned_text = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned_text)
                cleaned_text = re.sub(r"\n?```$", "", cleaned_text)
            groq_res = json.loads(cleaned_text.strip())
        except Exception as e:
            logger.error(f"Anthropic error: {e}")

    if not groq_res and not gemini_res:
        logger.warning("AI API calls failed or keys not set. Generating fallback study pack.")
        groq_res = create_fallback_study_pack(board, class_level, subject, topic)

    link_timeout = float(os.getenv("LINK_TIMEOUT", "8.0"))

    # Enrich search URLs into verified direct resources concurrently
    try:
        enriched_groq = await asyncio.wait_for(enrich_study_pack(groq_res, topic), timeout=link_timeout * 2) if groq_res else None
    except Exception as e:
        logger.warning(f"Groq enrichment timeout: {e}")
        enriched_groq = groq_res

    try:
        enriched_gemini = await asyncio.wait_for(enrich_study_pack(gemini_res, topic), timeout=link_timeout * 2) if gemini_res else None
    except Exception as e:
        logger.warning(f"Gemini enrichment timeout: {e}")
        enriched_gemini = gemini_res

    return {
        "response1": enriched_groq,
        "response2": enriched_gemini
    }

def create_fallback_study_pack(board: str, class_level: str, subject: str, topic: str) -> dict:
    t_encoded = urllib.parse.quote(f"{board} Class {class_level} {subject} {topic}".strip())
    return {
        "what_to_learn": [
            f"Understand core concepts of {topic} for {board} Class {class_level} {subject}.",
            f"Learn key definitions, laws, and theoretical principles of {topic}.",
            f"Master standard numerical problems and practice diagrams related to {topic}.",
            f"Review previous year exam questions and marking schemes for {board} Class {class_level}.",
            f"Practice time-bound sample question papers for thorough exam preparation."
        ],
        "question_papers": [
            {
                "title": f"{board} Class {class_level} {subject} - {topic} Sample Paper 1",
                "url": f"https://www.google.com/search?q={t_encoded}+sample+paper+question+paper",
                "source": f"{board} Official Resources",
                "resource_type": "paper",
                "verified": False,
                "is_search_fallback": True
            },
            {
                "title": f"{board} Class {class_level} Previous Year Questions - {topic}",
                "url": f"https://www.google.com/search?q={t_encoded}+previous+year+questions",
                "source": "Vedantu / BYJU'S / CBSE Online",
                "resource_type": "paper",
                "verified": False,
                "is_search_fallback": True
            }
        ],
        "marking_schemes": [
            {
                "title": f"{board} Class {class_level} {subject} Marking Scheme & Model Answers",
                "url": f"https://www.google.com/search?q={t_encoded}+marking+scheme+model+answers",
                "source": f"{board} Academic Portal",
                "resource_type": "scheme",
                "verified": False,
                "is_search_fallback": True
            }
        ],
        "topic_summary": {
            "overview": f"A comprehensive revision pack covering {topic} for {board} Class {class_level} {subject}. Designed to help students achieve high marks in school exams and board assessments.",
            "key_concepts": [
                f"Core Principles of {topic}",
                f"Application of {topic} in {subject}",
                f"Important Diagrams and Flowcharts",
                f"Formulae and Standard Units"
            ],
            "important_formulas": [
                f"Standard relation for {topic} (refer to textbook chapter)"
            ],
            "common_mistakes": [
                "Mixing up standard SI units during calculations.",
                "Omitting essential steps or labels in exam diagrams."
            ]
        },
        "videos": [
            {
                "title": f"{topic} Class {class_level} {subject} Full Chapter Explanation",
                "url": f"https://www.youtube.com/results?search_query={t_encoded}+full+chapter",
                "channel": "Physics Wallah / Khan Academy India",
                "why": "Clear visual explanations tailored for Indian school curricula.",
                "resource_type": "video",
                "verified": False,
                "is_search_fallback": True
            },
            {
                "title": f"{topic} Class {class_level} Top Exam Questions & Revision",
                "url": f"https://www.youtube.com/results?search_query={t_encoded}+one+shot+revision",
                "channel": "Vedantu 9&10 / Unacademy Class 10",
                "why": "Quick one-shot revision of high-weightage exam topics.",
                "resource_type": "video",
                "verified": False,
                "is_search_fallback": True
            }
        ],
        "notes_links": [
            {
                "title": f"{topic} Revision Notes & Summary PDF",
                "url": f"https://www.google.com/search?q={t_encoded}+revision+notes+pdf",
                "source": "NCERT / Board Notes",
                "type": "Study Notes",
                "resource_type": "notes",
                "verified": False,
                "is_search_fallback": True
            }
        ]
    }




