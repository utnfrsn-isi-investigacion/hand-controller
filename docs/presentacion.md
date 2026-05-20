# Hand Controller — Cómo funciona

Una explicación en lenguaje sencillo para lectores no técnicos.

## La idea en una frase

**Hacés un gesto con la mano frente a una cámara web, y un pequeño dispositivo del otro lado hace lo que le indicás** — avanzar, detenerse, girar a la izquierda, girar a la derecha.

## Diagrama

```
   ┌─────────────────────────────────────────────────────────────────────┐
   │                  HAND CONTROLLER — Cómo funciona                    │
   │     "Movés la mano, y un dispositivo del otro lado hace lo que      │
   │                            le indicás."                             │
   └─────────────────────────────────────────────────────────────────────┘


      👤 VOS                  📷 CÁMARA                 💻 COMPUTADORA
   ┌─────────┐             ┌──────────┐              ┌──────────────┐
   │  Tu     │   gesto     │  Ve tu   │   imágenes   │  Mira el     │
   │  mano   │ ──────────▶ │  mano    │ ───────────▶ │  video, mu-  │
   │ se mueve│             │          │              │  chas veces  │
   │         │             │          │              │  por segundo │
   └─────────┘             └──────────┘              └──────┬───────┘
                                                            │
                                                            ▼
                                            ┌───────────────────────────┐
                                            │  🧠  Visión con IA        │
                                            │                           │
                                            │  • Encuentra los 21       │
                                            │    puntos de tu mano      │
                                            │  • Lee la pose:           │
                                            │       ✊ puño   →  PARAR  │
                                            │       👈 izq    →  IZQ    │
                                            │       👉 der    →  DER    │
                                            │       ☝  arriba →  AVANZAR│
                                            └─────────────┬─────────────┘
                                                          │
                                                          ▼
                                            ┌───────────────────────────┐
                                            │  🛡️  Filtro suavizador    │
                                            │                           │
                                            │  Mira los últimos ~30     │
                                            │  cuadros y elige el gesto │
                                            │  más común, así un peque- │
                                            │  ño temblor no dispara un │
                                            │  comando equivocado.      │
                                            └─────────────┬─────────────┘
                                                          │
                                                          │  un comando
                                                          │  claro
                                                          ▼
                                            ┌───────────────────────────┐
                                            │  📡  Mensaje por Wi-Fi    │
                                            │                           │
                                            │  Envía un texto corto     │
                                            │  ("GO", "STOP", "LEFT"…)  │
                                            │  por tu red.              │
                                            └─────────────┬─────────────┘
                                                          │
              ╔═══════════════════════════════════════════╪═══════════════════════╗
              ║                                           ▼                       ║
              ║                              ┌────────────────────────┐           ║
              ║   📶 Router Wi-Fi  ◀──────▶  │   🔌 Chip ESP32        │           ║
              ║                              │   (pequeña computa-    │           ║
              ║                              │    dora de ~U$D 5 del  │           ║
              ║                              │    lado del dispositivo)│          ║
              ║                              └───────────┬────────────┘           ║
              ║                                          │                        ║
              ║                                          ▼                        ║
              ║                              ┌────────────────────────┐           ║
              ║                              │   🚗  Lo que se        │           ║
              ║                              │       controla         │           ║
              ║                              │      (un autito)       │           ║
              ║                              └────────────────────────┘           ║
              ╚══════════════════════════════════════════════════════════════════╝
                       "Lado del dispositivo" — en cualquier punto del Wi-Fi

                       ⟳  Todo el ciclo se repite ~30 veces por segundo  ⟳
```

## Paso a paso

1. **Hacés un gesto** frente a la cámara web (puño cerrado, dedo apuntando, mano abierta…).
2. **La computadora mira el video** muchas veces por segundo.
3. **Un modelo de visión con IA** encuentra tu mano y lee la pose.
4. **Un filtro suavizador** se asegura de que un pequeño temblor o un cuadro raro no dispare un comando incorrecto.
5. **El comando se envía por Wi-Fi** como un mensaje de texto corto (por ejemplo "GO" o "STOP").
6. **Un chip diminuto llamado ESP32** — una pequeña computadora inalámbrica conectada al dispositivo — recibe el mensaje.
7. **El dispositivo reacciona**: el auto se mueve.

## Por qué cada pieza importa

| Pieza | Para qué está |
|---|---|
| **Cámara web** | Los ojos del sistema — no hace falta hardware especial, sirve una cámara común. |
| **Visión con IA (MediaPipe)** | Convierte una imagen plana en 21 puntos entendidos de tu mano — nudillos, yemas, palma. |
| **Filtro suavizador** | Las manos tiemblan. Sin suavizado, un solo cuadro tembloroso podría disparar un comando equivocado. |
| **Wi-Fi** | Permite que el dispositivo esté en cualquier parte de la habitación — sin cables entre la laptop y el dispositivo. |
| **ESP32** | Un chip de unos 5 dólares, del tamaño de un pulgar, que se conecta al Wi-Fi y controla el dispositivo. Es el "oído" del lado del dispositivo. |

## Para qué sirve

- Controlar un robot pequeño o un auto a radiocontrol sin control remoto
- Demos y presentaciones sin tocar el teclado
- Experimentos de accesibilidad (controlar cosas sin tocarlas)
- Punto de partida para cualquier proyecto del estilo "gesto → acción"
