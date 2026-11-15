import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    # PORT muhit o'zgaruvchisi berilsa, o'sha portda ishlaydi (standart: 5000)
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
