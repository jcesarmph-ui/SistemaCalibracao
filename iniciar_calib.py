
import os
import sys
import time
import threading
import webbrowser
import subprocess
from pathlib import Path


def main():
    congelado = getattr(sys, "frozen", False)

    if congelado:
        pasta = Path(sys.executable).resolve().parent
    else:
        pasta = Path(__file__).resolve().parent

    os.chdir(pasta)

    arquivo = pasta / "main.py"

    if not arquivo.exists():
        print("ERRO: main.py nao encontrado.")
        print("Pasta:", pasta)
        input("Pressione ENTER para fechar...")
        return

    # Impede que o Streamlit entre no modo de desenvolvimento.
    os.environ["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = "false"

    argumentos = [
        "streamlit",
        "run",
        str(arquivo),
        "--global.developmentMode=false",
        "--server.address=127.0.0.1",
        "--server.port=8501",
        "--server.headless=true",
    ]

    if congelado:
        from streamlit.web import cli as stcli

        def abrir_navegador():
            time.sleep(4)
            webbrowser.open("http://127.0.0.1:8501")

        threading.Thread(
            target=abrir_navegador,
            daemon=True
        ).start()

        sys.argv = argumentos

        try:
            stcli.main()
        except Exception:
            import traceback
            traceback.print_exc()
            input("\nPressione ENTER para fechar...")

    else:
        comando = [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(arquivo),
            "--global.developmentMode=false",
            "--server.address=127.0.0.1",
            "--server.port=8501",
            "--server.headless=true",
        ]

        subprocess.run(comando)


if __name__ == "__main__":
    main()
