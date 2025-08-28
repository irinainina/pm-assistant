import json
import os
import time

DB_STATE_FILE = "data/db_state.json"

def get_last_update_time():
    if not os.path.exists(DB_STATE_FILE):
        return None
        
    try:
        with open(DB_STATE_FILE, 'r') as f:
            data = json.load(f)
            return data.get('last_update_timestamp')
    except:
        return None

def set_last_update_time():
    os.makedirs(os.path.dirname(DB_STATE_FILE), exist_ok=True)
    
    data = {
        'last_update_timestamp': time.time(),
        'last_update_human': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    with open(DB_STATE_FILE, 'w') as f:
        json.dump(data, f, indent=2)
