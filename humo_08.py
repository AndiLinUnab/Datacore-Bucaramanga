import os
import csv
import json
import asyncio
from datetime import datetime, timezone
from dotenv import load_dotenv
from azure.iot.device.aio import ProvisioningDeviceClient, IoTHubDeviceClient
from azure.iot.device import Message

load_dotenv()

ID_SCOPE = os.environ["ID_SCOPE"]
DEVICE_ID = os.environ["HUMO_DEVICE_ID"]
PRIMARY_KEY = os.environ["HUMO_PRIMARY_KEY"]

CSV_PATH = "humo_historico.csv"
DELAY_ENTRE_ENVIOS_SEC = 3  # velocidad de reproducción: 3s reales = 1 fila del CSV (acelerado, no tiempo real)


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


def leer_csv():
    with open(CSV_PATH, newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


async def main():
    hub_hostname = await provision_device()

    client = IoTHubDeviceClient.create_from_symmetric_key(
        symmetric_key=PRIMARY_KEY,
        hostname=hub_hostname,
        device_id=DEVICE_ID,
    )

    await client.connect()
    print(f"[{DEVICE_ID}] Conectado a IoT Central (modo replay histórico).")
    await client.patch_twin_reported_properties({
        "sensorModel": "MQ-2 + DS18B20 (replay de histórico CSV)"
    })

    filas = leer_csv()
    print(f"[{DEVICE_ID}] {len(filas)} registros históricos cargados desde {CSV_PATH}")

    try:
        for i, fila in enumerate(filas):
            payload = {
                "smokeLevel": float(fila["smokeLevel"]),
                "tempCeiling": float(fila["tempCeiling"]),
                "originalTimestamp": fila["timestamp"],  # marca de tiempo histórica original
                "replayTimestamp": datetime.now(timezone.utc).isoformat(),  # cuándo se reprodujo realmente
            }

            message = Message(json.dumps(payload))
            message.content_type = "application/json"
            message.content_encoding = "utf-8"

            await client.send_message(message)
            print(f"[{DEVICE_ID}] ({i+1}/{len(filas)}) Enviado: {json.dumps(payload)}")

            await asyncio.sleep(DELAY_ENTRE_ENVIOS_SEC)

        print(f"[{DEVICE_ID}] Replay completo. Todas las filas del histórico fueron enviadas.")

    except KeyboardInterrupt:
        print(f"[{DEVICE_ID}] Replay interrumpido manualmente.")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())