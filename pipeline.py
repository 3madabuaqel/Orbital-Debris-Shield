import numpy as np
import pandas as pd
from datetime import datetime, timedelta, UTC
from skyfield.api import EarthSatellite, load
from scipy.spatial import KDTree
from xgboost import XGBClassifier
import joblib

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report,
    roc_auc_score,
    confusion_matrix,
    roc_curve
)
import matplotlib.pyplot as plt


# =========================
# MISS DISTANCE (Physics)
# =========================
def compute_miss_distance(a, b):

    r1 = np.array([a['x'], a['y'], a['z']])
    v1 = np.array([a['vx'], a['vy'], a['vz']])

    r2 = np.array([b['x'], b['y'], b['z']])
    v2 = np.array([b['vx'], b['vy'], b['vz']])

    rel_r = r1 - r2
    rel_v = v1 - v2

    t_ca = -np.dot(rel_r, rel_v) / (np.dot(rel_v, rel_v) + 1e-6)

    closest = rel_r + rel_v * t_ca

    return np.linalg.norm(closest)


# =========================
# LABEL (Physics-based)
# =========================
def compute_label_from_physics(a, b):

    d_min = compute_miss_distance(a, b)

    rel_speed = np.linalg.norm(
        np.array([a['vx'], a['vy'], a['vz']]) -
        np.array([b['vx'], b['vy'], b['vz']])
    )

    risk_score = (10 / (d_min + 1e-6)) * (rel_speed / 10)

    return 1 if risk_score > 1 else 0


# =========================
# CACHE
# =========================
position_cache = {}


def compute_positions(df, ts, time):

    key = str(time)

    if key in position_cache:
        return position_cache[key]

    if len(position_cache) > 200:
        position_cache.clear()

    results = []

    t = ts.utc(
        time.year, time.month, time.day,
        time.hour, time.minute, time.second
    )

    for _, row in df.iterrows():
        try:
            sat = EarthSatellite(row['TLE_LINE1'], row['TLE_LINE2'])

            geo = sat.at(t)
            sub = geo.subpoint()

            pos = geo.position.km
            vel = geo.velocity.km_per_s

            if sub.elevation.km > 36000:
                continue

            results.append({
                "name": row["OBJECT_NAME"],
                "type": row["OBJECT_TYPE"],
                "x": pos[0], "y": pos[1], "z": pos[2],
                "vx": vel[0], "vy": vel[1], "vz": vel[2],
                "alt": sub.elevation.km
            })

        except:
            continue

    df_out = pd.DataFrame(results)
    position_cache[key] = df_out
    return df_out


# =========================
# FEATURES
# =========================
def calculate_features(a, b):

    pos_a = np.array([a['x'], a['y'], a['z']])
    pos_b = np.array([b['x'], b['y'], b['z']])

    vel_a = np.array([a['vx'], a['vy'], a['vz']])
    vel_b = np.array([b['vx'], b['vy'], b['vz']])

    distance = np.linalg.norm(pos_a - pos_b)
    rel_vel = np.linalg.norm(vel_a - vel_b)
    alt_diff = abs(a['alt'] - b['alt'])

    angle = np.dot(vel_a, vel_b) / (
        np.linalg.norm(vel_a) * np.linalg.norm(vel_b) + 1e-6
    )

    return [distance, rel_vel, alt_diff, angle]


# =========================
# CANDIDATES
# =========================
def detect_candidates(df_positions, threshold=50):

    df_positions = df_positions.replace([np.inf, -np.inf], np.nan)
    df_positions = df_positions.dropna(subset=['x', 'y', 'z'])
    df_positions = df_positions.reset_index(drop=True)

    coords = df_positions[['x', 'y', 'z']].values

    if len(coords) < 2:
        return [], df_positions

    tree = KDTree(coords)
    pairs = tree.query_pairs(r=threshold)

    return pairs, df_positions


# =========================
# DATASET BUILDER
# =========================
def build_dataset(df, ts, start_time, days=30, step_hours=3):

    X, y = [], []

    steps = int((days * 24) / step_hours)

    for t_step in range(steps):

        t = start_time + timedelta(hours=t_step * step_hours)

        df_pos = compute_positions(df, ts, t)
        df_pos = df_pos.reset_index(drop=True)

        pairs, df_pos = detect_candidates(df_pos)

        for i, j in pairs:

            a = df_pos.iloc[i]
            b = df_pos.iloc[j]

            # filter
            if not (
                (a['type'] == 'DEBRIS' and b['type'] == 'PAYLOAD') or
                (b['type'] == 'DEBRIS' and a['type'] == 'PAYLOAD')
            ):
                continue

            X_row = calculate_features(a, b)
            label = compute_label_from_physics(a, b)

            # =========================
            # BALANCING
            # =========================
            if label == 0:
                if np.random.rand() > 0.30:
                    continue

            X.append(X_row)
            y.append(label)

    return np.array(X), np.array(y)


# =========================
# TRAIN MODEL
# =========================
def train_model(X, y):

    neg = np.sum(y == 0)
    pos = np.sum(y == 1)
    scale = neg / (pos + 1e-6)

    model = XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.08,
        objective='binary:logistic',
        eval_metric='logloss',
        scale_pos_weight=scale
    )

    model.fit(X, y)

    return model


# =========================
# EVALUATION
# =========================
def evaluate_model(model, X_test, y_test):

    prob = model.predict_proba(X_test)[:, 1]
    pred = (prob > 0.5).astype(int)

    print("\n📊 MODEL EVALUATION")
    print("===================")

    print("AUC:", roc_auc_score(y_test, prob))
    print("\nClassification Report:\n", classification_report(y_test, pred))

    print("\nConfusion Matrix:")
    print(confusion_matrix(y_test, pred))

    # ROC curve
    fpr, tpr, _ = roc_curve(y_test, prob)

    plt.plot(fpr, tpr)
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("ROC Curve")
    plt.show()


# =========================
# MAIN PIPELINE
# =========================
def build_model():

    print("🚀 Loading data...")

    df = pd.read_csv("orbital_data_export.csv")
    ts = load.timescale()

    print("📦 Building dataset...")
    X, y = build_dataset(df, ts, datetime.now(UTC))

    print(f"Dataset size: {len(X)} samples")
    print("Class distribution:", np.bincount(y))

    # FIXED SPLIT (no leakage)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.2,
        random_state=42,
        stratify=y
    )

    print("🧠 Training model...")
    model = train_model(X_train, y_train)

    print("📊 Evaluating model...")
    evaluate_model(model, X_test, y_test)

    joblib.dump(model, "model.pkl")

    print("✅ Model saved as model.pkl")


if __name__ == "__main__":
    build_model()