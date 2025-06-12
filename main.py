# main.py
import os
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from gradio.routes import mount_gradio_app

from primary_app import create_primary_app
from tv_app      import create_tv_app

app = FastAPI()

# 1) Mount your primary quiz at "/primary"
primary_demo = create_primary_app()
mount_gradio_app(app, primary_demo, path="/primary")

# 2) Mount your TV quiz at "/tv"
tv_demo = create_tv_app()
mount_gradio_app(app, tv_demo, path="/tv")

# 3) Redirect the root "/" to "/primary"
@app.get("/")
def _():
    return RedirectResponse(url="/primary/")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level="warning",    # only warning+ show
        access_log=False        # disable the GET/200 lines
    )
