from psychopy import visual, core, event
import socket
import json
import time
from datetime import datetime
import csv

from eyetribe_utils import start_eyetracker, stop_eyetracker


# === Configuration ===
IMAGE_DURATION = 5.0  # seconds
IMAGE_FILES = ['DSC_0002.JPG', 'DSC_0004.JPG']  # Replace with your image paths
WINDOW_SIZE = [1920, 1080]
OUTPUT_FILE = f'gaze_log_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.csv'

# === Connect to Eye Tribe ===
def connect_eyetribe():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('127.0.0.1', 6555))
    push_request = {"category": "tracker", "request": "set", "values": {"push": True}}
    sock.sendall((json.dumps(push_request) + "\n").encode('utf-8'))
    return sock

# === Receive gaze data ===
def get_gaze_data(sock):
    try:
        data = sock.recv(4096).decode('utf-8')
        obj = json.loads(data)
        frame = obj.get("values", {}).get("frame", {})
        avg = frame.get("avg", {})
        return time.time(), avg.get("x", None), avg.get("y", None)
    except:
        return time.time(), None, None

# === Save all logged gaze ===
def save_log(log):
    with open(OUTPUT_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'image', 'x', 'y', 'event'])
        writer.writerows(log)
    print(f"Gaze log saved to {OUTPUT_FILE}")

# === Main Experiment ===
def run_experiment():
    sock = connect_eyetribe()
    print("Connected to Eye Tribe.")

    win = visual.Window(WINDOW_SIZE, color='black', units='pix', fullscr=False)
    log = []

    for image_file in IMAGE_FILES:
        # Load image
        stim = visual.ImageStim(win, image=image_file)

        # Display image
        onset_time = time.time()
        print(f"Showing {image_file}")
        while time.time() - onset_time < IMAGE_DURATION:
            stim.draw()
            win.flip()

            ts, x, y = get_gaze_data(sock)
            log.append([ts, image_file, x, y, 'image_on'])

        # Short gap (optional)
        win.flip()
        core.wait(0.5)

    sock.close()
    win.close()
    save_log(log)

# Run it
if __name__ == "__main__":
    run_experiment()
