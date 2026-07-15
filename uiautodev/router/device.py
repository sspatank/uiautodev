#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Fri Mar 01 2024 14:00:10 by codeskyblue
"""

import io
import logging
from functools import wraps
from itertools import chain
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from uiautodev import command_proxy
from uiautodev.command_types import Command, CurrentAppResponse, InstallAppRequest, InstallAppResponse, TapRequest
from uiautodev.model import DeviceInfo, Node, ShellResponse
from uiautodev.provider import BaseProvider

logger = logging.getLogger(__name__)

_MISSING = object()


def _handle_driver_errors(action: str):
    """Wraps an endpoint so any driver failure becomes a clean 500 (or 501 for
    unimplemented commands) instead of an uncaught exception."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except NotImplementedError as e:
                return Response(content=f"{action} not implemented", media_type="text/plain", status_code=501)
            except Exception as e:
                logger.exception(f"Error {action}")
                return Response(content=str(e), media_type="text/plain", status_code=500)

        return wrapper

    return decorator


def make_router(provider: BaseProvider) -> APIRouter:
    router = APIRouter()

    @router.get("/list")
    @_handle_driver_errors("listing devices")
    def _list() -> List[DeviceInfo]:
        """List devices"""
        return provider.list_devices()

    @router.get(
        "/{serial}/screenshot/{id}",
        responses={200: {"content": {"image/jpeg": {}}}},
        response_class=Response,
    )
    @_handle_driver_errors("taking screenshot")
    def _screenshot(serial: str, id: int) -> Response:
        """Take a screenshot of device"""
        driver = provider.get_device_driver(serial)
        pil_img = driver.screenshot(id).convert("RGB")
        buf = io.BytesIO()
        pil_img.save(buf, format="JPEG")
        image_bytes = buf.getvalue()
        return Response(content=image_bytes, media_type="image/jpeg")

    @router.get("/{serial}/hierarchy")
    @_handle_driver_errors("dumping hierarchy")
    def dump_hierarchy(serial: str, format: str = "json"):
        """Dump the view hierarchy of an Android device"""
        driver = provider.get_device_driver(serial)
        xml_data, hierarchy = driver.dump_hierarchy()
        if format == "xml":
            return Response(content=xml_data, media_type="text/xml")
        elif format == "json":
            return hierarchy
        else:
            return Response(content=f"Invalid format: {format}", media_type="text/plain", status_code=400)

    @router.post('/{serial}/command/tap')
    @_handle_driver_errors("tapping device")
    def command_tap(serial: str, params: TapRequest):
        """Run a command on the device"""
        driver = provider.get_device_driver(serial)
        command_proxy.tap(driver, params)
        return {"status": "ok"}

    @router.post('/{serial}/command/installApp')
    @_handle_driver_errors("installing app")
    def install_app(serial: str, params: InstallAppRequest) -> InstallAppResponse:
        """Install app"""
        driver = provider.get_device_driver(serial)
        return command_proxy.app_install(driver, params)

    @router.get('/{serial}/command/currentApp')
    @_handle_driver_errors("getting current app")
    def current_app(serial: str) -> CurrentAppResponse:
        """Get current app"""
        driver = provider.get_device_driver(serial)
        return command_proxy.app_current(driver)

    @router.post('/{serial}/command/{command}')
    @_handle_driver_errors("running command")
    def _command_proxy_other(serial: str, command: Command, params: Dict[str, Any] = None):
        """Run a command on the device"""
        driver = provider.get_device_driver(serial)
        return command_proxy.send_command(driver, command, params)

    @router.get('/{serial}/backupApp')
    @_handle_driver_errors("backing up app")
    def _backup_app(serial: str, packageName: str):
        """Backup app

        Added in 0.5.0
        """
        driver = provider.get_device_driver(serial)
        chunks = driver.open_app_file(packageName)
        first_chunk = next(chunks, _MISSING)
        file_name = f"{packageName}.apk"
        headers = {
            'Content-Disposition': f'attachment; filename="{file_name}"'
        }
        if first_chunk is _MISSING:
            return StreamingResponse(iter(()), headers=headers)
        return StreamingResponse(chain([first_chunk], chunks), headers=headers)



    return router
