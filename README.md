# ⚡ Screen Slicer

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/OpenCV-4.8%2B-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white" alt="OpenCV">
  <img src="https://img.shields.io/badge/MediaPipe-Tasks%20Vision-00C7B7?style=for-the-badge&logo=google&logoColor=white" alt="MediaPipe">
  <img src="https://img.shields.io/badge/NumPy-Fast%20Math-013243?style=for-the-badge&logo=numpy&logoColor=white" alt="NumPy">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="MIT License">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey?style=for-the-badge" alt="Platform">
</p>

<p align="center">
  <strong>Next-Generation Real-Time Augmented Reality (AR) Gesture Gaming & Interactive Creative Suite</strong>
</p>

<p align="center">
  <a href="#-overview">Overview</a> •
  <a href="#-game-modes">Game Modes</a> •
  <a href="#-controls--shortcuts">Controls</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-installation--usage">Installation</a> •
  <a href="#-t%C3%BCrk%C3%A7e-rehber">Türkçe Rehber</a>
</p>

---

<p align="center">
  <img src="screenshot_001.png" alt="Screen Slicer Gameplay Preview" width="850" style="border-radius: 12px; box-shadow: 0 8px 30px rgba(0,0,0,0.4);">
</p>

---

## 🌟 Overview

**Screen Slicer** transforms your standard webcam into an ultra-responsive, zero-latency Augmented Reality playground. Utilizing **Google MediaPipe Tasks Vision (HandLandmarker)**, **OpenCV**, and **NumPy**, Screen Slicer detects 21 3D hand landmarks in real time and translates natural hand gestures into high-speed physics interactions, mini-games, and 3D wireframe spatial drawings.

No special hardware or depth cameras are required—just your computer and a webcam!

### ✨ Key Highlights

- 🖐️ **21-Landmark Real-Time Multi-Hand Tracking**: Sub-millisecond tracking supporting 1 or 2 hands simultaneously.
- 🎯 **Moving Average Filter Smoothing**: Jitter-free fingertip cursor and blade trajectory stabilization.
- ⚡ **Ultra-Modern Glassmorphic UI**: TrueType anti-aliased typography (Segoe UI / Arial), dynamic glass cards, neon glows, and interactive HUD.
- 🖥️ **Dynamic Fullscreen & Per-Monitor High-DPI Awareness**: Seamless crisp rendering across 1080p, 2K, and 4K displays on Windows.
- 🎮 **7 Integrated Game & AR Simulation Modes**: Switch instantly on the fly with single-key shortcuts.

---

## 🎮 Game Modes

### 1. 🥊 AR Boxing Championship (`K`)
Enter the virtual ring! Face off against an animated AI opponent (**TITAN**).
- **Punch Detection**: Throw rapid jabs, crosses, and hooks with your fists.
- **Guard & Dodge**: Raise both hands to block incoming enemy punches or slip left/right to dodge.
- **Dynamic Feedback**: Real-time hit sparks, floating damage numbers, combo multipliers, and animated catch-up health bars.

### 2. 🍉 Fruit Ninja Slash (`F`)
A blade-slashing arcade classic in your living room!
- **Hand Blade Trail**: Fast hand motion generates a luminous particle slash trail.
- **Fruit Physics**: Watermelons, apples, oranges, lemons, and grapes launched in ballistic arcs.
- **Bombs & Combos**: Slice multiple fruits in a single swing for combo points; avoid deadly explosives!

### 3. 🏒 Neon Air Hockey (`H`)
Two-player fast-paced tabletop hockey right on your camera feed.
- **Dual Mallets**: Hand 1 controls the top mallet; Hand 2 controls the bottom mallet (or play solo with both hands!).
- **Realistic 2D Elastic Physics**: Wall rebounds, velocity-based collisions, friction, and goal detection.
- **Effects**: Goal celebrations, puck particle trails, and screen shake on heavy impacts.

### 4. 🏀 Physics Basketball (`B`)
Test your shooting and swatting skills.
- **Ball Interaction**: Swat and flick the basketball towards the hoop with your fingertips.
- **Moving Hoop Mode**: Press `1` for stationary hoop or `2` for an oscillating moving hoop.
- **Realistic Physics**: Gravity, backboard bounces, and net swishes.

### 5. 🏹 Precision Archery (`A`)
Draw and release arrows like a virtual archer.
- **Bow Mechanics**: Pull back on the bowstring with your hand gesture; the trajectory updates dynamically.
- **Wind & Gravity**: Realistic parabolic ballistic flight paths with target hit detection (Bullseye scoring).
- **Moving Target Mode**: Press `1` for fixed target or `2` for moving vertical targets.

