"""Local stdio MCP entry point for Jarvis tools."""

from mcp.server.fastmcp import FastMCP

from app.core.config import get_settings
from app.providers.desktop import desktop_command
from app.providers.voice import voice_status
from app.providers.web_search import search_web

server = FastMCP('jarvis-local')


@server.tool()
async def web_search(query: str) -> list[dict[str, str]]:
    """Search the web. The query is sent to an external search service."""
    return await search_web(query)


@server.tool()
async def speech_status() -> dict:
    """Check whether Jarvis speech recognition and synthesis are configured."""
    return await voice_status()


@server.tool()
async def run_desktop_command(command: str) -> str:
    """Run an explicitly requested macOS command to open an app or YouTube, or adjust volume."""
    settings = get_settings()
    if settings.environment != 'development' or not settings.desktop_voice_commands:
        raise ValueError('Mahalliy kompyuter buyruqlari o‘chirilgan.')
    result = await desktop_command(command)
    if result is None:
        raise ValueError('Buyruq tanilmadi. Dastur, YouTube yoki ovoz boshqaruvi buyrug‘ini yuboring.')
    return result


if __name__ == '__main__':
    server.run(transport='stdio')
