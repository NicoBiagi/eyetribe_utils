from psychopy import visual, core, event, gui
import socket
import json
import time
from datetime import datetime
import csv
import os

from eyetribe_utils import start_eyetracker, stop_eyetracker

# === Configuration ===
IMAGE_DURATION = 5.0  # seconds
IMAGE_FILES = ['DSC_0038.JPG', 'DSC_0004.JPG']
WINDOW_SIZE = [1920, 1080]

# === Prompt for participant ID ===
info = {'Participant ID': ''}
dlg = gui.DlgFromDict(info, title='Gaze Experiment')
if not dlg.OK:
    core.quit()
participant_id = info['Participant ID']

# Use the folder of the first image to save the CSV file
image_folder = os.path.dirname(IMAGE_FILES[0]) or '.'
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
output_file = os.path.join(image_folder, f'gaze_log_{participant_id}_{timestamp}.csv')

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

# === Save gaze log ===
def save_log(log):
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'image', 'x', 'y', 'event'])
        writer.writerows(log)
    print(f"Gaze log saved to {output_file}")

# === Main Experiment ===
def run_experiment():
    sock = connect_eyetribe()
    print("Connected to Eye Tribe.")

    win = visual.Window(WINDOW_SIZE, color='black', units='pix', fullscr=True)
    # Show the cursor again
    win.mouseVisible = False
    log = []

    # Instructions
    instructions = visual.TextStim(win, text="In this task, you will view a series of images.\n\nPlease keep your eyes on the screen.\n\nPress any key to begin.", color='white')
    instructions.draw()
    win.flip()
    event.waitKeys()

    fixation = visual.TextStim(win, text="+", color='white', height=50)

    for image_file in IMAGE_FILES:
        # Fixation cross before
        fixation.draw()
        win.flip()
        core.wait(1.0)

        # Display image
#        stim = visual.ImageStim(win, image=image_file)
        stim = visual.ImageStim(win, image=image_file, units='pix')
        iw, ih = stim.size  # native image size
        scale_factor = 0.8  # scale image to 80% of screen height
        
        # Calculate new size while preserving aspect ratio
        screen_h = WINDOW_SIZE[1]
        new_h = screen_h * scale_factor
        new_w = iw * (new_h / ih)
        
        stim.size = (new_w, new_h)

        onset_time = time.time()
        print(f"Showing {image_file}")
        while time.time() - onset_time < IMAGE_DURATION:
            stim.draw()
            win.flip()
            ts, x, y = get_gaze_data(sock)
            log.append([ts, image_file, x, y, 'image_on'])

        # Fixation cross after
        fixation.draw()
        win.flip()
        core.wait(1.0)

    # Goodbye message
    goodbye = visual.TextStim(win, text="Thank you for participating!\n\nYou may now close the experiment.", color='white')
    goodbye.draw()
    win.flip()
    core.wait(3.0)

    sock.close()
    win.close()
    save_log(log)

# Run the experiment immediately
run_experiment()
# Show the cursor again
win.mouseVisible = True
