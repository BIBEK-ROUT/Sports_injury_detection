"""
regenerate_dataset.py
=====================
Generates a realistic synthetic dataset for XGBoost injury risk classification.

KEY FIX vs previous dataset:
  The old dataset made knee angle the PRIMARY risk driver (low angle = high risk).
  This caused normal sprinting (85° knee) to always predict HIGH/CRITICAL.

  The new dataset makes BINARY FLAGS the primary risk driver.
  Continuous angles OVERLAP across all risk classes, just as in real sport.
  A sprinter (85° knee, 32° trunk lean) with zero flags = LOW RISK.
  The same angles with knee_valgus + low_symmetry flags = HIGH RISK.

Risk class definitions:
  0 = Low      : 0 flags active, symmetry > 70%, normal biomechanics
  1 = Moderate : 1 flag active OR symmetry 60-70%, minor concerns
  2 = High     : 2+ flags active OR symmetry < 60%, clear red flags
  3 = Critical : 3+ flags active AND severe angle deviations
"""

import numpy as np
import pandas as pd
import os

RANDOM_SEED  = 42
SAMPLES_PER_CLASS = 15_000
OUTPUT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "datasets", "synthetic", "sport_injury_dataset.csv"
)
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

rng = np.random.default_rng(RANDOM_SEED)

SPORTS = [
    "BASKETBALL", "SOCCER", "TENNIS", "BASEBALL", "AMERICAN_FOOTBALL",
    "VOLLEYBALL", "TRACK", "SWIMMING", "BOXING", "WRESTLING",
    "RUGBY", "HOCKEY", "BADMINTON", "GYMNASTICS", "CYCLING", "CRICKET", "OTHER"
]

def rand(lo, hi, n):
    return rng.uniform(lo, hi, n)

def clip(arr, lo, hi):
    return np.clip(arr, lo, hi)


# ── IMPORTANT: knee_flexion and trunk_lean OVERLAP across all classes ──────────
# This mirrors reality: a sprinter's 85° knee is not inherently risky.
# What differs is the FLAGS (hyperextension, valgus, low_sym) and symmetry.

