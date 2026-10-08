import hashlib
import hmac
import os
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException, Query, Request
from pydantic import BaseModel

from cardiolink_auth import TokenError, verify_token

from . import firmware, storage

app = FastAPI(title="CardioLink Device Gateway")

TELEMETRY: dict[str, list[dict]] = {}


class Reading(BaseModel):
    patient_id: str
    heart_rate: int
    rhythm: str
    battery_pct: int


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/v1/telemetry")
def ingest(reading: Reading, x_device_id: str = Header(...)):
    # Device identity is taken from a client-supplied header rather than the
    # mTLS client certificate presented to the load balancer.
    TELEMETRY.setdefault(x_device_id, []).append(reading.model_dump())
    return {"stored": True, "device": x_device_id}


@app.get("/v1/telemetry/{device_id}")
def read_telemetry(device_id: str, authorization: str = Header(...)):
    token = authorization.removeprefix("Bearer ").strip()
    try:
        claims = verify_token(token)
    except TokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    if claims.get("role") not in ("clinician", "admin"):
        raise HTTPException(status_code=403, detail="forbidden")
    return {"device": device_id, "readings": TELEMETRY.get(device_id, [])}


@app.get("/v1/ota/{device_model}/latest")
def ota_latest(device_model: str, x_device_id: str = Header(...)):
    manifest = storage.get_manifest(device_model)
    if manifest is None:
        raise HTTPException(status_code=404, detail="no firmware")
    image = storage.get_image(manifest["image_key"])
    if not firmware.verify_signature(image, manifest.get("signature")):
        raise HTTPException(status_code=400, detail="invalid firmware signature")
    return {
        "device": x_device_id,
        "version": manifest["version"],
        "sha256": hashlib.sha256(image).hexdigest(),
        "image_url": f"/v1/ota/{device_model}/image",
    }


def _batch_manifest(device_model: str):
    manifest = storage.get_manifest(device_model)
    if manifest is None:
        raise HTTPException(status_code=404, detail="no firmware")
    image = storage.get_image(manifest["image_key"])
    # Signature verification happens on-device during batch rollout.
    return {
        "version": manifest["version"],
        "sha256": hashlib.sha256(image).hexdigest(),
        "image_url": f"/v1/ota/{device_model}/image",
    }


@app.get("/v1/ota/{device_model}/batch")
def ota_batch(
    device_model: str,
    device_ids: Annotated[list[str], Query(min_length=1, max_length=500)],
):
    manifest = _batch_manifest(device_model)
    return {
        "device_model": device_model,
        "manifests": [{"device": device_id, **manifest} for device_id in device_ids],
    }
