import asyncio
import json
import random
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from azure.iot.device.aio import ProvisioningDeviceClient, IoTHubDeviceClient

load_dotenv()

ID_SCOPE = os.environ["ID_SCOPE"]
DEVICE_ID = os.environ["RACK_C_DEVICE_ID"]
PRIMARY_KEY = os.environ["RACK_C_PRIMARY_KEY"]
PROVISIONING_HOST = "global.azure-devices-provisioning.net"

SAMPLING_INTERVAL_SEC = 30  # coincide con la tabla del catálogo (Fase 0)


async def provision_device():
    """Aprovisiona el dispositivo vía DPS y devuelve el hostname de IoT Hub asignado."""
    provisioning_client = ProvisioningDeviceClient.create_from_symmetric_key(
        provisioning_host=PROVISIONING_HOST,
        registration_id=DEVICE_ID,
        id_scope=ID_SCOPE,
        symmetric_key=PRIMARY_KEY,
    )
    registration_result = await provisioning_client.register()

    if registration_result.status != "assigned":
        raise RuntimeError(f"Aprovisionamiento fallido: {registration_result.status}")

    print(f"[{DEVICE_ID}] Aprovisionado en: {registration_result.registration_state.assigned_hub}")
    return registration_result.registration_state.assigned_hub


def generar_telemetria():
    """Simula lecturas realistas de un rack, ancladas al rango del SHT31."""
    return {
        "tempIntake": round(random.uniform(20.0, 26.0), 1),
        "tempExhaust": round(random.uniform(30.0, 38.0), 1),
        "humidity": round(random.uniform(35.0, 55.0), 1),
    }


async def manejar_comando(command_request, client):
    """Responde al comando 'reboot' definido en el Device Template."""
    print(f"[{DEVICE_ID}] Comando recibido: {command_request.name}")
    if command_request.name == "reboot":
        print(f"[{DEVICE_ID}] Simulando reinicio del nodo...")
        payload = {"result": True, "data": "Reinicio simulado completado"}
    else:
        payload = {"result": False, "data": "Comando no reconocido"}

    from azure.iot.device import MethodResponse
    response = MethodResponse.create_from_method_request(command_request, 200, payload)
    await client.send_method_response(response)


async def manejar_property_update(patch, client):
    """Atiende cambios en la property writable samplingIntervalSec."""
    global SAMPLING_INTERVAL_SEC
    print(f"[{DEVICE_ID}] Property update recibido: {patch}")

    if "samplingIntervalSec" in patch:
        SAMPLING_INTERVAL_SEC = int(patch["samplingIntervalSec"])
        version = patch["$version"]
        reported = {
            "samplingIntervalSec": {
                "value": SAMPLING_INTERVAL_SEC,
                "ac": 200,
                "av": version,
                "ad": "Intervalo actualizado correctamente",
            }
        }
        await client.patch_twin_reported_properties(reported)
        print(f"[{DEVICE_ID}] Nuevo intervalo de muestreo: {SAMPLING_INTERVAL_SEC}s")

async def escuchar_comandos(client):
    while True:
        method_request = await client.receive_method_request()
        await manejar_comando(method_request, client)


async def escuchar_property_updates(client):
    while True:
        patch = await client.receive_twin_desired_properties_patch()
        await manejar_property_update(patch, client)

async def main():
    hub_hostname = await provision_device()

    client = IoTHubDeviceClient.create_from_symmetric_key(
        symmetric_key=PRIMARY_KEY,
        hostname=hub_hostname,
        device_id=DEVICE_ID,
    )

    await client.connect()
    print(f"[{DEVICE_ID}] Conectado a IoT Central.")

    await client.patch_twin_reported_properties({"firmwareVersion": "1.0.3-python"})

    # Lanza los "escuchadores" en segundo plano, en el mismo event loop
    asyncio.create_task(escuchar_comandos(client))
    asyncio.create_task(escuchar_property_updates(client))

    try:
        while True:
            data = generar_telemetria()
            data["timestamp"] = datetime.now(timezone.utc).isoformat()
            msg_json = json.dumps(data)

            from azure.iot.device import Message
            message = Message(msg_json)
            message.content_type = "application/json"
            message.content_encoding = "utf-8"

            await client.send_message(message)
            print(f"[{DEVICE_ID}] Enviado: {msg_json}")

            await asyncio.sleep(SAMPLING_INTERVAL_SEC)

    except KeyboardInterrupt:
        print(f"[{DEVICE_ID}] Desconexión manual.")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())