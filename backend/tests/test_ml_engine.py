"""
Machine Learning Engine & Biomechanics Unit Tests.
"""

from app.ml.inference import predict_injury_risk, RiskPrediction
from app.ml.biomechanics.math_utils import calculate_angle_3d, calculate_symmetry, calculate_trunk_lean


def test_predict_injury_risk_valid():
    """Verifies predict_injury_risk returns a valid RiskPrediction object."""
    pred = predict_injury_risk(
        sport_type="BASKETBALL",
        knee_flexion=145.0,
        hip_angle=155.0,
        elbow_angle=160.0,
        shoulder_rotation=15.0,
        trunk_lean=12.0,
        knee_valgus_angle=175.0,
        symmetry=0.95,
        flag_knee_hyperext=0,
        flag_knee_valgus=0,
        flag_trunk_lean=0,
        flag_low_symmetry=0,
    )
    assert isinstance(pred, RiskPrediction)
    assert pred.risk_level in ["low", "moderate", "high", "critical"]
    assert 0.0 <= pred.confidence <= 1.0
    assert "low" in pred.probabilities
    assert "high" in pred.probabilities


def test_predict_injury_risk_extreme_flags():
    """Verifies that high risk flags elevate injury risk."""
    pred = predict_injury_risk(
        sport_type="SOCCER",
        knee_flexion=185.0,
        hip_angle=120.0,
        elbow_angle=160.0,
        shoulder_rotation=35.0,
        trunk_lean=38.0,
        knee_valgus_angle=150.0,
        symmetry=0.55,
        flag_knee_hyperext=1,
        flag_knee_valgus=1,
        flag_trunk_lean=1,
        flag_low_symmetry=1,
    )
    assert pred.risk_level in ["moderate", "high", "critical"]


def test_calculate_angle_3d_geometry():
    """Verifies joint angle 3D trigonometry."""
    # Right angle (90 deg)
    a = (0.0, 1.0, 0.0)
    b = (0.0, 0.0, 0.0)
    c = (1.0, 0.0, 0.0)
    angle = calculate_angle_3d(a, b, c)
    assert round(angle, 1) == 90.0

    # Straight line (180 deg)
    a = (0.0, 1.0, 0.0)
    b = (0.0, 0.0, 0.0)
    c = (0.0, -1.0, 0.0)
    angle = calculate_angle_3d(a, b, c)
    assert round(angle, 1) == 180.0


def test_calculate_symmetry():
    """Verifies symmetry ratio calculation."""
    # Identical angles = 1.0 (100% symmetry)
    assert calculate_symmetry(140.0, 140.0) == 1.0

    # 10% asymmetry
    sym = calculate_symmetry(90.0, 100.0)
    assert 0.85 <= sym <= 0.95
