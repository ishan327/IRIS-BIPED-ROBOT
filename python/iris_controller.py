import cv2, socket, time, json, base64, threading, queue
import sounddevice as sd
from scipy.io.wavfile import write
import pyttsx3
import mediapipe as mp
from datetime import datetime
from groq import Groq

# --- CONFIGURATION ---
GROQ_API = "API KEY"
ESP32_IP = "192.168.1.68" 
PHONE_URL = "http://192.168.1.33:8080/video"  

client = Groq(api_key=GROQ_API)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# --- MEDIA PIPE FACE TRACKING ---
mp_face_detection = mp.solutions.face_detection.FaceDetection(min_detection_confidence=0.6)

# --- VIDEO THREAD (LAG KILLER) ---
class VideoStream:
    def __init__(self, src=PHONE_URL):
        self.stream = cv2.VideoCapture(src)
        self.ret, self.frame = self.stream.read()
        self.stopped = False
        threading.Thread(target=self.update, daemon=True).start()

    def update(self):
        while not self.stopped:
            self.ret, self.frame = self.stream.read()
            
    def read(self):
        return self.ret, self.frame
        
    def stop(self):
        self.stopped = True
        self.stream.release()

# --- AUDIO ENGINE ---
audio_queue = queue.Queue()
def audio_worker():
    tts = pyttsx3.init()
    tts.setProperty('rate', 160)
    while True:
        text = audio_queue.get()
        if text is None: break
        tts.say(text)
        tts.runAndWait()
        audio_queue.task_done()

threading.Thread(target=audio_worker, daemon=True).start()

# --- GLOBAL STATE ---
ai_state = "IDLE"
latest_frame = None
subtitle_text = "System Initialized."
tracking_mode = False
is_moving = False # Prevents overlapping move commands

print("\n" + "="*50)
print(" 🚀 IRIS V8.4: DISCRETE STEP & TRACKING AGENT")
print("="*50)
print("\n[ KEYBOARD CONTROLS ]")
print("  * CLICK the video window first to activate controls!")
print("  * W / S : Step Forward / Backward (0.3s)")
print("  * A / D : Step Left / Right (0.2s)")
print("  * T     : Toggle Face Tracking Mode")
print("  * SPACE : Voice Command Mode (Speak to AI)")
print("  * M     : Mood Analysis")
print("  * Q     : Quit System")
print("="*50 + "\n")

def send_cmd(cmd):
    try:
        sock.sendto(cmd.encode(), (ESP32_IP, 4210))
    except: pass

def speak(text):
    global ai_state, subtitle_text
    subtitle_text = text
    print(f"IRIS: {text}")
    audio_queue.put(text)
    ai_state = "IDLE"

def encode_image(img):
    _, buffer = cv2.imencode('.jpg', img)
    return base64.b64encode(buffer).decode('utf-8')

# --- DISCRETE MOVEMENT LOGIC (NASA STYLE) ---
def discrete_move(direction, duration):
    global is_moving
    if is_moving: return
    is_moving = True
    send_cmd(direction)
    time.sleep(duration)
    send_cmd('S')
    is_moving = False

