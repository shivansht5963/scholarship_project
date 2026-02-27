"""
scholarships/data/districts.py

Offline India district/city tier classification.
Source: Government of India DIPP classification + census data.

Tier-1  = 8 major metros (not rural, not tier-2)
Tier-2  = Government Category B cities + state capitals
Default = everything else is classified as rural/semi-urban

Usage: imported by pin_classifier.py — never call directly.
"""

# ── Tier-1 Metropolitan Districts ─────────────────────────────────────────────
TIER1_DISTRICTS = {
    # match against lowercase city/district name
    "delhi", "new delhi", "central delhi", "north delhi", "south delhi",
    "east delhi", "west delhi", "north west delhi", "south west delhi",
    "north east delhi",
    "mumbai", "mumbai suburban", "thane",
    "bengaluru", "bangalore", "bangalore urban", "bangalore rural",
    "hyderabad", "rangareddy", "medchal",
    "chennai",
    "kolkata", "north 24 parganas", "south 24 parganas", "howrah",
    "pune",
    "ahmedabad",
    "surat",
}

# ── Tier-2 Cities (Government Category B + key state capitals) ────────────────
TIER2_DISTRICTS = {
    # Rajasthan
    "jaipur", "jodhpur", "udaipur", "kota", "ajmer", "bikaner",
    # UP
    "lucknow", "agra", "kanpur", "varanasi", "meerut", "allahabad",
    "prayagraj", "ghaziabad", "noida", "greater noida", "gorakhpur",
    "aligarh", "bareilly", "moradabad", "firozabad", "mathura",
    # MP
    "bhopal", "indore", "gwalior", "jabalpur", "ujjain", "rewa",
    # Maharashtra
    "nashik", "nagpur", "aurangabad", "amravati", "solapur", "kolhapur",
    "sangli", "nanded",
    # Gujarat
    "vadodara", "rajkot", "bhavnagar", "jamnagar", "gandhinagar", "junagadh",
    # Punjab / Haryana
    "ludhiana", "amritsar", "jalandhar", "patiala", "chandigarh",
    "faridabad", "gurgaon", "gurugram", "ambala", "rohtak", "hisar",
    "panipat", "sonipat",
    # Bihar / Jharkhand
    "patna", "gaya", "muzaffarpur", "bhagalpur", "ranchi", "dhanbad",
    "jamshedpur", "bokaro",
    # West Bengal
    "durgapur", "asansol", "siliguri", "bardhaman",
    # Tamil Nadu
    "coimbatore", "madurai", "tiruchirappalli", "tirupur", "salem",
    "vellore", "erode", "tirunelveli", "thoothukudi",
    # Kerala
    "kochi", "ernakulam", "thiruvananthapuram", "kozhikode", "thrissur",
    "kollam", "malappuram", "kannur",
    # Karnataka
    "mysuru", "mysore", "hubli", "dharwad", "belgaum", "belagavi",
    "mangaluru", "mangalore", "shimoga",
    # Telangana / AP
    "warangal", "nizamabad", "karimnagar", "vijayawada", "visakhapatnam",
    "vizag", "tirupati", "guntur", "rajahmundry",
    # Odisha
    "bhubaneswar", "cuttack", "rourkela", "berhampur",
    # Assam / NE
    "guwahati", "silchar", "dibrugarh",
    # Himachal / Uttarakhand
    "shimla", "dehradun", "haridwar", "rishikesh", "roorkee", "mussorie",
    # Chhattisgarh
    "raipur", "bhilai", "bilaspur", "durg",
    # J&K / HP
    "jammu", "srinagar", "leh",
    # Goa
    "panaji", "margao", "vasco da gama",
    # Others
    "raigarh", "korba", "dhamtari", "kalyani", "berhampore", "kharagpur",
    "burdwan", "haldia", "dhule", "latur", "solapur",
}

# ── States (normalized) for metadata ──────────────────────────────────────────
KNOWN_STATES = {
    "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh",
    "goa", "gujarat", "haryana", "himachal pradesh", "jharkhand",
    "karnataka", "kerala", "madhya pradesh", "maharashtra", "manipur",
    "meghalaya", "mizoram", "nagaland", "odisha", "punjab", "rajasthan",
    "sikkim", "tamil nadu", "telangana", "tripura", "uttar pradesh",
    "uttarakhand", "west bengal", "delhi", "jammu & kashmir",
    "jammu and kashmir", "ladakh", "puducherry", "chandigarh",
    "andaman and nicobar islands", "dadra and nagar haveli", "lakshadweep",
}
