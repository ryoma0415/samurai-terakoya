import tkinter as tk
from tkinter import ttk, messagebox
import serial
import threading
import serial.tools.list_ports
import math

class SerialApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Measure Distortion")
        self.offset_d = 0.0
        self.offset_s1 = 0.0
        self.offset_s2 = 0.0
        self.offset_vol = [0.0] * 4

        self.measure_d = 0.0
        self.measure_s1 = 0.0
        self.measure_s2 = 0.0
        self.measure_vol = [0.0] * 4
        self.fixed_d = 0.0
        self.fixed_s1 = 0.0
        self.fixed_s2 = 0.0
        self.fixed_vol = [0.0] * 4

        # 接続状態を表示するラベル
        self.connection_status_label = tk.Label(master, text="未接続", font=("Arial", 12))
        self.connection_status_label.pack()
        self.connection_status_label.place(x=10, y=10)

        # COMポート選択のプルダウンメニュー
        self.com_port_var = tk.StringVar()
        self.com_ports = self.get_com_ports()
        self.com_port_menu = ttk.Combobox(master, textvariable=self.com_port_var, values=self.com_ports)
        self.com_port_menu.pack(pady=20)
        self.com_port_menu.place(x=120, y=12)

        # 接続ボタン
        self.connect_button = tk.Button(master, text="接続", command=self.connect_com_port)
        self.connect_button.pack(pady=20)
        self.connect_button.place(x=300, y=10)

        # ボタンの設定
        button_font = ("Arial", 16)
        self.start_button = tk.Button(master, text="計測開始", font=button_font, command=self.toggle_measurement)
        self.start_button.pack(pady=20)
        self.start_button.place(x=10, y=60)

        self.send_offset_button = tk.Button(master, text="原点調整", font=button_font, command=self.send_offset_command)
        self.send_offset_button.pack(pady=10)
        self.send_offset_button.place(x=600, y=60)

        # ラベルの定義
        label_font = ("Arial", 18)
        font_color = '#000000'
        self.data_label_d = tk.Label(master, text="Distance: 待機中", font=label_font, foreground=font_color)
        self.data_label_d.pack(pady=5)
        self.data_label_d.place(x=10, y=120)

        self.data_label_s1 = tk.Label(master, text="Tilt1: 待機中", font=label_font, foreground=font_color)
        self.data_label_s1.pack(pady=5)
        self.data_label_s1.place(x=300, y=120)

        self.data_label_s2 = tk.Label(master, text="Tilt2: 待機中", font=label_font, foreground=font_color)
        self.data_label_s2.pack(pady=5)
        self.data_label_s2.place(x=600, y=120)

        self.data_label_angle = tk.Label(master, text="Vol: 待機中", font=label_font, foreground=font_color)
        self.data_label_angle.pack(pady=5)
        self.data_label_angle.place(x=10, y=180)

        self.data_label_d_0 = tk.Label(master, text="Distance 0: 待機中", font=label_font, foreground=font_color)
        self.data_label_d_0.pack(pady=5)
        self.data_label_d_0.place(x=10, y=240)

        self.data_label_s1_0 = tk.Label(master, text="Tilt1 0: 待機中", font=label_font, foreground=font_color)
        self.data_label_s1_0.pack(pady=5)
        self.data_label_s1_0.place(x=300, y=240)

        self.data_label_s2_0 = tk.Label(master, text="Tilt2 0: 待機中", font=label_font, foreground=font_color)
        self.data_label_s2_0.pack(pady=5)
        self.data_label_s2_0.place(x=600, y=240)

        self.data_label_angle_0 = tk.Label(master, text="Vol 0: 待機中", font=label_font, foreground=font_color)
        self.data_label_angle_0.pack(pady=5)
        self.data_label_angle_0.place(x=10, y=300)



        # Initialize serial port
        self.ser = serial.Serial()
        self.ser.baudrate = 500000
        self.ser.timeout = 1

        # Measurement control flag
        self.measuring = False

        # Thread for handling the measurement loop
        self.thread = None


    def measurement_loop(self):
        command = bytes([0x52, 0x01, 0x00, 0x53])
        self.ser.timeout = 0.5
        while self.measuring and self.ser.is_open:
            try:
                self.ser.write(command)
                response = self.ser.read(14)
                if not self.measuring:
                    break
                if len(response) == 14:
                    gain = 0.95
                    self.measure_d = gain * self.measure_d + (1.0 - gain) * (float(int(response[2])) / 10.0)
                    self.measure_s1 = gain * self.measure_s1 + (1.0 - gain) * (float(int(response[3])) / 2.0 - 40.0)
                    self.measure_s2 = gain * self.measure_s2 + (1.0 - gain) * (float(int(response[4])) / 2.0 - 40.0)
                    self.measure_vol[0] = int(response[5] << 8) + int(response[6])
                    self.measure_vol[1] = int(response[7] << 8) + int(response[8])
                    self.measure_vol[2] = int(response[9] << 8) + int(response[10])
                    self.measure_vol[3] = int(response[11] << 8) + int(response[12])

                    self.fixed_d = self.measure_d - self.offset_d
                    self.fixed_s1 = self.measure_s1 - self.offset_s1
                    self.fixed_s2 = self.measure_s2 - self.offset_s2
                    self.fixed_vol[0] = self.measure_vol[0] - self.offset_vol[0]
                    self.fixed_vol[1] = self.measure_vol[1] - self.offset_vol[1]
                    self.fixed_vol[2] = self.measure_vol[2] - self.offset_vol[2]
                    self.fixed_vol[3] = self.measure_vol[3] - self.offset_vol[3]

                    self.update_gui_d(f"Distance: {self.measure_d:04.1f}", f"Distance 0: {self.fixed_d:04.1f}")
                    self.update_gui_s1(f"Tilt1: {self.measure_s1:04.1f}", f"Tilt1 0: {self.fixed_s1:04.1f}")
                    self.update_gui_s2(f"Tilt2: {self.measure_s2:04.1f}", f"Tilt2 0: {self.fixed_s2:04.1f}")
                    self.update_gui_angle(f"Vol: {self.measure_vol}", f"Vol 0: {self.fixed_vol}")
            except Exception as e:
                self.update_gui_d(f"エラー: {e}", f"エラー: {e}")
                break


    def get_com_ports(self):
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]


    def connect_com_port(self):
        selected_port = self.com_port_var.get()
        if not selected_port:
            messagebox.showerror("Error", "COMポートを選択してください")
            return
        try:
            self.ser.port = selected_port
            self.ser.open()
            self.connection_status_label.config(text=f"{selected_port} に接続")
            self.connect_button.config(state='disabled')
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open serial port: {e}")
            self.start_button.config(state='disabled')


    def toggle_measurement(self):
        if not self.measuring:
            self.measuring = True
            self.start_button.config(text="計測停止")
            self.thread = threading.Thread(target=self.measurement_loop)
            self.thread.daemon = True
            self.thread.start()
        else:
            self.measuring = False
            self.start_button.config(text="計測開始")


    def send_offset_command(self):
        self.offset_d = self.measure_d
        self.offset_s1 = self.measure_s1
        self.offset_s2 = self.measure_s2
        self.offset_vol[0] = self.measure_vol[0]
        self.offset_vol[1] = self.measure_vol[1]
        self.offset_vol[2] = self.measure_vol[2]
        self.offset_vol[3] = self.measure_vol[3]

        print(self.offset_d)
        print(self.offset_s1)
        print(self.offset_s2)
        print(self.offset_vol)


    def update_gui_d(self, text, text0):
        self.data_label_d.config(text=text)
        self.data_label_d_0.config(text=text0)

    def update_gui_s1(self, text, text0):
        self.data_label_s1.config(text=text)
        self.data_label_s1_0.config(text=text0)

    def update_gui_s2(self, text, text0):
        self.data_label_s2.config(text=text)
        self.data_label_s2_0.config(text=text0)

    def update_gui_angle(self, text, text0):
        self.data_label_angle.config(text=text)
        self.data_label_angle_0.config(text=text0)


    def on_closing(self):
        self.measuring = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        if self.ser.is_open:
            try:
                self.ser.close()
            except Exception:
                pass
        self.master.quit()
        self.master.destroy()



def main():
    root = tk.Tk()
    app = SerialApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.geometry("1200x800")
    root.resizable(False, False)
    root.mainloop()


if __name__ == "__main__":
    main()
