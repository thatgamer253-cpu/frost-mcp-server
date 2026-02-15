import tkinter as tk
from tkinter import messagebox, simpledialog

class UserInterface:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Episode Generator")
        self.root.geometry("400x200")
        self.user_input = None

        self.create_widgets()

    def create_widgets(self):
        self.label = tk.Label(self.root, text="Enter your script:")
        self.label.pack(pady=10)

        self.input_text = tk.Text(self.root, height=5, width=40)
        self.input_text.pack(pady=10)

        self.submit_button = tk.Button(self.root, text="Generate", command=self.submit_input)
        self.submit_button.pack(pady=10)

    def submit_input(self):
        try:
            self.user_input = self.input_text.get("1.0", tk.END).strip()
            if not self.user_input:
                raise ValueError("Input cannot be empty.")
            self.root.quit()
        except Exception as e:
            self.display_error_message(f"Error: {str(e)}")

    def get_user_input(self):
        self.root.mainloop()
        return self.user_input

    def display_success_message(self, message):
        messagebox.showinfo("Success", message)

    def display_error_message(self, message):
        messagebox.showerror("Error", message)