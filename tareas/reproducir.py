"""Reproduce en el brazo SO-101 real una tarea grabada con grabar.py.

    uv run python tareas/reproducir.py                 # tareas/tarea.json, 1 vez
    uv run python tareas/reproducir.py recoger.json    # otra tarea
    uv run python tareas/reproducir.py -n 3            # repetir 3 veces
    uv run python tareas/reproducir.py --lento 2       # a mitad de velocidad
    uv run python tareas/reproducir.py -p /dev/ttyUSB0

Necesita tareas/calibracion.json (de calibrar.py) para no pasarse de los topes.
El brazo se acerca DESPACIO a la pose inicial, pide confirmacion, y ejecuta.
"""

import glob
import json
import sys
import time
from pathlib import Path

import numpy as np
from scservo_sdk import (
    GroupSyncWrite, PacketHandler, PortHandler, SCS_HIBYTE, SCS_LOBYTE,
)

IDS = (1, 2, 3, 4, 5, 6)
MODE, TORQUE, ACC, GOAL_VEL, GOAL_POS, PRESENT_POS = 33, 40, 41, 46, 42, 56
SLEW = 25                               # tope de pasos por frame (red de seguridad)

ARGS = sys.argv[1:]
PUERTO = ARGS[ARGS.index("-p") + 1] if "-p" in ARGS else next(iter(sorted(
    glob.glob("/dev/cu.usbserial*") + glob.glob("/dev/cu.usbmodem*")
    + glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*"))), "")
VECES = int(ARGS[ARGS.index("-n") + 1]) if "-n" in ARGS else 1
LENTO = float(ARGS[ARGS.index("--lento") + 1]) if "--lento" in ARGS else 1.0

DIR = Path(__file__).parent
ENTRADA = DIR / next((a for a in ARGS
                      if a.endswith(".json") and "calib" not in a), "tarea.json")
CAL = DIR / "calibracion.json"
if not CAL.exists():
    sys.exit("Falta calibracion.json. Corre primero:  uv run python tareas/calibrar.py")
cal = json.loads(CAL.read_text())
smin, smax = np.array(cal["min"]), np.array(cal["max"])
tarea = json.loads(ENTRADA.read_text())
HZ, frames = tarea["hz"], np.clip(np.array(tarea["frames"]), smin, smax)

port = PortHandler(PUERTO)
if not PUERTO or not port.openPort() or not port.setBaudRate(1_000_000):
    sys.exit(f"No pude abrir el puerto ({PUERTO or 'no encontrado'}). Pasalo con -p.")
pk = PacketHandler(0)
sync = GroupSyncWrite(port, pk, GOAL_POS, 2)


def leer():
    return np.array([pk.read2ByteTxRx(port, i, PRESENT_POS)[0] for i in IDS], float)


def escribir(pasos):
    sync.clearParam()
    for i, v in zip(IDS, np.clip(pasos, smin, smax).astype(int)):
        sync.addParam(i, [SCS_LOBYTE(int(v)), SCS_HIBYTE(int(v))])
    sync.txPacket()


actual = leer()
for i in IDS:
    pk.write1ByteTxRx(port, i, MODE, 0)          # modo posicion
    pk.write1ByteTxRx(port, i, ACC, 20)          # aceleracion suave
    pk.write2ByteTxRx(port, i, GOAL_VEL, 300)
escribir(actual)                                 # objetivo = pose actual, sin tiron
for i in IDS:
    pk.write1ByteTxRx(port, i, TORQUE, 1)

print(f"{ENTRADA.name}: {len(frames)} frames a {HZ} Hz "
      f"({len(frames) / HZ:.1f} s) x{VECES}   lento={LENTO}")
input("Enter para ejecutar, Ctrl+C para abortar. ")

try:
    for vuelta in range(VECES):
        # acercarse a la pose inicial desde donde este el brazo (2 s)
        desde = leer()
        for a in np.linspace(0, 1, int(2 * HZ)):
            escribir((1 - a) * desde + a * frames[0])
            time.sleep(1 / HZ)
        # ejecutar la trayectoria, con reloj absoluto (no acumula deriva)
        goal = frames[0].astype(float)
        t0 = time.time()
        for k, obj in enumerate(frames):
            goal += np.clip(obj - goal, -SLEW, SLEW)
            escribir(goal)
            time.sleep(max(0, t0 + (k + 1) / HZ * LENTO - time.time()))
        print(f"  vuelta {vuelta + 1}/{VECES} lista")
except KeyboardInterrupt:
    print("\nabortado")

print("El par sigue activo sujetando la pose. Corta la corriente para soltar.")
