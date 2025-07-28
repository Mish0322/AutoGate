#!/usr/bin/env python3
"""
Gate-Genie: Intelligent Airport Gate Assignment System
Uses NVIDIA NIM Llama-3 to make smart gate assignments for SFO arrivals
"""

import pandas as pd
import time
import json
from datetime import datetime, timedelta
from openai import OpenAI
from typing import Dict, List, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GateGenie:
    def __init__(self, api_key: str):
        """Initialize Gate-Genie with NVIDIA NIM API"""
        self.api_key = api_key
        self.client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key
        )
        
        # Load data
        self.arrivals_df = pd.read_csv("data/arrivals.csv")
        self.gates_config_df = pd.read_csv("data/gates_config.csv")
        self.gate_occupancy_df = pd.read_csv("data/gate_occupancy.csv")
        
        # Initialize results
        self.assignments = []
        
        logger.info("Gate-Genie initialized successfully")
    
    def get_available_gates(self) -> List[Dict]:
        """Get list of currently available gates with their capabilities"""
        available_gates = []
        
        for _, gate in self.gates_config_df.iterrows():
            occupancy = self.gate_occupancy_df[
                self.gate_occupancy_df['gate_number'] == gate['gate_number']
            ]
            
            if not occupancy.empty and occupancy.iloc[0]['status'] == 'Available':
                available_gates.append({
                    'gate': gate['gate_number'],
                    'terminal': gate['terminal'],
                    'type': gate['gate_type'],
                    'max_size': gate['max_aircraft_size'],
                    'airline_pref': gate['airline_preference'],
                    'customs': gate['customs_capable']
                })
        
        return available_gates
    
    def classify_aircraft_size(self, aircraft_type: str) -> str:
        """Classify aircraft by size category"""
        large_aircraft = ['Boeing 777', 'Boeing 787', 'Airbus A350', 'Airbus A330', 'Airbus A340']
        extra_large_aircraft = ['Boeing 747', 'Airbus A380', 'Boeing 777-300ER', 'Airbus A340-600']
        
        if any(large_type in aircraft_type for large_type in extra_large_aircraft):
            return "Extra Large"
        elif any(large_type in aircraft_type for large_type in large_aircraft):
            return "Large"
        else:
            return "Medium"
    
    def is_international_flight(self, origin: str) -> bool:
        """Determine if flight is international based on origin"""
        domestic_cities = [
            "Los Angeles", "New York JFK", "Las Vegas", "Seattle", "Portland", 
            "Phoenix", "Denver", "Miami", "Atlanta", "Anchorage"
        ]
        return origin not in domestic_cities
    
    def assign_gate_with_ai(self, flight: Dict, available_gates: List[Dict]) -> Optional[str]:
        """Use NVIDIA NIM to intelligently assign a gate"""
        
        # Prepare context for AI
        flight_info = f"""
Flight: {flight['flight_number']} ({flight['airline']})
Aircraft: {flight['aircraft_type']}
Origin: {flight['origin']}
Passengers: {flight['passengers']}
Arrival Time: {flight['scheduled_arrival']}
"""
        
        gates_info = "\n".join([
            f"Gate {g['gate']} - {g['terminal']} - {g['type']} - Max: {g['max_size']} - Prefers: {g['airline_pref']} - Customs: {g['customs']}"
            for g in available_gates[:10]  # Limit to prevent token overflow
        ])
        
        prompt = f"""You are an expert airport operations manager at San Francisco International Airport (SFO). 
Your job is to assign the optimal gate for incoming flights based on multiple factors.

FLIGHT INFORMATION:
{flight_info}

AVAILABLE GATES:
{gates_info}

ASSIGNMENT CRITERIA (in order of priority):
1. Aircraft Size Compatibility - Gate must accommodate aircraft size
2. International vs Domestic - International flights need customs-capable gates 
3. Airline Preference - Gates are optimized for specific airlines
4. Terminal Efficiency - Minimize passenger walking distances
5. Operational Flow - Consider gate proximity and traffic patterns

AIRCRAFT SIZE REQUIREMENTS:
- Medium aircraft (737, A320 series): Can use Medium, Large, or Extra Large gates
- Large aircraft (777, 787, A350): Need Large or Extra Large gates  
- Extra Large aircraft (A380, 747): Need Extra Large gates only

IMPORTANT RULES:
- International flights MUST use gates with customs capability (International terminal)
- Respect airline preferences when possible (United → Terminal 3, American → Terminal 2, Southwest → Terminal 1)
- Consider passenger count for gate capacity

Respond with ONLY the gate number (e.g., "A7" or "72") that is the optimal choice. No explanation needed."""

        try:
            completion = self.client.chat.completions.create(
                model="meta/llama-3.1-70b-instruct",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                top_p=0.9,
                max_tokens=10,
                stream=False
            )
            
            assigned_gate = completion.choices[0].message.content.strip()
            
            # Validate the assignment
            valid_gates = [str(g['gate']) for g in available_gates]
            if assigned_gate in valid_gates:
                return assigned_gate
            else:
                logger.warning(f"AI suggested invalid gate {assigned_gate}, using fallback")
                return available_gates[0]['gate'] if available_gates else None
                
        except Exception as e:
            logger.error(f"Error during AI gate assignment: {e}")
            # Fallback to first available compatible gate
            return available_gates[0]['gate'] if available_gates else None
    
    def filter_compatible_gates(self, flight: Dict, available_gates: List[Dict]) -> List[Dict]:
        """Filter gates that are compatible with the flight requirements"""
        aircraft_size = self.classify_aircraft_size(flight['aircraft_type'])
        is_intl = self.is_international_flight(flight['origin'])
        
        compatible_gates = []
        
        for gate in available_gates:
            # Check size compatibility
            size_compatible = False
            if aircraft_size == "Medium":
                size_compatible = gate['max_size'] in ["Medium", "Large", "Extra Large"]
            elif aircraft_size == "Large":
                size_compatible = gate['max_size'] in ["Large", "Extra Large"]
            elif aircraft_size == "Extra Large":
                size_compatible = gate['max_size'] == "Extra Large"
            
            # Check customs requirement for international flights
            customs_compatible = not is_intl or gate['customs'] == "Yes"
            
            if size_compatible and customs_compatible:
                compatible_gates.append(gate)
        
        return compatible_gates
    
    def process_arrivals(self):
        """Process all arriving flights and assign gates"""
        logger.info("Starting gate assignment process...")
        
        # Filter flights that need gate assignment
        unassigned_flights = self.arrivals_df[
            (self.arrivals_df['gate_assigned'].isna() | (self.arrivals_df['gate_assigned'] == '')) &
            (self.arrivals_df['status'].isin(['Approaching', 'En Route']))
        ].copy()
        
        logger.info(f"Found {len(unassigned_flights)} flights needing gate assignment")
        
        for idx, flight in unassigned_flights.iterrows():
            logger.info(f"Processing flight {flight['flight_number']}...")
            
            # Get available gates
            available_gates = self.get_available_gates()
            
            # Filter compatible gates
            compatible_gates = self.filter_compatible_gates(flight.to_dict(), available_gates)
            
            if not compatible_gates:
                logger.warning(f"No compatible gates available for {flight['flight_number']}")
                assigned_gate = "WAITING"
            else:
                # Use AI to assign optimal gate
                assigned_gate = self.assign_gate_with_ai(flight.to_dict(), compatible_gates)
                
                if assigned_gate and assigned_gate != "WAITING":
                    # Mark gate as occupied
                    self.gate_occupancy_df.loc[
                        self.gate_occupancy_df['gate_number'] == assigned_gate, 'status'
                    ] = 'Occupied'
                    self.gate_occupancy_df.loc[
                        self.gate_occupancy_df['gate_number'] == assigned_gate, 'current_flight'
                    ] = flight['flight_number']
            
            # Update arrivals dataframe
            self.arrivals_df.at[idx, 'gate_assigned'] = assigned_gate
            
            # Record assignment
            self.assignments.append({
                'timestamp': datetime.now().isoformat(),
                'flight_number': flight['flight_number'],
                'airline': flight['airline'],
                'aircraft_type': flight['aircraft_type'],
                'origin': flight['origin'],
                'assigned_gate': assigned_gate,
                'assignment_reason': f"AI-optimized assignment"
            })
            
            logger.info(f"Assigned {flight['flight_number']} to gate {assigned_gate}")
            
            # Rate limiting for API calls (40 per minute)
            time.sleep(1.6)
        
        # Save results
        self.save_results()
        logger.info("Gate assignment process completed")
    
    def save_results(self):
        """Save assignment results to CSV files"""
        # Save updated arrivals
        self.arrivals_df.to_csv("data/arrivals_with_gates.csv", index=False)
        
        # Save assignment log
        assignments_df = pd.DataFrame(self.assignments)
        assignments_df.to_csv("data/gate_assignments_log.csv", index=False)
        
        # Save updated gate occupancy
        self.gate_occupancy_df.to_csv("data/gate_occupancy_updated.csv", index=False)
        
        logger.info("Results saved to CSV files")
    
    def get_dashboard_data(self) -> Dict:
        """Get data formatted for dashboard display"""
        return {
            'arrivals': self.arrivals_df.to_dict('records'),
            'assignments': self.assignments,
            'gate_occupancy': self.gate_occupancy_df.to_dict('records'),
            'gates_config': self.gates_config_df.to_dict('records')
        }

def main():
    """Main function to run Gate-Genie"""
    # Replace with your actual NVIDIA NIM API key
    API_KEY = "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"
    
    try:
        # Initialize Gate-Genie
        gate_genie = GateGenie(API_KEY)
        
        # Process arrivals and assign gates
        gate_genie.process_arrivals()
        
        print("\n=== GATE ASSIGNMENT SUMMARY ===")
        assignments_df = pd.read_csv("data/gate_assignments_log.csv")
        print(assignments_df[['flight_number', 'airline', 'assigned_gate']])
        
        print(f"\nAssigned {len(assignments_df)} flights to gates successfully!")
        print("Results saved to 'data/arrivals_with_gates.csv'")
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        raise

if __name__ == "__main__":
    main() 