# main.py
import os
from fastapi import FastAPI
from gradio.routes import mount_gradio_app

from primary_app import create_primary_app
from tv_app      import create_tv_app

app = FastAPI()

# ─── Primary quiz at "/" ───────────────────────────────────
primary = create_primary_app()
mount_gradio_app(app, primary, path="/primary")

# ─── TV quiz at "/tv" ─────────────────────────────────────
tv = create_tv_app()
mount_gradio_app(app, tv, path="/tv")

# ─── Run with Uvicorn ─────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
