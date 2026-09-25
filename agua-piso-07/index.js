require('dotenv').config({ path: '../.env' });
const mqtt = require('mqtt');

const HOSTNAME = "iotc-3a01adfb-1862-4c2e-9211-ef6c980285ca.azure-devices.net"; // ej: iotc-xxxxx.azure-devices.net
const DEVICE_ID = process.env.AGUA_PISO_DEVICE_ID;
const SAS_TOKEN = "SharedAccessSignature sr=iotc-3a01adfb-1862-4c2e-9211-ef6c980285ca.azure-devices.net%2Fdevices%2Fagua-piso-07&sig=RKHWK1BvbNOPdk4KxxNGukr7XzOD%2FHBBiiZVB%2FKtg%2BA%3D&se=1790298104";

const SAMPLING_INTERVAL_MS = 60000; // 60s según catálogo

const brokerUrl = `mqtts://${HOSTNAME}:8883`;
const topic = `devices/${DEVICE_ID}/messages/events/`;

const options = {
  clientId: DEVICE_ID,
  username: `${HOSTNAME}/${DEVICE_ID}/?api-version=2021-04-12`,
  password: SAS_TOKEN,
  protocolVersion: 4, // MQTT 3.1.1
  rejectUnauthorized: true,
};

const client = mqtt.connect(brokerUrl, options);

let fugaSimulada = false; // estado del sensor, para simular un evento de fuga a mitad de sesión

client.on('connect', () => {
  console.log(`[${DEVICE_ID}] Conectado a IoT Central vía MQTT.js (Node.js)`);

  setInterval(() => {
    const humedadPiso = fugaSimulada
      ? +(85 + Math.random() * 10).toFixed(1)  // humedad alta si hay "fuga"
      : +(20 + Math.random() * 10).toFixed(1); // humedad normal

    const payload = {
      waterLeak: fugaSimulada,
      floorHumidity: humedadPiso,
      timestamp: new Date().toISOString(),
    };

    client.publish(topic, JSON.stringify(payload), { qos: 1 }, (err) => {
      if (err) {
        console.error(`[${DEVICE_ID}] Error al publicar:`, err.message);
      } else {
        console.log(`[${DEVICE_ID}] Enviado:`, JSON.stringify(payload));
      }
    });
  }, SAMPLING_INTERVAL_MS);
});

client.on('error', (err) => {
  console.error(`[${DEVICE_ID}] Error de conexión:`, err.message);
});

client.on('close', () => {
  console.log(`[${DEVICE_ID}] Conexión cerrada.`);
});

// Simula el disparo de una fuga después de 3 minutos (útil para probar la Rule "Water Leak Detected" en vivo)
setTimeout(() => {
  fugaSimulada = true;
  console.log(`[${DEVICE_ID}] *** Simulando fuga de agua detectada ***`);
}, 3 * 60 * 1000);