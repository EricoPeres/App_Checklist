"""
e-ST Software - Ponto de entrada do sistema.

Fluxo:
  1. Mostra a tela de abertura (PyQt6).
  2. Enquanto ela está visível, carrega o módulo do checklist
     (pandas / reportlab são pesados, então o splash "esconde" essa espera).
  3. Garante um tempo mínimo de exibição, fecha o splash e encerra o Qt.
  4. Abre o Gerenciador de Checklists (Tkinter).

Observação: PyQt6 e Tkinter não podem rodar juntos no mesmo loop de eventos,
por isso o Qt é totalmente encerrado ANTES de o Tkinter ser iniciado.

Execute este arquivo:  python abertura.py
"""

import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0] if getattr(sys, "frozen", False) else __file__))

# Nome do arquivo de imagem (deve ficar na mesma pasta deste script)
IMAGEM_SPLASH = "splash_screen.png"

# Tempo mínimo (em milissegundos) que a tela de abertura fica visível
TEMPO_MINIMO_MS = 4000


def abrir_programa():
    """Importa e executa o checklist (Tkinter)."""
    import checklist_appv1_4
    checklist_appv1_4.main()


def iniciar_sistema():
    # Se o PyQt6 não estiver instalado, abre o sistema direto, sem splash
    try:
        from PyQt6.QtCore import Qt, QTimer
        from PyQt6.QtGui import QPixmap
        from PyQt6.QtWidgets import QApplication, QMessageBox, QSplashScreen
    except ImportError:
        print("PyQt6 não encontrado - iniciando sem tela de abertura.")
        abrir_programa()
        return

    app = QApplication(sys.argv)

    # 1. Carrega a imagem da abertura (se não existir, segue sem splash)
    caminho_imagem = os.path.join(BASE_DIR, IMAGEM_SPLASH)
    splash = None
    pixmap = QPixmap(caminho_imagem)

    if pixmap.isNull():
        print(f"Aviso: imagem '{caminho_imagem}' não encontrada - iniciando sem splash.")
    else:
        pixmap = pixmap.scaled(
            960,
            540,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        splash = QSplashScreen(pixmap)
        splash.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint
        )
        splash.show()
        app.processEvents()  # força o splash a aparecer antes do carregamento

    inicio = time.monotonic()

    # 2. Pré-carrega o checklist enquanto o splash está na tela
    try:
        import checklist_appv1_3  # noqa: F401  (apenas pré-carrega)
    except ImportError as erro:
        if splash:
            splash.close()
        QMessageBox.critical(
            None,
            "Dependência ausente",
            f"Não foi possível carregar o checklist:\n{erro}\n\n"
            "Instale as dependências com:\n"
            "pip install pandas openpyxl reportlab PyQt6",
        )
        sys.exit(1)

    # 3. Aguarda o tempo mínimo restante e encerra o Qt
    if splash:
        decorrido_ms = int((time.monotonic() - inicio) * 1000)
        restante_ms = max(0, TEMPO_MINIMO_MS - decorrido_ms)
        QTimer.singleShot(restante_ms, app.quit)
        app.exec()

        splash.close()
        splash.deleteLater()
        app.processEvents()

    # Libera o Qt por completo antes de iniciar o Tkinter
    del splash
    app.quit()
    del app

    # 4. Abre o sistema principal
    abrir_programa()


if __name__ == "__main__":
    iniciar_sistema()
