#!/usr/bin/env python3
"""
Gate-Genie Web Server
Simple Flask server to display real-time gate assignments
"""

from flask import Flask, render_template, jsonify, send_from_directory
import pandas as pd
import json
import os
from datetime import datetime
import threading
import time
from gate_genie import GateGenie

app = Flask(__name__)

# Global data store
dashboard_data = {
    'arrivals': [],
    'assignments': [],
    'gate_occupancy': [],
    'gates_config': [],
    'last_updated': datetime.now().isoformat()
}

def load_data():
    """Load data from CSV files"""
    global dashboard_data
    
    try:
        # Load arrivals with gates if exists, otherwise original arrivals
        if os.path.exists("data/arrivals_with_gates.csv"):
            arrivals_df = pd.read_csv("data/arrivals_with_gates.csv")
        else:
            arrivals_df = pd.read_csv("data/arrivals.csv")
        
        # Load other data
        gates_config_df = pd.read_csv("data/gates_config.csv")
        
        if os.path.exists("data/gate_occupancy_updated.csv"):
            gate_occupancy_df = pd.read_csv("data/gate_occupancy_updated.csv")
        else:
            gate_occupancy_df = pd.read_csv("data/gate_occupancy.csv")
        
        assignments = []
        if os.path.exists("data/gate_assignments_log.csv"):
            assignments_df = pd.read_csv("data/gate_assignments_log.csv")
            assignments = assignments_df.to_dict('records')
        
        # Update global data
        dashboard_data.update({
            'arrivals': arrivals_df.to_dict('records'),
            'assignments': assignments,
            'gate_occupancy': gate_occupancy_df.to_dict('records'),
            'gates_config': gates_config_df.to_dict('records'),
            'last_updated': datetime.now().isoformat()
        })
        
        print(f"Data loaded successfully at {dashboard_data['last_updated']}")
        
    except Exception as e:
        print(f"Error loading data: {e}")

def simulate_real_time_updates():
    """Simulate real-time updates by periodically running gate assignments"""
    while True:
        try:
            print("Running real-time gate assignment update...")
            
            # Initialize Gate-Genie with API key
            API_KEY = "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"
            gate_genie = GateGenie(API_KEY)
            
            # Process any new arrivals
            gate_genie.process_arrivals()
            
            # Reload data
            load_data()
            
            # Wait 5 minutes before next update
            time.sleep(300)
            
        except Exception as e:
            print(f"Error in real-time update: {e}")
            time.sleep(60)  # Wait 1 minute before retrying

@app.route('/')
def index():
    """Serve the main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/data')
def get_data():
    """API endpoint to get all dashboard data"""
    return jsonify(dashboard_data)

@app.route('/api/arrivals')
def get_arrivals():
    """API endpoint to get arrivals data"""
    return jsonify({
        'arrivals': dashboard_data['arrivals'],
        'last_updated': dashboard_data['last_updated']
    })

@app.route('/api/gates')
def get_gates():
    """API endpoint to get gate occupancy data"""
    return jsonify({
        'gate_occupancy': dashboard_data['gate_occupancy'],
        'gates_config': dashboard_data['gates_config'],
        'last_updated': dashboard_data['last_updated']
    })

@app.route('/api/assignments')
def get_assignments():
    """API endpoint to get recent gate assignments"""
    return jsonify({
        'assignments': dashboard_data['assignments'],
        'last_updated': dashboard_data['last_updated']
    })

@app.route('/refresh')
def refresh_data():
    """Manual refresh endpoint"""
    load_data()
    return jsonify({
        'status': 'success',
        'message': 'Data refreshed successfully',
        'last_updated': dashboard_data['last_updated']
    })

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    # Load initial data
    load_data()
    
    # Start real-time update thread
    update_thread = threading.Thread(target=simulate_real_time_updates, daemon=True)
    update_thread.start()
    
    print("Gate-Genie Web Server starting...")
    print("Dashboard will be available at: http://localhost:5000")
    
    # Run Flask app
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False) 