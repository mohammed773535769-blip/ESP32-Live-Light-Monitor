import csv
import queue
import threading
from collections import deque
from datetime import datetime

import serial
import tkinter as tk
from serial.tools import list_ports
from tkinter import filedialog, messagebox, ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


BAUD_RATE = 115200
MAX_GRAPH_POINTS = 60
MAX_SAVED_READINGS = 86400

LOW_LIGHT_BELOW = 1000
BRIGHT_ABOVE = 3000

message_queue = queue.Queue()
stop_event = threading.Event()
reader_thread = None

graph_values = deque(maxlen=MAX_GRAPH_POINTS)
saved_readings = deque(maxlen=MAX_SAVED_READINGS)

min_reading = None
max_reading = None
graph_changed = False


def parse_light(line):
    line = line.strip()

    if not line.startswith("LIGHT:"):
        return None

    try:
        value = int(line[6:])
    except ValueError:
        return None

    return value if 0 <= value <= 4095 else None


def get_light_status(reading):
    if reading < LOW_LIGHT_BELOW:
        return "Low Light"
    if reading > BRIGHT_ABOVE:
        return "Bright"
    return "Medium Light"


def read_serial(port_name):
    port = None
    reason = "Disconnected"

    try:
        port = serial.Serial(port_name, BAUD_RATE, timeout=1)
        message_queue.put(("connected", port_name))

        while not stop_event.is_set():
            raw_line = port.readline()

            if not raw_line:
                continue

            reading = parse_light(
                raw_line.decode("utf-8", errors="ignore")
            )

            if reading is not None:
                timestamp = datetime.now().isoformat(timespec="seconds")
                message_queue.put(("light", timestamp, reading))

    except (serial.SerialException, OSError) as error:
        if port is None:
            reason = f"Could not open {port_name}"
        else:
            reason = f"Connection lost: {error}"

    finally:
        if port is not None:
            port.close()

        message_queue.put(("closed", reason))


def handle_new_reading(timestamp, reading):
    global min_reading, max_reading, graph_changed

    saved_readings.append((timestamp, reading))
    graph_values.append(reading)
    graph_changed = True

    if min_reading is None or reading < min_reading:
        min_reading = reading

    if max_reading is None or reading > max_reading:
        max_reading = reading

    reading_var.set(str(reading))
    light_status_var.set(get_light_status(reading))
    min_max_var.set(f"Min: {min_reading}    Max: {max_reading}")


def check_messages():
    while True:
        try:
            message = message_queue.get_nowait()
        except queue.Empty:
            break

        kind = message[0]

        if kind == "light":
            handle_new_reading(message[1], message[2])

        elif kind == "connected":
            status_var.set(f"Connected to {message[1]}")
            disconnect_button.config(state="normal")

        elif kind == "closed":
            status_var.set(message[1])
            connect_button.config(state="normal")
            disconnect_button.config(state="disabled")

    root.after(200, check_messages)


def update_graph():
    global graph_changed

    if graph_changed:
        line.set_data(range(len(graph_values)), list(graph_values))
        canvas.draw_idle()
        graph_changed = False

    root.after(1000, update_graph)


def refresh_ports():
    ports = [
        f"{port.device} - {port.description}"
        for port in list_ports.comports()
    ]

    port_box["values"] = ports

    if ports and not port_var.get():
        port_var.set(ports[0])


def connect():
    global reader_thread, min_reading, max_reading

    selected = port_var.get().strip()

    if not selected:
        messagebox.showwarning("No port", "Please select a COM port first.")
        return

    port_name = selected.split(" - ")[0]

    min_reading = None
    max_reading = None
    min_max_var.set("Min: --    Max: --")

    stop_event.clear()
    connect_button.config(state="disabled")
    status_var.set(f"Connecting to {port_name}...")

    reader_thread = threading.Thread(
        target=read_serial,
        args=(port_name,),
        daemon=True
    )
    reader_thread.start()


def disconnect():
    stop_event.set()
    disconnect_button.config(state="disabled")
    status_var.set("Disconnecting...")


def save_csv():
    if not saved_readings:
        messagebox.showinfo("No data", "There are no readings to save yet.")
        return

    file_name = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv")],
        initialfile="light_readings.csv"
    )

    if not file_name:
        return

    try:
        with open(file_name, "w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["timestamp", "adc_reading", "light_status"])

            for timestamp, reading in saved_readings:
                writer.writerow([
                    timestamp,
                    reading,
                    get_light_status(reading)
                ])

    except OSError as error:
        messagebox.showerror("Could not save", str(error))
        return

    status_var.set(f"Saved {len(saved_readings)} readings to {file_name}")


def on_close():
    stop_event.set()

    if reader_thread is not None and reader_thread.is_alive():
        reader_thread.join(timeout=1.5)

    root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    root.title("ESP32 Live Light Monitor")

    tk.Label(
        root,
        text="ESP32 Live Light Monitor",
        font=("Segoe UI", 16, "bold")
    ).pack(pady=(10, 5))

    top_frame = tk.Frame(root)
    top_frame.pack(padx=10, pady=5)

    tk.Label(top_frame, text="COM port:").pack(side="left")

    port_var = tk.StringVar()
    port_box = ttk.Combobox(
        top_frame,
        textvariable=port_var,
        width=35
    )
    port_box.pack(side="left", padx=5)

    tk.Button(
        top_frame,
        text="Refresh",
        command=refresh_ports
    ).pack(side="left", padx=2)

    connect_button = tk.Button(
        top_frame,
        text="Connect",
        command=connect
    )
    connect_button.pack(side="left", padx=2)

    disconnect_button = tk.Button(
        top_frame,
        text="Disconnect",
        command=disconnect,
        state="disabled"
    )
    disconnect_button.pack(side="left", padx=2)

    status_var = tk.StringVar(value="Not connected")
    tk.Label(
        root,
        textvariable=status_var,
        fg="gray30"
    ).pack()

    reading_var = tk.StringVar(value="--")
    tk.Label(
        root,
        textvariable=reading_var,
        font=("Segoe UI", 48, "bold")
    ).pack(pady=(5, 0))

    tk.Label(
        root,
        text="ADC reading (0 - 4095)",
        font=("Segoe UI", 10)
    ).pack()

    light_status_var = tk.StringVar(value="--")
    tk.Label(
        root,
        textvariable=light_status_var,
        font=("Segoe UI", 18)
    ).pack(pady=5)

    min_max_var = tk.StringVar(value="Min: --    Max: --")
    tk.Label(
        root,
        textvariable=min_max_var,
        font=("Segoe UI", 12)
    ).pack()

    figure = Figure(figsize=(6, 3), dpi=100)
    axes = figure.add_subplot(111)

    axes.set_xlabel("Last readings (about 1 per second)")
    axes.set_ylabel("ADC reading")
    axes.set_xlim(0, MAX_GRAPH_POINTS - 1)
    axes.set_ylim(0, 4095)
    axes.grid(True)

    line, = axes.plot([], [], color="tab:orange")
    figure.tight_layout()

    canvas = FigureCanvasTkAgg(figure, master=root)
    canvas.get_tk_widget().pack(
        fill="both",
        expand=True,
        padx=10,
        pady=5
    )

    tk.Button(
        root,
        text="Save readings to CSV",
        command=save_csv
    ).pack(pady=(0, 10))

    refresh_ports()
    root.protocol("WM_DELETE_WINDOW", on_close)

    check_messages()
    update_graph()
    root.mainloop()
