#define LDR_PIN 34
#define SAMPLES 5

void setup() {
  Serial.begin(115200);
  analogReadResolution(12);
  analogSetPinAttenuation(LDR_PIN, ADC_11db);
}

void loop() {
  int total = 0;

  for (int i = 0; i < SAMPLES; i++) {
    total += analogRead(LDR_PIN);
    delay(5);
  }

  int reading = total / SAMPLES;

  Serial.print("LIGHT:");
  Serial.println(reading);

  delay(1000);
}

