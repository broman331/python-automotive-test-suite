# Virtual Vehicle Simulation Walkthrough

This document outlines the implementation and verification of the Mocked Modern Automotive System. The system simulates a vehicle's hardware and network environment to enable "Shift Left" testing of ECUs and software logic.

## Architecture

The project follows a **Virtual Vehicle** architecture:

*   **Simulation Engine (`sim/`)**: Manages the physics clock and the **Virtual Bus** (mocking CAN/Ethernet).
*   **Plant Models (`plants/`)**: Simulate physical components (Vehicle Dynamics, Battery, Radar).
*   **Virtual ECUs (`ecus/`)**: Run application software logic (BMS, ADAS, Gateway).

### Component Flow
1.  **VehicleDynamics** calculates speed/position based on throttle/brake.
2.  **RadarGenerator** detects obstacles relative to the vehicle position.
3.  **AdasECU** processes radar data and sends `BRAKE_CMD` if a collision is imminent.
4.  **VehicleDynamics** receives `BRAKE_CMD` and applies deceleration.

## Implemented Domains

| Domain | Component | Function |
| :--- | :--- | :--- |
| **Dynamics** | `VehicleDynamics` | Bicycle Model, handling, acceleration/braking physics. |
| **Powertrain** | `BatteryPlant` | Li-ion SoC tracking, thermal model, voltage sag. |
| **Logic** | `BmsECU` | Contactors control, Over-voltage/temp protection. |
| **ADAS** | `RadarGenerator` | Simulates object lists with relative speed/distance. |
| **ADAS** | `AdasECU` | TTC calculation, AEB triggering. |
| **Security** | `GatewayECU` | Firewall, IDPS (Intrusion Detection). |
| **Safety** | `FaultInjector` | Injects signal drops/corruption for FFI/Safety testing. |

## Verification: AEB Scenario

We ran an integration test (`virtual_vehicle/tests/integration_test.py`) simulating a **Stationary Obstacle** scenario.

### Scenario Setup
*   **Initial Speed**: 72 km/h (20 m/s)
*   **Obstacle Distance**: 100 m
*   **Goal**: Prevent Collision (AEB Activation)

### Results
The system successfully avoided the collision. The AEB logic triggered at ~48m distance (2.3s TTC), bringing the vehicle to a complete stop 8 meters from the target.

## Advanced Scenarios

We verified the system against more complex Euro NCAP and Dynamics scenarios:

### 1. Cut-In Scenario
Simulates a vehicle changing lanes into the Ego vehicle's path.
*   **Verification**: Verified that AEB **does not** trigger while the target is in the adjacent lane, but **does** trigger once it crosses the lane boundary.
*   **Mechanism**: `RadarGenerator` updated to track lateral position; `AdasECU` updated to filter objects by lane width.

### 2. Moose Test (Stability Control)
Simulates a severe double-lane change maneuver at high speed (80 km/h).
*   **Verification**: Verified that the **ESC System** detects high yaw rate and activates braking to prevent spin-out.
*   **Mechanism**: `VehicleDynamics` updated with tire friction limits and slip angle dynamics; `EscECU` implemented to apply restorative yaw moments.
*   **Outcome**: Max yaw rate limited to 0.88 rad/s (safe) vs >4.0 rad/s (unstable) without ESC.

## Automated Reporting

The test suite now automatically generates HTML reports for each run.
*   **Location**: `virtual_vehicle/reports/`
*   **Format**: Detailed message logs with "PASS/FAIL" status and timestamps.
*   **Usage**: Run `PYTHONPATH=. ./venv/bin/pytest virtual_vehicle/tests/test_scenarios.py` to generate new reports.

## Phase 2: Robustness Results

### 1. Functional Safety (Fault Injection)
*   **Suite**: `virtual_vehicle/tests/test_safety.py`
*   **Tests**:
    *   **Brake Command Loss**: Injected `DROP` fault on `BRAKE_CMD` during AEB event. Verified collision occurs (validating the injection mechanism).
    *   **Radar Corruption**: Injected `CORRUPT` fault on `RADAR_OBJECTS`. Verified ADAS ECU catches the error and safely aborts processing without crashing.

### 2. Cybersecurity (Secure OTA)
*   **Suite**: `virtual_vehicle/tests/test_cybersecurity.py`
*   **Mechanism**: Implemented `GatewayECU.handle_ota_update` with signature verification and atomic A/B flashing simulation.
*   **Tests**:
    *   **Valid Update**: Verified successful install and reboot.
    *   **Signature Fail**: Verified rejection of updates with invalid signatures.
    *   **Rollback**: Verified system restores previous version upon flash failure ("corrupt binary").

### 3. Vehicle Dynamics (Split-Mu Braking)
*   **Suite**: `virtual_vehicle/tests/test_dynamics.py`
*   **Scenario**: Braking on a split-friction surface (Left $\mu=1.0$, Right $\mu=0.2$).
*   **Mechanism**: Modified `VehicleDynamics` to calculate differential braking moments and yaw disturbance.
*   **Verification**: Verified that braking causes the vehicle to pull towards the high-friction side (Left) with significant yaw rate (> 0.3 rad/s), demonstrating realistic instability.

### 4. Environmental Stress (BMS)
*   **Suite**: `virtual_vehicle/tests/test_environmental.py`
*   **Tests**:
    *   **Thermal Shock**: Simulated ambient temp rise to 60°C. Verified BMS detects Over-Temperature (>60°C) and opens contactors.
    *   **Sensor Drift**: Injected +30V drift into voltage sensor. Verified BMS detects False Over-Voltage (>420V) and triggers safety shutdown.

