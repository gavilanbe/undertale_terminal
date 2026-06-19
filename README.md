# 👾 UNDERSHELL
Un RPG de terminal inspirado en Undertale, ambientado dentro de un sistema operativo moribundo. Exploración, combate por puzzles-protocolo, esquiva estilo bullet-hell y finales ramificados. 100% Python, 100% terminal. 💻

## ✨ Características
- 🗺️ Exploración con puzzles: empuja bloques de datos, activa interruptores, rota nodos de router y resuelve cadenas de protocolos para abrir rutas.
- ⚔️ Combate como máquina de estados: cada ACT es un paso de reparación con marcadores `>`, `OK` y `^C`; nada de adivinar a ciegas.
- 🎯 Bullet-hell: mueve tu "alma" para esquivar patrones de balas que siguen reglas legibles (cada enemigo te avisa de su RULE/READ).
- 🤝 Ruta pacifista o genocida: cada monstruo es un proceso abandonado con su propio arco; perdonar es siempre viable.
- 🌳 Finales ramificados: Pacifista, Genocida y dos Neutrales según tu ruta, protocolos recuperados e identidad resuelta.
- 🆔 Sistema de identidad: el juego rastrea tu `PPID` y la historia reacciona a ello.
- 💾 Guardado que se consume al llegar a un final (cada final es su propia decisión).
- 🎵 Audio opcional con `pygame` (el juego corre en silencio sin él); los sonidos se generan a medida en el primer arranque.

## 🚀 Cómo jugar / ejecutar
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Sonido opcional:
pip install -r requirements-audio.txt

python3 main.py
# o, con el lanzador incluido:
./undertale
```
Requisitos: Python 3.11+, terminal con 256 colores y mínimo 80x24.

## 🎮 Controles
### Exploración
- WASD / Flechas: moverse (camina contra un bloque para empujarlo)
- Z / Enter / E: interactuar (carteles, NPCs, interruptores, puntos de guardado)
- I / Tab: menú de pausa (estado, inventario, ayuda)
- ESC: salir (autoguarda en el mundo exterior)

### Combate
- ← / → : navegar el menú principal
- ↑ / ↓ : navegar submenús (ACT, ITEM, BUF)
- Z / Enter: confirmar / avanzar texto
- X: cancelar / volver
- WASD / Flechas: mover el alma durante el bullet-hell
- ESC: salir

## 🛠️ Tecnología
- Python 3.11+ con `curses` (sólo librería estándar para el núcleo del juego)
- `pygame` opcional para audio
- Assets de audio (WAV) generados proceduralmente — incluidos en `assets/`

## 📦 Parte de mi colección de juegos
Uno más de mis juegos de terminal hechos por afición. 🎮
