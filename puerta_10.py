import os
import json
import asyncio
import threading
from datetime import datetime, timezone
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from azure.iot.device.aio import ProvisioningDeviceClient, IoTHubDeviceClient
from azure.iot.device import Message

load_dotenv()

ID_SCOPE = os.environ["ID_SCOPE"]
DEVICE_ID = os.environ["PUERTA_DEVICE_ID"]
PRIMARY_KEY = os.environ["PUERTA_PRIMARY_KEY"]

app = Flask(__name__)
iot_client = None
loop = None


async def provision_and_connect():
    provisioning_client = ProvisioningDeviceClient.create_from_symmetric_key(
        provisioning_host="global.azure-devices-provisioning.net",
        registration_id=DEVICE_ID,
        id_scope=ID_SCOPE,
        symmetric_key=PRIMARY_KEY,
    )
    result = await provisioning_client.register()
    if result.status != "assigned":
        raise RuntimeError(f"Aprovisionamiento fallido: {result.status}")

    hub_hostname = result.registration_state.assigned_hub
    client = IoTHubDeviceClient.create_from_symmetric_key(
        symmetric_key=PRIMARY_KEY,
        hostname=hub_hostname,
        device_id=DEVICE_ID,
    )
    await client.connect()
    print(f"[{DEVICE_ID}] Conectado a IoT Central (puente HTTP/REST activo).")
    return client


async def enviar_a_central(payload: dict):
    message = Message(json.dumps(payload))
    message.content_type = "application/json"
    message.content_encoding = "utf-8"
    await iot_client.send_message(message)
    print(f"[{DEVICE_ID}] Reenviado a IoT Central: {json.dumps(payload)}")


@app.route("/webhook/access-event", methods=["POST"])
def recibir_evento():
    """
    Simula un sistema externo de control de acceso notificando vía REST.
    Ejemplo de body esperado (JSON):
    {"action": "open", "actor": "badge_4521"}
    """
    data = request.get_json(force=True)
    action = data.get("action", "unknown")
    actor = data.get("actor", "manual")

    payload = {
        "doorState": "open" if action == "open" else "closed",
        "accessEvent": f"{action} by {actor}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Reenvía de forma segura al event loop de asyncio desde el hilo de Flask
    asyncio.run_coroutine_threadsafe(enviar_a_central(payload), loop)

    return jsonify({"status": "forwarded", "payload": payload}), 200


def iniciar_flask():
    app.run(host="0.0.0.0", port=5000)


async def main():
    global iot_client, loop
    loop = asyncio.get_event_loop()
    iot_client = await provision_and_connect()

    # Flask corre en un hilo separado porque su servidor es bloqueante (síncrono)
    flask_thread = threading.Thread(target=iniciar_flask, daemon=True)
    flask_thread.start()

    print(f"[{DEVICE_ID}] Puente activo. Escuchando POST en http://localhost:5000/webhook/access-event")
    print(f"[{DEVICE_ID}] Presiona Ctrl+C para detener.")

    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        print(f"[{DEVICE_ID}] Desconexión manual del puente.")
    finally:
        await iot_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())