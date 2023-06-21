import tkinter as tk
import tkinter.ttk as ttk
import serial.tools.list_ports
import threading
from datetime import datetime
from ttkthemes import ThemedTk
from tkinter.scrolledtext import ScrolledText


class SerialMonitorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Serial Monitor")
        self.serial_port = serial.Serial()
        self.receive_thread = None
        self.is_connected = False
        self.style = ttk.Style()
        self.style.theme_use("plastik")

        # Set root window background color
        self.root.configure(background=self.style.lookup("TFrame", "background"))

        # Create GUI elements
        self.frame = ttk.Frame(self.root)
        self.frame.pack(padx=10, pady=10)

        self.port_label = ttk.Label(self.frame, text="Serial Port:")
        self.port_label.grid(row=0, column=0, sticky=tk.W)

        self.port_combobox = ttk.Combobox(self.frame)
        self.port_combobox.grid(row=0, column=1, padx=5, sticky=tk.W)
        self.port_combobox.configure(takefocus=True, state="readonly", style="TCombobox")
        self.port_combobox.bind("<<ComboboxSelected>>", lambda event: self.port_combobox.selection_clear())

        self.connect_button = ttk.Button(self.frame, text="Connect", command=self.toggle_connection, style="Connect.TButton")
        self.connect_button.grid(row=0, column=2, padx=5, sticky=tk.W)

        self.baud_label = ttk.Label(self.frame, text="Baud Rate:")
        self.baud_label.grid(row=1, column=0, sticky=tk.W)

        self.baud_entry = ttk.Entry(self.frame)
        self.baud_entry.grid(row=1, column=1, padx=5, sticky=tk.W)
        self.baud_entry.insert(tk.END, "115200")  # Default baud rate

        self.line_ending_label = ttk.Label(self.frame, text="Line Ending:")
        self.line_ending_label.grid(row=1, column=2, padx=5, sticky=tk.W)

        self.line_ending_combobox = ttk.Combobox(self.frame)
        self.line_ending_combobox.grid(row=1, column=3, padx=0, sticky=tk.W)
        self.line_ending_combobox["values"] = ["None", "New Line (\\n)", "Carriage Return (\\r)", "Both (\\r\\n)"]
        self.line_ending_combobox.current(1)
        self.line_ending_combobox.configure(takefocus=True, state="readonly", style="TCombobox")
        self.line_ending_combobox.bind("<<ComboboxSelected>>", lambda event: self.line_ending_combobox.selection_clear())

        self.send_label = ttk.Label(self.root, text="Send Data:")
        self.send_label.pack(padx=10, pady=(0, 10), anchor=tk.W)

        self.send_entry = ttk.Entry(self.root)
        self.send_entry.pack(padx=10, pady=(0, 10), fill="x")
        self.send_entry.configure(state="disabled")
        self.send_entry.bind("<Return>", self.send_data)  # Bind Enter key to send data

        self.autoscroll_var = tk.BooleanVar(value=True)
        self.autoscroll_checkbox = ttk.Checkbutton(self.frame, text="AutoScroll", variable=self.autoscroll_var)
        self.autoscroll_checkbox.grid(row=0, column=3, padx=0, sticky=tk.W)

        self.timestamp_var = tk.BooleanVar(value=True)
        self.timestamp_checkbox = ttk.Checkbutton(self.frame, text="TimeStamp", variable=self.timestamp_var)
        self.timestamp_checkbox.grid(row=0, column=3, padx=80, sticky=tk.W)

        self.scrollbox = ScrolledText(self.root, height=10, width=50, background=self.style.lookup("TFrame", "background"))
        self.scrollbox.pack(padx=10, pady=10, expand=True, fill=tk.BOTH)
        self.scrollbox.configure(font=("Courier", 12), background='#ffffeb')  # Set the desired font family and size

        self.style.configure('ClearButton.TButton')
        self.clear_button = ttk.Button(self.root, text="Clear", command=self.clear_textbox, style='ClearButton.TButton')
        self.clear_button.pack(padx=10, pady=(0, 10))

        self.populate_serial_ports()

    def clear_textbox(self):
        self.scrollbox.delete("1.0", tk.END)

    def populate_serial_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combobox["values"] = ports

        if ports:
            self.port_combobox.current(0)

    def toggle_connection(self):
        if self.is_connected:
            self.disconnect()
        else:
            self.connect()

    def connect(self):
        port = self.port_combobox.get()
        baud_rate = int(self.baud_entry.get())

        try:
            self.serial_port = serial.Serial(port, baud_rate, timeout=0)  # Set timeout to 0 for non-blocking read
            self.is_connected = True
            self.connect_button.configure(text="Disconnect")

            # Start the receive thread
            self.receive_thread = threading.Thread(target=self.read_data)
            self.receive_thread.daemon = True  # Set the thread as a daemon thread to automatically exit when the main thread exits
            self.receive_thread.start()

            self.send_entry.configure(state="normal")  # Enable send entry for writing
        except serial.SerialException:
            self.scrollbox.insert(tk.END, "Failed to connect to " + port + "\n")

    def disconnect(self):
        if self.receive_thread:
            self.is_connected = False  # Set the flag to stop the receive thread
            self.receive_thread.join()  # Wait for receive thread to exit
            self.receive_thread = None

        if self.serial_port.is_open:
            self.serial_port.close()

        self.connect_button.configure(text="Connect")
        self.send_entry.configure(state="disabled")  # Disable send entry

    def send_data(self, event=None):
        data = self.send_entry.get()
        line_ending = self.get_selected_line_ending()

        if data:
            if self.is_connected:
                data += line_ending
                self.serial_port.write(data.encode("utf-8"))
            self.send_entry.delete(0, tk.END)

    def get_selected_line_ending(self):
        line_ending_index = self.line_ending_combobox.current()
        line_endings = ["", "\n", "\r", "\r\n"]
        return line_endings[line_ending_index]

    def read_data(self):
        while self.is_connected:
            try:
                data = self.serial_port.readline().decode("utf-8")
                if data:
                    message = data
                    if self.timestamp_var.get():
                        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # Keep only milliseconds
                        message = f"[{timestamp}] {data}"
                    self.scrollbox.insert(tk.END, message)
                    if self.autoscroll_var.get():
                        self.scrollbox.see(tk.END)
            except serial.SerialException:
                self.scrollbox.insert(tk.END, "Serial connection closed.\n")
                break

    def run(self):
        self.root.mainloop()
        


if __name__ == "__main__":
    root = ThemedTk()  # Use a theme from ttkthemes
    root.geometry("480x400")  # Set the initial width and height of the window
    app = SerialMonitorGUI(root)
    app.run()