# --- HEAVY AI THREAD ---
def ai_worker_thread(task_type, frame_snapshot):
    global ai_state
    send_cmd('Z') 
    
    try:
        if task_type == "MOOD":
            ai_state = "ANALYZING MOOD"
            encoded = encode_image(frame_snapshot)
            prompt = "Look at the person. Output JSON: {'speech': 'A short empathetic sentence reacting to their mood.'}"
            res = client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}}]}],
                response_format={"type": "json_object"}
            )
            speak(json.loads(res.choices[0].message.content).get("speech", ""))

        elif task_type == "COMMAND":
            ai_state = "LISTENING (Speak Now)"
            print("\n>> Listening for 4 seconds...")
            audio = sd.rec(int(4 * 44100), samplerate=44100, channels=1)
            sd.wait()
            write('cmd.wav', 44100, audio)
            
            ai_state = "TRANSCRIBING"
            with open('cmd.wav', "rb") as file:
                user_text = client.audio.transcriptions.create(file=("cmd.wav", file.read()), model="whisper-large-v3").text.strip()
            
            print(f">> You said: '{user_text}'")
            ai_state = "THINKING"
            
            # --- THE FEW-SHOT MASTER PROMPT ---
            prompt = f"""
            You are the central intelligence core for IRIS, an advanced robotics system built by ISHAN.
            Your job is to read the User Request and translate it into a STRICT JSON command object.

            AVAILABLE COMMANDS:
            * 'F' (Forward), 'B' (Backward), 'L' (Left), 'R' (Right)

            RULES FOR PARSING:
            1. GENERAL CHAT: If the user asks a general question ("How are you?", "What is your name?", "Tell me a fact"), answer naturally in the "speech" field. Leave the "sequence" array completely empty. Set all booleans to false.
            2. MOVEMENT: If the user asks to move, populate the "sequence" array. Map directions to F, B, L, R. If a specific time is given (e.g., "for 5 seconds"), use it. If no time is given, default to 1.0. Do not add movements unless explicitly requested.
            3. PHOTOGRAPHY: If the user explicitly asks to take a photo, capture an image, or save a picture, set "take_photo" to true. 
            4. VISION / SIGHT: If the user asks what you see, or asks you to identify an object in front of you, set "vision_req" to true, and write their specific question into "vision_prompt". 
            5. MULTI-TASKING: You can combine these commands safely. If the user says "Move forward for 2 seconds and take a photo", populate the sequence AND set take_photo to true.

            EXAMPLES OF CORRECT BEHAVIOR:
            
            User: "Hey IRIS, how are you today?"
            JSON: {{"speech": "I am functioning perfectly. All systems are nominal.", "sequence": [], "take_photo": false, "vision_req": false, "vision_prompt": ""}}

            User: "Move forward for 4 seconds, then turn left."
            JSON: {{"speech": "Moving forward and turning left.", "sequence": [{{"cmd": "F", "time": 4.0}}, {{"cmd": "L", "time": 1.0}}], "take_photo": false, "vision_req": false, "vision_prompt": ""}}

            User: "Take a picture of me."
            JSON: {{"speech": "Initializing camera sequence.", "sequence": [], "take_photo": true, "vision_req": false, "vision_prompt": ""}}

            User: "Turn right for 2 seconds and tell me what you see."
            JSON: {{"speech": "Turning right to scan the area.", "sequence": [{{"cmd": "R", "time": 2.0}}], "take_photo": false, "vision_req": true, "vision_prompt": "Describe what is in front of you in detail."}}

            User Requested: "{user_text}"
            OUTPUT STRICTLY RAW JSON ONLY. NO MARKDOWN FORMATTING. NO EXTRA TEXT.
            """
            
            res = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0, # Keeps the AI highly logical and predictable
                response_format={"type": "json_object"}
            )
            
            data = json.loads(res.choices[0].message.content)
            speak(data.get("speech", "Processing command."))
            
            # --- EXECUTION LOOP ---
            global is_moving
            for action in data.get("sequence", []):
                cmd = action.get("cmd", "S")
                # Cap the maximum duration at 15 seconds to prevent runaway motors
                duration = min(float(action.get("time", 1.0)), 15.0) 
                
                if cmd in ['F', 'B', 'L', 'R']:
                    is_moving = True
                    send_cmd(cmd)
                    time.sleep(duration)
                    send_cmd('S')
                    is_moving = False
                    time.sleep(0.2) # Short mechanical pause between connected moves
            
            if data.get("take_photo"):
                # 3-Second Visual & Audio Countdown
                speak("Taking picture in 3")
                time.sleep(1)
                speak("2")
                time.sleep(1)
                speak("1")
                time.sleep(1)
                send_cmd('Z') # Flash buzzer like a camera shutter
                
                filename = f"IRIS_Capture_{int(time.time())}.jpg"
                cv2.imwrite(filename, latest_frame) # Takes a fresh frame after countdown
                speak(f"Image successfully saved.")
                
            if data.get("vision_req"):
                ai_state = "ANALYZING VISUALLY"
                encoded = encode_image(frame_snapshot)
                v_prompt = f"Answer this query based on the image: {data.get('vision_prompt')}. Output JSON: {{'speech': 'Your specific answer'}}"
                v_res = client.chat.completions.create(
                    model="meta-llama/llama-4-scout-17b-16e-instruct",
                    messages=[{"role": "user", "content": [{"type": "text", "text": v_prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}}]}],
                    response_format={"type": "json_object"}
                )
                speak(json.loads(v_res.choices[0].message.content).get("speech", ""))

    except Exception as e:
        print(f"Error: {e}")
        speak("My neural link failed to process the request.")
    
    ai_state = "IDLE"

