import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTranslator, QLocale, QLibraryInfo

from core.bootstrap.container import Container
from core.view.main_window import MainWindow
from core.services.toast.toast import MsgToast


def main():
    app = QApplication(sys.argv)
    
    # 🔹 Charger la traduction Qt en français ----------------------
    translator = QTranslator()
    translator.load(
        QLocale("fr_FR"),
        "qtbase",
        "_",
        QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    )
    app.installTranslator(translator)
    #-----------------------------------------------------------------
    container = Container()
    
    window = container.main_window
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()