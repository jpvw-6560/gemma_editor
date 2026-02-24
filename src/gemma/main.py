import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTranslator, QLocale, QLibraryInfo

from gemma.infrastructure.container import Container
from gemma.ui_qt.main_window import MainWindow
from gemma.application.services.toast import MsgToast


def main():
    app = QApplication(sys.argv)
    
    # 🔹 Charger la traduction Qt en français
    translator = QTranslator()
    translator.load(
        QLocale("fr_FR"),
        "qtbase",
        "_",
        QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    )
    app.installTranslator(translator)

    container = Container()
    window = MainWindow(container)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()