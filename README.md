# 🛫 Gate-Genie: AI-Powered Airport Gate Assignment System

**Gate-Genie** is an intelligent gate assignment system for San Francisco International Airport (SFO) that uses **NVIDIA NIM Llama-3** to make smart, real-time gate assignments for arriving aircraft.

## ✨ Features

- **🤖 AI-Powered Assignments**: Uses NVIDIA NIM Llama-3.1-70B to intelligently assign gates based on multiple factors
- **📊 Real-time Dashboard**: Beautiful web interface showing arrivals, gate status, and assignments
- **🎯 Smart Logic**: Considers aircraft size, airline preferences, customs requirements, and operational efficiency
- **📈 Live Updates**: Automatic processing of new arrivals every 5 minutes
- **🏢 Realistic Data**: Uses actual SFO gate numbers and terminal configurations

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- NVIDIA NIM API key (replace in `gate_genie.py` and `web_server.py`)

### Installation

1. **Clone and setup**:
   ```bash
   cd AutoGate
   pip install -r requirements.txt
   ```

2. **Update API Key**:
   - Edit `gate_genie.py` line 252: Replace the API key with your NVIDIA NIM key
   - Edit `web_server.py` line 67: Replace the API key with your NVIDIA NIM key

3. **Run the system**:
   ```bash
   # Option 1: Run gate assignment once
   python gate_genie.py
   
   # Option 2: Run web server with real-time updates
   python web_server.py
   ```

4. **Access Dashboard**:
   Open http://localhost:5000 in your browser

## 📁 Project Structure

```
AutoGate/
├── data/                          # CSV data files
│   ├── arrivals.csv              # Incoming flight data
│   ├── gates_config.csv          # SFO gate configurations  
│   ├── gate_occupancy.csv        # Current gate status
│   └── [generated files]         # Output CSVs
├── templates/
│   └── dashboard.html            # Web interface
├── gate_genie.py                 # Main AI assignment engine
├── web_server.py                 # Flask web server
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## 🧠 How It Works

### AI Decision Process
1. **Compatibility Check**: Filters gates based on aircraft size and customs requirements
2. **AI Analysis**: NVIDIA NIM evaluates factors like:
   - Aircraft size compatibility (Medium/Large/Extra Large)
   - International vs Domestic routing
   - Airline terminal preferences (United→T3, American→T2, Southwest→T1)
   - Gate availability and passenger capacity
3. **Smart Assignment**: Returns optimal gate choice with reasoning

### Real-time Processing
- **Automatic Updates**: Web server runs gate assignments every 5 minutes
- **Live Dashboard**: Frontend refreshes every 30 seconds
- **Rate Limiting**: Respects NVIDIA NIM API limits (40 calls/minute)

## 📊 Sample Data

### Airlines & Terminals
- **Terminal 1**: Southwest, Alaska Airlines
- **Terminal 2**: American, Delta, Virgin America  
- **Terminal 3**: United (hub)
- **International**: All international carriers

### Aircraft Classifications
- **Medium**: Boeing 737, Airbus A320 series
- **Large**: Boeing 777, 787, Airbus A350, A330
- **Extra Large**: Boeing 747, Airbus A380, wide-body variants

## 🔧 API Endpoints

- `GET /` - Main dashboard
- `GET /api/data` - All data (arrivals, gates, assignments)
- `GET /api/arrivals` - Flight arrivals only
- `GET /api/gates` - Gate status only  
- `GET /api/assignments` - Recent AI assignments
- `GET /refresh` - Manual data refresh

## 📈 Output Files

- `arrivals_with_gates.csv` - Updated arrivals with gate assignments
- `gate_assignments_log.csv` - Detailed assignment history
- `gate_occupancy_updated.csv` - Updated gate status

## 🎛️ Configuration

### API Key Setup
Replace the API key in both files:
```python
API_KEY = "your-nvidia-nim-api-key-here"
```

### Customization Options
- Modify gate priorities in `assign_gate_with_ai()`
- Adjust update frequency in `web_server.py` (currently 5 minutes)
- Add more airlines/aircraft types in classification functions

## 🚨 Notes

- **Demo System**: Uses mock data for realistic testing
- **API Costs**: Each assignment makes 1 NVIDIA NIM API call
- **Rate Limits**: Built-in delays to respect API limits
- **Fallback Logic**: Handles API errors gracefully

## 🛠️ Troubleshooting

**Common Issues:**
- **Missing CSV files**: Ensure `data/` directory exists with all CSV files
- **API errors**: Check NVIDIA NIM API key and network connection
- **Port conflicts**: Web server uses port 5000 (configurable)

**Dependencies Issues:**
```bash
pip install --upgrade pandas flask openai requests
```

## 🎯 Future Enhancements

- Real SFO data integration via APIs
- WebSocket real-time updates
- Historical analytics and reporting
- Mobile-responsive design improvements
- Multi-airport support

---

Built with ❤️ using NVIDIA NIM, Python, and modern web technologies. 