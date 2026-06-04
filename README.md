# IRIS - Intelligent Robotic Interactive System 🤖

IRIS is a biped AI-powered robot capable of voice interaction, real-time vision processing, autonomous tracking, and ESP32-based movement control. It combines computer vision, speech recognition, and large language models to create a natural human-robot interaction system.

---

## 🚀 Features

- 🎙️ Voice command understanding (speech-to-text via AI)
- 🗣️ Natural speech responses (text-to-speech)
- 👁️ Real-time camera vision processing
- 😊 Facial mood detection and response
- 🎯 Autonomous face tracking system
- 🚶 Discrete biped movement control via ESP32
- 📸 Image capture on command
- 🤖 AI decision-making using LLM (Groq API)
- 📡 Wireless communication with robot hardware
- 🖥️ Live HUD interface with system status

---

## 🧠 How It Works

IRIS uses a combination of:
- A Python-based AI brain running on a PC
- ESP32 microcontroller for robot movement
- Live camera stream from a mobile device or webcam
- AI models for speech, vision, and reasoning

The system interprets voice commands, processes visual input, and executes movement or responses in real time.

---

## 🛠️ Tech Stack

- Python
- OpenCV
- MediaPipe
- SoundDevice
- SciPy
- pyttsx3
- Groq API (LLM + Vision + Whisper)
- ESP32 (Arduino firmware)
- UDP socket communication

---

## 🎮 Controls

| Key | Function |
|-----|----------|
| Space | Voice command mode |
| M | Mood analysis |
| T | Toggle face tracking |
| W | Move forward |
| S | Move backward |
| A | Move left |
| D | Move right |
| Q | Shutdown system |

---

## 📁 Project Structure

```text
IRIS/
├── python/
│   └── iris_controller.py
├── esp32/
│   └── iris_esp32.ino
├── README.md
├── LICENSE
├── .gitignore
└── requirements.txt
