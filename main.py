# main.py
import os
from fastapi import FastAPI
from gradio.routes import mount_gradio_app

from tv_app      import create_tv_app
from primary_app import create_primary_app

app = FastAPI()

# 1) Mount the TV quiz under /tv first
tv_demo = create_tv_app()
mount_gradio_app(app, tv_demo, path="tv")

# 2) Mount your primary quiz at the root path "/"
primary_demo = create_primary_app()
mount_gradio_app(app, primary_demo, path="primary")

# 3) Uvicorn entrypoint
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
