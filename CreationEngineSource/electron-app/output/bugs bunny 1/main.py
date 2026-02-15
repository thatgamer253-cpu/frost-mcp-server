import sys
from PyQt6.QtWidgets import QApplication
from gui import MainWindow

def main():
    app = QApplication(sys.argv)
    
    try:
        window = MainWindow()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()