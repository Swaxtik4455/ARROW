"""
info_services.py
Free internet & reference services: Open-Meteo Weather (no key needed),
NewsAPI + Free RSS fallback, Wikipedia summaries, and Date/Time helpers.
"""

import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Optional

import requests
import wikipedia

from config import config


class InfoServices:
    """Provides weather, news, Wikipedia, and date/time information."""

    WEATHER_CODES = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Foggy",
        48: "Depositing rime fog",
        51: "Light drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        71: "Slight snow",
        80: "Rain showers",
        95: "Thunderstorm",
    }

    # ---------------- Date & Time ----------------
    @staticmethod
    def get_current_time() -> str:
        return f"The current time is {datetime.now().strftime('%I:%M %p')}."

    @staticmethod
    def get_current_date() -> str:
        return f"Today is {datetime.now().strftime('%A, %B %d, %Y')}."

    # ---------------- Open-Meteo Weather (100% Free, No API Key) ----------------
    def get_weather(self, city: Optional[str] = None) -> str:
        target_city = (city or config.get("default_city", "Faizabad")).strip()
        try:
            geo_url = (
                "https://geocoding-api.open-meteo.com/v1/search"
                f"?name={urllib.parse.quote(target_city)}&count=1&language=en&format=json"
            )
            geo_res = requests.get(geo_url, timeout=8).json()
            results = geo_res.get("results")
            if not results:
                return f"Could not find location coordinates for '{target_city}'."

            loc = results[0]
            lat, lon = loc["latitude"], loc["longitude"]
            resolved_name = f"{loc['name']}, {loc.get('country', '')}".strip(", ")

            weather_url = (
                f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
                "&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code"
                "&daily=temperature_2m_max,temperature_2m_min&timezone=auto&forecast_days=2"
            )
            w_data = requests.get(weather_url, timeout=8).json()
            curr = w_data.get("current", {})
            daily = w_data.get("daily", {})

            temp = curr.get("temperature_2m", "N/A")
            humidity = curr.get("relative_humidity_2m", "N/A")
            wind = curr.get("wind_speed_10m", "N/A")
            desc = self.WEATHER_CODES.get(curr.get("weather_code", -1), "Clear conditions")

            tomorrow_note = ""
            if len(daily.get("temperature_2m_max", [])) >= 2:
                t_max = daily["temperature_2m_max"][1]
                t_min = daily["temperature_2m_min"][1]
                tomorrow_note = f" Tomorrow's forecast: {t_min}°C to {t_max}°C."

            return (
                f"Weather in {resolved_name}: {desc}, {temp}°C, "
                f"humidity {humidity}%, wind {wind} km/h.{tomorrow_note}"
            )
        except requests.RequestException:
            return "Unable to reach the Open-Meteo weather service. Check your internet connection."
        except Exception as e:
            return f"Weather lookup failed: {e}"

    # ---------------- News (NewsAPI + Free Google News RSS Fallback) ----------------
    def get_news(self, category: Optional[str] = None, max_items: int = 5) -> str:
        api_key = config.news_api_key
        if api_key and api_key != "your_news_api_key_here":
            news_api_result = self._fetch_newsapi(api_key, category, max_items)
            if news_api_result:
                return news_api_result

        # Free fallback requiring zero API keys
        return self._fetch_google_news_rss(category, max_items)

    def _fetch_newsapi(self, api_key: str, category: Optional[str], max_items: int) -> Optional[str]:
        valid_cats = {"business", "entertainment", "general", "health", "science", "sports", "technology"}
        params = {"country": "in", "apiKey": api_key, "pageSize": max_items}
        if category and category.lower() in valid_cats:
            params["category"] = category.lower()
        elif category:
            params["q"] = category

        try:
            endpoint = "https://newsapi.org/v2/top-headlines"
            resp = requests.get(endpoint, params=params, timeout=8)
            if resp.status_code != 200:
                return None
            articles = resp.json().get("articles", [])
            if not articles:
                return None
            headlines = [f"{i}. {a['title']}" for i, a in enumerate(articles[:max_items], start=1) if a.get("title")]
            label = f" ({category})" if category else ""
            return f"Top Indian Headlines{label}:\n" + "\n".join(headlines)
        except Exception:
            return None

    def _fetch_google_news_rss(self, topic: Optional[str], max_items: int) -> str:
        try:
            if topic:
                q = urllib.parse.quote(topic.strip())
                url = f"https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
            else:
                url = "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en"

            resp = requests.get(url, timeout=8)
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
            items = root.findall(".//item")[:max_items]
            if not items:
                return "No news articles were returned at the moment."

            headlines: List[str] = []
            for idx, item in enumerate(items, start=1):
                title_el = item.find("title")
                if title_el is not None and title_el.text:
                    headlines.append(f"{idx}. {title_el.text.strip()}")

            header = f"Top Headlines on '{topic}':" if topic else "Top Indian News Headlines:"
            return header + "\n" + "\n".join(headlines)
        except requests.RequestException:
            return "Unable to fetch news right now. Check your internet connection."
        except Exception as e:
            return f"News feed error: {e}"

    # ---------------- Wikipedia ----------------
    @staticmethod
    def search_wikipedia(topic: str) -> str:
        if not topic.strip():
            return "Please specify a topic to look up on Wikipedia."
        try:
            wikipedia.set_lang("en")
            summary = wikipedia.summary(topic.strip(), sentences=3, auto_suggest=True)
            return f"According to Wikipedia: {summary}"
        except wikipedia.DisambiguationError as e:
            options = ", ".join(e.options[:5])
            return f"'{topic}' is ambiguous. Did you mean one of these: {options}?"
        except wikipedia.PageError:
            return f"No Wikipedia article was found for '{topic}'."
        except Exception:
            return "Could not reach Wikipedia right now. Check your internet connection."