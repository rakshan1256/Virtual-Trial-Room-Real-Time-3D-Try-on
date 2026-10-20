"""
tryon_server.py: the bridge between the browser try-on (Track 2) and CatVTON (Track 1).

What it does:
  1. The browser page sends two pictures when you press C:
       person  - a clean photo of you (768x1024)
       garment - the 3D shirt rendered flat on white (768x1024)
  2. This program saves both into the "captures" folder (handy for checking),
  3. sends them to CatVTON on Hugging Face - the same way your Track 1 does,
  4. and sends the result picture back to the page (and saves it in captures/ too).

How to run (in the same folder as index.html), in PowerShell:
    pip install flask pillow gradio_client
    $env:HF_TOKEN = "hf_your_token_here"     # same token as Track 1
    python tryon_server.py
Leave it running, then press C in the browser.
"""

import io
import os
import random
import time
from pathlib import Path

from flask import Flask, jsonify, request, send_file
from PIL import Image

app = Flask(__name__)
CAPTURES = Path(__file__).parent / "captures"
CAPTURES.mkdir(exist_ok=True)


# Public copies of CatVTON on Hugging Face, tried in this order. All of them have the
# same "/submit_function" as the official one. Spaces break or go to sleep now and then
# (the official one was in RUNTIME_ERROR on 3 Oct 2026), so we fall back to the next.
SPACES = ["zhengchong/CatVTON", "multimodalart/CatVTON-zerogpu"]
# Your OWN CatVTON (e.g. running on Google Colab) goes first when you give its link:
#   PowerShell:  $env:CATVTON_URL = "https://xxxxxxxx.gradio.live"
if os.environ.get("CATVTON_URL"):
    SPACES.insert(0, os.environ["CATVTON_URL"].strip().rstrip("/"))
_clients = {}  # connections, made once and then reused


def get_client(space):
    """Connect to one CatVTON Space (connecting takes a few seconds, so we keep it)."""
    if space not in _clients:
        from gradio_client import Client
        token = os.environ.get("HF_TOKEN")
        if not token:
            print("WARNING: no HF_TOKEN set - you may wait longer in the queue.")
        print(f"Connecting to {space}...")
        _clients[space] = Client(space, token=token) if token else Client(space)
    return _clients[space]


def flatten_on_white(img: Image.Image) -> Image.Image:
    """Product photos are often PNGs with a see-through background. Simply dropping the
    transparency turns it BLACK, so paste the garment onto white (like Track 1's prepare_shirt.py)."""
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        img = img.convert("RGBA")
        white = Image.new("RGBA", img.size, (255, 255, 255, 255))
        return Image.alpha_composite(white, img).convert("RGB")
    return img.convert("RGB")


def run_catvton(person: Image.Image, garment: Image.Image, stamp: str, mask=None) -> Image.Image:
    """Take a photo of the person + a garment image, return the try-on result.
    Uses exactly the call from your Track 1 (ai_helper.py).

    mask: the area CatVTON may repaint (white = repaint, transparent = keep), drawn by the
    browser from your pose. None = blank layer = CatVTON guesses the area itself (which is
    how your pants got repainted)."""
    from gradio_client import handle_file

    # CatVTON wants files: the photo, a "mask" layer, and the garment on white.
    person_png = CAPTURES / f"{stamp}_person.png"
    layer_png = CAPTURES / f"{stamp}_mask_layer.png"
    garment_jpg = CAPTURES / f"{stamp}_garment.jpg"
    person.save(person_png)
    if mask is not None:
        mask.resize(person.size).save(layer_png)
    else:
        Image.new("RGBA", person.size, (0, 0, 0, 0)).save(layer_png)
    garment.save(garment_jpg, quality=95)

    # A new random seed per capture: with a fixed seed (Track 1 used 42), the same shirt
    # and pose always give the SAME answer, so retrying a bad result could never help.
    # It's printed, so a good result can be reproduced later.
    seed = random.randint(0, 10000)
    print(f"  seed {seed}")
    errors = []
    for space in SPACES:
        try:
            result = get_client(space).predict(
                person_image={
                    "background": handle_file(str(person_png)),
                    "layers": [handle_file(str(layer_png))],
                    "composite": handle_file(str(person_png)),
                },
                cloth_image=handle_file(str(garment_jpg)),
                cloth_type="upper",
                num_inference_steps=50,
                guidance_scale=5.0,
                seed=seed,
                show_type="result only",
                api_name="/submit_function",
            )
            print(f"  answered by {space}")
            break
        except Exception as e:
            print(f"  {space} failed: {e}")
            _clients.pop(space, None)          # reconnect fresh next time
            errors.append(f"{space}: {e}")
    else:
        raise RuntimeError("every CatVTON Space failed - " + " | ".join(errors))
    # The Space answers with the path of the result picture it downloaded for us.
    if isinstance(result, (list, tuple)):
        result = result[0]
    if isinstance(result, dict):
        result = result.get("path") or result.get("value")
    return Image.open(result).convert("RGB")


@app.after_request
def allow_browser(resp):
    # The page runs on localhost:8000 and this bridge on localhost:5000. Browsers
    # block that unless the bridge says "this page may talk to me".
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "*"
    return resp


@app.route("/tryon", methods=["POST", "OPTIONS"])
def tryon():
    if request.method == "OPTIONS":
        return "", 204
    if "person" not in request.files or "garment" not in request.files:
        return jsonify(error="expected two pictures: person and garment"), 400

    stamp = time.strftime("%Y%m%d-%H%M%S")
    person = Image.open(request.files["person"].stream).convert("RGB")
    garment = flatten_on_white(Image.open(request.files["garment"].stream))
    mask = Image.open(request.files["mask"].stream).convert("RGBA") if "mask" in request.files else None
    person.save(CAPTURES / f"{stamp}_person.jpg", quality=95)
    garment.save(CAPTURES / f"{stamp}_garment.png")
    print(f"[{stamp}] received person {person.size} + garment {garment.size} + "
          f"{'mask from the page' if mask else 'NO mask (CatVTON will guess the area)'}")

    t0 = time.time()
    try:
        print(f"[{stamp}] sending to CatVTON (can take up to a minute or two)...")
        result = run_catvton(person, garment, stamp, mask)
    except Exception as e:  # show the real reason in the browser instead of a silent failure
        print(f"[{stamp}] CatVTON failed: {e!r}")
        return jsonify(error=f"CatVTON failed: {e}"), 500

    result.save(CAPTURES / f"{stamp}_result.png")
    print(f"[{stamp}] result ready in {time.time() - t0:.1f}s")
    buf = io.BytesIO()
    result.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


if __name__ == "__main__":
    print("Try-on bridge running at http://localhost:5000  (Ctrl+C to stop)")
    print("CatVTON sources, tried in order:", " -> ".join(SPACES))
    # one request at a time, so a second capture waits instead of overloading the model
    app.run(host="127.0.0.1", port=5000, threaded=False)