#!/usr/bin/env python3
"""
Simple Gate Assignment Runner
Runs gate assignments once and saves to CSV files.
Separate from web server for cleaner architecture.
"""

from gate_genie import GateGenie

def main():
    """Run gate assignment once and exit"""
    print("🛫 Starting Gate-Genie assignment process...")
    
    # Get API key from environment variable
import os
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv('NVIDIA_API_KEY')
if not API_KEY:
    raise ValueError("NVIDIA_API_KEY environment variable not set. Please create a .env file with your API key.")
    
    try:
        # Initialize Gate-Genie
        gate_genie = GateGenie(API_KEY)
        
        # Process arrivals and assign gates
        gate_genie.process_arrivals()
        
        print("\n✅ Gate assignment completed successfully!")
        print("📄 Results saved to CSV files:")
        print("   - data/arrivals_with_gates.csv")
        print("   - data/gate_assignments_log.csv") 
        print("   - data/gate_occupancy_updated.csv")
        print("\n🌐 Now start the web server with: python3 web_server.py")
        
    except Exception as e:
        print(f"❌ Error during gate assignment: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 