### 6. ☀️ Sun in Palm (`G`)
Harness cosmic power in the palm of your hands!
- **Dynamic Solar Flare**: An animated celestial orb generates orbiting energy particles directly over your open palm.
- **Dual Hands**: Left hand can hold a star, right hand can channel a swirling Black Hole.
- **Color Cycling (`Space`)**: Cycle between Fire, Plasma, Yellow Star, White Dwarf, and Black Hole.

### 7. 🎨 AR Spatial Drawing & 3D Shapes (`D`)
Draw in 3D space with your fingers!
- **Pinch to Draw**: Pinch your index and middle fingers together to lay down neon strokes.
- **Wireframe Solids (`T`)**: Project and rotate 3D wireframe models (Cube, Pyramid, Diamond) anchored in space.
- **Creative Tools**:
  - `1-5`: Quick color palette selection
  - `+/-`: Adjust brush thickness
  - `E`: Dynamic Eraser
  - `P`: Particle Spray Brush
  - `Z` / `X`: Undo last stroke or remove last 3D shape

---

## ⌨️ Controls & Shortcuts

| Key | Mode / Scope | Action |
|:---:|:---:|---|
| <kbd>M</kbd> | Global | Return to **Main Menu / Dashboard** |
| <kbd>U</kbd> | Global | Toggle **Fullscreen** mode |
| <kbd>S</kbd> | Global | Capture high-resolution **Screenshot** |
| <kbd>Q</kbd> / <kbd>ESC</kbd> | Global | Quit Application |
| <kbd>K</kbd> | Mode Switch | Launch **AR Boxing Mode** |
| <kbd>F</kbd> | Mode Switch | Launch **Fruit Ninja Mode** |
| <kbd>H</kbd> | Mode Switch | Launch **Air Hockey Mode** |
| <kbd>B</kbd> | Mode Switch | Launch **Basketball Mode** |
| <kbd>A</kbd> | Mode Switch | Launch **Archery Mode** |
| <kbd>G</kbd> | Mode Switch | Launch **Sun in Palm Mode** |
| <kbd>D</kbd> | Mode Switch | Launch **AR Draw & 3D Shapes Mode** |
| <kbd>R</kbd> | In-Game | **Restart** active game mode (Fruit Ninja / Air Hockey / Boxing) |
| <kbd>Space</kbd> | Sun Mode | Cycle celestial orb colors & Black Hole |
| <kbd>1</kbd> / <kbd>2</kbd> | Mini-games | Toggle stationary / moving targets (Basketball & Archery) |
| <kbd>1</kbd> - <kbd>5</kbd> | AR Draw | Select drawing color palette |
| <kbd>+</kbd> / <kbd>-</kbd> | AR Draw | Increase / decrease brush stroke thickness |
| <kbd>E</kbd> | AR Draw | Toggle **Eraser** |
| <kbd>P</kbd> | AR Draw | Toggle **Particle Brush** |
| <kbd>T</kbd> | AR Draw | Cycle 3D shape (**Cube** / **Pyramid** / **Diamond**) |
| <kbd>Z</kbd> | AR Draw | **Undo** last brush stroke |
| <kbd>X</kbd> | AR Draw | **Delete** last placed 3D shape |
| <kbd>C</kbd> | AR Draw | **Clear** entire canvas |

---

## 🖐️ Hand Gestures Guide

```
        INDEX PINCH                   OPEN PALM                    CLOSED FIST
       (Draw / Slice)             (Celestial Energy)             (Boxing Strike)
            /\                         \  |  /                         ____
           /  \                         \ | /                         |####|
          /    \                         \|/                          |####|
      [Index + Middle]                [Open Palm]                   [Fist Clenched]
```

- **Pointer Cursor**: Extend index finger alone to navigate menus and position items.
- **Draw / Slice / Swat**: Pinch index and middle fingers together to draw in AR or slash flying objects.
- **Manipulate Shapes / Zoom**: Pinch thumb and index finger to scale or interact with 3D wireframes.
- **Hold Orb**: Hold an open palm facing the webcam to ignite the solar sphere.
- **Punch / Guard**: Clench a fist and drive forward to punch; hold both fists up to guard.

---

## 📁 Architecture & File Structure

