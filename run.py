"""
run.py — точка входа для запуска приложения.
Запуск: python run.py
"""

from app.app import create_app

if __name__ == '__main__':
    app = create_app()
    try:
        # Set host to 0.0.0.0 to make the app accessible on the network
        app.run(debug=True, host='0.0.0.0', port=5001)
    except Exception as e:
        print(f"Error starting app: {e}")
        import sys
        sys.exit(1) 