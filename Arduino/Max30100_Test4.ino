#include <Wire.h>
#include "MAX30100_PulseOximeter.h"
 
#define REPORTING_PERIOD_MS     1000
 
// PulseOximeter is the higher level interface to the sensor
// it offers:
//  * beat detection reporting
//  * heart rate calculation
//  * SpO2 (oxidation level) calculation
PulseOximeter pox;
 
uint32_t tsLastReport = 0;
uint32_t tsElapsed = 0;
int beats = 0;
char header[] = "{\"name\":\"SP02\",\"labels\":[\"Heart_rate\",\"Oxygen\"],\"data_range\":[[0,150],[0,100]],\"sampling_rate\":1,\"Version\":\"1.0_Alpha\"}";
// Callback (registered below) fired when a pulse is detected
void onBeatDetected()
{
    beats++;
    //Serial.println("Beat!");
}
 
void setup()
{
    Serial.begin(115200);
 
    //Serial.print("Initializing pulse oximeter..");
 
    // Initialize the PulseOximeter instance
    // Failures are generally due to an improper I2C wiring, missing power supply
    // or wrong target chip
    if (!pox.begin()) {
        //Serial.println("FAILED");
        for(;;);
    } else {
        //Serial.println("SUCCESS");
    }
 
    // The default current for the IR LED is 50mA and it could be changed
    //   by uncommenting the following line. Check MAX30100_Registers.h for all the
    //   available options.
    pox.setIRLedCurrent(MAX30100_LED_CURR_24MA);
    // pox.setIRLedCurrent(MAX30100_LED_CURR_7_6MA);
 
    // Register a callback for the beat detection
    pox.setOnBeatDetectedCallback(onBeatDetected);
    tsLastReport = millis();
}
 
void loop()
{
  // Make sure to call update as fast as possible
  pox.update();
  
  if (Serial.available()) {
    char incomingByte = Serial.read();
    /*
     * 1. Wait for setup signal from Pi
     * 2. Send header to Pi
     *  - device name: "SpO2 sensor"
     *  - data labels: ["Heart rate", "SpO2"]
     *  - units: ["bpm", "%"]
     *  - sampling rate: 1 Hz
     *  - expected data range: [[0, 220], [0, 100]]
     * 3. Respond to Pi requests
     *  - request data
     *  - stop?
     */
 
    // Asynchronously dump heart rate and oxidation levels to the serial
    // For both, a value of 0 means "invalid"
    switch (incomingByte) {
      case 'A':
        Serial.println(header);
        break;
        
      case 'B':
        pox.update();
        Serial.print("{\"Heart_rate\":");
        Serial.print(pox.getHeartRate());
        Serial.print(",");
        Serial.print("\"Oxygen\":");
        Serial.print(pox.getSpO2());
        Serial.print("}");
        Serial.print("\n");
        break;
    }
  }
}
