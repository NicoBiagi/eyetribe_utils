import pygame
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

    while recording:
        try:
            data = sock.recv(4096).decode('utf-8', errors='replace')
            buffer += data.strip()

            while buffer:
                try:
                    obj, idx = decoder.raw_decode(buffer)
                    buffer = buffer[idx:].lstrip()

                    frame = obj.get("values", {}).get("frame", {})
                    avg = frame.get("avg", {})
                    x, y = avg.get("x"), avg.get("y")

                    if isinstance(x, (float, int)) and isinstance(y, (float, int)):
                        if 0 <= x <= screen_width and 0 <= y <= screen_height:
                            current_gaze["x"] = int(x)
                            current_gaze["y"] = int(y)
                except json.JSONDecodeError:
                    break
        except Exception as e:
            print(f"[gaze_stream error] {e}")
            break

def main():
    global recording

    # Connect to Eye Tribe
    sock = start_eyetracker()
    if not sock:
        return

    # Get screen resolution
    pygame.init()
    info = pygame.display.Info()
    screen_width, screen_height = info.current_w, info.current_h
    screen = pygame.display.set_mode((screen_width, screen_height), pygame.FULLSCREEN)
    pygame.display.set_caption("Gaze Tracker")
    clock = pygame.time.Clock()

    # Start gaze streaming in a thread
    thread = threading.Thread(target=gaze_stream, args=(sock, screen_width, screen_height), daemon=True)
    thread.start()

    # Calibration markers
    roi_radius = 10
    rois = [
        (screen_width // 2, screen_height // 2),
        (screen_width // 4, screen_height // 4),
        (3 * screen_width // 4, screen_height // 4),
        (screen_width // 4, 3 * screen_height // 4),
        (3 * screen_width // 4, 3 * screen_height // 4),
    ]

    print("Press ENTER to exit.")
    running = True
    while running:
        screen.fill((0, 0, 0))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                running = False

        # Draw calibration markers
        for roi in rois:
            pygame.draw.circle(screen, (0, 255, 0), roi, roi_radius, 2)

        # Draw gaze point
        x, y = current_gaze["x"], current_gaze["y"]
        if x is not None and y is not None:
            pygame.draw.circle(screen, (255, 0, 0), (x, y), 15)

        pygame.display.flip()
        clock.tick(60)

    # Cleanup
    recording = False
    stop_eyetracker(sock)
    pygame.quit()
    print("Exited successfully.")

if __name__ == "__main__":
    main()
