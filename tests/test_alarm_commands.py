import asyncio
import json

from aioring.alarm import RingAlarmConnection


class FakeWs:
    closed = False

    def __init__(self):
        self.sent = []

    async def send_str(self, s):
        self.sent.append(json.loads(s))


def _run(coro_fn):
    conn = RingAlarmConnection(None, None, "loc")
    conn.asset_id = "asset"
    conn._ws = FakeWs()
    asyncio.run(coro_fn(conn))
    return conn._ws.sent[-1]["msg"]


def test_sound_siren_payload():
    msg = _run(lambda c: c.sound_siren("panel"))
    assert msg["msg"] == "DeviceInfoSet" and msg["dst"] == "asset"
    assert msg["body"] == [{"zid": "panel", "command": {"v1": [
        {"commandType": "security-panel.sound-siren", "data": {}}]}}]


def test_silence_siren_payload():
    msg = _run(lambda c: c.silence_siren("panel"))
    assert msg["body"][0]["command"]["v1"][0] == {
        "commandType": "security-panel.silence-siren", "data": {}}


def test_set_mode_payload_unchanged():
    msg = _run(lambda c: c.set_mode("panel", "all"))
    assert msg["body"][0]["command"]["v1"][0] == {
        "commandType": "security-panel.switch-mode", "data": {"mode": "all", "bypass": []}}
