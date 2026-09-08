# tareas/ — enseñar y repetir (aprendizaje kinestésico)

Mueves el brazo SO-101 con la mano para hacer una tarea, se graban las
posiciones de las 6 juntas, y luego el brazo la repite solo.

```
calibrar.py        graba HOME + topes min/max de cada junta -> calibracion.json
grabar.py          graba una tarea (brazo BLANDO, lo mueves tú)
reproducir.py      repite una tarea grabada (brazo con par)
calibracion.json   límites del brazo (lo usa reproducir.py y wasd_real.py)
*.json             las grabaciones se guardan aquí
```

## Requisito: calibrar una vez

`reproducir.py` necesita `calibracion.json` (en esta carpeta) para no pasarse
de los topes físicos de cada junta. Si no lo tienes:

```bash
uv run python tareas/calibrar.py
```

El brazo queda blando. Lo pones en la pose HOME → **Enter**. Mueves cada junta
de tope a tope. **Ctrl+C** para guardar. Solo se repite si cambias motores de
sitio o inviertes un signo.

## 1. Grabar una tarea

```bash
uv run python tareas/grabar.py recoger.json
```

- El brazo arranca **blando** (sin par).
- Ponlo en la pose inicial y pulsa **Enter**.
- Haz la tarea con la mano. Graba a 30 Hz (descarta lecturas con glitches).
- **Ctrl+C** para parar → escribe `tareas/recoger.json`.

Sin nombre → `tareas/tarea.json`. Puerto: se autodetecta; si hace falta, `-p /dev/ttyUSB0`.

## 2. Repetir la tarea

```bash
uv run python tareas/reproducir.py recoger.json          # 1 vez
uv run python tareas/reproducir.py recoger.json -n 5     # 5 veces
uv run python tareas/reproducir.py recoger.json --lento 2  # a mitad de velocidad
```

Qué hace:

1. Carga la grabación y **recorta cada frame a los `min`/`max`** de `tareas/calibracion.json`.
2. Activa el par en la pose actual (sin tirón), muestra duración y repeticiones,
   y pide **Enter**.
3. Cada vuelta: se acerca despacio (2 s) a la pose inicial desde donde esté el
   brazo, y luego ejecuta la trayectoria con reloj absoluto (no acumula deriva).
   `SLEW = 25` pasos por frame es la red de seguridad contra saltos.
4. Al terminar deja el par **activo** sujetando la pose. Corta la corriente para soltar.

**Ctrl+C** aborta en cualquier momento.

## Opciones

| Flag | Script | Efecto |
|---|---|---|
| `nombre.json` | ambos | archivo de la tarea (por defecto `tarea.json`) |
| `-p PUERTO` | ambos | puerto serie si la autodetección falla |
| `-n N` | reproducir | repetir la tarea N veces |
| `--lento F` | reproducir | factor de tiempo (2 = mitad de velocidad) |

## Formato del archivo

```json
{ "hz": 30, "frames": [[s1, s2, s3, s4, s5, s6], ...] }
```

`sN` = posición del servo N en pasos (0–4095), del hombro (ID 1) a la pinza (ID 6).

## Seguridad

- La primera vez, ten la mano en el conector de corriente.
- Si una junta se mueve rara al reproducir, es señal de calibración mala:
  revisa `SIGNOS` en `wasd_real.py` y vuelve a correr `tareas/calibrar.py`.
- Empieza con `--lento 3` y `-n 1` para verificar la tarea antes de dejarla en bucle.
