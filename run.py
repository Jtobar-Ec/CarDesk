import sys
from os.path import abspath, dirname

# Añade el directorio del proyecto al PYTHONPATH
sys.path.insert(0, dirname(abspath(__file__)))

from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)