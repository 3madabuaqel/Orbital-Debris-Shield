import matplotlib.pyplot as plt
import math
import csv
import os

# --- 1. البحث عن الملف ---
filename = 'orbital_debris_final.csv'
file_path = None

for root, dirs, files in os.walk(os.getcwd()):
    if filename in files:
        file_path = os.path.join(root, filename)
        break

if file_path:
    print(f"✅ لقينا الملف في: {file_path}")
else:
    print("⚠️ الملف مش موجود، عملنا ملف تجريبي.")
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['NORAD_ID', 'INCLINATION', 'MEAN_MOTION', 'ECCENTRICITY'])
        writer.writerow(['41901', '98.2', '14.5', '0.0001'])
        writer.writerow(['25544', '51.6', '15.5', '0.0003'])
    file_path = filename

# --- 2. إعدادات ---
sat_x, sat_y = 0, 10
sat_speed = 0.3
RADAR_RANGE = 5
SAFE_DISTANCE = 1.5
warnings_count = 0
debris_list = []

# قراءة البيانات
with open(file_path, 'r') as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        if i >= 8: break
        debris_list.append([
            25.0,
            float(row.get('INCLINATION', 10)) / 5,
            -(float(row.get('MEAN_MOTION', 15)) / 40),
            0.0,
            row.get('NORAD_ID', '00000')
        ])

# --- 3. المحاكاة ---
plt.figure(figsize=(9, 7))

for step in range(70):

    # حفظ الموقع السابق
    prev_sat_x, prev_sat_y = sat_x, sat_y

    # حركة القمر
    sat_x += sat_speed

    plt.clf()

    # رسم مسار القمر
    plt.plot([prev_sat_x, sat_x], [prev_sat_y, sat_y], c='blue')

    # رادار
    plt.gca().add_patch(
        plt.Circle((sat_x, sat_y), RADAR_RANGE, color='blue', alpha=0.1)
    )

    plt.scatter(sat_x, sat_y, c='blue', s=120, label='Satellite')

    for d in debris_list:

        # حفظ موقع الحطام السابق
        prev_dx, prev_dy = d[0], d[1]

        # حركة الحطام
        d[0] += d[2]

        # رسم مسار الحطام
        plt.plot([prev_dx, d[0]], [prev_dy, d[1]], c='red', alpha=0.5)

        dist = math.hypot(sat_x - d[0], sat_y - d[1])

        if dist < RADAR_RANGE:
            plt.scatter(d[0], d[1], c='red', s=40)
            plt.text(d[0], d[1]+0.3, f"ID:{d[4]}", fontsize=8, weight='bold')

            # تجنب التصادم
            if dist < SAFE_DISTANCE:
                warnings_count += 1
                sat_y += 0.6   # تعديل ناعم بدل قفزة كبيرة
                plt.title(f"⚠️ COLLISION AVOIDED WITH {d[4]}", color='red')

        else:
            plt.scatter(d[0], d[1], c='gray', s=15, alpha=0.3)

    plt.xlim(0, 30)
    plt.ylim(0, 20)
    plt.grid(True, linestyle='--', alpha=0.3)

    plt.pause(0.15)  # سرعة مناسبة

plt.show()

print(f"Total Warnings: {warnings_count}")




















































