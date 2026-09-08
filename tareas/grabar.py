"""Graba una tarea moviendo el brazo SO-101 con la MANO (aprendizaje
kinestesico). El brazo queda BLANDO (sin par); se guardan las posiciones de
las 6 juntas HZ veces por segundo.

    uv run python tareas/grabar.py                  # -> tareas/tarea.json
    uv run python tareas/grabar.py recoger.json     # -> tareas/recoger.json
    uv run python tareas/grabar.py -p /dev/ttyUSB0  # puerto explicito

Enter para empezar, Ctrl+C para parar y guardar. Se reproduce con reproducir.py.
"""

import glob
import json
import sys
import time
from pathlib import Path

import numpy as np
from scservo_sdk import PacketHandler, PortHandler

IDS = (1, 2, 3, 4, 5, 6)                 # del hombro a la pinza
TORQUE, PRESENT_POS = 40, 56
HZ = 30                                  # muestras por segundo

ARGS = sys.argv[1:]
PUERTO = ARGS[ARGS.index("-p") + 1] if "-p" in ARGS else next(iter(sorted(
    glob.glob("/dev/cu.usbserial*") + glob.glob("/dev/cu.usbmodem*")
    + glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*"))), "")
SALIDA = Path(__file__).parent / next(
    (a for a in ARGS if a.endswith(".json")), "tarea.json")

port = PortHandler(PUERTO)
if not PUERTO or not port.openPort() or not port.setBaudRate(1_000_000):
    sys.exit(f"No pude abrir el puerto ({PUERTO or 'no encontrado'}). Pasalo con -p.")
pk = PacketHandler(0)                    # STS / SMS: protocol_end = 0


def leer():
    return np.array([pk.read2ByteTxRx(port, i, PRESENT_POS)[0] for i in IDS], int)


for i in IDS:                            # par OFF: el brazo queda blando
    pk.write1ByteTxRx(port, i, TORQUE, 0)

input(f"Puerto {PUERTO}. Pon el brazo en la pose inicial y pulsa Enter para grabar... ")
print("Grabando. Haz la tarea con la mano. Ctrl+C para terminar.\n")

frames = []
prev = leer()
try:
    while True:
        t0 = time.time()
        p = leer()
        if (p == 0).any() or (np.abs(p - prev) > 300).any():   # lectura mala: la repito
            p = prev
        frames.append(p.tolist())
        prev = p
        print(f"\r{len(frames):5d} frames  ({len(frames) / HZ:5.1f} s)", end="", flush=True)
        time.sleep(max(0, 1 / HZ - (time.time() - t0)))
except KeyboardInterrupt:
    pass

SALIDA.write_text(json.dumps({"hz": HZ, "frames": frames}))
port.closePort()
print(f"\n\n{len(frames)} frames -> {SALIDA}  ({len(frames) / HZ:.1f} s)")
