import joblib
import os

MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "v1_baseline")
hazard_path = os.path.join(MODEL_DIR, "hazard_category_classifier_tfidf_logreg.joblib")
risk_path = os.path.join(MODEL_DIR, "risk_level_classifier_tfidf_logreg.joblib")

def main():
    print("Loading models from:")
    print(" ", hazard_path)
    print(" ", risk_path)
    hazard = joblib.load(hazard_path)
    risk = joblib.load(risk_path)
    sample = "Workplace scenario: Loose electrical wires are exposed near a workstation. | Location: office area"
    print("Sample input:", sample)
    print("Predicted hazard category:", hazard.predict([sample])[0])
    print("Predicted risk level:", risk.predict([sample])[0])

if __name__ == "__main__":
    main()
