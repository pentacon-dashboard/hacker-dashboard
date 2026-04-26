"""
WebSocket 프록시.

GET /ws/ticks?markets=upbit:KRW-BTC,binance:BTCUSDT

서버가 각 거래소 WS에 연결해 실시간 틱을 공통 포맷으로 정규화 후 클라이언트로 broadcast.
- Upbit: wss://api.upbit.com/websocket/v1
- Binance: wss://stream.binance.com:9443/ws/<symbol>@miniTicker

클라이언트 연결 종료 시 업스트림 close.
한 연결당 최대 10 심볼. 초과 시 rate limit 경고만 (연결은 유지).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

_MAX_SYMBOLS = 10

# 공통 tick 포맷
# {"market": "upbit", "symbol": "KRW-BTC", "price": 45000000, "change_pct": 1.2, "volume": 12345, "ts": "..."}


@router.websocket("/ws/ticks")
async def ws_ticks(websocket: WebSocket, markets: str = "") -> None:
    """
    실시간 시세 WebSocket.
    ?markets=upbit:KRW-BTC,binance:BTCUSDT 형식으로 심볼 지정.
    """
    await websocket.accept()

    # 심볼 파싱
    symbol_list: list[tuple[str, str]] = []
    for entry in markets.split(","):
        entry = entry.strip()
        if ":" not in entry:
            continue
        parts = entry.split(":", 1)
        symbol_list.append((parts[0].strip(), parts[1].strip()))

    if not symbol_list:
        await websocket.send_json({"error": "markets 파라미터가 비어 있습니다"})
        await websocket.close()
        return

    if len(symbol_list) > _MAX_SYMBOLS:
        await websocket.send_json(
            {
                "warning": f"최대 {_MAX_SYMBOLS}개 심볼 지원. {len(symbol_list)}개 요청됨. 앞 {_MAX_SYMBOLS}개만 구독.",
            }
        )
        symbol_list = symbol_list[:_MAX_SYMBOLS]

    tasks: list[asyncio.Task[None]] = []
    stop_event = asyncio.Event()

    async def _stream_upbit(sym: str) -> None:
        """Upbit WS 연결 → 정규화 → 클라이언트로 전달."""
        try:
            import httpx

            # Upbit WS는 httpx-ws 또는 websockets 필요. 여기서는 Polling fallback
            # TODO: pip install websockets 후 실 연결로 교체
            while not stop_event.is_set():
                # 폴링 방식 fallback (MVP)
                try:
                    async with httpx.AsyncClient(timeout=3.0) as client:
                        resp = await client.get(
                            "https://api.upbit.com/v1/ticker",
                            params={"markets": sym},
                        )
                        data = resp.json()
                        if data:
                            t = data[0]
                            tick = {
                                "market": "upbit",
                                "symbol": sym,
                                "price": float(t.get("trade_price", 0)),
                                "change_pct": float(t.get("signed_change_rate", 0)) * 100,
                                "volume": float(t.get("acc_trade_volume_24h", 0)),
                                "ts": datetime.now(UTC).isoformat(),
                            }
                            await websocket.send_json(tick)
                except Exception as exc:
                    logger.debug("Upbit polling error for %s: %s", sym, exc)
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            pass

    async def _stream_binance(sym: str) -> None:
        """Binance WS 연결 → 정규화 → 클라이언트로 전달."""
        try:
            import httpx

            # TODO: pip install websockets 후 wss://stream.binance.com:9443/ws/<sym>@miniTicker 교체
            while not stop_event.is_set():
                try:
                    async with httpx.AsyncClient(timeout=3.0) as client:
                        resp = await client.get(
                            "https://api.binance.com/api/v3/ticker/24hr",
                            params={"symbol": sym},
                        )
                        data = resp.json()
                        tick = {
                            "market": "binance",
                            "symbol": sym,
                            "price": float(data.get("lastPrice", 0)),
                            "change_pct": float(data.get("priceChangePercent", 0)),
                            "volume": float(data.get("volume", 0)),
                            "ts": datetime.now(UTC).isoformat(),
                        }
                        await websocket.send_json(tick)
                except Exception as exc:
                    logger.debug("Binance polling error for %s: %s", sym, exc)
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            pass

    # 심볼별 스트리밍 태스크 생성
    for market_name, sym in symbol_list:
        if market_name == "upbit":
            task = asyncio.create_task(_stream_upbit(sym))
        elif market_name == "binance":
            task = asyncio.create_task(_stream_binance(sym))
        else:
            await websocket.send_json({"warning": f"미지원 market: {market_name}"})
            continue
        tasks.append(task)

    try:
        # 클라이언트 연결 유지 (disconnet 대기)
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30)
            except TimeoutError:
                # keepalive ping
                await websocket.send_json({"type": "ping"})
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        stop_event.set()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