## Phase 3: Advanced Features Results

### 1. Perception & LKA
*   **Suite**: `virtual_vehicle/tests/test_perception.py`
*   **Components**: Synthetic `CameraPlant` (Lane Detection) + `AdasECU` (LKA Logic).
*   **Verification**: 
    *   Simulated vehicle starting with **1.0m** lateral offset.
    *   Verified LKA controller steers the vehicle back to center.
    *   Final Offset: < **0.25m** (Stable).

### 2. Homologation (OBD-II)
*   **Suite**: `virtual_vehicle/tests/test_homologation.py`
*   **Functions**: Implemented Virtual OBD Service in `GatewayECU`.
*   **Verified Modes**:
    *   **Mode 09** (Vehicle Info): Returned correct VIN (`1FA-VIRTUAL-CAR-001`).
    *   **Mode 03** (DTCs): Returned stored faults (`P0123`).
    *   **Mode 01** (Readiness): Returned `0x00` (All Systems Ready).

### 3. Efficiency (WLTP)
*   **Suite**: `virtual_vehicle/tests/test_efficiency.py`
*   **Cycle**: Micro-WLTP (Idle -> Accel -> Cruise -> Decel -> Stop).
*   **Result**: 
    *   Followed target speed profile (Driver Model PI control).
    *   Verified Energy Consumption calculation based on `Load Current` broadcast from `VehicleDynamics`.
    *   Result: **11.68 kWh/100km** (Realistic EV figure).

### Phase 4: Operationalization and Advanced Systems

**Objective**: Harden the codebase and implement emerging technologies (V2X, Passive Safety, AI Safety).

#### Results
*   **Software Verification**:
    *   **Code Quality**: Achieved `8.41/10` pylint rating (up from 5.0).
    *   **Code Coverage**: **94%** overall coverage across all modules.
*   **Emerging Tech: V2X**:
    *   Implemented `V2XRadio` broadcasting BSMs (Basic Safety Messages).
    *   `GatewayECU` successfully detects collision risks from remote vehicles ("Intersection Movement Assist").
*   **Passive Safety**:
    *   Implemented `AirbagECU` and `CrashSensor` logic.
    *   Verified Airbag deployment on high-G impact (-6g) and non-deployment on hard braking.
*   **AI Safety (SOTIF)**:
    *   Simulated **Optical Occlusion** (Heavy Rain).
    *   Verified `AdasECU` gracefully degrades (disables LKA) when sensor confidence drops below threshold.

## Conclusion

The Virtual Vehicle Simulation is now a fully operational, multi-domain testbed. It supports:
1.  **Vehicle Dynamics** (Longitudinal/Lateral/Split-Mu)
2.  **Functional Safety** (ISO 26262 Fault Injection)
3.  **Cybersecurity** (ISO 21434 SecOC/Fuzzing)
4.  **ADAS** (ACC/AEB/LKA with SOTIF)
5.  **Electrification** (BMS/Thermal/Regen)
6.  **Homologation** (OBD-II/WLTP)
7.  **Connectivity** (V2X/OTA)

### Phase 5: Expansion & New Domains Results

**Objective**: Verify implementation of industry-standard protocols and advanced vehicle physics.

#### 1. Diagnostics (UDS ISO 14229)
*   **Suite**: `virtual_vehicle/tests/test_diagnostics.py`
*   **Services Verified**:
    *   **0x10 (Session Control)**: Transitions between Default/Programming sessions.
    *   **0x27 (Security Access)**: Seed/Key exchange unlock mechanism.
    *   **0x22 (Read Data)**: Retrieval of VIN and Battery Voltage via DID.
    *   **0x31 (Routine Control)**: Remote activation of wiper test.

#### 2. Electrification (Charging CCS/NACS)
*   **Suite**: `virtual_vehicle/tests/test_charging.py`
*   **Components**: Low-Level `ChargingStation` Plant Model + `BmsECU` Charging State Machine.
*   **Scenario Verified**:
    *   **Handshake**: Cable plug-in triggers transition to `HANDSHAKE` state.
    *   **Profile**: Charger delivers voltage/current requested by BMS based on SoC.
    *   **Termination**: Charging stops automatically when Target SoC (90%) is reached.

#### 3. Enhanced Vehicle Dynamics
*   **Suite**: `virtual_vehicle/tests/test_dynamics_advanced.py`
*   **Physics Upgrade**: Replaced simple kinematic model with **Force-Based Tire Model** (Pacejka-style linear approximation with friction saturation).
*   **Verified Behaviors**:
    *   **Understeer Limit**: Cornering at high speed on low friction ($\mu=0.4$) results in front tire saturation. Lateral acceleration is correctly clamped at ~0.4g (3.9 m/s²).
    *   **Stability**: Vehicle naturally damps out yaw oscillations from split-mu braking events.

## Conclusion

The Virtual Vehicle Simulation is now a fully operational, multi-domain testbed. It supports:
1.  **Vehicle Dynamics** (Longitudinal/Lateral/Split-Mu/Stability)
2.  **Functional Safety** (ISO 26262 Fault Injection)
3.  **Cybersecurity** (ISO 21434 SecOC/Fuzzing)
4.  **ADAS** (ACC/AEB/LKA with SOTIF)
5.  **Electrification** (BMS/Thermal/Regen/Charging)
6.  **Homologation** (OBD-II/WLTP/UDS)
7.  **Connectivity** (V2X/OTA)

This framework is ready for integration into a CI/CD pipeline to serve as a **Shift-Left** validation tool for automotive software development.
