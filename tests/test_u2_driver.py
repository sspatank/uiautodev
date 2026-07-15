from unittest import mock

import pytest

from uiautodev.driver.android.u2_driver import U2AndroidDriver
from uiautodev.exceptions import AndroidDriverException


def _make_driver(port=None):
    with mock.patch("uiautodev.driver.android.adb_driver.adbutils.device"):
        return U2AndroidDriver("dummy-serial", port=port)


def test_ud_forwards_port_when_set():
    driver = _make_driver(port=9104)
    with mock.patch("uiautodev.driver.android.u2_driver._get_installed_u2_version", return_value=(3, 7, 0)), \
         mock.patch("uiautodev.driver.android.u2_driver.u2.connect_usb") as connect_usb:
        driver.ud
    connect_usb.assert_called_once_with("dummy-serial", port=9104)


def test_ud_omits_port_when_unset():
    driver = _make_driver(port=None)
    with mock.patch("uiautodev.driver.android.u2_driver.u2.connect_usb") as connect_usb:
        driver.ud
    connect_usb.assert_called_once_with("dummy-serial")


def test_ud_raises_on_old_uiautomator2_when_port_set():
    driver = _make_driver(port=9104)
    with mock.patch("uiautodev.driver.android.u2_driver._get_installed_u2_version", return_value=(3, 5, 0)), \
         mock.patch("uiautodev.driver.android.u2_driver.u2.connect_usb") as connect_usb:
        with pytest.raises(AndroidDriverException, match="3.6.0.*3.5.0"):
            driver.ud
    connect_usb.assert_not_called()


def test_ud_raises_when_installed_version_unknown():
    driver = _make_driver(port=9104)
    with mock.patch("uiautodev.driver.android.u2_driver._get_installed_u2_version", return_value=None), \
         mock.patch("uiautodev.driver.android.u2_driver.u2.connect_usb") as connect_usb:
        with pytest.raises(AndroidDriverException, match="unknown"):
            driver.ud
    connect_usb.assert_not_called()


def test_ud_raises_on_out_of_range_port():
    driver = _make_driver(port=99999)
    with mock.patch("uiautodev.driver.android.u2_driver._INSTALLED_U2_VERSION", (3, 7, 0)), \
         mock.patch("uiautodev.driver.android.u2_driver.u2.connect_usb") as connect_usb:
        with pytest.raises(AndroidDriverException, match="1-65535"):
            driver.ud
    connect_usb.assert_not_called()


def test_parse_version_parses_clean_release_string():
    from uiautodev.driver.android.u2_driver import _parse_version

    assert _parse_version("3.6.0") == (3, 6, 0)
    assert _parse_version("3.6.0.dev1") == (3, 6, 0)


def test_parse_version_returns_none_for_unparseable_string():
    from uiautodev.driver.android.u2_driver import _parse_version

    assert _parse_version("3.6.0rc1") is None
    assert _parse_version("3.6") is None
