# Gate-Genie

An intelligent gate assignment system for airports that uses AI to optimize gate allocations based on multiple operational factors.

## Overview

Gate-Genie processes flight arrival data and automatically assigns aircraft to available gates using NVIDIA's NIM API with Llama-3. The system considers aircraft size, airline preferences, turnaround times, gate capabilities, and passenger volume to make optimal assignments.

The system provides two interfaces: a data table dashboard for operational oversight and an interactive map view for spatial gate management.

## Possible Use Cases

- **Airport Operations Centers**: Real-time gate assignment optimization
- **Ground Handling Companies**: Resource planning and coordination
- **Airlines**: Gate preference enforcement and conflict resolution
- **Airport Planning**: Capacity analysis and bottleneck identification

## Making It Actually Useful

To transform this from a demonstration into a production system, several components would need development:

**Real-time Data Integration:**
- Airport Operational Database (AODB) integration
- SITA or ARINC flight information feeds
- Gate management system APIs
- Aircraft positioning and status feeds

**Production Infrastructure:**
- Database backend replacing CSV files
- User authentication and role-based access
- Audit logging and compliance tracking
- Failover and redundancy systems
- Integration with existing airport management software

**Operational Requirements:**
- 24/7 monitoring and alerting
- Multi-airport configuration management
- Historical data analysis and reporting
- Conflict resolution workflows
- Manual override capabilities

**Regulatory Compliance:**
- Airport authority approval processes
- Safety management system integration
- Data privacy and security standards
- Change management procedures

## Limitations

- Currently configured for SFO airport layout
- Requires manual CSV data updates for real-time operation
- AI decisions are recommendations, not automated implementations
- Single-user interface without authentication

## Disclaimer

This project is an experimental demonstration of AI applications in airport operations. It is not production-ready software and should not be used for actual gate assignment decisions. The system uses mock data and simplified logic that does not account for the full complexity of real airport operations, safety protocols, or regulatory requirements. This is purely an educational exploration of how AI might assist in operational decision-making processes.

## Technical Implementation

**Backend:**
- Python Flask web server for API endpoints and dashboard serving
- Pandas for CSV data processing and manipulation
- NVIDIA NIM API integration for AI-powered decision making
- Real-time data updates via threaded background processes

**Frontend:**
- HTML/CSS/JavaScript dashboard with dark theme
- Leaflet.js interactive map for spatial gate visualization
- RESTful API consumption for live data updates
- Responsive design for multiple device types

**Data Sources:**
- Flight arrivals CSV with aircraft and timing data
- Gate configuration with capacity and airline preferences
- Real-time gate occupancy status
- Assignment history and reasoning logs

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CSV Data      │───▶│   Gate-Genie     │───▶│   Web Dashboard │
│   Sources       │    │   AI Processor   │    │   & Map View    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │   NVIDIA NIM     │
                       │   Llama-3 API    │
                       └──────────────────┘
```

## Data Processing

The system processes four main data types:

- **arrivals.csv**: Flight schedules, aircraft types, passenger counts, origins
- **gates_config.csv**: Gate specifications, airline preferences, aircraft size limits
- **gate_occupancy.csv**: Current gate status, turnaround times, availability
- **gate_assignments_log.csv**: Assignment history with AI reasoning

Gate assignments consider:
- Aircraft size compatibility with gate specifications
- Airline preference matching where possible
- Minimum turnaround time requirements
- Passenger volume and gate capacity
- Terminal logistics and customs requirements

## API Endpoints

- `GET /api/data` - Complete dashboard dataset
- `GET /api/arrivals` - Flight arrival information
- `GET /api/gates` - Gate status and configuration
- `GET /api/assignments` - Recent assignment history
- `POST /refresh` - Manual data refresh trigger

## Requirements

- Python 3.8+
- NVIDIA NIM API access
- 2GB RAM minimum for data processing
- Modern web browser for dashboard access

## Setup

1. **Install Dependencies**:
```bash
pip install -r requirements.txt
```

2. **Set up Environment Variables**:
```bash
# Copy the example environment file
cp .env_example.txt .env

# Edit .env and add your NVIDIA NIM API key
# NVIDIA_API_KEY=your-actual-api-key-here
```

3. **Run the System**:
```bash
# Start the web server
python3 web_server.py

# In a separate terminal, run gate assignments
python3 gate_genie.py
```

4. **Access Interfaces**:
- Dashboard: http://localhost:5000
- Interactive Map: http://localhost:5000/map 