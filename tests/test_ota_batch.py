import hashlib
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app import main


@pytest.fixture
def firmware_store(monkeypatch):
    image = b"release-image"
    manifest = {
        "version": "2.1.0",
        "image_key": "cl-monitor-v2/2.1.0.bin",
        "signature": "release-signature",
    }
    get_manifest = Mock(return_value=manifest)
    get_image = Mock(return_value=image)
    monkeypatch.setattr(main.storage, "get_manifest", get_manifest)
    monkeypatch.setattr(main.storage, "get_image", get_image)
    return manifest, image, get_manifest, get_image


def test_batch_fans_out_one_manifest(firmware_store):
    manifest, image, get_manifest, get_image = firmware_store
    response = TestClient(main.app).get(
        "/v1/ota/cl-monitor-v2/batch",
        params=[("device_ids", "relay-1"), ("device_ids", "relay-2")],
    )
    assert response.status_code == 200
    assert response.json() == {
        "device_model": "cl-monitor-v2",
        "manifests": [
            {
                "device": device,
                "version": manifest["version"],
                "sha256": hashlib.sha256(image).hexdigest(),
                "image_url": "/v1/ota/cl-monitor-v2/image",
            }
            for device in ["relay-1", "relay-2"]
        ],
    }
    get_manifest.assert_called_once_with("cl-monitor-v2")
    get_image.assert_called_once_with(manifest["image_key"])


def test_batch_missing_firmware(firmware_store):
    _, _, get_manifest, get_image = firmware_store
    get_manifest.return_value = None
    response = TestClient(main.app).get(
        "/v1/ota/cl-monitor-v2/batch", params={"device_ids": "relay-1"}
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "no firmware"}
    get_image.assert_not_called()


@pytest.mark.parametrize("device_count", [0, 501])
def test_batch_requires_bounded_device_list(firmware_store, device_count):
    _, _, get_manifest, get_image = firmware_store
    response = TestClient(main.app).get(
        "/v1/ota/cl-monitor-v2/batch",
        params=[("device_ids", f"relay-{i}") for i in range(device_count)],
    )
    assert response.status_code == 422
    get_manifest.assert_not_called()
    get_image.assert_not_called()


@pytest.mark.parametrize("valid_signature, status", [(True, 200), (False, 400)])
def test_latest_keeps_signature_check(monkeypatch, firmware_store, valid_signature, status):
    manifest, image, _, _ = firmware_store
    verify = Mock(return_value=valid_signature)
    monkeypatch.setattr(main.firmware, "verify_signature", verify)
    response = TestClient(main.app).get(
        "/v1/ota/cl-monitor-v2/latest", headers={"X-Device-Id": "relay-1"}
    )
    assert response.status_code == status
    verify.assert_called_once_with(image, manifest["signature"])
