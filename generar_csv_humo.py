# generar_csv_humo.py
import csv
import random
from datetime import datetime, timedelta

# Los 4 días no continuos de tu proyecto (ajusta a tus fechas reales elegidas)
DIAS = [
    datetime(2026, 9, 20),
    datetime(2026, 9, 22),
    datetime(2026, 9, 24),
    datetime(2026, 9, 25),
]

INTERVALO_MINUTOS = 5  # una lectura cada 5 min dentro de cada día simulado
HORAS_ACTIVAS = (6, 22)  # el sensor "histórico" solo registró de 6am a 10pm

rows = []

for dia in DIAS:
    hora_actual = dia.replace(hour=HORAS_ACTIVAS[0], minute=0, second=0)
    hora_fin = dia.replace(hour=HORAS_ACTIVAS[1], minute=0, second=0)

    # Elige un momento aleatorio de ESE día para simular un pico de humo (evento de incendio simulado)
    minuto_evento = random.randint(0, int((hora_fin - hora_actual).total_seconds() / 60))
    momento_evento = hora_actual + timedelta(minutes=minuto_evento)

    while hora_actual <= hora_fin:
        # Si estamos cerca del momento del evento (ventana de 30 min), sube el humo
        if abs((hora_actual - momento_evento).total_seconds()) < 1800:
            smoke_level = round(random.uniform(1200, 2500), 1)
            temp_ceiling = round(random.uniform(45, 60), 1)
        else:
            smoke_level = round(random.uniform(300, 500), 1)
            temp_ceiling = round(random.uniform(20, 26), 1)

        rows.append({
            "timestamp": hora_actual.isoformat(),
            "smokeLevel": smoke_level,
            "tempCeiling": temp_ceiling,
        })
        hora_actual += timedelta(minutes=INTERVALO_MINUTOS)

with open("humo_historico.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["timestamp", "smokeLevel", "tempCeiling"])
    writer.writeheader()
    writer.writerows(rows)

print(f"CSV generado con {len(rows)} filas en humo_historico.csv")
print(f"Días incluidos: {[d.strftime('%Y-%m-%d') for d in DIAS]}")