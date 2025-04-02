import socket
import json
import csv

HOST = '127.0.0.1'
PORT = 6555
OUTPUT_FILE = 'parsed_gaze_data.csv'

def parse_chunk(chunk):
    try:
        obj = json.loads(chunk)
        frame = obj.get("values", {}).get("frame", {})
        avg = frame.get("avg", {})
        lefteye = frame.get("lefteye", {})
        righteye = frame.get("righteye", {})

        return {
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

def main():
    raw_chunks = []

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((HOST, PORT))
        print("Connected to Eye Tribe server.")

        push_request = {
            "category": "tracker",
            "request": "set",
            "values": {"push": True}
        }
        sock.sendall(json.dumps(push_request).encode('utf-8') + b'\n')
        print("Requested push mode.")
        print("Recording data... (Press Ctrl+C to stop)\n")

        while True:
            data = sock.recv(4096)
            if not data:
                continue

            decoded = data.decode('utf-8', errors='replace')
            print("Raw data chunk:")
            print(decoded)
            raw_chunks.extend([chunk for chunk in decoded.strip().split('\n') if chunk.strip()])

    except KeyboardInterrupt:
        print("\nRecording stopped.")
    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        sock.close()

    print(f"\nTotal chunks recorded: {len(raw_chunks)}")
    print("Parsing and saving to CSV...")

    parsed_rows = [parse_chunk(chunk) for chunk in raw_chunks]
    parsed_rows = [row for row in parsed_rows if row is not None]

    with open(OUTPUT_FILE, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["x", "y", "fix", "state", "left_psize", "right_psize"])
        writer.writeheader()
        writer.writerows(parsed_rows)

    print(f"Done. Parsed data saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
