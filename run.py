import os

from app import create_app
from app.envfile import load_env

load_env()
if __name__ == "__main__":
    os.environ.setdefault("FLASK_DEBUG", "1")      # ishlab chiqish: SECRET_KEY shart emas, cookie http'da ham ishlaydi
    os.environ.setdefault("RM_WORKER", "1")        # fon vazifalari shu jarayonda (app/worker.py)
app = create_app()

if __name__ == "__main__":
    # PORT muhit o'zgaruvchisi berilsa, o'sha portda ishlaydi (standart: 5000)
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
