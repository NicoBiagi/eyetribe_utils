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
            "right_psize": righteye.get("psize", ""),
            "message": ""  # Add empty message field for eye data rows
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

# This function is maintained for backward compatibility
# but is not needed with the new EyeTrackingRecorder class
def send_message(csv_writer, message_content):
    """
    Sends a message that will be recorded in the CSV file.
    
    Args:
        csv_writer: The CSV writer object to write the message
        message_content: Content of the message (e.g., "Stimulus ON")
    
    Returns:
        Dictionary with the message row that was written to the CSV
    """
    message_row = {
        "timestamp": time.time(),
        "x": "",
        "y": "",
        "fix": "",
        "state": "",
        "left_psize": "",
        "right_psize": "",
        "message": message_content
    }
    
    if csv_writer:
        csv_writer.writerow(message_row)
        print(f"Message recorded: {message_content}")
    
    return message_row

class EyeTrackingRecorder:
    """
    Class for continuous eye tracking data recording with the ability to send messages.
    """
    def __init__(self, sock, output_file=None):
        """
        Initialize the eye tracking recorder.
        
        Args:
            sock: Socket connected to the Eye Tribe server
            output_file: File to save the data (auto-generated if None)
        """
        self.sock = sock
        if self.sock is None:
            raise ValueError("[ERROR] No valid socket provided.")
            
        if output_file is None:
            timestamp_str = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            output_file = f'gaze_data_{timestamp_str}.csv'
        self.output_file = output_file
        
        self.csv_file = None
        self.writer = None
        self.is_recording = False
        self.recording_thread = None
        self.buffer = ""
        self.decoder = json.JSONDecoder()
        self.all_rows = []
        
    def start_recording(self):
        """
        Start recording eye tracking data continuously until stop_recording is called.
        """
        if self.is_recording:
            print("[WARNING] Recording is already in progress.")
            return False
            
        import threading
        
        self.csv_file = open(self.output_file, mode='w', newline='', encoding='utf-8')
        self.writer = csv.DictWriter(self.csv_file, fieldnames=[
            "timestamp", "x", "y", "fix", "state", "left_psize", "right_psize", "message"
        ])
        self.writer.writeheader()
        
        self.is_recording = True
        self.recording_thread = threading.Thread(target=self._record_loop)
        self.recording_thread.daemon = True
        self.recording_thread.start()
        
        print(f"Recording started. Data will be saved to: {self.output_file}")
        return True
        
    def _record_loop(self):
        """
        Internal method for continuous data recording.
        """
        self.sock.settimeout(0.1)  # Small timeout to check is_recording flag
        
        try:
            while self.is_recording:
                try:
                    data = self.sock.recv(4096).decode('utf-8', errors='replace')
                    self.buffer += data.strip()
                    
                    while self.buffer:
                        try:
                            obj, idx = self.decoder.raw_decode(self.buffer)
                            self.buffer = self.buffer[idx:].lstrip()
                            
                            # Parse and write eye tracking data
                            parsed_row = parse_chunk(obj)
                            if parsed_row and self.writer:
                                self.writer.writerow(parsed_row)
                                self.all_rows.append(parsed_row)
                                
                        except json.JSONDecodeError:
                            # Incomplete JSON, wait for next recv()
                            break
                except socket.timeout:
                    # Just a timeout to allow checking the is_recording flag
                    continue
                except Exception as e:
                    print(f"[ERROR] Socket read error: {e}")
                    if self.is_recording:
                        # Only break the loop if we're still supposed to be recording
                        break
        
        except Exception as e:
            print(f"[ERROR] Recording error: {e}")
        
        print("Recording thread stopped.")
        
    def send_message(self, message_content):
        """
        Send a message that will be recorded in the CSV file.
        
        Args:
            message_content: Content of the message (e.g., "Stimulus ON")
            
        Returns:
            True if message was sent successfully, False otherwise
        """
        if not self.is_recording or not self.writer:
            print("[ERROR] Recording not active. Start recording before sending messages.")
            return False
            
        message_row = {
            "timestamp": time.time(),
            "x": "",
            "y": "",
            "fix": "",
            "state": "",
            "left_psize": "",
            "right_psize": "",
            "message": message_content
        }
        
        self.writer.writerow(message_row)
        self.all_rows.append(message_row)
        print(f"Message recorded: {message_content}")
        return True
        
    def stop_recording(self):
        """
        Stop the recording and close the CSV file.
        
        Returns:
            List of all recorded rows
        """
        if not self.is_recording:
            print("[WARNING] No recording in progress.")
            return self.all_rows
            
        self.is_recording = False
        
        if self.recording_thread:
            self.recording_thread.join(timeout=2.0)
            
        if self.csv_file:
            self.csv_file.close()
            self.csv_file = None
            self.writer = None
            
        print(f"Recording stopped. Total rows recorded: {len(self.all_rows)}")
        return self.all_rows


# Legacy function for backward compatibility
def record_eye_data(sock, duration=10, output_file=None):
    """
    Records gaze data for `duration` seconds from the provided Eye Tribe socket.
    Saves to CSV and returns parsed rows.
    
    Note: This is maintained for backward compatibility.
    Consider using EyeTrackingRecorder class for more control.
    """
    print("[DEPRECATED] Using fixed-duration recording. Consider using EyeTrackingRecorder instead.")
    
    if sock is None:
        print("[ERROR] No socket provided.")
        return []
        
    recorder = EyeTrackingRecorder(sock, output_file)
    recorder.start_recording()
    
    # Wait for the specified duration
    time.sleep(duration)
    
    return recorder.stop_recording()