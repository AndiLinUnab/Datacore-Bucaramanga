import os
import json
import time
import random
import asyncio
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
from azure.iot.device.aio import ProvisioningDeviceClient, IoTHubDeviceClient
from azure.iot.device import Message

load_dotenv()

ID_SCOPE = os.environ["ID_SCOPE"]
DEVICE_ID = os.environ["AIRE_SALA_DEVICE_ID"]
PRIMARY_KEY = os.environ["AIRE_SALA_PRIMARY_KEY"]

LATITUDE = 7.1193
LONGITUDE = -73.1227

SAMPLING_INTERVAL_SEC = 300  # 5 min, según catálogo

AIR_QUALITY_URL = (
    f"https://air-quality-api.open-meteo.com/v1/air-quality"
    f"?latitude={LATITUDE}&longitude={LONGITUDE}"
    f"&current=pm2_5,pm10,us_aqi"
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


def consultar_air_quality():
    """Consulta PM2.5 y AQI reales de la API. CO2 se simula (variable indoor, no disponible en API)."""
    try:
        response = requests.get(AIR_QUALITY_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        current = data["current"]
        return {
            "pm25": current["pm2_5"],
            "aqi": current["us_aqi"],
            "sourceTimestamp": current["time"],
        }
    except requests.exceptions.RequestException as e:
        print(f"[{DEVICE_ID}] Error consultando API de calidad de aire: {e}")
        return None


def simular_co2():
    """CO2 indoor simulado (sensor tipo SCD41), no disponible vía API pública."""
    return random.randint(420, 900)


async def main():
    hub_hostname = await provision_device()

    client = IoTHubDeviceClient.create_from_symmetric_key(
        symmetric_key=PRIMARY_KEY,
        hostname=hub_hostname,
        device_id=DEVICE_ID,
    )

    await client.connect()
    print(f"[{DEVICE_ID}] Conectado a IoT Central.")
    await client.patch_twin_reported_properties({
        "sensorModel": "Open-Meteo Air Quality API (PM2.5/AQI) + SCD41 simulado (CO2)"
    })

    try:
        while True:
            datos_api = consultar_air_quality()

            if datos_api is not None:
                payload = {
                    "pm25": datos_api["pm25"],
                    "aqi": datos_api["aqi"],
                    "co2": simular_co2(),
                    "sourceTimestamp": datos_api["sourceTimestamp"],
                    "ingestionTimestamp": datetime.now(timezone.utc).isoformat(),
                }

                message = Message(json.dumps(payload))
                message.content_type = "application/json"
                message.content_encoding = "utf-8"

                await client.send_message(message)
                print(f"[{DEVICE_ID}] Enviado: {json.dumps(payload)}")
            else:
                print(f"[{DEVICE_ID}] Sin datos en este ciclo, se reintenta en el próximo intervalo.")

            await asyncio.sleep(SAMPLING_INTERVAL_SEC)

    except KeyboardInterrupt:
        print(f"[{DEVICE_ID}] Desconexión manual — evidencia documentada.")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())