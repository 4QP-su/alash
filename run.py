"""
run.py — точка входа для запуска приложения.
Запуск: python run.py
"""

from dotenv import load_dotenv

import sys
from pathlib import Path
from app.app import create_app

 
def print_startup_info(app, host, port, debug):
    
    cwd = Path.cwd()
    script_path = Path(__file__).resolve()
    python_exe = Path(sys.executable).resolve()
    print(f"PS {cwd}>  & '{python_exe}' '{script_path}'")
    if 'debugpy' in sys.modules:
        import debugpy
        debugpy_path = Path(debugpy.__file__).resolve()
        print(f"Debugpy launcher: '{debugpy_path}'")
    print(f"* Serving Flask app '{app.import_name}'")
    print(f"* Debug mode: {'on' if debug else 'off'}")
    print(f"* Running on http://{host}:{port}")
    if host == '0.0.0.0':
        print(f"* Running on http://127.0.0.1:{port}")


if __name__ == '__main__':
    app = create_app()
    host = '0.0.0.0'
    port = 5001
    debug = True
    try:
        print_startup_info(app, host, port, debug)
        app.run(debug=debug, host=host, port=port)
    except Exception as e:
        print(f"Error starting app: {e}")
        sys.exit(1) 