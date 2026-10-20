# Virtual-Trial-Room-Real-Time-3D-Try-on

A webcam "mirror" that puts a 3D shirt on you **live**: it follows your shoulders, turns with your body, bends its sleeves with your arms and fits itself to your body shape — all in the browser, no install.
A second mode takes a photo and sends it to a diffusion try-on model (CatVTON) for a photo-realistic result.

![Live 3D mirror with the developer readout on](/screenshots/catvton_capture.jpg)
*Live mirror (developer view): the 3D polo tracks shoulders, arms and turn in real time. The readout on the left shows the live tracking and fit numbers.*

![Photo try-on with CatVTON](/screenshots/live_mirror.jpg)
*Photo mode: your camera frame (left; red = the only area the AI may repaint), the garment (middle), and the CatVTON result (right).*

---

## Features

**Live 3D mirror** (Three.js + MediaPipe Pose)
- Tracks 33 body points and a person mask from the webcam, mirrored like a real mirror.
- Shirt is sized from your shoulder width and torso, and turns with your body (front, side and back views).
- **Sleeves follow your arms** — the shirt is rigged in code (per-vertex weights + rotations around the shoulder joint), so any plain `.glb` shirt works without a pre-rigged model.
- **Body-fit learning** — the shirt's body is widened band by band to match *your* outline, and deepened when you stand side-on.
- **Looks worn, not pasted on** — room-matched lighting and colour tint, soft shadow, camera-like grain, an invisible neck so the collar wraps around you, and your head, forearms and hands drawn *in front* of the shirt (with a skin-colour check so only real skin is drawn).
- **Soft fabric motion** — spring-damped hem sway, hem twist when you turn, and cuffs that trail fast arm moves.
- **Smooth tracking** — One-Euro filter (~40% less jitter and ~70% less lag than fixed smoothing in tests).
- **Switch shirts** with a hand swipe, the ‹ › buttons, or keys 1–9; shirts slide in and settle.

**Photo try-on** (Python bridge + CatVTON)
- Press **C**: after a countdown the app sends a clean photo, a product image of the garment and a custom repaint mask to a local Flask server, which calls CatVTON and returns the result.
- Custom mask built from the pose and person outline, so pants, face and background are left untouched (plus a paste-back step).
- Colour-key option for dark garments: render in a key colour, then recolour to the true colour.

## Tech stack

| Part | Tools |
|---|---|
| Live mirror | JavaScript, Three.js (r160), MediaPipe Tasks Vision — Pose Landmarker |
| Photo try-on bridge | Python, Flask, gradio_client, Pillow, NumPy |
| AI model | CatVTON (runs on a free Google Colab GPU, or a Hugging Face Space) |

## Project files

| File | What it is |
|---|---|
| `index.html` | The whole live mirror app (single file) |
| `catalog.json` | The list of shirts: name, 3D model, optional colour / photo / fit settings |
| `tryon_server.py` | Flask bridge between the page and CatVTON (`localhost:5000`) |
| `catvton_colab.ipynb` | Runs CatVTON on a free Colab GPU and gives you a public link |

## Run it

### 1. Live mirror
3D models are **not included** (licences). Download a T-shirt / polo `.glb` (e.g. from BlendKit or Sketchfab — check the licence), put it in the project folder, and point `catalog.json` at it:

```json
{ "items": [ { "name": "My shirt", "model": "myshirt.glb" } ] }
```

Then start a local server in the project folder and open the page:

```bash
python -m http.server 8000
```

Open **http://localhost:8000** in Chrome/Edge/Brave and allow the camera. Stand back so your shoulders and hips are visible.

### 2. Photo try-on (optional)
1. Open `catvton_colab.ipynb` in Google Colab (GPU runtime), run all cells and copy the `gradio.live` link it prints.
2. Save that link in a file called `catvton_url.txt` in the project folder (this file is git-ignored).
3. Install and start the bridge:
   ```bash
   pip install flask flask-cors gradio_client pillow numpy
   python tryon_server.py
   ```
4. In the mirror, press **C**.

## Keys

| Key | Action |
|---|---|
| `` ` `` | Customer view ↔ developer view (readout, skeleton, arm lines) |
| `C` / `Q` | Capture photo for CatVTON / quick vs quality |
| `1`–`9`, `,` `.`, `G` | Pick shirt, previous / next, swipe on/off |
| `↑ ↓ ← →`, `+ −`, `P` | Move / resize the shirt, print the fit values |
| `F` | Freeze the frame (5 s countdown) |
| `M` `L` `J` `D` `[ ]` | Smoothing, realistic light, grain, shadow, brightness |
| `B` `W` `A` `O` | Sleeve bending, weight view, arm lines, arms-in-front |
| `K` `U` `X` `V` | Neck, head in front, skin check, fabric motion |
| `Y` `N` | Flip / disable body turn |

## Known limits
- Short-sleeve tops only for now (no elbow bending for long sleeves).
- Fabric motion is a whole-garment spring, not a cloth simulation — no folds or wrinkles.
- A baggy shirt worn underneath can show at the shoulders.
- Needs decent light and a camera that sees your shoulders and hips.

## Credits & licences
- [Three.js](https://threejs.org) (MIT) and [MediaPipe](https://developers.google.com/mediapipe) (Apache 2.0).
- [CatVTON](https://github.com/Zheng-Chong/CatVTON) by Zheng Chong et al. — **non-commercial licence**; this project is for learning and research only.
- One-Euro filter: Casiez, Roussel & Vogel, *"1€ Filter"*, CHI 2012.
- 3D shirt models are not redistributed here; credit their authors when you use them.

---
Built by **Rakshan M H** · [LinkedIn](https://www.linkedin.com/in/rakshan-m-h-06122128b/) · [GitHub](https://github.com/rakshan1256)
