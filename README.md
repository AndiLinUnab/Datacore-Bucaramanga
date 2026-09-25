# DataCore Bucaramanga — IoT Central: Flota de Centro de Datos

Proyecto para el Parcial 1 de IoT + Cloud + Sistemas Distribuidos (UNAB, 2026-II).
Flota heterogénea de 10 dispositivos enviando telemetría a **Azure IoT Central**
desde 10 orígenes de envío distintos, con Rules, dashboard de control room y
un backend adicional de visualización en vivo.

**Integrantes:** Andi Lin – U00180153 · Miguel Ángel Solano Díaz – U00177983

Documento completo del proyecto (arquitectura, catálogo, datasheets, Rules,
comparativa de 4 días): ver `docs/Documento_Profesional_DataCore_Bucaramanga.docx`.

---

## 1. Estructura del repositorio

```
.
├── README.md                     # este archivo
├── .env.example                  # plantilla de variables de entorno (sin valores reales)
├── .gitignore
├── requirements.txt               # dependencias Python
├── scripts/
│   ├── rack_c_03.py                # Origen 3 — Python + azure-iot-device (DPS/MQTT)
│   ├── pasillo_frio_04.py          # Origen 4 — Python + paho-mqtt (SAS manual)
│   ├── clima_ext_05.py             # Origen 5 — Puente API pública (Open-Meteo clima)
│   ├── aire_sala_06.py             # Origen 6 — Puente API pública (Open-Meteo Air Quality) + CO2 simulado
│   ├── humo_08.py                  # Origen 8 — Replay de CSV histórico
│   ├── humo_historico.csv          # Datos históricos generados para el replay
│   ├── generar_csv_humo.py         # Genera humo_historico.csv
│   ├── generar_sas_token.py        # Utilidad: genera SAS token + hostname para Wokwi/Node
│   ├── puerta_10.py                # Origen 10 — Puente HTTP/REST (Flask)
│   └── agua-piso-07/
│       ├── index.js                # Origen 7 — Node.js + MQTT.js
│       ├── package.json
│       └── .env                    # (no versionado — ver sección 3)
├── wokwi/
│   ├── rack-b-02/                  # Origen 2 — ESP32 + DHT22
│   │   ├── sketch.ino
│   │   ├── diagram.json
│   │   └── libraries.txt
│   └── pdu-09/                     # Origen 9 — ESP32 + potenciómetro (simula ACS712)
│       ├── sketch.ino
│       ├── diagram.json
│       └── libraries.txt
├── datacore-backend/                # Dashboard de control room en vivo (Node.js)
│   ├── server.js
│   ├── devices.json
│   ├── package.json
│   └── .env                        # (no versionado — ver sección 3)
└── docs/
    ├── Documento_Profesional_DataCore_Bucaramanga.docx
    ├── Pruebas_con_capturas_día_1.docx
    ├── Pruebas_con_capturas_día_2.docx
    ├── Pruebas_con_capturas_día_3.docx
    ├── Pruebas_con_capturas_día_4.docx    # se agrega antes de la entrega final
    ├── diagrama_arquitectura_referencia.png
    └── diagrama_zonas_datacenter.png
```

> El dispositivo **rack-a-01** (Origen 1 — Digital Twin / simulador nativo) no
> tiene script propio: se ejecuta enteramente dentro de IoT Central como
> dispositivo simulado del Device Template "Rack Monitor".

---

## 2. Prerrequisitos

- Python 3.10+ y `pip`
- Node.js 18+ y `npm`
- Una aplicación de Azure IoT Central ya creada, con los 3 Device Templates
  (Rack Monitor, Environment Node, Power & Access Node) publicados y los 10
  dispositivos aprovisionados
