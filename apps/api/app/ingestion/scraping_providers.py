"""Small REST clients. No provider credentials or response bodies in errors."""

import json
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener


class ProviderError(RuntimeError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward an API bearer token to another endpoint.
        return None


def post_json(url: str, key: str, payload: dict) -> dict:
    request = Request(
        url,
        data=json.dumps(payload, allow_nan=False).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with build_opener(NoRedirect).open(request, timeout=75) as response:
            raw = response.read(12000001)
        if len(raw) > 12000000:
            raise ProviderError("Provider response exceeds 12 MB.")
        result = json.loads(raw)
        if not isinstance(result, dict) or result.get("error"):
            raise ProviderError("Provider returned an error or invalid response.")
        return result
    except HTTPError as error:
        raise ProviderError(
            f"Provider HTTP {error.code}; request not retried."
        ) from None
    except (URLError, TimeoutError, OSError, ValueError):
        raise ProviderError("Provider request failed; request not retried.") from None


class OpenRouter:
    def __init__(self, key: str, model: str):
        self.key, self.model = key, model

    def complete(self, messages: list, tools: list, max_tokens: int) -> dict:
        return post_json(
            "https://openrouter.ai/api/v1/chat/completions",
            self.key,
            {
                "model": self.model,
                "messages": messages,
                "tools": tools,
                "tool_choice": "required",
                "parallel_tool_calls": False,
                "max_tokens": max_tokens,
                "provider": {"require_parameters": True},
            },
        )


class Firecrawl:
    def __init__(self, key: str):
        self.key = key

    def discover(self, url: str, search: str) -> dict:
        return post_json(
            "https://api.firecrawl.dev/v2/map",
            self.key,
            {
                "url": url,
                "search": search,
                "includeSubdomains": False,
                "limit": 50,
                "timeout": 60000,
            },
        )

    def scrape(self, url: str) -> dict:
        return post_json(
            "https://api.firecrawl.dev/v2/scrape",
            self.key,
            {
                "url": url,
                "formats": ["markdown", "rawHtml", "links"],
                "parsers": ["pdf"],
                "onlyMainContent": False,
                "maxAge": 0,
                "proxy": "basic",
                "timeout": 60000,
            },
        )
