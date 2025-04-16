import firebase_admin
from firebase_admin import credentials, firestore
import cv2
import numpy as np
import time
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
from PIL import Image, ImageTk
from datetime import datetime
import os
import csv
from twilio.rest import Client

# --- Firebase Setup ---
cred = credentials.Certificate("XXXXXXXX_credentials.json") #ADD UR JSON FILE
firebase_admin.initialize_app(cred)
db = firestore.client()

# --- Twilio Setup ---
#ADD UR NECESSARY DETAILS
account_sid = 'XXXXXXXXXXXX'
auth_token = 'XXXXXXXXXXX'
twilio_number = 'XXXXXXXXX'
ALERT_PHONE_NUMBER = 'XXXXXXXXXXX'
twilio_client = Client(account_sid, auth_token)

def send_sms(speed):
    message = twilio_client.messages.create(
        body=f'Alert! Overspeed detected: {speed:.2f} km/h',
        from_=twilio_number,
        to=ALERT_PHONE_NUMBER
    )
    print(f"SMS sent: {message.sid}")


# --- Parameters ---
REFERENCE_DISTANCE = 100
SPEED_LIMIT = 50  # km/h
CSV_FILE = "speed_log.csv"

# Color range for blue detection
lower_blue = np.array([100, 150, 0])
upper_blue = np.array([140, 255, 255])

def calculate_speed(pos1, pos2, time_elapsed):
    pixel_distance = abs(pos2 - pos1)
    speed = (pixel_distance / REFERENCE_DISTANCE) / time_elapsed * 3.6
    return speed

class SpeedDetectorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Speed Detector GUI")
        self.root.geometry("800x600")

        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.video_frame = tk.Frame(self.main_frame, bg="gray")
        self.video_frame.grid(row=0, column=0, padx=10, pady=10)

        self.video_label = tk.Label(self.video_frame)
        self.video_label.grid(row=0, column=0)

        self.status_label = tk.Label(self.video_frame, text="Status: Paused", font=("Arial", 12, "bold"), fg="red")
        self.status_label.grid(row=1, column=0, padx=10, pady=5)

        alert_frame = tk.Frame(self.main_frame, bg="lightgray")
        alert_frame.grid(row=0, column=1, padx=10, pady=10)

        tk.Label(alert_frame, text="Alerts (Overspeed)", font=("Arial", 12, "bold")).pack()
        self.alert_box = ScrolledText(alert_frame, width=50, height=12, font=("Consolas", 10), wrap=tk.WORD)
        self.alert_box.pack()

        tk.Label(alert_frame, text="Speed History", font=("Arial", 12, "bold")).pack(pady=(10, 0))
        self.history_box = ScrolledText(alert_frame, width=50, height=10, font=("Consolas", 10), wrap=tk.WORD)
        self.history_box.pack()

        button_frame = tk.Frame(self.main_frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=10)

        self.start_button = ttk.Button(button_frame, text="Start Detection", command=self.start_detection, width=20)
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(button_frame, text="Stop", command=self.stop_detection, width=20)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        self.reset_button = ttk.Button(button_frame, text="Reset", command=self.reset_logs, width=20)
        self.reset_button.pack(side=tk.LEFT, padx=5)

        self.cap = None
        self.previous_position = None
        self.previous_time = None
        self.running = False
        self.sms_sent_this_session = False

    def reset_logs(self):
        confirm = messagebox.askyesno("Confirm Reset", "Are you sure you want to reset the logs?")
        if confirm:
            self.alert_box.delete(1.0, tk.END)
            self.history_box.delete(1.0, tk.END)
            self.sms_sent_this_session = False

            # Clear CSV file
            if os.path.exists(CSV_FILE):
                with open(CSV_FILE, 'w') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Timestamp', 'Speed', 'Status', 'Exceeded_by'])

            # Delete all documents in Firestore
            docs = db.collection('speed_logs').stream()
            for doc in docs:
                db.collection('speed_logs').document(doc.id).delete()

    def start_detection(self):
        if not self.running:
            self.cap = cv2.VideoCapture(0)
            self.running = True
            self.status_label.config(text="Status: Active", fg="green")
            self.process_frame()

    def stop_detection(self):
        self.running = False
        if self.cap:
            self.cap.release()
            self.cap = None
        self.status_label.config(text="Status: Paused", fg="red")

    def log_speed_history(self, timestamp, speed, status, exceeded_by=""):
        msg = f"{timestamp} - {speed:.2f} km/h - {status}"
        if exceeded_by:
            msg += f" ({exceeded_by:.2f} km/h above limit)"
        msg += "\n"
        self.history_box.insert(tk.END, msg)
        self.history_box.see(tk.END)

        # Log to CSV
        with open(CSV_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, f"{speed:.2f}", status, f"{exceeded_by:.2f}" if exceeded_by else ""])

    def log_to_firestore(self, timestamp, speed, status, exceeded_by=""):
        doc_ref = db.collection('speed_logs').document()
        doc_ref.set({
            'timestamp': timestamp,
            'speed': speed,
            'status': status,
            'exceeded_by': exceeded_by
        })

    def process_frame(self):
        if not self.running:
            return

        ret, frame = self.cap.read()
        if not ret:
            return

        frame = cv2.flip(frame, 1)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, lower_blue, upper_blue)
        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        current_time = time.time()
        current_position = None

        if contours:
            largest = max(contours, key=cv2.contourArea)
            if cv2.contourArea(largest) > 500:
                x, y, w, h = cv2.boundingRect(largest)
                current_position = x + w // 2

                cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
                cv2.putText(frame, "Object Detected", (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

                if self.previous_position is not None and self.previous_time is not None:
                    time_elapsed = current_time - self.previous_time
                    speed = calculate_speed(self.previous_position, current_position, time_elapsed)

                    cv2.putText(frame, f"Speed: {speed:.2f} km/h", (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    if speed > SPEED_LIMIT:
                        exceeded_by = speed - SPEED_LIMIT
                        alert_msg = (f"[OVERSPEED] {timestamp} - Speed = {speed:.2f} km/h "
                                     f"({exceeded_by:.2f} km/h above limit)\n")
                        self.alert_box.insert(tk.END, alert_msg)
                        self.alert_box.see(tk.END)

                        self.log_speed_history(timestamp, speed, "OVERSPEED", exceeded_by)
                        self.log_to_firestore(timestamp, speed, "OVERSPEED", exceeded_by)

                        # Send SMS with speed
                        send_sms(speed)

                        cv2.putText(frame, "SLOW DOWN!", (10, 60),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
                    else:
                        self.log_speed_history(timestamp, speed, "NORMAL")
                        self.log_to_firestore(timestamp, speed, "NORMAL")

                self.previous_position = current_position
                self.previous_time = current_time

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        imgtk = ImageTk.PhotoImage(image=img)
        self.video_label.imgtk = imgtk
        self.video_label.configure(image=imgtk)

        self.root.after(10, self.process_frame)

# --- Run App ---
if __name__ == "__main__":
    # Clear CSV on startup
    with open(CSV_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Timestamp', 'Speed', 'Status', 'Exceeded_by'])

    # Clear Firebase logs on startup
    try:
        docs = db.collection('speed_logs').stream()
        for doc in docs:
            db.collection('speed_logs').document(doc.id).delete()
        print("Firebase 'speed_logs' cleared at startup.")
    except Exception as e:
        print(f"Error clearing Firebase: {e}")

    root = tk.Tk()
    app = SpeedDetectorApp(root)
    root.mainloop()
