import socket
import json
import csv
import time
from datetime import datetime

def parse_chunk(chunk):
    try:
        obj = chunk  # chunk is already a dictionary now
        frame = obj.get("values", {}).get("frame", {})
        avg = frame.get("avg", {})
        lefteye = frame.get("lefteye", {})
        righteye = frame.get("righteye", {})

        return {
            "timestamp": time.time(),
            "x": avg.get("x", ""),
            "y": avg.get("y", ""),
            "fix": frame.get("fix", ""),
            "state": frame.get("state", ""),
            "left_psize": lefteye.get("psize", ""),
            "right_psize": righteye.get("psize", "")
        }
    except Exception as e:
        print(f"[PARSE ERROR] Skipping chunk: {e}")
        return None


def start_eyetracker():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('127.0.0.1', 6555))
        print("Connected to Eye Tribe server.")

        push_request = {
            "category": "tracker",
            "request": "set",
            "values": {"push": True}
        }
        message = json.dumps(push_request).encode('utf-8') + b'\n'
        sock.sendall(message)
        print("Push mode enabled.")
        return sock
    except Exception as e:
        print(f"[ERROR] Failed to connect to Eye Tribe: {e}")
        return None

def stop_eyetracker(sock):
    if sock:
        sock.close()
        print("Eye Tribe connection closed.")

def record_eye_data(sock, duration=10, output_file=None):
    """
    Records gaze data for `duration` seconds from the provided Eye Tribe socket.
    Saves to CSV and returns parsed rows.
    """
    if sock is None:
        print("[ERROR] No socket provided.")
        return []

    if output_file is None:
        timestamp_str = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        output_file = f'gaze_data_{timestamp_str}.csv'

    raw_chunks = []
    start_time = time.time()
    buffer = ""
    decoder = json.JSONDecoder()

    try:
        while time.time() - start_time < duration:
            data = sock.recv(4096).decode('utf-8', errors='replace')
            print(data)
            buffer += data.strip()

            while buffer:
                try:
                    obj, idx = decoder.raw_decode(buffer)
                    # json_str = json.dumps(obj)
                    # raw_chunks.append(json_str)
                    raw_chunks.append(obj)
                    buffer = buffer[idx:].lstrip()
                except json.JSONDecodeError:
                    # Incomplete JSON, wait for next recv()
                    break

    except Exception as e:
        print(f"[ERROR] Data recording error: {e}")

    print(f"Total raw chunks recorded: {len(raw_chunks)}")

    parsed_rows = [parse_chunk(chunk) for chunk in raw_chunks]
    parsed_rows = [row for row in parsed_rows if row is not None]

    with open(output_file, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            "timestamp", "x", "y", "fix", "state", "left_psize", "right_psize"
        ])
        writer.writeheader()
        writer.writerows(parsed_rows)

    print(f"Gaze data saved to: {output_file}")
    return parsed_rows


