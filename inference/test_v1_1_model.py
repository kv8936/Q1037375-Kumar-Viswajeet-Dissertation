"""
Test script for v1.1 candidate model integration.

Tests:
- Model files exist
- Config file exists
- Model loads without error
- Sample electrical case produces a hazard prediction
- severity_score=8 produces High risk level
- Fire escape route obstructed case triggers manual_review=True
"""

import json
import sys
from pathlib import Path

# Ensure we can import from services
sys.path.insert(0, str(Path(__file__).parent))

from services.hazard_model_service import load_hazard_model_v1_1


def test_files_exist():
    """Check that model and config files exist."""
    print("Test 1: Model and config files exist...")
    
    model_path = Path(__file__).resolve().parent.parent / "models" / "v1_1_candidate" / "hazard_category_model_v1_1_candidate.joblib"
    config_path = Path(__file__).resolve().parent.parent / "models" / "v1_1_candidate" / "hybrid_model_config_v1_1_candidate.json"
    
    assert model_path.exists(), f"Model file not found: {model_path}"
    print(f"  ✓ Model file exists: {model_path}")
    
    assert config_path.exists(), f"Config file not found: {config_path}"
    print(f"  ✓ Config file exists: {config_path}")


def test_model_loads():
    """Check that model loads successfully."""
    print("\nTest 2: Model loads without error...")
    
    model = load_hazard_model_v1_1()
    assert model.ready, f"Model failed to load: {model.load_error}"
    print(f"  ✓ Model loaded successfully")
    print(f"  ✓ Config version: {model.config.get('version', 'unknown')}")


def test_sample_electrical_prediction():
    """Test prediction on electrical hazard scenario."""
    print("\nTest 3: Sample electrical case produces hazard prediction...")
    
    model = load_hazard_model_v1_1()
    
    sample_input = (
        "Workplace scenario: Loose wiring is visible near an electrical panel during maintenance work. | "
        "Location: maintenance area | "
        "Visual context from image caption: Not available"
    )
    
    result = model.predict_v1_1_candidate(sample_input, severity_score=5.0)
    
    assert result["hazard_category"], "No hazard category predicted"
    assert result["hazard_confidence"] > 0, "No confidence score"
    print(f"  ✓ Predicted hazard: {result['hazard_category']}")
    print(f"  ✓ Confidence: {result['hazard_confidence_percent']}")
    print(f"  ✓ Risk level: {result['risk_level']}")


def test_severity_score_high():
    """Test that severity_score=8 produces High risk level."""
    print("\nTest 4: severity_score=8 produces High risk level...")
    
    model = load_hazard_model_v1_1()
    
    sample_input = "Generic workplace hazard scenario"
    result = model.predict_v1_1_candidate(sample_input, severity_score=8.0)
    
    assert result["severity_score"] == 8.0, "Severity score not recorded"
    assert result["risk_level"] == "High", f"Expected High, got {result['risk_level']}"
    print(f"  ✓ Severity score 8.0 → Risk level: {result['risk_level']}")


def test_severity_score_medium():
    """Test that severity_score=5 produces Medium risk level."""
    print("\nTest 5: severity_score=5 produces Medium risk level...")
    
    model = load_hazard_model_v1_1()
    
    sample_input = "Generic workplace hazard scenario"
    result = model.predict_v1_1_candidate(sample_input, severity_score=5.0)
    
    assert result["risk_level"] == "Medium", f"Expected Medium, got {result['risk_level']}"
    print(f"  ✓ Severity score 5.0 → Risk level: {result['risk_level']}")


def test_severity_score_low():
    """Test that severity_score=2 produces Low risk level."""
    print("\nTest 6: severity_score=2 produces Low risk level...")
    
    model = load_hazard_model_v1_1()
    
    sample_input = "Generic workplace hazard scenario"
    result = model.predict_v1_1_candidate(sample_input, severity_score=2.0)
    
    assert result["risk_level"] == "Low", f"Expected Low, got {result['risk_level']}"
    print(f"  ✓ Severity score 2.0 → Risk level: {result['risk_level']}")


def test_fire_escape_obstruction_triggers_review():
    """Test that fire escape + obstruction triggers manual_review."""
    print("\nTest 7: Fire escape route obstructed case triggers manual_review=True...")
    
    model = load_hazard_model_v1_1()
    
    # Scenario with fire escape and obstruction keywords
    sample_input = (
        "Workplace scenario: Fire escape route is partially blocked by storage boxes. | "
        "Location: emergency stairwell | "
        "Visual context from image caption: Boxes stacked near exit"
    )
    
    result = model.predict_v1_1_candidate(sample_input, severity_score=4.0)
    
    assert result["needs_manual_review"] == True, "Fire obstruction case should trigger manual review"
    assert "fire/exit-route obstruction ambiguity detected" in result["manual_review_reason"]
    print(f"  ✓ Fire escape obstruction detected → manual_review: {result['needs_manual_review']}")
    print(f"  ✓ Reason: {result['manual_review_reason']}")


def test_low_confidence_triggers_review():
    """Test that low confidence (if model produces it) triggers manual_review."""
    print("\nTest 8: Low confidence scenarios are flagged for review...")
    
    model = load_hazard_model_v1_1()
    
    # Generic input that may produce lower confidence
    sample_input = "Some text"
    result = model.predict_v1_1_candidate(sample_input, severity_score=4.0)
    
    if result["hazard_confidence"] < 0.40:
        assert result["needs_manual_review"] == True, "Low confidence should trigger manual review"
        print(f"  ✓ Confidence {result['hazard_confidence_percent']} < 40% → manual_review: True")
        print(f"  ✓ Reason: {result['manual_review_reason']}")
    else:
        print(f"  ℹ Sample input produced confidence {result['hazard_confidence_percent']} (not low enough to trigger review)")


def main():
    """Run all tests."""
    try:
        test_files_exist()
        test_model_loads()
        test_sample_electrical_prediction()
        test_severity_score_high()
        test_severity_score_medium()
        test_severity_score_low()
        test_fire_escape_obstruction_triggers_review()
        test_low_confidence_triggers_review()
        
        print("\n" + "="*60)
        print("✓ ALL TESTS PASSED")
        print("="*60)
        return 0
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
