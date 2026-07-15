#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Fri Mar 01 2024 14:19:29 by codeskyblue
"""

import logging
import time
from functools import cached_property
from importlib.metadata import PackageNotFoundError, version as pkg_version
from typing import Optional, Tuple

import uiautomator2 as u2
from PIL import Image

from uiautodev.driver.android.adb_driver import ADBAndroidDriver
from uiautodev.driver.android.common import parse_xml
from uiautodev.exceptions import AndroidDriverException
from uiautodev.model import AppInfo, Node, WindowSize

logger = logging.getLogger(__name__)

MIN_CUSTOM_PORT_VERSION = (3, 6, 0)


def _parse_version(version_str: str) -> Tuple[int, int, int]:
    """Parses a clean "X.Y.Z" version string, e.g. as published by uiautomator2 on PyPI."""
    parts = (version_str.split(".") + ["0", "0"])[:3]
    return tuple(int(p) for p in parts)


def _get_installed_u2_version() -> Optional[Tuple[int, int, int]]:
    try:
        return _parse_version(pkg_version("uiautomator2"))
    except (PackageNotFoundError, ValueError):
        return None


_INSTALLED_U2_VERSION = _get_installed_u2_version()

class U2AndroidDriver(ADBAndroidDriver):
    def __init__(self, serial: str, port: Optional[int] = None):
        super().__init__(serial)
        self.port = port

    @cached_property
    def ud(self) -> u2.Device:
        if self.port is not None:
            if _INSTALLED_U2_VERSION is None or _INSTALLED_U2_VERSION < MIN_CUSTOM_PORT_VERSION:
                installed_desc = (
                    ".".join(map(str, _INSTALLED_U2_VERSION)) if _INSTALLED_U2_VERSION else "unknown"
                )
                min_desc = ".".join(map(str, MIN_CUSTOM_PORT_VERSION))
                raise AndroidDriverException(
                    f"Custom uiautomator2 port requires uiautomator2>={min_desc}, "
                    f"but {installed_desc} is installed. "
                    f"Upgrade with: pip install -U uiautomator2 (or poetry update uiautomator2 "
                    f"if you're developing uiautodev with poetry)"
                )
            try:
                from uiautomator2.core import check_port
            except ImportError:
                logger.warning(
                    "uiautomator2.core.check_port is unavailable; skipping port range validation"
                )
            else:
                try:
                    check_port(self.port)
                except ValueError as e:
                    raise AndroidDriverException(str(e))
            return u2.connect_usb(self.serial, port=self.port)
        return u2.connect_usb(self.serial)
    
    def screenshot(self, id: int) -> Image.Image:
        if id > 0:
            # u2 is not support multi-display yet
            return super().screenshot(id)
        return self.ud.screenshot()

    def dump_hierarchy(self, display_id: Optional[int] = 0) -> Tuple[str, Node]:
        """returns xml string and hierarchy object"""
        start = time.time()
        xml_data = self._dump_hierarchy_raw()
        logger.debug("dump_hierarchy cost: %s", time.time() - start)

        wsize = self.adb_device.window_size()
        logger.debug("window size: %s", wsize)
        return xml_data, parse_xml(
            xml_data, WindowSize(width=wsize[0], height=wsize[1]), display_id
        )

    def _dump_hierarchy_raw(self) -> str:
        """
        uiautomator2 server is conflict with "uiautomator dump" command.

        uiautomator dump errors:
        - ERROR: could not get idle state.
        """
        try:
            return self.ud.dump_hierarchy()
        except Exception as e:
            raise AndroidDriverException(f"Failed to dump hierarchy: {str(e)}")
    
    def tap(self, x: int, y: int):
        self.ud.click(x, y)
    
    def send_keys(self, text: str):
        self.ud.send_keys(text)
    
    def clear_text(self):
        self.ud.clear_text()