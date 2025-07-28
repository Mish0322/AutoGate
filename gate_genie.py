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
        """Get list of currently available gates with their capabilities and turnaround analysis"""
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
                    'customs': gate['customs_capable'],
                    'lat': gate['lat'],
                    'lng': gate['lng'],
                    'turnaround_mins': occupancy.iloc[0]['turnaround_mins'],
                    'available_since': occupancy.iloc[0]['available_time']
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
    
    def assign_gate_with_ai(self, flight: Dict, available_gates: List[Dict]) -> tuple[Optional[str], str]:
        """Use NVIDIA NIM to intelligently assign a gate with detailed reasoning"""
        
        if not available_gates:
            return None, "No compatible gates available - all suitable gates are currently occupied"
        
        # Sort gates by preference score for better AI decision making
        scored_gates = self._score_gates_for_flight(flight, available_gates)
        
        # Prepare comprehensive context for AI
        flight_info = f"""
Flight: {flight['flight_number']} ({flight['airline']})
Aircraft: {flight['aircraft_type']} ({self.classify_aircraft_size(flight['aircraft_type'])})
Origin: {flight['origin']} ({'International' if self.is_international_flight(flight['origin']) else 'Domestic'})
Passengers: {flight['passengers']}
Scheduled Arrival: {flight['scheduled_arrival']}
Status: {flight['status']}
"""
        
        gates_info = "\n".join([
            f"Gate {g['gate']} - {g['terminal']} - {g['type']} - Max: {g['max_size']} - Airline Pref: {g['airline_pref']} - Customs: {g['customs']} - Turnaround: {g['turnaround_mins']}min - Score: {g.get('score', 0):.1f}"
            for g in scored_gates[:8]  # Top 8 gates for AI consideration
        ])
        
        prompt = f"""You are an expert airport operations manager at San Francisco International Airport (SFO). 
Your mission is to assign the OPTIMAL gate for this incoming flight based on SFO's real operational requirements.

FLIGHT DETAILS:
{flight_info}

TOP COMPATIBLE GATES (pre-scored by operational priority):
{gates_info}

SFO TERMINAL ASSIGNMENTS (CRITICAL):
- Terminal 1 (B gates): Southwest Airlines hub, Alaska Airlines, some Delta/American
- Terminal 2 (C/D gates): American Airlines hub, Alaska Airlines  
- Terminal 3 (E/F gates): United Airlines hub (primary domestic & some international)
- International Terminal (A/G gates): ALL international flights, some domestic overflow

OPERATIONAL PRIORITIES:
1. AIRLINE HUB MATCHING: Airlines MUST use their primary terminal when possible
   - Southwest → Terminal 1 (B gates)
   - American → Terminal 2 (C/D gates) 
   - United → Terminal 3 (E/F gates)
   - International carriers → International Terminal (A/G gates)

2. AIRCRAFT SIZE COMPATIBILITY:
   - Medium (737, A320): Can use any gate size
   - Large (777, 787, A350): Need Large or Extra Large gates
   - Extra Large (A380, 747-8): Need Extra Large gates only

3. CUSTOMS REQUIREMENTS:
   - International arrivals → MUST use International Terminal (A/G gates)
   - Domestic flights → Can use any domestic terminal

4. OPERATIONAL EFFICIENCY:
   - Consider turnaround time requirements
   - Minimize passenger walking distances
   - Balance terminal traffic loads

5. GATE UTILIZATION:
   - Prefer gates with appropriate turnaround times
   - Consider gate availability duration

Analyze the flight requirements against available gates and respond with ONLY the gate number (e.g., "B5", "D3", "A7") that provides the BEST operational match considering all factors above."""

        try:
            completion = self.client.chat.completions.create(
                model="meta/llama-3.1-70b-instruct",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,  # Lower temperature for more consistent decisions
                top_p=0.9,
                max_tokens=15,
                stream=False
            )
            
            assigned_gate = completion.choices[0].message.content.strip()
            
            # Validate the assignment
            valid_gates = [str(g['gate']) for g in available_gates]
            if assigned_gate in valid_gates:
                # Find the selected gate for reasoning
                selected_gate = next((g for g in scored_gates if g['gate'] == assigned_gate), None)
                reason = self._generate_assignment_reason(flight, selected_gate, scored_gates)
                return assigned_gate, reason
            else:
                logger.warning(f"AI suggested invalid gate {assigned_gate}, using top-scored gate")
                fallback_gate = scored_gates[0]['gate']
                reason = f"AI suggested invalid gate, assigned top-scored compatible gate {fallback_gate}"
                return fallback_gate, reason
                
        except Exception as e:
            logger.error(f"Error during AI gate assignment: {e}")
            # Fallback to top-scored compatible gate
            fallback_gate = scored_gates[0]['gate'] if scored_gates else None
            reason = f"API error - assigned top-scored compatible gate due to technical issue"
            return fallback_gate, reason
    
    def _score_gates_for_flight(self, flight: Dict, available_gates: List[Dict]) -> List[Dict]:
        """Score and rank gates based on suitability for the flight"""
        scored_gates = []
        
        for gate in available_gates:
            score = 0
            
            # Airline preference matching (high priority)
            if gate['airline_pref'] == flight['airline']:
                score += 100
            elif gate['airline_pref'] == 'Any':
                score += 20
            
            # Terminal preference by airline
            airline_terminal_prefs = {
                'Southwest': 'Terminal 1',
                'United': 'Terminal 3', 
                'American': 'Terminal 2',
                'Alaska': ['Terminal 1', 'Terminal 2'],
                'Delta': ['Terminal 1', 'Terminal 2']
            }
            
            if flight['airline'] in airline_terminal_prefs:
                pref_terminals = airline_terminal_prefs[flight['airline']]
                if isinstance(pref_terminals, list):
                    if gate['terminal'] in pref_terminals:
                        score += 80
                else:
                    if gate['terminal'] == pref_terminals:
                        score += 80
            
            # Aircraft size compatibility
            aircraft_size = self.classify_aircraft_size(flight['aircraft_type'])
            if aircraft_size == "Medium" and gate['max_size'] in ["Medium", "Large", "Extra Large"]:
                score += 50
            elif aircraft_size == "Large" and gate['max_size'] in ["Large", "Extra Large"]:
                score += 50
            elif aircraft_size == "Extra Large" and gate['max_size'] == "Extra Large":
                score += 50
            else:
                score -= 100  # Size incompatible
            
            # International flight requirements
            is_intl = self.is_international_flight(flight['origin'])
            if is_intl and gate['customs'] == 'Yes':
                score += 60
            elif is_intl and gate['customs'] == 'No':
                score -= 200  # International flights MUST have customs
            
            # Turnaround time efficiency
            turnaround = gate.get('turnaround_mins', 45)
            if aircraft_size == "Extra Large" and turnaround >= 60:
                score += 30
            elif aircraft_size == "Large" and turnaround >= 45:
                score += 20
            elif aircraft_size == "Medium" and turnaround >= 30:
                score += 15
            
            # Passenger capacity considerations  
            passengers = int(flight.get('passengers', 0))
            if passengers > 300 and gate['max_size'] == "Extra Large":
                score += 25
            elif passengers > 180 and gate['max_size'] in ["Large", "Extra Large"]:
                score += 15
            
            gate_copy = gate.copy()
            gate_copy['score'] = score
            scored_gates.append(gate_copy)
        
        # Sort by score (highest first)
        return sorted(scored_gates, key=lambda x: x['score'], reverse=True)
    
    def _generate_assignment_reason(self, flight: Dict, selected_gate: Dict, all_gates: List[Dict]) -> str:
        """Generate detailed reasoning for the gate assignment"""
        if not selected_gate:
            return "No suitable gate available"
        
        reasons = []
        
        # Airline matching
        if selected_gate['airline_pref'] == flight['airline']:
            reasons.append(f"{flight['airline']} hub gate in {selected_gate['terminal']}")
        
        # Terminal appropriateness
        airline_terminal_map = {
            'Southwest': 'Terminal 1', 'United': 'Terminal 3', 'American': 'Terminal 2'
        }
        if flight['airline'] in airline_terminal_map:
            if selected_gate['terminal'] == airline_terminal_map[flight['airline']]:
                reasons.append(f"correct {flight['airline']} terminal")
        
        # International requirements
        if self.is_international_flight(flight['origin']) and selected_gate['customs'] == 'Yes':
            reasons.append("international arrival with customs capability")
        
        # Aircraft size
        aircraft_size = self.classify_aircraft_size(flight['aircraft_type'])
        reasons.append(f"{aircraft_size.lower()} aircraft fits {selected_gate['max_size'].lower()} gate")
        
        # Operational efficiency
        if selected_gate.get('score', 0) == max(g.get('score', 0) for g in all_gates):
            reasons.append("highest operational efficiency score")
        
        return f"Optimal assignment: {', '.join(reasons)}"
    
    def _analyze_gate_shortage(self, flight: Dict, all_available_gates: List[Dict]) -> str:
        """Analyze why no compatible gates are available and provide specific reasoning"""
        issues = []
        
        aircraft_size = self.classify_aircraft_size(flight['aircraft_type'])
        is_intl = self.is_international_flight(flight['origin'])
        airline = flight['airline']
        
        # Check if there are any gates at all
        if not all_available_gates:
            return "All gates currently occupied - high traffic period"
        
        # Check size compatibility issues
        size_compatible_gates = []
        for gate in all_available_gates:
            if aircraft_size == "Medium" and gate['max_size'] in ["Medium", "Large", "Extra Large"]:
                size_compatible_gates.append(gate)
            elif aircraft_size == "Large" and gate['max_size'] in ["Large", "Extra Large"]:
                size_compatible_gates.append(gate)
            elif aircraft_size == "Extra Large" and gate['max_size'] == "Extra Large":
                size_compatible_gates.append(gate)
        
        if not size_compatible_gates:
            issues.append(f"{aircraft_size} aircraft requires {aircraft_size.lower()} or larger gates, but none available")
        
        # Check international flight requirements
        if is_intl:
            intl_gates = [g for g in size_compatible_gates if g['customs'] == 'Yes']
            if not intl_gates:
                issues.append("International flight requires customs-capable gates, but none available")
        
        # Check airline hub constraints
        airline_terminal_prefs = {
            'Southwest': 'Terminal 1',
            'United': 'Terminal 3', 
            'American': 'Terminal 2'
        }
        
        if airline in airline_terminal_prefs:
            pref_terminal = airline_terminal_prefs[airline]
            terminal_gates = [g for g in size_compatible_gates if g['terminal'] == pref_terminal]
            if not terminal_gates and not is_intl:  # Don't suggest terminal changes for international
                issues.append(f"{airline} prefers {pref_terminal} but no suitable gates available there")
        
        # Check specific capacity constraints
        passengers = int(flight.get('passengers', 0))
        if passengers > 300:
            large_capacity_gates = [g for g in size_compatible_gates if g['max_size'] == "Extra Large"]
            if not large_capacity_gates:
                issues.append(f"High passenger count ({passengers}) requires extra-large gates")
        
        # Summary based on constraints found
        if not issues:
            return "Complex operational constraints prevent assignment"
        else:
            return "; ".join(issues[:2])  # Limit to top 2 issues for clarity
    
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
                # Analyze why no compatible gates available
                failure_reason = self._analyze_gate_shortage(flight.to_dict(), available_gates)
                logger.warning(f"No compatible gates available for {flight['flight_number']}: {failure_reason}")
                assigned_gate = "WAITING"
                assignment_reason = f"No assignment possible: {failure_reason}"
            else:
                # Use AI to assign optimal gate
                assigned_gate, assignment_reason = self.assign_gate_with_ai(flight.to_dict(), compatible_gates)
                
                if assigned_gate and assigned_gate != "WAITING":
                    # Mark gate as occupied
                    self.gate_occupancy_df.loc[
                        self.gate_occupancy_df['gate_number'] == assigned_gate, 'status'
                    ] = 'Occupied'
                    self.gate_occupancy_df.loc[
                        self.gate_occupancy_df['gate_number'] == assigned_gate, 'current_flight'
                    ] = flight['flight_number']
                    
                    # Update turnaround time if available
                    self.gate_occupancy_df.loc[
                        self.gate_occupancy_df['gate_number'] == assigned_gate, 'available_time'
                    ] = flight['scheduled_arrival']  # Will be available after arrival + turnaround
                else:
                    assigned_gate = "WAITING"
                    assignment_reason = "System error - no gate assigned despite availability"
            
            # Update arrivals dataframe
            self.arrivals_df.at[idx, 'gate_assigned'] = assigned_gate
            
            # Record assignment with detailed reasoning
            self.assignments.append({
                'timestamp': datetime.now().isoformat(),
                'flight_number': flight['flight_number'],
                'airline': flight['airline'],
                'aircraft_type': flight['aircraft_type'],
                'origin': flight['origin'],
                'assigned_gate': assigned_gate,
                'assignment_reason': assignment_reason,
                'passengers': flight['passengers'],
                'scheduled_arrival': flight['scheduled_arrival'],
                'status': flight['status']
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