# --- MAIN VIDEO LOOP ---
cam = VideoStream(PHONE_URL) 
cv2.namedWindow("IRIS HUD")

while True:
    ret, frame = cam.read()
    if not ret or frame is None: 
        time.sleep(0.1)
        continue
    
    frame = cv2.resize(frame, (800, 600))
    latest_frame = frame.copy()
    
    # --- FACE TRACKING LOGIC ---
    if tracking_mode and ai_state == "IDLE" and not is_moving:
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = mp_face_detection.process(rgb_frame)
        if results.detections:
            bboxC = results.detections[0].location_data.relative_bounding_box
            cx = bboxC.xmin + bboxC.width / 2
            
            # Draw tracking box
            cv2.circle(frame, (int(cx * 800), int((bboxC.ymin + bboxC.height/2) * 600)), 10, (0, 0, 255), -1)
            cv2.putText(frame, "TRACKING LOCK", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Autonomously center the robot
            if cx < 0.40: # Face is on the left
                threading.Thread(target=discrete_move, args=('L', 0.15)).start()
            elif cx > 0.60: # Face is on the right
                threading.Thread(target=discrete_move, args=('R', 0.15)).start()

    # --- DRAW HUD ---
    time_str = datetime.now().strftime("%I:%M:%S %p")
    cv2.putText(frame, f"TIME: {time_str}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    cv2.putText(frame, f"STATE: {ai_state}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0) if ai_state == "IDLE" else (0, 0, 255), 2)
    if tracking_mode:
        cv2.putText(frame, "AUTONOMOUS TRACKING: ON", (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    
    # Subtitles Box
    cv2.rectangle(frame, (0, 550), (800, 600), (0, 0, 0), -1)
    cv2.putText(frame, f"IRIS: {subtitle_text}", (20, 580), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    
    cv2.imshow("IRIS HUD", frame)
    
    # --- KEYBOARD CONTROLS ---
    key = cv2.waitKey(1) & 0xFF
    if key != 255: 
        char_key = chr(key).lower()
        
        # AI Triggers
        if char_key == ' ' and ai_state == "IDLE":
            threading.Thread(target=ai_worker_thread, args=("COMMAND", latest_frame.copy())).start()
        elif char_key == 'm' and ai_state == "IDLE":
            threading.Thread(target=ai_worker_thread, args=("MOOD", latest_frame.copy())).start()
        elif char_key == 't':
            tracking_mode = not tracking_mode
            speak(f"Tracking mode {'activated' if tracking_mode else 'deactivated'}.")
            
        # Discrete Manual Drive
        elif char_key == 'w' and not is_moving:
            threading.Thread(target=discrete_move, args=('F', 0.3)).start()
        elif char_key == 's' and not is_moving:
            threading.Thread(target=discrete_move, args=('B', 0.3)).start()
        elif char_key == 'a' and not is_moving:
            threading.Thread(target=discrete_move, args=('L', 0.2)).start()
        elif char_key == 'd' and not is_moving:
            threading.Thread(target=discrete_move, args=('R', 0.2)).start()
            
        elif char_key == 'q':
            break

# Cleanup
send_cmd('S')
cam.stop()
audio_queue.put(None)
cv2.destroyAllWindows()
