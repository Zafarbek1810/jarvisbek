"""Local macOS commands parsed from a voice turn."""
import asyncio
import re
import sys
from urllib.parse import urlencode

from app.providers.ollama import ProviderError
from app.providers.voice import VoiceError, run_audio_tool


async def _run(*args: str) -> None:
    try:
        process = await asyncio.create_subprocess_exec(
            *args, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            status = await asyncio.wait_for(process.wait(), 8)
        except TimeoutError:
            if process.returncode is None:
                process.kill()
            await process.wait()
            raise
        if status:
            raise OSError
    except (OSError, TimeoutError) as exc:
        raise ProviderError('macOS buyruqni bajara olmadi. Dastur nomini tekshirib qayta urining.') from exc


async def _find_youtube_video(query: str) -> str | None:
    try:
        output = await run_audio_tool(
            sys.executable, '-m', 'yt_dlp', '--ignore-config', '--flat-playlist',
            '--skip-download', '--socket-timeout', '5', '--retries', '0',
            '--print', 'id', f'ytsearch1:{query[:500]}', timeout=12,
        )
    except VoiceError:
        return None
    video_id = output.decode('utf-8', errors='replace').strip()
    return video_id if re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id) else None


async def desktop_command(content: str) -> str | None:
    command = content.strip().rstrip('.!?').strip()
    volume = re.fullmatch(
        r'(?:tizim )?ovoz(?:ni|ini)?\s+(pasaytir|kamaytir|ko.tar|kuchaytir|oshir|o.chir|yoq)(?:ing)?',
        command, re.IGNORECASE,
    )
    if volume:
        action = volume[1].lower()
        if re.fullmatch(r'o.chir|yoq', action):
            script = 'set volume output muted ' + ('false' if action == 'yoq' else 'true')
        else:
            change = -10 if action in ('pasaytir', 'kamaytir') else 10
            script = (
                f'set level to (output volume of (get volume settings)) + ({change})\n'
                'if level < 0 then set level to 0\n'
                'if level > 100 then set level to 100\n'
                'set volume output volume level'
            )
        await _run('/usr/bin/osascript', '-e', script)
        return 'Tizim ovozi sozlandi.'

    if re.fullmatch(
        r"(?:menga\s+)?youtube(?:['‘’ʻʼ]?ni)?\s+och(?:ib ber)?(?:ing)?",
        command, re.IGNORECASE,
    ):
        await _run('/usr/bin/open', 'https://www.youtube.com/')
        return 'YouTube ochildi.'

    youtube = re.fullmatch(
        r"(?:(?P<prefix>[^.!?]{1,100})\s+)?"
        r"youtube(?:['‘’ʻʼ]?(?:ga|da|dan))?(?:\s+kirib)?\s+"
        r"(?P<query>.+?)\s+(?:qo['‘’ʻʼ]?y(?:ib ber)?|och|ijro et)(?:ing)?",
        command, re.IGNORECASE,
    )
    if youtube:
        query = re.sub(r'^menga\s+', '', youtube['query'], flags=re.IGNORECASE).strip()
        if re.fullmatch(r'(?:biron|biror|birorta) (?:ashula|qo.shiq|musiqa)', query, re.IGNORECASE):
            query = 'uzbek music song'
        prefix = youtube['prefix'] or ''
        browser = ('-a', 'Google Chrome') if re.search(r'\b(?:google|chrome|xrom|krom)', prefix, re.IGNORECASE) else ()
        video = await _find_youtube_video(query)
        if video:
            params = urlencode({'v': video, 'autoplay': 1})
            await _run('/usr/bin/open', *browser, 'https://www.youtube.com/watch?' + params)
            return 'YouTube videosini ochdim.'
        await _run('/usr/bin/open', *browser, 'https://www.youtube.com/results?' + urlencode({'search_query': query}))
        return 'YouTube qidiruv natijalarini ochdim.'

    app = re.fullmatch(r'([\w][\w .+-]{0,79}?)\s+(?:dasturini\s+)?och(?:ing)?', command, re.IGNORECASE)
    if app:
        name = re.sub(r'ni$', '', app[1], flags=re.IGNORECASE)
        if name.lower() == 'youtube':
            await _run('/usr/bin/open', 'https://www.youtube.com/')
            return 'YouTube ochildi.'
        await _run('/usr/bin/open', '-a', name)
        return f'{name} ochildi.'
    return None
