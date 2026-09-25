import os
import json
import time
import asyncio
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
from azure.iot.device.aio import ProvisioningDeviceClient, IoTHubDeviceClient
from azure.iot.device import Message

load_dotenv()

ID_SCOPE = os.environ["ID_SCOPE"]
DEVICE_ID = os.environ["CLIMA_EXT_DEVICE_ID"]
PRIMARY_KEY = os.environ["CLIMA_EXT_PRIMARY_KEY"]

# Coordenadas de Bucaramanga (ajusta si tu escenario está en otra ciudad)
LATITUDE = 7.1193
LONGITUDE = -73.1227

SAMPLING_INTERVAL_SEC = 300  # 5 min, según catálogo (el origen más lento de la flota)

OPEN_METEO_URL = (
    f"https://api.open-meteo.com/v1/forecast"
    f"?latitude={LATITUDE}&longitude={LONGITUDE}"
    f"&current=temperature_2m,relative_humidity_2m,shortwave_radiation"
)


async def provision_device():
    provisioning_client = ProvisioningDeviceClient.create_from_symmetric_key(
        provisioning_host="global.azure-devices-provisioning.net",
        registration_id=DEVICE_ID,
        id_scope=ID_SCOPE,
        symmetric_key=PRIMARY_KEY,
    )
    result = await provisioning_client.register()
    if result.status != "assigned":
        raise RuntimeError(f"Aprovisionamiento fallido: {result.status}")
    return result.registration_state.assigned_hub


def consultar_open_meteo():
    """Consulta la API pública y devuelve las variables mapeadas al Device Template."""
    try:
        response = requests.get(OPEN_METEO_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        current = data["current"]

        return {
            "tempExt": current["temperature_2m"],
            "humidityExt": current["relative_humidity_2m"],
            "solarRadiation": current["shortwave_radiation"],
            "sourceTimestamp": current["time"],  # marca de tiempo de la fuente original
        }
    except requests.exceptions.RequestException as e:
        print(f"[{DEVICE_ID}] Error consultando Open-Meteo: {e}")
        return None


async def main():
    hub_hostname = await provision_device()

    client = IoTHubDeviceClient.create_from_symmetric_key(
        symmetric_key=PRIMARY_KEY,
        hostname=hub_hostname,
        device_id=DEVICE_ID,
    )

    await client.connect()
    print(f"[{DEVICE_ID}] Conectado a IoT Central.")
    await client.patch_twin_reported_properties({"sensorModel": "API Open-Meteo (puente HTTP)"})

    try:
        while True:
            datos_api = consultar_open_meteo()

            if datos_api is not None:
                ingestion_timestamp = datetime.now(timezone.utc).isoformat()

                payload = {
                    "tempExt": datos_api["tempExt"],
                    "humidityExt": datos_api["humidityExt"],
                    "solarRadiation": datos_api["solarRadiation"],
                    "sourceTimestamp": datos_api["sourceTimestamp"],
                    "ingestionTimestamp": ingestion_timestamp,
                }

                message = Message(json.dumps(payload))
                message.content_type = "application/json"
                message.content_encoding = "utf-8"

                await client.send_message(message)
                print(f"[{DEVICE_ID}] Enviado: {json.dumps(payload)}")
            else:
                print(f"[{DEVICE_ID}] Sin datos de la API en este ciclo, se reintenta en el próximo intervalo.")

            await asyncio.sleep(SAMPLING_INTERVAL_SEC)

    except KeyboardInterrupt:
        print(f"[{DEVICE_ID}] Desconexión manual — evidencia documentada.")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())