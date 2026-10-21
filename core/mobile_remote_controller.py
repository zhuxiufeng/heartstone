"""
MobileRemoteController: Bi-Directional LAN Smartphone & Tablet Remote Control Hub.
Dispatches remote control commands from mobile companion browser to PC Overlay
(toggle capsule, select plan, toggle checklist, trigger AI re-evaluation, switch locale).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("MobileRemoteController")


class RemoteCommandType:
    TOGGLE_OVERLAY = "TOGGLE_OVERLAY"
    TOGGLE_CAPSULE = "TOGGLE_CAPSULE"
    TOGGLE_CHECKLIST = "TOGGLE_CHECKLIST"
    SELECT_PLAN = "SELECT_PLAN"
    REEVALUATE = "REEVALUATE"
    SET_LOCALE = "SET_LOCALE"
    BOOKMARK_HIGHLIGHT = "BOOKMARK_HIGHLIGHT"


@dataclass
class RemoteCommandResult:
    status: str
    command: str
    message: str
    payload: Dict[str, Any]


class MobileRemoteController:
    """Dispatches commands sent from mobile browser to desktop overlay."""

    _instance: Optional[MobileRemoteController] = None

    def __init__(self) -> None:
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}

    @classmethod
    def get_instance(cls) -> MobileRemoteController:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_handler(self, command: str, handler: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
        self._handlers[command] = handler

    def dispatch(self, command: str, params: Optional[Dict[str, Any]] = None) -> RemoteCommandResult:
        params = params or {}
        cmd_upper = command.upper()
        handler = self._handlers.get(cmd_upper)
        if not handler:
            logger.warning(f"No handler registered for remote command: {command}")
            return RemoteCommandResult(
                status="unsupported",
                command=command,
                message=f"未注册的远程控制指令: {command}",
                payload={},
            )

        try:
            res_payload = handler(params) or {}
            return RemoteCommandResult(
                status="ok",
                command=command,
                message="指令已成功响应并在PC端生效",
                payload=res_payload,
            )
        except Exception as e:
            logger.error(f"Error handling remote command {command}: {e}")
            return RemoteCommandResult(
                status="error",
                command=command,
                message=f"执行指令异常: {e}",
                payload={},
            )
