🚗 Speed Detection System with GUI, Firebase & Twilio Alerts

A real-time speed monitoring and alerting system using OpenCV, Tkinter, Firebase Firestore, and Twilio. This application is designed to simulate speed detection of moving objects using a blue-colored object (e.g., a book or toy), log data locally and on Firebase, and send SMS alerts if speed exceeds a defined limit.

Features
--------
- Real-time speed detection using a webcam  
- Tkinter GUI for user-friendly interaction  
- Blue object tracking with OpenCV and HSV masking  
- Speed calculation using pixel displacement over time  
- Alert system:  
  - Alerts in GUI when speed exceeds the defined limit  
  - SMS alerts via Twilio for overspeeding  
- Firebase Firestore integration:  
  - Stores each speed log (timestamp, speed, status, etc.)  
  - Clears previous logs on startup or reset  
- CSV logging for offline speed history  
- Reset functionality to clear GUI, Firebase, and CSV logs  

Technologies Used
-----------------
- Python  
- OpenCV  
- Tkinter  
- Firebase Firestore  
- Twilio API for SMS  
- PIL (Pillow)  
- NumPy  

Object Detection Note
---------------------
This project uses a blue-colored object instead of a real car.  
To simulate movement, wave a blue object (like a book or card) in front of your webcam.

How to Change Object Color:
---------------------------
If you want to track other colors (like red, green, yellow), modify the HSV range in the code:

```python
# In your code (speed_gui.py), look for:
lower_blue = np.array([100, 150, 0])
upper_blue = np.array([140, 255, 255])

# Change to red for example:
lower_red = np.array([0, 150, 50])
upper_red = np.array([10, 255, 255])
```

To Detect Real Cars:
--------------------
You can replace the color tracking logic with object detection using pre-trained models like:

```bash
pip install ultralytics
```

Then, integrate YOLOv8:

```python
from ultralytics import YOLO
model = YOLO("yolov8n.pt")
results = model(source=frame)
```

Filter for `car` class from detections and use bounding box center for speed.

GUI Overview
------------
- Live webcam feed  
- Status label (Active / Paused)  
- Overspeed alerts panel  
- Speed history panel  
- Start, Stop, and Reset buttons  

How Speed is Calculated
------------------------
```
Speed (km/h) = (pixel_distance / reference_distance) / time_elapsed * 3.6
```
- Reference distance is a manually assumed value (~100 px)  
- Displacement is calculated based on object center x position  

How to Run
----------
1. Install dependencies:

```bash
pip install opencv-python firebase-admin twilio pillow numpy
```

2. Add Firebase credentials:

```bash
# Place your credentials file and rename:
mv path_to_your_key.json firebase_credentials.json
```

3. Configure Twilio in the script:
- Add your:
  - account SID
  - auth token
  - verified Twilio number
  - recipient phone number

4. Run the application:

```bash
python speed_gui.py
```

File Structure
--------------
```
.
├── firebase_credentials.json   Firebase credentials  
├── speed_log.csv               Auto-generated CSV for logs  
├── speed_gui.py                Main application  
```

Safety & Privacy
----------------
- Only test with verified Twilio numbers  
- Never expose Twilio or Firebase credentials publicly  
- Not intended for real traffic enforcement use  

To Do / Enhancements
--------------------
- Adjustable reference distance calibration  
- Speed analytics dashboard  
- Save video clips on overspeed events  
- Email alerts support  
- Track other object colors or use YOLO for car detection  

Author
------
T Hrashikesh Padiyar  
