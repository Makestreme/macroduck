/*
 * MacroDuck Firmware
 * Target: ESP32-C3 and ESP32-S3 variants
 * Tools > USB CDC On Boot: and set it to Enabled.
 */

// const int BUTTON_PIN = 6; // For xiao samd21 (seeeduino)
const int BUTTON_PIN = 4; // For Esp32 Superminis and Xiao c3  (uncomment + enable USB CDC on Boot)
// const int BUTTON_PIN = 3; // For xiao s3

// --- Timing Thresholds (in milliseconds) ---
const unsigned long DEBOUNCE_DELAY = 30;   
const unsigned long DOUBLE_TAP_GAP = 250;  
const unsigned long LONG_PRESS_HOLD = 600; 

// Set to 1 to print raw "DOWN"/"UP" on every debounced button transition
// (for diagnosing wiring/pin choice). Leave 0 for normal use.
#define DEBUG_RAW 0

// --- State Variables ---
bool lastPhysicalState = HIGH;
bool currentPhysicalState = HIGH;
unsigned long lastDebounceTime = 0;

bool buttonPressed = false;
unsigned long pressStartTime = 0;
unsigned long releaseTime = 0;
bool waitingForSecondTap = false;
bool longPressFired = false;
bool doubleTapFired = false;

void setup() {
  Serial.begin(115200);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
#if defined(ARDUINO_ARCH_SAMD) || defined(ARDUINO_ARCH_ESP32) || defined(ARDUINO_ARCH_RP2040)
  // Wait briefly for USB CDC to enumerate so the boot banner isn't dropped.
  unsigned long t0 = millis();
  while (!Serial && (millis() - t0) < 2000) { /* wait for host */ }
  delay(200);
#endif
  Serial.println("READY");
  Serial.print("PIN=");
  Serial.println(BUTTON_PIN);
}

void loop() {
  // --- 0. Host handshake: answer "PING" with "READY" (non-blocking) ---
  static String cmdBuf = "";
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      cmdBuf.trim();
      if (cmdBuf == "PING") {
        Serial.println("READY");
      }
      cmdBuf = "";
    } else {
      cmdBuf += c;
    }
  }

  bool rawReading = digitalRead(BUTTON_PIN);
  unsigned long now = millis();

  // --- 1. Hardware Debouncing ---
  if (rawReading != lastPhysicalState) {
    lastDebounceTime = now;
    lastPhysicalState = rawReading;
  }

  if ((now - lastDebounceTime) > DEBOUNCE_DELAY) {
    if (rawReading != currentPhysicalState) {
      currentPhysicalState = rawReading;

#if DEBUG_RAW
      Serial.println(currentPhysicalState == LOW ? "DOWN" : "UP");
#endif

      // --- 2. Button Down (Press Event) ---
      if (currentPhysicalState == LOW) {
        buttonPressed = true;
        pressStartTime = now;
        longPressFired = false;

        if (waitingForSecondTap) {
          Serial.println("TAP_2");
          waitingForSecondTap = false;
          doubleTapFired = true;  // this press is the second tap of a double
        } else {
          doubleTapFired = false;
        }
      }
      // --- 3. Button Up (Release Event) ---
      else {
        buttonPressed = false;
        releaseTime = now;

        if (doubleTapFired) {
          // Double tap complete — do NOT re-arm, otherwise the release of the
          // second tap would fire a spurious TAP_1 after the gap window.
          doubleTapFired = false;
        } else if (!longPressFired && (now - pressStartTime < LONG_PRESS_HOLD)) {
          waitingForSecondTap = true;
        }
      }
    }
  }

  // --- 4. Long Press Hold Check ---
  if (buttonPressed && !longPressFired && !doubleTapFired) {
    if (now - pressStartTime >= LONG_PRESS_HOLD) {
      Serial.println("TAP_HOLD");
      longPressFired = true;
      waitingForSecondTap = false; 
    }
  }

  // --- 5. Single Tap Timeout Check ---
  if (waitingForSecondTap && !buttonPressed) {
    if (now - releaseTime >= DOUBLE_TAP_GAP) {
      Serial.println("TAP_1");
      waitingForSecondTap = false;
    }
  }
}