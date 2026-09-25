import asyncio
import os
import time
import base64
import hmac
import hashlib
import urllib.parse
from dotenv import load_dotenv
from azure.iot.device.aio import ProvisioningDeviceClient

load_dotenv()

ID_SCOPE = os.environ["ID_SCOPE"]
DEVICE_ID = os.environ["RACK_B_DEVICE_ID"]
PRIMARY_KEY = os.environ["RACK_B_PRIMARY_KEY"]
PROVISIONING_HOST = "global.azure-devices-provisioning.net"

TOKEN_VALIDITY_SECONDS = 3600 * 24 * 30  # 30 días — ajusta según cuánto vayas a dejar Wokwi corriendo


def generar_sas_token(hostname, device_id, key, expiry_epoch):
    resource_uri = f"{hostname}/devices/{device_id}"
    encoded_resource_uri = urllib.parse.quote_plus(resource_uri)
    to_sign = f"{encoded_resource_uri}\n{expiry_epoch}"

    decoded_key = base64.b64decode(key)
    signature = hmac.new(decoded_key, to_sign.encode("utf-8"), hashlib.sha256).digest()
    encoded_signature = urllib.parse.quote_plus(base64.b64encode(signature))

    token = (
        f"SharedAccessSignature sr={encoded_resource_uri}"
        f"&sig={encoded_signature}&se={expiry_epoch}"
    )
    return token


async def main():
    provisioning_client = ProvisioningDeviceClient.create_from_symmetric_key(
        provisioning_host=PROVISIONING_HOST,
        registration_id=DEVICE_ID,
        id_scope=ID_SCOPE,
        symmetric_key=PRIMARY_KEY,
    )
    registration_result = await provisioning_client.register()

    if registration_result.status != "assigned":
        raise RuntimeError(f"Aprovisionamiento fallido: {registration_result.status}")

    hostname = registration_result.registration_state.assigned_hub
    print(f"\nHub asignado: {hostname}")

    expiry = int(time.time()) + TOKEN_VALIDITY_SECONDS
    token = generar_sas_token(hostname, DEVICE_ID, PRIMARY_KEY, expiry)

    username = f"{hostname}/{DEVICE_ID}/?api-version=2021-04-12"

    print("\n===== Copia esto en tu sketch.ino de Wokwi =====")
    print(f'const char* MQTT_HOST = "{hostname}";')
    print(f'const char* MQTT_USERNAME_TEMPLATE = "{username}";')
    print(f'const char* SAS_TOKEN = "{token}";')
    print(f"\nEste token expira en {TOKEN_VALIDITY_SECONDS / 3600:.0f} horas (a las {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expiry))})")


if __name__ == "__main__":
    asyncio.run(main())