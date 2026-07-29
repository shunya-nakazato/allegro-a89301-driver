"""Async facade over the synchronous A89301 driver (``asyncio.to_thread``)."""

from __future__ import annotations

import asyncio

from allegro_a89301.driver import A89301Driver

__all__ = ["AsyncA89301Driver"]


class AsyncA89301Driver:
    """Async counterpart of :class:`A89301Driver`; identical method contracts.

    Blocking calls (bus I/O, ~30 ms EEPROM waits) run via ``asyncio.to_thread``
    so the event loop never blocks. Concurrent awaits are safe (the wrapped
    driver's lock serializes access). The constructor opens the bus synchronously.
    """

    def __init__(self, bus: int = 1, *, use_cache: bool = False) -> None:
        self._driver = A89301Driver(bus, use_cache=use_cache)

    async def read(self, name: str) -> int | float:
        """Async version of :meth:`A89301Driver.read`."""
        return await asyncio.to_thread(self._driver.read, name)

    async def write(self, name: str, physical_value: int | float) -> int | float:
        """Async version of :meth:`A89301Driver.write`."""
        return await asyncio.to_thread(self._driver.write, name, physical_value)

    async def persist(self, name: str) -> None:
        """Async version of :meth:`A89301Driver.persist`."""
        await asyncio.to_thread(self._driver.persist, name)

    async def invalidate_cache(self, name: str | None = None) -> None:
        """Async version of :meth:`A89301Driver.invalidate_cache`."""
        await asyncio.to_thread(self._driver.invalidate_cache, name)

    async def close(self) -> None:
        """Async version of :meth:`A89301Driver.close` (idempotent)."""
        await asyncio.to_thread(self._driver.close)

    async def __aenter__(self) -> AsyncA89301Driver:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()
