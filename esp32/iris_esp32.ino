#include <WiFi.h>
#include <WiFiUdp.h>
#include <ESP32Servo.h>

// --- NETWORK CONFIGURATION ---
const char* ssid     = "wifi_ssid";     
const char* password = "password"; 
const int localPort  = 4210;                 

WiFiUDP udp;
char packetBuffer[255]; 

// --- PIN CONFIGURATION ---
const int RF_PIN = 14;  // Right Foot
const int LF_PIN = 25;  // Left Foot
const int RH_PIN = 27;  // Right Hip
const int LH_PIN = 26;  // Left Hip

Servo rightFoot;
Servo leftFoot;
Servo rightHip;
Servo leftHip;

// --- GEOMETRY VARIATION RULES ---
const int SERVO_CENTER = 90; 
const int FOOT_TOE     = 120; // ++ configuration
const int FOOT_HEEL    = 60;  // -- configuration
const int HIP_RIGHT    = 120; // ++ configuration
const int HIP_LEFT     = 60;  // -- configuration

bool forwardStepToggle = false;
bool backwardStepToggle = false;

void setup() {
  Serial.begin(115200);
  
  // Allocate hardware timers
  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);
  ESP32PWM::allocateTimer(2);
  ESP32PWM::allocateTimer(3);
  
  rightFoot.setPeriodHertz(50);
  leftFoot.setPeriodHertz(50);
  rightHip.setPeriodHertz(50);
  leftHip.setPeriodHertz(50);

  rightFoot.attach(RF_PIN);
  leftFoot.attach(LF_PIN);
  rightHip.attach(RH_PIN);
  leftHip.attach(LH_PIN);
  
  standNeutral(); // Start balanced

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) { delay(500); }
  udp.begin(localPort);
}

void loop() {
  int packetSize = udp.parsePacket();
  if (packetSize) {
    int len = udp.read(packetBuffer, 255);
    if (len > 0) packetBuffer[len] = 0;
    
    char command = packetBuffer[0];

    switch (command) {
      case 'F': // Forward Stride Request
        if (!forwardStepToggle) {
          // Step A: rf++ , lf-- , rh++ , lh++
          moveServos(FOOT_TOE, FOOT_HEEL, HIP_RIGHT, HIP_RIGHT);
        } else {
          // Step B: rf-- , lf++ , rh-- , lh--
          moveServos(FOOT_HEEL, FOOT_TOE, HIP_LEFT, HIP_LEFT);
        }
        forwardStepToggle = !forwardStepToggle; 
        break;
        
      case 'B': // Backward Stride Request
        if (!backwardStepToggle) {
          // Step A: rf++ , lf-- , rh-- , lh--
          moveServos(FOOT_TOE, FOOT_HEEL, HIP_LEFT, HIP_LEFT);
        } else {
          // Step B: rf-- , lf++ , rh++ , lh++
          moveServos(FOOT_HEEL, FOOT_TOE, HIP_RIGHT, HIP_RIGHT);
        }
        backwardStepToggle = !backwardStepToggle;
        break;
        
      case 'L': // Turn Left (Face Tracking Left)
        // Shift weight left, turn both hips right to pivot counter-clockwise
        moveServos(FOOT_TOE, FOOT_HEEL, HIP_RIGHT, HIP_RIGHT);
        break;
        
      case 'R': // Turn Right (Face Tracking Right)
        // Shift weight right, turn both hips left to pivot clockwise
        moveServos(FOOT_HEEL, FOOT_TOE, HIP_LEFT, HIP_LEFT);
        break;
        
      case 'Z': // AI State / Photo Countdown Flash
        moveServos(SERVO_CENTER + 5, SERVO_CENTER - 5, SERVO_CENTER, SERVO_CENTER);
        break;

      case 'S': // Immediate Stop
      default:
        standNeutral();
        break;
    }
  }
}

// Direct, snappy writing to the hardware pins
void moveServos(int rf_angle, int lf_angle, int rh_angle, int lh_angle) {
  rightFoot.write(rf_angle);
  leftFoot.write(lf_angle);
  rightHip.write(rh_angle);
  leftHip.write(lh_angle);
}

void standNeutral() {
  moveServos(SERVO_CENTER, SERVO_CENTER, SERVO_CENTER, SERVO_CENTER);
}
