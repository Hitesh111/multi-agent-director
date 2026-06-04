import httpx
import re
from urllib.parse import quote

_IMAGE_PROMPT_RE = re.compile(
    r"\*{0,2}IMAGE\s*PROMPT:\*{0,2}\s*(.+?)(?:\n|$)", re.DOTALL | re.IGNORECASE
)

POLLINATIONS_BASE = "https://image.pollinations.ai/prompt"


def _clean_prompt(prompt: str) -> str:
    prompt = re.sub(r"^\*{1,2}\s*", "", prompt)
    prompt = re.sub(r"\s*\*{1,2}$", "", prompt)
    prompt = prompt.strip().strip('"').strip("'")
    # Truncate to stay within Pollinations URL length limit (~200 chars for prompt)
    if len(prompt) > 200:
        prompt = prompt[:197] + "..."
    return prompt


def extract_prompt(text: str) -> str | None:
    m = _IMAGE_PROMPT_RE.search(text)
    if m:
        return _clean_prompt(m.group(1))
    return None


async def generate_image(prompt: str, width: int = 1024, height: int = 1024) -> str | None:
    cleaned = _clean_prompt(prompt)
    url = f"{POLLINATIONS_BASE}/{quote(cleaned)}?width={width}&height={height}&nologo=true"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, follow_redirects=True)
            if resp.status_code < 500 and len(resp.content) > 1000:
                return url
    except httpx.TimeoutException:
        pass
    return url if len(cleaned) < 250 else None
