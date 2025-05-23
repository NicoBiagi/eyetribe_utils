from psychopy import visual, core, event, gui
from new_eyetribe_utils import start_eyetracker, stop_eyetracker, EyeTrackingRecorder
import os
import glob

# === Get Participant Info ===
info = {'Participant ID': ''}
dlg = gui.DlgFromDict(dictionary=info, title='Participant Info')
if not dlg.OK:
    core.quit()
participant_id = info['Participant ID']

# === Setup Window on Second Monitor and Hide Cursor ===
win = visual.Window(
    size=[1920, 1080],
    screen=1,
    color='grey',
    units='pix',
    fullscr=True
)
win.mouseVisible = False

# === Get All JPG Files in the Current Folder ===
image_files = sorted(glob.glob("*.JPG"))  # Change to *.jpg if files are lowercase
if not image_files:
    print("No JPG files found in the current folder.")
    core.quit()

# === Connect to Eye Tribe and Prepare Recorder ===
sock = start_eyetracker()
if sock is None:
    print("Eye tracker connection failed.")
    core.quit()

output_filename = f'gaze_{participant_id}.csv'
recorder = EyeTrackingRecorder(sock, output_file=output_filename)
recorder.start_recording()

# === Welcome Message ===
welcome = visual.TextStim(win, text="Welcome to the experiment.\n\nPress any key to continue.", height=30, color='white')
welcome.draw()
win.flip()
event.waitKeys()

# === Instructions ===
instructions = visual.TextStim(win, text="You will see a series of images.Each image will be shown for 5 seconds.\n\nPlease keep your eyes on the screen.\n\nPress any key to begin.", height=30, color='white')
instructions.draw()
win.flip()
event.waitKeys()

# === Fixation Cross ===
fixation = visual.TextStim(win, text='+', height=40, color='white')

# === Run Trials ===
for image_path in image_files:
    img_stim = visual.ImageStim(win, image=image_path)
    
    # Pre-trial fixation
    fixation.draw()
    win.flip()
    core.wait(1)

    # Present image
    recorder.send_message(f"IMAGE {image_path} ON")
    img_stim.draw()
    win.flip()
    core.wait(5)
    recorder.send_message(f"IMAGE {image_path} OFF")

    # Post-trial fixation
    fixation.draw()
    win.flip()
    core.wait(1)

# === Goodbye Message ===
goodbye = visual.TextStim(win, text='This is the end of the task. \n\nThank you!', height=30, color='white')
goodbye.draw()
win.flip()
core.wait(2)

# === Cleanup ===
recorder.stop_recording()
stop_eyetracker(sock)
win.close()
core.quit()