```
Screen Slicer/
├── main.py                 # Core application loop, high-DPI handling, mode coordinator
├── hand_tracker.py         # MediaPipe Tasks Vision Multi-HandLandmarker tracker (21 landmarks)
├── hand_landmarker.task    # Google MediaPipe HandLandmarker neural network model asset
├── gesture_engine.py       # Gesture recognition, finger states, stroke & particle brush engine
├── geometry_engine.py      # 3D perspective projection, rotation matrices, wireframe solids
├── ui_engine.py            # Glassmorphic UI renderer, TrueType Segoe UI typography, neon glow
├── boxing_engine.py        # AR Boxing engine: AI opponent, punch/dodge detection, health HUD
├── fruit_ninja.py          # Fruit Ninja engine: projectile physics, blade trails, combo system
├── air_hockey.py           # 2-Player Air Hockey: 2D physics engine, mallets, goals, particle effects
├── basketball_engine.py    # Basketball physics, moving backboard & hoop, swat detection
├── archery_engine.py       # Archery ballistics, trajectory prediction, bullseye scoring
├── sun_engine.py           # Solar & black hole particle simulation anchored to palm orientation
├── requirements.txt        # Python package dependencies
├── Oyunu_Baslat.bat        # Windows 1-click launch batch script
├── LICENSE                 # MIT Open-Source License
└── README.md               # Documentation & usage guide
```

---

## 🚀 Installation & Usage

### 1. Prerequisites
- **Python 3.9** or higher installed ([Download Python](https://www.python.org/downloads/))
- A functional **Webcam** (built-in or USB)

### 2. Clone the Repository
```bash
git clone https://github.com/FireNemesisx/Screen-Slicer.git
cd Screen-Slicer
```

### 3. Create a Virtual Environment (Recommended)
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Run Screen Slicer
```bash
python main.py
```
> **Windows Quick Launch**: You can also simply double-click **`Oyunu_Baslat.bat`** to start the application with one click!

---

## 🇹🇷 Türkçe Rehber

**Screen Slicer**, kameranızı kullanarak el hareketlerinizle oynayabileceğiniz ve 3 boyutlu çizimler yapabileceğiniz gerçek zamanlı bir Artırılmış Gerçeklik (AR) oyun paketidir.

### 🎯 Öne Çıkan Modlar
1. **Boks Modu (`K`)**: Ekrana gelen boksöre karşı yumruk atın, gard alın ve kaçın (dodge).
2. **Fruit Ninja (`F`)**: Havada uçuşan meyveleri elinizi savurarak kesin; bombalara dikkat edin!
3. **Air Hockey (`H`)**: İki elinizle veya bir arkadaşınızla neon hokey masasında yarışın.
4. **Basketbol (`B`)**: Topa elinizle vurarak potaya basket atın (Hareketli pota için `2` tuşuna basın).
5. **Okçuluk (`A`)**: Yayı gererek hedefe nişan alın ve tam on ikiden vurun.
6. **Avuçta Güneş (`G`)**: Avucunuzu açarak parlayan bir yıldız veya kara delik oluşturun (`Boşluk` ile renk değiştirin).
7. **3B Çizim Modu (`D`)**: Parmaklarınızla havaya çizim yapın, 3B dönen geometrik cisimler (`T`) yerleştirin.

### 🚀 Hızlı Başlangıç (Windows)
1. Python yüklü olduğundan emin olun.
2. Klasör içindeki **`Oyunu_Baslat.bat`** dosyasına çift tıklayarak oyunu doğrudan başlatabilirsiniz.

---

## 🛠️ Troubleshooting & FAQ

<details>
<summary><strong>1. "Model not found: hand_landmarker.task" Error</strong></summary>

Make sure the file `hand_landmarker.task` is located in the root directory alongside `main.py`. If missing, it can be downloaded directly from Google MediaPipe:
```bash
# Direct download link:
# https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task
```
</details>

<details>
<summary><strong>2. Camera is not opening or black screen</strong></summary>

- Verify that your camera is not being used by another application (Zoom, Teams, Discord, etc.).
- If you have multiple cameras, change `cv2.VideoCapture(0)` in `main.py` to `cv2.VideoCapture(1)`.
- Make sure Windows Camera privacy permissions are enabled for desktop applications.
</details>

<details>
<summary><strong>3. Low FPS or Lag</strong></summary>

- Ensure good lighting for optimal hand landmark tracking accuracy.
- Reduce camera capture resolution in `main.py` if running on older hardware.
</details>

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

## 👤 Author

Developed with ❤️ by **[Etka Kudret Çeliköz](https://github.com/FireNemesisx)**.
Feel free to open issues or contribute pull requests!
