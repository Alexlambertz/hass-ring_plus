from aioring.devices import alarm_category, flatten_doc


def test_flatten_and_category():
    doc = {"general": {"v2": {"zid": "abc", "deviceType": "sensor.contact", "name": "Door"}},
           "device": {"v1": {"faulted": True}}}
    flat = flatten_doc(doc)
    assert flat["zid"] == "abc" and flat["faulted"] is True
    assert alarm_category(flat["deviceType"]) == "contact_sensors"
    assert alarm_category("lock") is None