def make_class(n, risk_class):
    sports = rng.choice(SPORTS, n)

    # ── Continuous angles: wide realistic ranges, overlapping across classes ──
    # All athletes (any risk) can have deeply bent knees in dynamic motion.
    # Knee flexion: 60-170° is realistic across all phases of sport.
    # Lower mean for higher risk = slightly more extreme positions on average,
    # but with significant overlap. Flags carry the primary classification signal.
    if risk_class == 0:   # Low  - good form at any speed
        knee   = rand(75, 170, n)        # Full range: sprint to standing
        hip    = rand(90, 175, n)
        elbow  = rand(90, 175, n)
        shoulder = rand(20, 100, n)
        trunk  = rand(0,  38, n)         # Up to 38° (valid sprint lean)
        valgus = rand(162, 182, n)       # Near-healthy frontal plane angle
        sym    = rand(0.70, 1.00, n)     # Good bilateral symmetry

        # Binary flags: mostly 0, rarely 1 (incidental edge cases)
        f_hyperext = rng.integers(0, 2, n) * (rand(0,1,n) > 0.93).astype(int)
        f_valgus   = rng.integers(0, 2, n) * (rand(0,1,n) > 0.95).astype(int)
        f_trunk    = rng.integers(0, 2, n) * (rand(0,1,n) > 0.95).astype(int)
        f_sym      = rng.integers(0, 2, n) * (rand(0,1,n) > 0.97).astype(int)

    elif risk_class == 1: # Moderate - 1 flag, or consistently poor symmetry
        knee   = rand(65, 165, n)
        hip    = rand(80, 165, n)
        elbow  = rand(85, 175, n)
        shoulder = rand(20, 120, n)
        trunk  = rand(10, 50, n)
        valgus = rand(155, 175, n)
        sym    = rand(0.58, 0.82, n)

        # Exactly 1 flag is active for most samples
        f_hyperext = (rand(0,1,n) > 0.65).astype(int)
        f_valgus   = (rand(0,1,n) > 0.65).astype(int)
        f_trunk    = (rand(0,1,n) > 0.70).astype(int)
        f_sym      = (rand(0,1,n) > 0.65).astype(int)
        # Cap: max 1 flag active on average
        total = f_hyperext + f_valgus + f_trunk + f_sym
        # For samples with 0 flags, force at least one
        zero_mask = total == 0
        f_valgus[zero_mask] = 1
        # For samples with 3+, zero out some
        hi_mask = total >= 3
        f_trunk[hi_mask]    = 0
        f_sym[hi_mask]      = 0

    elif risk_class == 2: # High - 2+ flags, lower symmetry
        knee   = rand(55, 145, n)
        hip    = rand(65, 145, n)
        elbow  = rand(80, 170, n)
        shoulder = rand(20, 140, n)
        trunk  = rand(25, 65, n)
        valgus = rand(145, 165, n)
        sym    = rand(0.42, 0.68, n)

        f_hyperext = (rand(0,1,n) > 0.40).astype(int)
        f_valgus   = (rand(0,1,n) > 0.30).astype(int)
        f_trunk    = (rand(0,1,n) > 0.35).astype(int)
        f_sym      = (rand(0,1,n) > 0.35).astype(int)
        # Ensure at least 2 flags for most samples
        total = f_hyperext + f_valgus + f_trunk + f_sym
        low_mask = total < 2
        f_valgus[low_mask]   = 1
        f_hyperext[low_mask] = 1

    else:                 # Critical - 3+ flags, severe positions
        knee   = rand(20, 100, n)
        hip    = rand(35, 110, n)
        elbow  = rand(75, 155, n)
        shoulder = rand(20, 160, n)
        trunk  = rand(40, 90, n)
        valgus = rand(120, 152, n)
        sym    = rand(0.10, 0.52, n)

        f_hyperext = (rand(0,1,n) > 0.15).astype(int)
        f_valgus   = (rand(0,1,n) > 0.10).astype(int)
        f_trunk    = (rand(0,1,n) > 0.15).astype(int)
        f_sym      = (rand(0,1,n) > 0.10).astype(int)
        # Ensure at least 3 flags
        total = f_hyperext + f_valgus + f_trunk + f_sym
        low_mask = total < 3
        f_valgus[low_mask]   = 1
        f_hyperext[low_mask] = 1
        f_trunk[low_mask]    = 1

    return pd.DataFrame({
        "sport_type":          sports,
        "knee_flexion":        clip(knee,    20,  180).round(2),
        "hip_angle":           clip(hip,     30,  180).round(2),
        "elbow_angle":         clip(elbow,   40,  180).round(2),
        "shoulder_rotation":   clip(shoulder, 0, 180).round(2),
        "trunk_lean":          clip(trunk,    0,  90).round(2),
        "knee_valgus_angle":   clip(valgus, 110,  185).round(2),
        "symmetry":            clip(sym,    0.05, 1.00).round(4),
        "flag_knee_hyperext":  f_hyperext,
        "flag_knee_valgus":    f_valgus,
        "flag_trunk_lean":     f_trunk,
        "flag_low_symmetry":   f_sym,
        "risk_level":          risk_class,
    })


print("Generating realistic synthetic dataset...")
frames = [make_class(SAMPLES_PER_CLASS, c) for c in range(4)]
df = pd.concat(frames, ignore_index=True)
df = df.sample(frac=1, random_state=RANDOM_SEED).reset_index(drop=True)

print(f"Total rows: {len(df):,}")
print("\nClass distribution:")
print(df["risk_level"].value_counts().sort_index())
print("\nFeature means per class (now with OVERLAPPING angles):")
print(df.groupby("risk_level")[["knee_flexion","trunk_lean","symmetry","flag_knee_valgus","flag_low_symmetry"]].mean().round(2))

df.to_csv(OUTPUT_PATH, index=False)
print(f"\nSaved to: {OUTPUT_PATH}")
