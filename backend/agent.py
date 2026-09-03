import os
import json
import re
import asyncio
import urllib.parse
import httpx
from dotenv import load_dotenv
from anthropic import AsyncAnthropic
import google.generativeai as genai

try:
    from groq import AsyncGroq
except ImportError:
    AsyncGroq = None

# Load environment variables from .env file
env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(env_path, override=True)

async def resolve_youtube_video(client, title, channel="", topic=""):
    search_term = f"{title} {channel} {topic}".strip()
    try:
        encoded_query = urllib.parse.quote(search_term)
        url = f"https://www.youtube.com/results?search_query={encoded_query}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        res = await client.get(url, headers=headers, timeout=2.0)
        video_ids = re.findall(r'"videoId":"([^"]+)"', res.text)
        if video_ids:
            return f"https://www.youtube.com/watch?v={video_ids[0]}"
    except Exception as e:
        print("YT resolution error:", e)
    return f"https://www.youtube.com/results?search_query={urllib.parse.quote(search_term)}"

async def resolve_web_resource(client, title, source="", topic=""):
    search_term = f"{title} {source} {topic}".strip()
    try:
        url = "https://lite.duckduckgo.com/lite/"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = await client.post(url, data={"q": search_term}, headers=headers, timeout=2.0)
        links = re.findall(r'href="(https?://[^"]+)"', res.text)
        valid_links = [l for l in links if "duckduckgo.com" not in l and "bing.com" not in l]
        if valid_links:
            return valid_links[0]
    except Exception as e:
        print("Web resolution error:", e)
    return f"https://www.google.com/search?q={urllib.parse.quote(search_term)}"

async def enrich_study_pack(pack, topic=""):
    if not pack or not isinstance(pack, dict):
        return pack
    
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=2.0) as client:
            # Resolve videos
            if "videos" in pack and isinstance(pack["videos"], list):
                tasks = [resolve_youtube_video(client, v.get("title", ""), v.get("channel", ""), topic) for v in pack["videos"]]
                yt_urls = await asyncio.gather(*tasks, return_exceptions=True)
                for i, vid in enumerate(pack["videos"]):
                    res_url = yt_urls[i] if i < len(yt_urls) else None
                    if isinstance(res_url, str) and res_url:
                        vid["url"] = res_url
                    else:
                        search_term = f"{vid.get('title', '')} {vid.get('channel', '')} {topic}".strip()
                        vid["url"] = f"https://www.youtube.com/results?search_query={urllib.parse.quote(search_term)}"
                        
            # Resolve web links (notes, question papers, marking schemes)
            for key in ["notes_links", "question_papers", "marking_schemes"]:
                if key in pack and isinstance(pack[key], list):
                    tasks = [resolve_web_resource(client, item.get("title", ""), item.get("source", ""), topic) for item in pack[key]]
                    web_urls = await asyncio.gather(*tasks, return_exceptions=True)
                    for i, item in enumerate(pack[key]):
                        res_url = web_urls[i] if i < len(web_urls) else None
                        existing_url = item.get("url", "")
                        if not existing_url or "google.com/search" in existing_url or "youtube.com/results" in existing_url:
                            if isinstance(res_url, str) and res_url:
                                item["url"] = res_url
                            else:
                                search_term = f"{item.get('title', '')} {item.get('source', '')} {topic}".strip()
                                item["url"] = f"https://www.google.com/search?q={urllib.parse.quote(search_term)}"
    except Exception as e:
        print("Enrichment fallback triggered:", e)
        
    return pack

async def generate_study_pack(board: str, class_level: str, subject: str, topic: str) -> dict:
    # Always ensure latest keys are loaded per request
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
        try:
            client = AsyncGroq(api_key=groq_api_key)
            response = await client.chat.completions.create(
                model="llama-3.3-70b-versatile",
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
            print(f"Groq error: {e}")
            return None

    async def get_gemini_response():
        if not gemini_api_key or gemini_api_key == "your_api_key_here":
            return None
        try:
            genai.configure(api_key=gemini_api_key)
            model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=system_prompt)
            response = await model.generate_content_async(
                user_message,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                )
            )
            return json.loads(response.text)
        except Exception as e:
            print(f"Gemini error: {e}")
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
            print(f"Anthropic error: {e}")

    if not groq_res and not gemini_res:
        raise RuntimeError("Failed to generate responses from the models. Please verify GROQ_API_KEY or GEMINI_API_KEY environment variables.")

    # Enrich search URLs into direct video & web links concurrently with strict 3s max timeout
    try:
        enriched_groq = await asyncio.wait_for(enrich_study_pack(groq_res, topic), timeout=3.0) if groq_res else None
    except Exception as e:
        print("Groq enrichment skipped due to timeout:", e)
        enriched_groq = groq_res

    try:
        enriched_gemini = await asyncio.wait_for(enrich_study_pack(gemini_res, topic), timeout=3.0) if gemini_res else None
    except Exception as e:
        print("Gemini enrichment skipped due to timeout:", e)
        enriched_gemini = gemini_res

    return {
        "response1": enriched_groq,
        "response2": enriched_gemini
    }


