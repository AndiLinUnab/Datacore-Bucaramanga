require("dotenv").config();
const express = require("express");
const fetch = require("node-fetch");
const fs = require("fs");
const path = require("path");

const app = express();
const PORT = process.env.PORT || 5000;
const APP_URL = process.env.CENTRAL_APP_URL;
const TOKEN = process.env.CENTRAL_API_TOKEN;
const API_VERSION = "2022-07-31";
const POLL_MS = 15000;
const HISTORY_MAX_POINTS = 200;

const devices = JSON.parse(fs.readFileSync(path.join(__dirname, "devices.json"), "utf8"));

if (!APP_URL || !TOKEN) {
  console.error("Falta CENTRAL_APP_URL o CENTRAL_API_TOKEN en el archivo .env");
  process.exit(1);
}

// ---- Reglas (Rules) tomadas del documento de proyecto ----
const RULES = [
  { name: "Rack Overheat", deviceIds: ["rack-a-01", "rack-b-02", "rack-c-03"],
    check: (r) => num(r.tempIntake) > 27 && num(r.tempExhaust) > 35 },
  { name: "Rack Low Humidity", deviceIds: ["rack-a-01", "rack-b-02", "rack-c-03"],
    check: (r) => num(r.humidity) < 20 || num(r.humidity) > 60 },
  { name: "Cold Aisle Pressure Fault", deviceIds: ["pasillo-frio-04"],
    check: (r) => num(r.diffPressure) < 5 },
  { name: "Air Quality Alert", deviceIds: ["aire-sala-06"],
    check: (r) => num(r.pm25) > 35 || num(r.aqi) > 100 },
  { name: "CO2 High", deviceIds: ["aire-sala-06"],
    check: (r) => num(r.co2) > 1000 },
  { name: "Smoke Detected", deviceIds: ["humo-08"],
    check: (r) => num(r.smokeLevel) > 1000 },
  { name: "Water Leak Detected", deviceIds: ["agua-piso-07"],
    check: (r) => r.waterLeak === true || r.waterLeak === "true" },
  { name: "Power Overload", deviceIds: ["pdu-09"],
    check: (r) => num(r.powerKw) > 5 },
];

function num(v) { const n = Number(v); return Number.isFinite(n) ? n : NaN; }

// ---- Estado en memoria (se reinicia al reiniciar el servidor) ----
const state = {
  fetchedAt: null,
  devices: {},      // id -> { displayName, zona, origen, template, connected, unassociated, lastSeen, readings:{name:value} }
  history: {},       // "deviceId.telemetryName" -> [{t, v}]
  stats: {},          // "deviceId.telemetryName" -> {min, max, last, lastTs}
  activeAlerts: {},   // ruleName+deviceId -> {rule, deviceId, since}
  alertLog: [],        // últimas alertas disparadas (edge-trigger), más reciente primero
};

async function getTelemetryValue(deviceId, telemetryName) {
  const url = `${APP_URL}/api/devices/${encodeURIComponent(deviceId)}/telemetry/${encodeURIComponent(telemetryName)}?api-version=${API_VERSION}`;
  try {
    const res = await fetch(url, { headers: { Authorization: TOKEN } });
    if (!res.ok) return { name: telemetryName, value: null, timestamp: null };
    const data = await res.json();
    return { name: telemetryName, value: data.value, timestamp: data.timestamp };
  } catch (err) {
    return { name: telemetryName, value: null, timestamp: null };
  }
}

async function getDeviceInfo(deviceId) {
  const url = `${APP_URL}/api/devices/${encodeURIComponent(deviceId)}?api-version=${API_VERSION}`;
  try {
    const res = await fetch(url, { headers: { Authorization: TOKEN } });
    if (!res.ok) return { template: null };
    const data = await res.json();
    return { template: data.template || null };
  } catch (err) {
    return { template: null };
  }
}

function isConnected(latestTimestamp, samplingIntervalSec) {
  if (!latestTimestamp) return false;
  const ageSec = (Date.now() - new Date(latestTimestamp).getTime()) / 1000;
  const threshold = samplingIntervalSec > 0 ? samplingIntervalSec * 3 : 600;
  return ageSec <= threshold;
}

