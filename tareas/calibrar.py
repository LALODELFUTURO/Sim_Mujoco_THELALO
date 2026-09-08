import glob
import json
import sys
import time
from pathlib import Path

import numpy as np
from scservo_sdk import PacketHandler, PortHandler

IDS = (1, 2, 3, 4, 5, 6)                 # del hombro a la pinza
TORQUE, PRESENT_POS = 40, 56
NOMBRES = ("hombro_giro", "hombro_sube", "codo",
           "muneca_sube", "muneca_gira", "pinza")
ARCHIVO = Path(__file__).parent / "calibracion.json"

PUERTO = sys.argv[1] if len(sys.argv) > 1 else next(iter(sorted(
    glob.glob("/dev/cu.usbserial*") + glob.glob("/dev/cu.usbmodem*")
    + glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*"))), "")
port = PortHandler(PUERTO)
if not PUERTO or not port.openPort() or not port.setBaudRate(1_000_000):
    sys.exit(f"No pude abrir el puerto ({PUERTO or 'no encontrado'}). Pasalo como argumento.")
pk = PacketHandler(0)                    # STS / SMS: protocol_end = 0


def leer():
    return np.array([pk.read2ByteTxRx(port, i, PRESENT_POS)[0] for i in IDS], int)


for i in IDS:                            # par OFF: el brazo queda blando
    pk.write1ByteTxRx(port, i, TORQUE, 0)

input(f"Puerto {PUERTO}. Pon el brazo en la pose HOME y pulsa Enter... ")
home = leer()
lo = home.copy()
hi = home.copy()
print("HOME:", list(home))
print("\nMueve cada junta de tope a tope. Ctrl+C para guardar.\n")

try:
    while True:
        p = leer()
        if (p == 0).any():              # lectura fallida, la ignoro
            continue
        lo = np.minimum(lo, p)
        hi = np.maximum(hi, p)
        print("\r" + "  ".join(f"{n[:4]}:{a}-{b}" for n, a, b in zip(NOMBRES, lo, hi)),
              end="", flush=True)
        time.sleep(0.02)
except KeyboardInterrupt:
    pass

ARCHIVO.write_text(json.dumps(
    {"home": home.tolist(), "min": lo.tolist(), "max": hi.tolist()}, indent=2
))
port.closePort()
print(f"\n\nGuardado en {ARCHIVO.name}:")
for n, h, a, b in zip(NOMBRES, home, lo, hi):
    print(f"  {n:12s} home={h:4d}  min={a:4d}  max={b:4d}  ({b - a} pasos)")
