# cardiolink-device-gateway

Edge API for CardioLink implantable cardiac monitors.

- `POST /v1/telemetry` ingests readings from bedside/phone relays (device identified by `X-Device-Id`).
- `GET /v1/telemetry/{device_id}` returns readings to clinicians (bearer token from `cardiolink-shared-auth`).
- `GET /v1/ota/{device_model}/latest` serves the latest signed firmware manifest from the firmware S3 bucket.

- `GET /v1/ota/{device_model}/batch?device_ids=relay-1&device_ids=relay-2` prepares fleet rollout manifests for up to 500 devices, fetching and hashing the image once per request.

Firmware images are RSA-signed by the release pipeline; the gateway verifies the
signature against `/etc/cardiolink/firmware_signing.pub` before offering an update.

Run the full stack with docker compose from `cardiolink-infra/local`.
