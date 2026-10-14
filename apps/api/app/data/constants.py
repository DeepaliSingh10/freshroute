"""Generation constants: commodity catalog, locations, and grade factors."""

from __future__ import annotations

# Relative price a batch of a given quality grade commands (multiplier on destination price).
GRADE_PRICE_FACTOR = {"A": 1.05, "B": 1.0, "C": 0.9}

# Perishability classes recognized across the dataset.
PERISHABILITY_CLASSES = ("leafy", "berry", "soft_fruit", "root", "tuber")

# Commodity catalog. `shelf` = base shelf life (days); `price` = base market price (INR/kg);
# `pop` = relative demand weight. cost_basis is derived as 60% of price.
COMMODITY_CATALOG = [
    {"id": "TOM", "name": "Tomato", "cls": "soft_fruit", "shelf": 7, "price": 28, "pop": 1.5},
    {"id": "SPN", "name": "Spinach", "cls": "leafy", "shelf": 3, "price": 22, "pop": 1.0},
    {"id": "STR", "name": "Strawberry", "cls": "berry", "shelf": 4, "price": 180, "pop": 0.4},
    {"id": "MAN", "name": "Mango", "cls": "soft_fruit", "shelf": 9, "price": 70, "pop": 1.2},
    {"id": "BAN", "name": "Banana", "cls": "soft_fruit", "shelf": 12, "price": 35, "pop": 1.6},
    {"id": "ONI", "name": "Onion", "cls": "root", "shelf": 60, "price": 18, "pop": 1.4},
    {"id": "POT", "name": "Potato", "cls": "tuber", "shelf": 45, "price": 16, "pop": 1.5},
    {"id": "CAU", "name": "Cauliflower", "cls": "leafy", "shelf": 6, "price": 30, "pop": 0.9},
    {"id": "GRP", "name": "Grapes", "cls": "berry", "shelf": 8, "price": 90, "pop": 0.7},
    {"id": "OKR", "name": "Okra", "cls": "soft_fruit", "shelf": 5, "price": 40, "pop": 0.8},
]

# Origins (farm aggregation hubs): (id, name, lat, lon).
ORIGIN_CATALOG = [
    ("ORG-NSK", "Nashik Hub", 20.00, 73.79),
    ("ORG-PUN", "Pune Rural Hub", 18.52, 73.86),
    ("ORG-RTN", "Ratnagiri Coastal Hub", 16.99, 73.31),
    ("ORG-IND", "Indore Hub", 22.72, 75.86),
    ("ORG-LDH", "Ludhiana Hub", 30.90, 75.86),
]

# Destinations (markets): (id, name, region, lat, lon).
DESTINATION_CATALOG = [
    ("DST-MUM", "Mumbai", "West", 19.08, 72.88),
    ("DST-DEL", "Delhi", "North", 28.61, 77.21),
    ("DST-BLR", "Bengaluru", "South", 12.97, 77.59),
    ("DST-HYD", "Hyderabad", "South", 17.39, 78.49),
    ("DST-CHN", "Chennai", "South", 13.08, 80.27),
    ("DST-KOL", "Kolkata", "East", 22.57, 88.36),
    ("DST-AMD", "Ahmedabad", "West", 23.02, 72.57),
    ("DST-NAG", "Nagpur", "Central", 21.15, 79.09),
    ("DST-LKO", "Lucknow", "North", 26.85, 80.95),
    ("DST-JAI", "Jaipur", "North", 26.91, 75.79),
]

# Delivery windows (HH:MM) assigned round-robin to destinations.
DELIVERY_WINDOWS = [("06:00", "12:00"), ("08:00", "14:00"), ("10:00", "18:00")]

# Truck average speed (km/h) and fixed loading/inspection overhead (h) for travel-time.
AVG_SPEED_KMH = 45.0
TRAVEL_OVERHEAD_HOURS = 0.5
