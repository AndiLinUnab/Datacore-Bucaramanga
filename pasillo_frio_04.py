import os
import json
import time
import random
from datetime import datetime, timezone
from dotenv import load_dotenv
import paho.mqtt.client as mqtt
import ssl

# Reutilizamos la función de generar_sas_token.py
from generar_sas_token import generar_sas_token
import asyncio
from azure.iot.device.aio import ProvisioningDeviceClient

load_dotenv()

ID_SCOPE = os.environ["ID_SCOPE"]
DEVICE_ID = os.environ["PASILLO_DEVICE_ID"]
PRIMARY_KEY = os.environ["PASILLO_PRIMARY_KEY"]
SAMPLING_INTERVAL_SEC = 60  # según catálogo


async def obtener_hostname():
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


def generar_telemetria():
    return {
        "tempAisle": round(random.uniform(18.0, 24.0), 1),
        "diffPressure": round(random.uniform(3.0, 15.0), 1),
        "humidityAisle": round(random.uniform(30.0, 55.0), 1),
    }


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[{DEVICE_ID}] Conectado a IoT Central vía paho-mqtt.")
    else:
        print(f"[{DEVICE_ID}] Fallo de conexión, código: {rc}")


def on_disconnect(client, userdata, rc):
    print(f"[{DEVICE_ID}] Desconectado (rc={rc}).")


def main():
    hostname = asyncio.run(obtener_hostname())
    print(f"[{DEVICE_ID}] Hub asignado: {hostname}")

    expiry = int(time.time()) + 3600 * 6
    sas_token = generar_sas_token(hostname, DEVICE_ID, PRIMARY_KEY, expiry)
    username = f"{hostname}/{DEVICE_ID}/?api-version=2021-04-12"
    topic = f"devices/{DEVICE_ID}/messages/events/"

    client = mqtt.Client(client_id=DEVICE_ID, protocol=mqtt.MQTTv311)
    client.username_pw_set(username=username, password=sas_token)
    client.tls_set(cert_reqs=ssl.CERT_NONE)
    client.tls_insecure_set(True)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    client.connect(hostname, 8883, keepalive=60)
    client.loop_start()

    try:
        while True:
            data = generar_telemetria()
            data["timestamp"] = datetime.now(timezone.utc).isoformat()
            payload = json.dumps(data)
            client.publish(topic, payload, qos=1)
            print(f"[{DEVICE_ID}] Enviado: {payload}")
            time.sleep(SAMPLING_INTERVAL_SEC)
    except KeyboardInterrupt:
        print(f"[{DEVICE_ID}] Desconexión manual — evidencia de desconexión documentada.")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()