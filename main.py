
import os
import time
import uvicorn
import asyncio
import subprocess
from advcms.app import app
from advcms.settings import app_settings
from advcms.agents.tools.chroma_tool import app_chromaconnector

def main():
    
    os.environ["GEMINI_API_KEY"] = app_settings.GEMINI_API_KEY
    
    server_process = subprocess.Popen(
        ["chroma", "run", "--host", "localhost", "--port", str(app_settings.CHROMA_PORT), "--path", app_settings.CHROMA_DATA_DIR],
        #stdout=subprocess.PIPE,
        #stderr=subprocess.PIPE,
        text=True
    )

    time.sleep(10)
    
    app_chromaconnector.SetPersistDirectory(os.path.dirname(__file__))
    asyncio.run(app_chromaconnector.setup())
    
    if app_settings.WEBSERVER_SECURE_ENABLED:
        uvicorn.run(
            "main:app", 
            host=app_settings.WEBSERVER_HOST,
            port=app_settings.WEBSERVER_SECURE_PORT,
            reload=app_settings.WEBSERVER_RELOAD,
            ssl_certfile=app_settings.WEBSERVER_SSL_CERT_FILE,
            ssl_keyfile=app_settings.WEBSERVER_SSL_KEY_FILE
            )
    else:
        uvicorn.run(
            "main:app",
            host=app_settings.WEBSERVER_HOST,
            port=app_settings.WEBSERVER_PORT,
            reload=app_settings.WEBSERVER_RELOAD
            )

if __name__ == "__main__":
    main()
    