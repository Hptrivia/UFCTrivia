import os
import uvicorn
from fastapi import FastAPI
import gradio as gr

from UFC import create_v1
from v2 import create_v2 # you’ll create similarly

app = FastAPI()

# mount v1 at “/”
app = gr.mount_gradio_app(app, create_v1(), path="")
# mount v2 at “/v2”
app = gr.mount_gradio_app(app, create_v2(), path="/v2")

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT",8080)),
        share=False
    )