function pushHistory(key, ts, value) {
  if (typeof value !== "number") return;
  if (!state.history[key]) state.history[key] = [];
  const arr = state.history[key];
  arr.push({ t: ts, v: value });
  if (arr.length > HISTORY_MAX_POINTS) arr.shift();

  const s = state.stats[key] || { min: value, max: value, last: value, lastTs: ts };
  s.min = Math.min(s.min, value);
  s.max = Math.max(s.max, value);
  s.last = value;
  s.lastTs = ts;
  state.stats[key] = s;
}

function evaluateRules(devicesOut) {
  const readingsByDevice = {};
  devicesOut.forEach((d) => {
    const r = {};
    d.readings.forEach((rd) => { r[rd.name] = rd.value; });
    readingsByDevice[d.id] = r;
  });

  RULES.forEach((rule) => {
    rule.deviceIds.forEach((devId) => {
      const readings = readingsByDevice[devId];
      if (!readings) return;
      const key = rule.name + "::" + devId;
      const isActive = !!rule.check(readings);
      const wasActive = !!state.activeAlerts[key];

      if (isActive && !wasActive) {
        const entry = { rule: rule.name, deviceId: devId, since: new Date().toISOString() };
        state.activeAlerts[key] = entry;
        state.alertLog.unshift(entry);
        if (state.alertLog.length > 30) state.alertLog.pop();
      } else if (!isActive && wasActive) {
        delete state.activeAlerts[key];
      }
    });
  });
}

async function pollOnce() {
  const devicesOut = await Promise.all(
    devices.map(async (dev) => {
      const [readings, info] = await Promise.all([
        Promise.all(dev.telemetry.map((t) => getTelemetryValue(dev.id, t))),
        getDeviceInfo(dev.id),
      ]);

      readings.forEach((r) => {
        if (r.timestamp) pushHistory(`${dev.id}.${r.name}`, r.timestamp, typeof r.value === "number" ? r.value : NaN);
      });

      const latestTs = readings.map((r) => r.timestamp).filter(Boolean).sort().pop() || null;
      const unassociated = !info.template;
      const connected = !unassociated && isConnected(latestTs, dev.samplingIntervalSec);

      return {
        id: dev.id,
        displayName: dev.displayName,
        zona: dev.zona,
        origen: dev.origen,
        samplingIntervalSec: dev.samplingIntervalSec,
        unassociated,
        connected,
        lastSeen: latestTs,
        readings,
      };
    })
  );

  evaluateRules(devicesOut);

  const connectedCount = devicesOut.filter((d) => d.connected).length;
  const unassociatedCount = devicesOut.filter((d) => d.unassociated).length;
  const disconnectedCount = devicesOut.length - connectedCount - unassociatedCount;

  state.fetchedAt = new Date().toISOString();
  state.devices = devicesOut;
  state.connectedCount = connectedCount;
  state.disconnectedCount = disconnectedCount;
  state.unassociatedCount = unassociatedCount;
  state.total = devicesOut.length;
}

app.get("/api/status", (req, res) => {
  if (!state.fetchedAt) return res.status(202).json({ pending: true });

  const seriesKeys = [
    "rack-a-01.tempIntake", "rack-a-01.tempExhaust",
    "rack-b-02.tempIntake", "rack-b-02.tempExhaust",
    "rack-c-03.tempIntake", "rack-c-03.tempExhaust",
    "pasillo-frio-04.diffPressure",
    "aire-sala-06.pm25", "aire-sala-06.aqi",
    "pdu-09.powerKw",
  ];
  const series = {};
  seriesKeys.forEach((k) => { series[k] = state.history[k] || []; });

  const stats = {};
  Object.keys(state.stats).forEach((k) => { stats[k] = state.stats[k]; });

  res.json({
    fetchedAt: state.fetchedAt,
    connectedCount: state.connectedCount,
    disconnectedCount: state.disconnectedCount,
    unassociatedCount: state.unassociatedCount,
    total: state.total,
    devices: state.devices,
    series,
    stats,
    activeAlerts: Object.values(state.activeAlerts),
    alertLog: state.alertLog.slice(0, 12),
  });
});

app.use(express.static(path.join(__dirname, "public")));

app.listen(PORT, async () => {
  console.log(`DataCore Control Room backend corriendo en http://localhost:${PORT}`);
  console.log(`Consultando IoT Central en: ${APP_URL}`);
  await pollOnce();
  setInterval(pollOnce, POLL_MS);
});
