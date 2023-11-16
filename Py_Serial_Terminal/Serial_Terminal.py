import tkinter as tk
import tkinter.ttk as ttk
import serial.tools.list_ports
import threading
from datetime import datetime
from ttkthemes import ThemedTk
from tkinter.scrolledtext import ScrolledText
import time
from tkinter import Menu
from tkinter import messagebox
import binascii


class SerialMonitorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Serial Monitor")
        self.serial_port = serial.Serial()
        self.receive_thread = None
        self.is_connected = False
        self.style = ttk.Style()
        self.style.theme_use("plastik")
        self.data_buf = 0
        

        # Set root window background color
        self.root.configure(background=self.style.lookup("TFrame", "background"))
        self.root.iconbitmap("icon.ico")

        # Create the menubar
        self.menubar = Menu(self.root)
        self.root.config(menu=self.menubar)

        # Create the "File" menu
        self.file_menu = Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=self.file_menu)

        # Add the "Exit" option to the "File" menu
        self.file_menu.add_command(label="Exit", command=self.root.quit)
        
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

        self.send_label = ttk.Label(self.frame, text="Mode :")
        self.send_label.grid(row=4, column=0, pady=0, sticky=tk.W)

        self.ascii_hex_radio_button_value=tk.IntVar(value=1)
        self.ascii_hex_radio_button1 = ttk.Radiobutton(self.frame, text="ASCII", variable=self.ascii_hex_radio_button_value, command=self.ascii_hex_radio_button_changed, value=1).grid(row=4, column=1, padx=0, pady=5, sticky=tk.W)
        self.ascii_hex_radio_button2 = ttk.Radiobutton(self.frame, text="HEX", variable=self.ascii_hex_radio_button_value, command=self.ascii_hex_radio_button_changed, value=2).grid(row=4, column=1, padx=50, pady=5, sticky=tk.W) 
        
        self.send_entry = ttk.Entry(self.root)
        self.send_entry.pack(padx=10, pady=(0, 0), fill="x")
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

        self.parity_label = ttk.Label(self.frame, text="Parity :")
        self.parity_label.grid(row=4, column=2, padx=5, sticky=tk.W)

        self.parity_combobox = ttk.Combobox(self.frame)
        self.parity_combobox["values"] = ["None", "Odd", "Even"]
        self.parity_combobox.current(0)
        self.parity_combobox.configure(takefocus=True, state="readonly", style="TCombobox")
        self.parity_combobox.grid(row=4, column=3, padx=0, sticky=tk.W)
        self.parity_combobox.bind("<<ComboboxSelected>>", lambda event: self.parity_combobox.selection_clear())


        self.style.configure('ClearButton.TButton')
        self.clear_button = ttk.Button(self.root, text="Clear", command=self.clear_textbox, style='ClearButton.TButton')
        self.clear_button.pack(padx=100, pady=(0, 10), anchor="center")

        



        self.populate_serial_ports()    


    def ascii_hex_radio_button_changed(self):
        if(self.ascii_hex_radio_button_value.get() == 2):
            self.line_ending_combobox.configure(state="disabled")
        else:
            self.line_ending_combobox.configure(state="enabled")    
        

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

        parity_bit=serial.PARITY_NONE

        if(self.parity_combobox.get() == 'Odd'):
            parity_bit=serial.PARITY_ODD
        elif(self.parity_combobox.get() == 'Even'):
            parity_bit=serial.PARITY_EVEN

        try:
            self.serial_port = serial.Serial(port, baudrate=baud_rate, parity=parity_bit, timeout=0)  # Set timeout to 0 for non-blocking read
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
            # self.receive_thread.join()  # Wait for receive thread to exit
            self.receive_thread = None

        if self.serial_port.is_open:
            self.serial_port.close()

        self.connect_button.configure(text="Connect")
        self.send_entry.configure(state="disabled")  # Disable send entry

    def send_data(self, event=None):
        data = self.send_entry.get().strip()
        line_ending = self.get_selected_line_ending()

        
        if data:
            if self.is_connected:
                if(self.ascii_hex_radio_button_value.get() == 1):
                    data += line_ending
                    self.serial_port.write(data.encode("utf-8"))
                    self.scrollbox.insert(tk.END, '\nSent : '+data+'\n', 'sent')
                    self.scrollbox.tag_config('sent', foreground='green')
                else:
                    try:
                        hex_list = data.split(" ")
                        bytes_list = []

                        for i in range(len(hex_list)):
                            hex_val = hex_list[i]
                            if len(hex_val) == 1:
                                hex_val = "0" + hex_val
                            bytes_list.append(int(hex_val, 16))

                        bytes_array = bytes(bytes_list)
                        self.serial_port.write(bytes_array)

                        self.scrollbox.insert(tk.END, '\nSent : '+data, 'sent')
                        self.scrollbox.tag_config('sent', foreground='green')

                    except ValueError:
                        messagebox.showerror('Value Error', 'Improper Hex String or Value out of Range (0-255)')

            self.send_entry.delete(0, tk.END)

    def get_selected_line_ending(self):
        line_ending_index = self.line_ending_combobox.current()
        line_endings = ["", "\n", "\r", "\r\n"]
        return line_endings[line_ending_index]

    def read_data(self):
        while self.is_connected:
            try:
                if(self.ascii_hex_radio_button_value.get() == 1):
                    data = ""
                    message = ""
                    if self.serial_port.in_waiting:
                        data = self.serial_port.read(256).decode("utf-8", errors="replace")
                        if data:
                            message = f"{data}"
                            self.data_buf += len(data)
                            if self.timestamp_var.get():
                                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # Keep only milliseconds
                                message = f"\n[{timestamp}] > {data}"
                            self.scrollbox.insert(tk.END, message)

                            # Limit data history
                            if self.data_buf > 1000000:
                                self.data_buf = 0
                                self.scrollbox.delete(1.0, tk.END)

                            if self.autoscroll_var.get():
                                self.scrollbox.see(tk.END)
                            
                            # print('still in ASCII')
                else:
                    data = ""
                    message = ""
                    if self.serial_port.in_waiting:
                        data = self.serial_port.read(256)
                        if data:
                            ## Convert data to hexstring with space between each pair of digits
                            message = " ".join([f"{byte:02X}" for byte in data])
                            message = f"\n{message}"
                            self.data_buf += len(message)
                            if self.timestamp_var.get():
                                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # Keep only milliseconds
                                message = f"\n[{timestamp}] > {message}"

                            self.scrollbox.insert(tk.END, message)

                            # Limit data history
                            if self.data_buf > 1000000:
                                self.data_buf = 0
                                self.scrollbox.delete(1.0, tk.END)

                            if self.autoscroll_var.get():
                                self.scrollbox.see(tk.END)

                    
            except serial.SerialException:
                self.scrollbox.insert(tk.END, "Serial connection closed.\n")
                break
            time.sleep(0.0001)  # Add a small delay of 0.1 milliseconds

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    root = ThemedTk()  # Use a theme from ttkthemes
    root.geometry("480x400")  # Set the initial width and height of the window
    app = SerialMonitorGUI(root)
    app.run()
