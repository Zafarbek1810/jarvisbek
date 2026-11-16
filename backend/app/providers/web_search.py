"""Explicit web searches. Only the user-provided query leaves Jarvis."""
import asyncio
from urllib.parse import urlsplit

from app.providers.ollama import ProviderError


def _search(query: str) -> list[dict[str, str]]:
    from ddgs import DDGS

    results = []
    for item in DDGS(timeout=8).text(query, max_results=5):
        url = item.get('href', '')
        parsed = urlsplit(url)
        if parsed.scheme not in ('https', 'http') or not parsed.hostname:
            continue
        if any(char.isspace() or char in '<>\\' for char in url):
            continue
        results.append({
            'url': url,
            'title': item.get('title', '')[:200],
            'snippet': item.get('body', '')[:700],
        })
    return results


async def search_web(query: str) -> list[dict[str, str]]:
    if not query or len(query) > 500:
        raise ProviderError('/search dan keyin 1–500 belgili qidiruv so‘rovini yozing.')
    try:
        results = await asyncio.wait_for(asyncio.to_thread(_search, query), timeout=15)
    except Exception as exc:
        raise ProviderError('Veb-qidiruv bajarilmadi. Keyinroq qayta urinib ko‘ring.') from exc
    if not results:
        raise ProviderError('Qidiruv natija bermadi. Boshqa so‘zlar bilan urinib ko‘ring.')
    return results
