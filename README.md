# RetroAvatarQuest

## Important Requirement

This project requires the **CAPE dataset (sample 00096)** for full functionality of the AI body pipeline.

Due to its size (approximately 6–8 GB), the dataset is not included in this repository.

Users must download the dataset separately and place it locally before executing the pipeline.

If the dataset is not provided, the system will still run, but will fall back to simplified geometric heuristics instead of learned deformation.

---

## Overview

RetroAvatarQuest is a hybrid system integrating 3D model processing, lightweight machine learning, and a 2D game engine. The project converts a 3D humanoid model into a 2D playable character and enables control through either conventional keyboard input or real-time sensor input via an Arduino device.

The system is divided into two primary components:

1. An AI-based preprocessing pipeline that converts a `.glb` model into a segmented 2D avatar and joint representation.
2. A retro-style platformer game implemented in Python using `pygame`.

---

## Features

* Parsing and processing of `.glb` 3D models
* Automatic segmentation into anatomical regions
* Lightweight neural network trained on CAPE dataset samples
* Extraction of joint positions
* 2D platformer game engine with physics and collision handling
* Dual input system:

  * Keyboard controls
  * Arduino-based sensor input
* Fallback rendering when generated assets are unavailable

---

## Requirements

Install dependencies using:

```bash
pip install pygame numpy torch trimesh pillow scipy pygltflib pyserial keyboard
```

---

## Project Structure

```
RetroAvatarQuest/
├── ai_body/
│   ├── train_body_model.py
│   ├── glb_parser.py
│   ├── mesh_segment.py
│   ├── skeleton_extract.py
│   ├── render_profile.py
│
├── game/
│   ├── main.py
│   ├── player.py
│   ├── physics.py
│   ├── level.py
│   ├── arduino_bridge.py
│
├── assets/
│   └── input_model.glb
│
├── outputs/
│   ├── avatar.png
│   ├── joints.json
│   └── clean_mesh.glb
│
├── README.md
└── requirements.txt
```

---

## External Data Setup

### 1. CAPE Dataset (Required for Full Pipeline)

Download the CAPE dataset and extract sample `00096`.

Place the files in:

```
ai_body/cape_data/00096/
```

Ensure the directory contains `.npz` files.

Update the path in `train_body_model.py`:

```python
CAPE_DATA_DIR = "ai_body/cape_data/00096"
```

---

### 2. GLB Model (Required)

Provide a humanoid `.glb` file.

Place it in:

```
assets/input_model.glb
```

Update:

```python
GLB_INPUT_PATH = "assets/input_model.glb"
```

---

## Part 1: Avatar Generation

Run the preprocessing pipeline:

```bash
cd ai_body
python train_body_model.py
```

This step performs:

* Parsing of the input `.glb` file
* Neural model training (lightweight, CPU-compatible)
* Mesh segmentation
* Skeleton extraction
* Output generation

Generated files:

```
outputs/avatar.png
outputs/joints.json
outputs/clean_mesh.glb
```

---

## Part 2: Game Execution

Run the game:

```bash
cd game
python main.py
```

The game loads the generated avatar automatically. If unavailable, a fallback character is used.

---

## Controls

### Keyboard

| Key                  | Action     |
| -------------------- | ---------- |
| Left Arrow / A       | Move left  |
| Right Arrow / D      | Move right |
| Space / Up Arrow / W | Jump       |
| R                    | Restart    |
| Escape               | Exit       |

---

### Sensor Input (Arduino)

| Sensor Condition | Action     |
| ---------------- | ---------- |
| Very close       | Jump       |
| Moderate         | Move left  |
| Far              | Move right |

---

## Arduino Integration

Update the serial port in `arduino_bridge.py`:

```python
PORT = "COM3"
```

Ensure the Arduino outputs data in the format:

```
PROX:<value>
```

Example:

```
PROX:3
```

---

## Notes

* All file paths should be relative.
* The system remains functional without CAPE data, but with reduced accuracy.
* The neural model is intentionally lightweight for CPU execution.

---

## Limitations

* Simplified physics and collision handling
* Limited animation fidelity
* Dependence on stable serial communication for sensor input

---

## Future Work

* Improved animation using joint data
* Enhanced physics system
* Expanded sensor integration
* Performance optimization

---
