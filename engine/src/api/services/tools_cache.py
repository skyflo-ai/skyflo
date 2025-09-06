import asyncio
from typing import Dict, List, Any, Callable, Awaitable, Optional


class ToolsCache:
    def __init__(self) -> None:
        self._by_name: Dict[str, Dict[str, Any]] = {}
        self._all_dumped: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()

    def invalidate(self) -> None:
        self._by_name.clear()
        self._all_dumped.clear()

    def _build(self, tools: List[Any]) -> None:
        by_name: Dict[str, Dict[str, Any]] = {}
        dumped: List[Dict[str, Any]] = []
        for t in tools:
            d = t.model_dump() if hasattr(t, "model_dump") else t
            name = d.get("name")
            if isinstance(name, str) and name:
                by_name[name] = d
                dumped.append(d)
        self._by_name = by_name
        self._all_dumped = dumped

    async def _load(self, fetcher: Callable[[], Awaitable[List[Any]]]) -> None:
        tools = await fetcher()
        self._build(tools)

    async def ensure_loaded(self, fetcher: Callable[[], Awaitable[List[Any]]]) -> None:
        if self._all_dumped:
            return
        async with self._lock:
            if self._all_dumped:
                return
            await self._load(fetcher)

    async def get_all(self, fetcher: Callable[[], Awaitable[List[Any]]]) -> List[Dict[str, Any]]:
        await self.ensure_loaded(fetcher)
        return self._all_dumped

    async def get_by_name(
        self, name: str, fetcher: Callable[[], Awaitable[List[Any]]]
    ) -> Optional[Dict[str, Any]]:
        await self.ensure_loaded(fetcher)
        item = self._by_name.get(name)
        if item is not None:
            return item

        async with self._lock:
            if not self._all_dumped:
                await self._load(fetcher)
            return self._by_name.get(name)
