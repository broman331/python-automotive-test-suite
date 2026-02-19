# Virtual Vehicle Test Catalog

This document provides a comprehensive overview of all test suites, scenarios, and verification logic implemented in the Virtual Vehicle Simulation.

## 1. Integrated & Scenario Tests
Tests that verify end-to-end system behavior.

| Test File | Scenario | Description |
| :--- | :--- | :--- |
| `integration_test.py` | AEB Stationary Obstacle | Verifies that the ADAS ECU detects a stationary target and applies AEB to prevent a collision from 72 km/h. |
| `test_scenarios.py` | Euro NCAP Cut-In | Simulates a vehicle cutting into the ego lane. Verifies ADAS ignores objects in adjacent lanes but triggers AEB once they cross the boundary. |
| `test_scenarios.py` | Moose Test (ESC) | rapid double-lane change at 80 km/h. Verifies that the Stability Control (ESC) prevents spin-out by limiting yaw rate. |

## 2. ADAS & Perception Tests
Tests focused on sensors (Camera/Radar) and logic (AEB/LKA/AI Safety).

| Test File | Scenario | Description |
| :--- | :--- | :--- |
| `test_perception.py` | LKA Centering | Verifies that the Lane Keep Assist controller steers a vehicle starting with a 1m offset back to the lane center (<0.25m). |
| `test_ai_safety.py` | Rain/Fog Degradation | Simulates heavy rain (noise) causing low camera confidence. Verifies the ADAS ECU gracefully disables LKA and warns the system. |
| `test_v2x.py` | Intersection Assist | Simulates receiving a V2X Basic Safety Message from a hidden vehicle. Verifies the Gateway warns of a potential intersection collision. |

## 3. Vehicle Dynamics Tests
Tests focusing on physics, handling, and braking.

| Test File | Scenario | Description |
| :--- | :--- | :--- |
| `test_dynamics.py` | Split-Mu Braking | Simulates braking on a split-friction surface (Left=Dry, Right=Ice). Verifies the vehicle pulls towards the high-friction side. |
| `test_dynamics_advanced.py` | Understeer Saturation | Verifies that lateral acceleration is limited by the friction circle (~0.4g on low mu) using the force-based tire model. |
| `test_dynamics_advanced.py` | Stability Correction | Verifies that the vehicle naturally damps out yaw oscillations during transient maneuvers, ensuring stability. |

## 4. Functional Safety & Cybersecurity Tests
Tests following ISO 26262 and ISO 21434 principles.

| Test File | Scenario | Description |
| :--- | :--- | :--- |
| `test_safety.py` | Brake Command Loss | Injects a "DROP" fault on brake commands. Verifies that a collision occurs, validating the fault injection architecture. |
| `test_safety.py` | Radar Corruption | Injects "CORRUPT" data into radar object lists. Verifies the ADAS ECU filters invalid data without crashing. |
| `test_cybersecurity.py` | Secure OTA Update | Simulates an Over-the-Air update. Verifies that valid signatures pass, invalid signatures fail, and corrupt flashes prompt a rollback. |
| `test_diagnostics.py` | UDS Services | Verifies ISO 14229 services: Session Control (0x10), Security Access (0x27), Read Data (0x22), and Routine Control (0x31). |

## 5. Electrification & Environmental Tests
Tests for BMS, Battery, and Charging systems.

| Test File | Scenario | Description |
| :--- | :--- | :--- |
| `test_charging.py` | CCS Handshake/Profile | Simulates the CCS/NACS charging state machine: Cable detection -> Handshake -> Power Delivery -> Auto-termination at 90% SoC. |
| `test_efficiency.py` | WLTP Drive Cycle | Runs a micro-WLTP speed profile. Verifies energy consumption calculation (kWh/100km) based on powertrain loads. |
| `test_environmental.py` | Thermal Shock | Simulates high ambient temperature (60°C). Verifies the BMS detects over-temperature and opens contactors for safety. |
| `test_environmental.py` | Voltage Sensor Drift | Injects a +30V drift into the voltage sensor. Verifies the BMS triggers a safety shutdown due to perceived over-voltage. |

## 6. Passive Safety Tests
Tests for restraint systems and crash detection.

| Test File | Scenario | Description |
| :--- | :--- | :--- |
| `test_passive_safety.py` | High-G Crash | Simulates a -6g impact pulse. Verifies the Airbag ECU deploys airbags and seatbelt pretensioners within 10ms. |
| `test_passive_safety.py` | Non-Deploy Event | Verifies that hard braking (-1g) does NOT trigger airbags, ensuring reliability against false deployments. |

## 7. System Integrity (Negative Verification)
Tests demonstrating reporting and constraint verification.

| Test File | Scenario | Description |
| :--- | :--- | :--- |
| `test_known_failures.py` | Physics Constraints | Verifies that acceleration remains within realistic limits (G-force clamping). |
| `test_known_failures.py` | Security Denial | Verifies that unauthorized UDS access attempts are rejected, ensuring no security holes exist. |
| `test_known_failures.py` | Energy Conservation | Verifies logical consistency and reporting of passing integrity checks. |

## 8. Body Controls & Odometer Tests
Tests for distance tracking, persistence, and dash functions.

| Test File | Scenario | Description |
| :--- | :--- | :--- |
| `test_odometer.py` | Accumulation (72km/h) | Verifies that the odometer integrates speed correctly to calculate distance (0.1km in 5s). |
| `test_odometer.py` | Reverse Monotonicity | Verifies that driving in reverse (negative velocity) still results in distance increment (total travel distance). |
| `test_odometer.py` | Persistence (NVM) | Verifies that odometer values are saved to "flash" and correctly loaded upon ECU reboot. |
| `test_odometer.py` | Trip Reset | Verifies that resetting the trip meter works as expected without affecting the life-to-date odometer. |
| `test_odometer.py` | High Range Stability | Verifies that the system handles extremely high values (999,999 km) without overflow or data corruption. |

## 9. AI Adversary Tests
Fuzzing, RL-based traffic, and Neural Sensor simulation.

| Test File | Scenario | Description |
| :--- | :--- | :--- |
| `test_genai_fuzzing.py` | Adversarial Braking | Uses `ScenarioGenerator` to fuzz speed and friction, creating edge-case braking scenarios. |
| `test_rl_traffic.py` | Cut-In Learning | Trains an RL `TrafficAgent` to execute dangerous cut-in maneuvers against the Ego vehicle. |
| `test_neural_perception.py` | Rain Robustness | Verifies AEB triggers despite heavy rain noise (0.5m std dev) in `NeuralRadar`. |
| `test_neural_perception.py` | Fog & Ghost Objects | Verifies system behavior when presented with false positive detections (ghosts) in Fog conditions. |
