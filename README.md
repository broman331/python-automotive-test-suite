# Virtual Vehicle Simulation Framework

[![View Walkthrough](https://img.shields.io/badge/Documentation-Walkthrough-blue?style=for-the-badge)](WALKTHROUGH.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

## Overview
The **Virtual Vehicle Simulation** is a comprehensive Python-based testbed for automotive software. It mocks a modern vehicle's electronic architecture, including Electronic Control Units (ECUs), physical plant models (Dynamics, Battery, Sensors), and a virtual communication bus (CAN/Ethernet). 

This framework enables **"Shift-Left" testing**, allowing engineers to validate functional safety, cybersecurity, and advanced driver assistance systems (ADAS) logic before simulated or physical hardware is available.

## Project Structure
```
project 019/
├── virtual_vehicle/
│   ├── ecus/            # Virtual ECUs (ADAS, BMS, Gateway, etc.)
│   ├── plants/          # Physics Models (Vehicle Dynamics, Battery, Sensors)
│   ├── sim/             # Simulation Engine & Virtual Bus
│   ├── tests/           # Pytest Test Suites (Safety, Security, Efficiency, etc.)
│   ├── utilities/       # Helpers (Report Generation, Drive Cycles)
│   └── reports/         # Automated HTML Test Reports
├── venv/                # Python Virtual Environment
└── requirements.txt     # Dependencies
```

## Setup & Installation

1.  **Clone the repository** (or navigate to the project directory).
2.  **Create a Virtual Environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
3.  **Install Dependencies**:
    ```bash
    pip install -r virtual_vehicle/requirements.txt
    ```
    *Dependencies include: `pytest`, `pytest-cov`, `numpy`, `simpy` (if used), `pylint`.*

## Running the Simulation

The framework uses `pytest` for executing scenarios. Ensure your `PYTHONPATH` includes the project root.

### 1. Run All Tests
To execute the full regression suite (Safety, Security, Dynamics, ADAS):
```bash
PYTHONPATH=. ./venv/bin/pytest virtual_vehicle/tests/
```

### 2. Run Specific Domains
*   **ADAS (AEB & LKA)**:
    ```bash
    PYTHONPATH=. ./venv/bin/pytest virtual_vehicle/tests/test_perception.py
    ```
*   **Cybersecurity (OTA & Fuzzing)**:
    ```bash
    PYTHONPATH=. ./venv/bin/pytest virtual_vehicle/tests/test_cybersecurity.py
    ```
*   **Functional Safety (Fault Injection)**:
    ```bash
    PYTHONPATH=. ./venv/bin/pytest virtual_vehicle/tests/test_safety.py
    ```
*   **Vehicle Dynamics (Split-Mu & Stability)**:
    ```bash
    PYTHONPATH=. ./venv/bin/pytest virtual_vehicle/tests/test_dynamics.py
    ```

### 3. Generate Coverage Report
```bash
PYTHONPATH=. ./venv/bin/pytest --cov=virtual_vehicle --cov-report=html
open htmlcov/index.html
```

## Implemented Domains

### 🚗 Vehicle Dynamics
*   **Bicycle Model**: Simulates longitudinal/lateral physics.
*   **Tire Friction**: Support for Split-Mu surfaces and slip angle dynamics.
*   **ESC**: Electronic Stability Control logic to arrest yaw instability.

### 🛡️ Functional Safety (ISO 26262)
*   **Fault Injection**: Capable of injecting `DROP`, `DELAY`, and `CORRUPT` faults into bus messages.
*   **Safe States**: ECUs enter safe modes (e.g., "Limp Home") upon fault detection.
*   **Passive Safety**: Airbag ECU simulation with crash pulse detection.

### 🔒 Cybersecurity (ISO 21434)
*   **Secure OTA**: FOTA updates with signature verification and A/B partition rollback.
*   **IDPS**: Gateway firewall rules to detect and block unauthorized CAN IDs.
*   **V2X**: Simulated Vehicle-to-Everything communication with Basic Safety Messages (BSM).

### 🔋 Electrification
*   **Battery Management (BMS)**: Thermal modeling, Over-Voltage/Over-Temperature protection, and contactor control.
*   **Efficiency**: Micro-WLTP drive cycle simulation for energy consumption analysis.

### 🤖 ADAS & AI
*   **Sensors**: Synthetic Camera (Lane Detection) and Radar (Object Tracking).
*   **Features**: Automatic Emergency Braking (AEB) and Lane Keep Assist (LKA).
*   **SOTIF**: Perception degradation simulation (e.g., occlusion/rain) to test robust degradation.

## Reporting
Automated HTML reports are generated in `virtual_vehicle/reports/` after each test run, containing detailed signal logs and pass/fail criteria.
