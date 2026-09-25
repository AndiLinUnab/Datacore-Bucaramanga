# DataCore Bucaramanga — Control Room en vivo

Backend en Node.js que consulta la API REST de Azure IoT Central y sirve el
dashboard de la flota con datos reales.

## ⚠️ Antes de nada — seguridad

El archivo `.env` ya trae tu URL de aplicación y tu token de API (rol Operator).
**No subas esta carpeta a un repositorio público** ni la compartas tal cual —
el token da acceso de lectura a tu aplicación completa. Si el proyecto va a un
repo de GitHub (como pide el parcial), agrega `.env` a tu `.gitignore` y sube
solo un `.env.example` sin los valores reales.

## 1. Instalar dependencias

```bash
cd datacore-backend
npm install
```

## 2. Verificar los nombres de telemetría

En `devices.json` puse los nombres de telemetría según las variables de tu
documento (`tempIntake`, `tempExhaust`, `humidity`, `diffPressure`, `pm25`,
`co2`, `powerKw`, `doorState`, etc.), pero **debes confirmar que coincidan
exactamente** con los nombres de capacidad (camelCase) definidos en tus tres
Device Templates (Rack Monitor, Environment Node, Power & Access Node) dentro
de IoT Central. Si un nombre no coincide, esa fila mostrará "—" en vez de un
valor.

Para ver los nombres exactos: abre cada Device Template en IoT Central →
pestaña del modelo (Interface) → cada telemetría muestra su "Capability name".
Ajusta el arreglo `"telemetry"` en `devices.json` si hace falta.

## 3. Ejecutar el servidor

```bash
npm start
```

Verás:

```
DataCore Control Room backend corriendo en http://localhost:5000
Consultando IoT Central en: https://datacore-bucaramanga1.azureiotcentral.com
```

## 4. Abrir el dashboard

Abre **http://localhost:5000** en el navegador. Se actualiza solo cada 15
segundos consultando tu aplicación real de IoT Central.

## Qué cubre este dashboard (punto 7 del enunciado)

- **Logo y nombre propio**: "DataCore Bucaramanga" en el header, no el nombre de la app de Azure.
- **Estado de la flota**: Connected / Disconnected / **Unassociated** (se infiere `Unassociated` cuando el dispositivo aún no tiene `template` asignado en IoT Central).
- **4 gráficos en vivo**: Rack A (Temp Intake/Exhaust), Pasillo Frío (Diff Pressure), Sala de Aire (PM2.5/AQI) y Tablero PDU (Power kW) — se van dibujando con cada sondeo de 15s.
- **KPIs**: último valor, mínimo y máximo por variable, acumulados **desde que arrancó el proceso** (`npm start`). Si necesitas que cubran exactamente "el día seleccionado", tendrías que guardar el historial en disco con fecha y filtrar por día — dime si lo necesitas y te lo agrego.
- **Bloque de alertas**: evalúa en el propio backend las condiciones reales de tus 8 Rules (Rack Overheat, Cold Aisle Pressure Fault, Power Overload, etc.) contra la telemetría en vivo, y muestra cuáles están activas ahora mismo más un historial de las últimas disparadas.
- **Mapa de zonas**: el grid de colores dispositivo ↔ zona física.

## Cómo se determina "Connected" / "Disconnected"

La API pública de IoT Central no expone un campo de estado de conexión, así
que el backend lo infiere: compara la marca de tiempo del último dato de
telemetría recibido contra el intervalo de muestreo esperado de cada
dispositivo (columna `samplingIntervalSec` en `devices.json`). Si no ha
llegado un dato nuevo en más de 3x ese intervalo, se marca como
Disconnected. Puedes ajustar ese margen en la función `isConnected` de
`server.js` si lo ves muy estricto o muy laxo el día de la demo.

## Para la sustentación

Ejecuta este backend en el mismo portátil donde vas a correr uno de tus dos
códigos en vivo (por ejemplo el de Python, `rack_c_03.py`). Así, mientras el
ingeniero ve tus dos códigos enviando datos, el dashboard de esta carpeta
muestra en tiempo real cómo esos dispositivos pasan a "Connected" con
telemetría fresca.

## Si algo falla

- **401 / 403 en consola**: el token expiró o no tiene permisos — genera uno
  nuevo con rol Operator.
- **"No se pudo consultar IoT Central"**: revisa que `CENTRAL_APP_URL` en
  `.env` no tenga `/` al final y que el subdominio sea correcto.
- **Todo aparece Disconnected**: revisa primero los nombres de telemetría
  (paso 2) — un nombre mal escrito hace que nunca llegue timestamp.
