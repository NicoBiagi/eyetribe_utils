from psychopy import visual, core, event
import threading
import socket
import json
import time
from eyetribe_utils import start_eyetracker, stop_eyetracker

# Shared gaze variable
current_gaze = {"x": None, "y": None}
recording = True

def gaze_stream(sock, screen_width, screen_height):
    global current_gaze
    buffer = ""
    decoder = json.JSONDecoder()
    
    print(f"Starting gaze stream thread with screen dimensions: {screen_width}x{screen_height}")

    while recording:
        try:
            data = sock.recv(4096).decode('utf-8', errors='replace')
            if data:
                print(f"Received data length: {len(data)} bytes")
            buffer += data.strip()

            while buffer:
                try:
                    obj, idx = decoder.raw_decode(buffer)
                    buffer = buffer[idx:].lstrip()
                    
                    print(f"Decoded JSON object: {obj}")

                    frame = obj.get("values", {}).get("frame", {})
                    avg = frame.get("avg", {})
                    x, y = avg.get("x"), avg.get("y")
                    
                    print(f"Extracted x={x}, y={y} from frame data")

                    if isinstance(x, (float, int)) and isinstance(y, (float, int)):
                        print(f"Valid gaze coordinates: x={x}, y={y}")
                        
                        # Store raw pixel coordinates without conversion
                        if 0 <= x <= screen_width and 0 <= y <= screen_height:
                            current_gaze["x"] = int(x)
                            current_gaze["y"] = int(y)
                            print(f"Updated current gaze to: x={current_gaze['x']}, y={current_gaze['y']}")
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {e}")
                    # If we can't decode the buffer now, keep the last 1000 characters
                    # in case we're in the middle of a JSON object
                    if len(buffer) > 1000:
                        buffer = buffer[-1000:]
                    break
        except Exception as e:
            print(f"[gaze_stream error] {e}")
            time.sleep(0.1)  # Add small delay to prevent tight loop in case of error

def main():
    global recording

    print("Starting Eye Tribe gaze tracking application...")
    
    # Connect to Eye Tribe
    print("Attempting to connect to Eye Tribe tracker...")
    sock = start_eyetracker()
    if not sock:
        print("Failed to connect to the Eye Tribe tracker")
        return
    print("Successfully connected to Eye Tribe tracker")

    # Create PsychoPy window (fullscreen)
    print("Creating PsychoPy window...")
    win = visual.Window(
        size=(1920, 1080),
        fullscr=True,
        monitor="testMonitor",
        units="pix",
        color=(0, 0, 0)  # Black background (0 in RGB scale)
    )
    
    # Get actual window size
    screen_width, screen_height = win.size
    print(f"Window created with size: {screen_width}x{screen_height}")
    
    # Create gaze point indicator
    gaze_point = visual.Circle(
        win=win,
        radius=15,
        fillColor='red',
        lineColor=None,
        autoLog=False
    )
    print("Created gaze point indicator")
    
    # Start gaze streaming in a thread
    print("Starting gaze stream thread...")
    thread = threading.Thread(target=gaze_stream, args=(sock, screen_width, screen_height), daemon=True)
    thread.start()
    print("Gaze stream thread started")

    # Calibration markers
    roi_radius = 10
    
    # Calculate positions in raw pixel coordinates
    rois = [
        (screen_width // 2, screen_height // 2),  # Center
        (screen_width // 4, screen_height // 4),  # Top left
        (3 * screen_width // 4, screen_height // 4),  # Top right
        (screen_width // 4, 3 * screen_height // 4),  # Bottom left
        (3 * screen_width // 4, 3 * screen_height // 4)  # Bottom right
    ]
    print(f"Created calibration markers at positions: {rois}")
    
    # Create calibration marker stimuli
    calibration_markers = []
    for pos in rois:
        # Convert from raw pixel coordinates to PsychoPy coordinates
        # In PsychoPy with units='pix', (0,0) is the center
        psychopy_x = pos[0] - screen_width // 2
        psychopy_y = screen_height // 2 - pos[1]
        
        marker = visual.Circle(
            win=win,
            pos=(psychopy_x, psychopy_y),
            radius=roi_radius,
            lineColor='green',
            lineWidth=2,
            fillColor=None,
            autoLog=False
        )
        calibration_markers.append(marker)
    
    # Instructions text
    instructions = visual.TextStim(
        win=win,
        text="Press ENTER to exit",
        pos=(0, -screen_height//2 + 30),  # Bottom of screen
        color='white',
        height=20,
        autoLog=False
    )

    print("Press ENTER to exit.")
    
    # For FPS calculation
    fps_counter = 0
    fps_timer = time.time()
    
    # Main loop
    frame_count = 0
    while not event.getKeys(keyList=['return', 'escape']):
        frame_count += 1
        
        # Print debug info every 60 frames
        debug_frame = frame_count % 60 == 0
        
        # Draw calibration markers
        for marker in calibration_markers:
            marker.draw()
            
        # Get current gaze
        x, y = current_gaze["x"], current_gaze["y"]
        
        # Print debug info
        if debug_frame:
            print(f"Frame {frame_count}: Current gaze data: x={x}, y={y}")
            
        # Draw gaze point if available
        if x is not None and y is not None:
            # Convert from raw pixel coordinates to PsychoPy coordinates
            psychopy_x = x - screen_width // 2
            psychopy_y = screen_height // 2 - y
            
            if debug_frame:
                print(f"Drawing gaze point at PsychoPy coordinates: x={psychopy_x}, y={psychopy_y}")
                
            gaze_point.pos = (psychopy_x, psychopy_y)
            gaze_point.draw()
        elif debug_frame:
            print("No gaze data available to display")
        
        # Draw instructions
        instructions.draw()
        
        # Update display
        win.flip()
        
        # Calculate FPS every 100 frames
        fps_counter += 1
        if fps_counter >= 100:
            current_time = time.time()
            fps = fps_counter / (current_time - fps_timer)
            print(f"FPS: {fps:.2f}")
            fps_counter = 0
            fps_timer = current_time
            
        # Maintain refresh rate
        core.wait(1/60.0)

    # Cleanup
    print("Exiting application...")
    recording = False
    print("Stopping eye tracker...")
    stop_eyetracker(sock)
    print("Closing window...")
    win.close()
    core.quit()
    print("Exited successfully.")

# Call main function directly
main()