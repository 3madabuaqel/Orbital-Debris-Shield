from spacetrack import SpaceTrackClient
import csv

# --- Configuration & Authentication ---
# Using your credentials from the previous step
# st = SpaceTrackClient(identity='email', password='password')

filename = 'orbital_debris_final.csv'

# Professional Headers (10 Columns)
headers = [
    'NORAD_ID', 
    'OBJECT_NAME', 
    'INCLINATION', 
    'RAAN', 
    'ECCENTRICITY', 
    'ARG_OF_PERIGEE', 
    'MEAN_ANOMALY', 
    'MEAN_MOTION', 
    'BSTAR', 
    'EPOCH'
]



try:
    # Fetching data using the optimized GP class
    data = st.gp(
        decay_date='null-val', 
        creation_date='>now-60', 
        object_type='DEBRIS', 
        format='tle'
    )

    lines = data.strip().split('\n')
    total_objects = len(lines) // 2
    print(f"Successfully retrieved {total_objects} debris objects.\n")

    # --- Processing and Saving to CSV ---
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        # Write the header row
        writer.writerow(headers)

        # Iterate through TLE pairs
        for i in range(0, len(lines), 2):
            l1 = lines[i].strip()
            l2 = lines[i+1].strip()

            if len(l1) < 60 or len(l2) < 60:
                continue

            # --- Extraction from Line 1 ---
            norad_id = l1[2:7].strip()
            # BSTAR (Drag Term): Found at index 53-61
            bstar_raw = l1[53:61].strip()
            epoch = l1[18:32].strip()

            # --- Extraction from Line 2 ---
            inclination = l2[8:16].strip()
            raan = l2[17:25].strip()
            # Eccentricity (Implied decimal point)
            eccentricity = "0." + l2[26:33].strip()
            arg_perigee = l2[34:42].strip()
            mean_anomaly = l2[43:51].strip()
            mean_motion = l2[52:63].strip()

            # --- Saving Row ---
            # We add "UNKNOWN_DEBRIS" as a placeholder for OBJECT_NAME 
            # because raw TLE format doesn't include the name inside the two lines.
            writer.writerow([
                norad_id, 
                "DEBRIS_" + norad_id, 
                inclination, 
                raan, 
                eccentricity, 
                arg_perigee, 
                mean_anomaly, 
                mean_motion, 
                bstar_raw, 
                epoch
            ])

    print(f"✅ Clean CSV generated: {filename}")
    print("Columns are now perfectly aligned with their headers.")

except Exception as e:
    print(f"❌ An error occurred: {e}")