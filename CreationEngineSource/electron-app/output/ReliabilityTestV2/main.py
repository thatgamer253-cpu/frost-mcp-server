import sys
from PyQt6.QtWidgets import QApplication
from ui import CryptoPortfolioDashboard

def main():
    try:
        app = QApplication(sys.argv)
        window = CryptoPortfolioDashboard()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()