import json
import os

def load_medicines():
    """Load medicines from the JSON file."""
    try:
        with open('medicine_dataset/medicines.json', 'r') as file:
            data = json.load(file)
            return data['medicines']
    except FileNotFoundError:
        print("Medicine dataset file not found.")
        return []
    except json.JSONDecodeError:
        print("Error reading medicine dataset file.")
        return []

def search_medicine(query):
    """Search for a medicine by name."""
    medicines = load_medicines()
    query = query.lower()
    
    # Search for exact match first
    for medicine in medicines:
        if medicine['name'].lower() == query:
            return medicine
    
    # Search for partial matches
    matches = []
    for medicine in medicines:
        if query in medicine['name'].lower():
            matches.append(medicine)
    
    return matches[0] if matches else None

def get_all_medicines():
    """Get all medicines from the dataset."""
    return load_medicines() 