- Cuenta gratuita en [wokwi.com](https://wokwi.com) para los orígenes 2 y 9

---

## 3. Variables de entorno (`.env`)

**Ningún token, key o SAS se sube al repositorio.** Cada carpeta que lo
necesita tiene su propio `.env`, ignorado por Git. Usa `.env.example` como
plantilla:

```dotenv
ID_SCOPE=<tu ID Scope de la app>

RACK_B_DEVICE_ID=rack-b-02
RACK_B_PRIMARY_KEY=<primary key>

RACK_C_DEVICE_ID=rack-c-03
RACK_C_PRIMARY_KEY=<primary key>

PASILLO_DEVICE_ID=pasillo-frio-04
PASILLO_PRIMARY_KEY=<primary key>

CLIMA_EXT_DEVICE_ID=clima-ext-05
CLIMA_EXT_PRIMARY_KEY=<primary key>

AIRE_SALA_DEVICE_ID=aire-sala-06
AIRE_SALA_PRIMARY_KEY=<primary key>

AGUA_PISO_DEVICE_ID=agua-piso-07
AGUA_PISO_PRIMARY_KEY=<primary key>

HUMO_DEVICE_ID=humo-08
HUMO_PRIMARY_KEY=<primary key>

PDU_DEVICE_ID=pdu-09
PDU_PRIMARY_KEY=<primary key>

PUERTA_DEVICE_ID=puerta-10
PUERTA_PRIMARY_KEY=<primary key>
```

El backend de `datacore-backend/` usa además:

```dotenv
CENTRAL_APP_URL=https://<tu-subdominio>.azureiotcentral.com
CENTRAL_API_TOKEN=<token de API, rol Operator>
```

⚠️ **El token de API da acceso de lectura a toda la aplicación de IoT
Central.** Si regeneras cualquier primary key o token, actualiza el `.env`
correspondiente — nunca los pegues en un commit, en el documento, ni en
capturas de pantalla que vayan a compartirse.

---

## 4. Instalación

```bash
# Entorno Python
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Dependencias Node (agua-piso-07)
cd scripts/agua-piso-07 && npm install && cd ../..

# Dependencias Node (dashboard en vivo)
cd datacore-backend && npm install && cd ..
```

---

## 5. Cómo ejecutar cada origen

| # | Origen | Comando |
|---|---|---|
| 1 | Digital Twin nativo | No requiere código — se administra desde el portal de IoT Central |
| 2 | Wokwi ESP32 (rack-b-02) | Abrir `wokwi/rack-b-02/` en wokwi.com, generar SAS token con `python scripts/generar_sas_token.py rack-b`, pegar en `sketch.ino`, dar Play |
| 3 | Python DPS/MQTT | `python scripts/rack_c_03.py` |
| 4 | Python paho-mqtt | `python scripts/pasillo_frio_04.py` |
| 5 | Puente API Open-Meteo (clima) | `python scripts/clima_ext_05.py` |
| 6 | Puente API Open-Meteo (aire) | `python scripts/aire_sala_06.py` |
| 7 | Node.js + MQTT.js | `cd scripts/agua-piso-07 && node index.js` |
| 8 | Replay CSV histórico | `python scripts/humo_08.py [YYYY-MM-DD]` (fecha opcional para fraccionar por día) |
| 9 | Wokwi ESP32 (pdu-09) | Igual que el origen 2, usando `wokwi/pdu-09/` y `python scripts/generar_sas_token.py pdu` |
| 10 | Puente HTTP/REST | `python scripts/puerta_10.py`, luego simular eventos con `Invoke-RestMethod` (PowerShell) o `curl.exe` |

Detalle de cada script, su justificación técnica y su datasheet asociado:
ver el documento profesional, sección "Catálogo de 10 Dispositivos".

---

## 6. Dashboard de Control Room en vivo (`datacore-backend/`)

Backend en Node.js que consulta la API REST de Azure IoT Central en tiempo
real y sirve un dashboard propio — complementario al dashboard nativo de la
aplicación IoT Central (Sección 7 del enunciado).

```bash
cd datacore-backend
npm start
```

Abre **http://localhost:5000**. Se refresca solo cada 15 segundos.

**Qué cubre:**
- Logo y nombre propio ("DataCore Bucaramanga"), no el nombre genérico de Azure.
- Estado de la flota: Connected / Disconnected / Unassociated, inferido
  comparando el timestamp del último dato contra 3× el intervalo de muestreo
  esperado de cada dispositivo (ajustable en `isConnected()` en `server.js`).
- 4 gráficos en vivo (Rack A, Pasillo Frío, Sala de Aire, Tablero PDU).
- KPIs de último valor, mínimo y máximo — acumulados desde que arranca el
  proceso (no desde una fecha fija; ver nota de limitación abajo).
- Bloque de alertas: evalúa en el propio backend las condiciones de las 8
  Rules contra la telemetría en vivo.
- Mapa de zonas dispositivo ↔ ubicación física.

**Antes de usarlo**, confirma en `datacore-backend/devices.json` que los
nombres de telemetría (`tempIntake`, `diffPressure`, `pm25`, `powerKw`, etc.)
coincidan exactamente con los "Capability name" definidos en tus tres Device
Templates — un nombre mal escrito hace que esa fila muestre "—".

**Limitación conocida:** los KPIs de mínimo/máximo se acumulan desde el
arranque del proceso, no desde una fecha específica. Para que reflejen
exactamente "el día seleccionado" habría que persistir el historial en disco
filtrado por fecha — no implementado por alcance de tiempo del parcial.

**Para la sustentación:** correr este backend en el mismo portátil donde se
ejecuta uno de los dos códigos en vivo (recomendado: `rack_c_03.py`), para
que el ingeniero vea el dispositivo pasar a Connected con datos frescos en
tiempo real sobre este dashboard.

---

## 7. Seguridad

- Ningún archivo `.env` está versionado (ver `.gitignore`).
- Las primary keys y el token de API del dashboard en vivo se manejan solo
  como variables de entorno, nunca hardcodeadas.
- Si una key o token quedó expuesto accidentalmente (por ejemplo, compartido
  en una captura o chat), regenerarlo desde el portal de IoT Central antes de
  la entrega final.
- El SAS token usado por los proyectos Wokwi expira (6 h por defecto en
  `generar_sas_token.py`); regenerarlo antes de cada sesión de captura o
  demostración en vivo.

---

## 8. Solución de problemas frecuentes

| Síntoma | Causa probable |
|---|---|
| `KeyError` al leer `os.environ[...]` | El `.env` no está en la misma carpeta desde donde se ejecuta el script, o se escribió el valor en vez del nombre de la variable |
| `Gateway timeout` al ejecutar un Command desde el portal | El handler de comandos no corre en el mismo event loop del cliente (ver patrón `receive_method_request` en `rack_c_03.py`) |
| Wokwi: `rc=-1` al conectar por MQTT | Buffer de `PubSubClient` insuficiente — usar `client.setBufferSize(512)` |
| Wokwi: `fatal error: *.h: No such file` | Falta declarar la librería en `libraries.txt` |
| No llega el correo de una Rule | Verificar que el correo esté autorizado en **Permissions/Notifications** de la aplicación (no solo configurado en la Rule) |
| Rule nunca se dispara | Revisar el operador lógico (AND vs. OR) y que el umbral sea alcanzable por el rango real del sensor simulado |
| `datacore-backend` muestra todo "Disconnected" | Revisar que los nombres de telemetría en `devices.json` coincidan exactamente con las capabilities del Device Template |

---

## 9. Referencias

- Documentación oficial de Azure IoT Central: https://learn.microsoft.com/es-es/azure/iot-central/
- Wokwi ESP32 Wi-Fi: https://docs.wokwi.com/guides/esp32-wifi
- Open-Meteo (clima y calidad de aire): https://open-meteo.com/
