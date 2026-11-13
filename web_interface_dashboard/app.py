import importlib.util
import sys
from pathlib import Path

from flask import Flask, jsonify, render_template, request  # type: ignore[import-not-found]

from dashboard.municipality_dashboard import MunicipalityDashboard
from web_interface.analysis_controller import AnalysisController
from web_interface.classification_result_view import ClassificationResultView
from web_interface.waste_upload_view import WasteUploadView

# The database/ folder is in the project root, one level above this file
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))
from database.db import DatabaseManager  # noqa: E402
from database.guidance import GuidanceService  # noqa: E402

app = Flask(__name__)

# Limit uploaded files to 10 MB
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


# ---------------------------------------------------------------------------
# Database connection (created once when the app starts)
# ---------------------------------------------------------------------------
database_manager = DatabaseManager()
database_manager.initialize()  # creates the tables and loads the rules the first time

# AI explanations (Ha's subsystem). Without an AI key in .env, GuidanceService
# still works: it falls back to showing the official rule as the explanation.
guidance_service = GuidanceService(database_manager)


# ---------------------------------------------------------------------------
# Classifier connection
# ---------------------------------------------------------------------------
REGION = "Dortmund"
UNCERTAIN_THRESHOLD = 0.6  # below this confidence a result is stored as "uncertain"

# Load the real model ONCE here, when the app starts (not on every request).
# Subsystem 3 (classifier/): pretrained CLIP, zero-shot. It needs torch and
# transformers; without them (or if they cannot load) the app keeps working with
# the placeholder below instead of crashing.
classifier = None
if importlib.util.find_spec("torch") and importlib.util.find_spec("transformers"):
    try:
        from classifier import WasteClassifier  # noqa: E402

        classifier = WasteClassifier()
        classifier.warm_up()  # downloads the model (~600 MB) the first time only
    except Exception as error:  # e.g. a blocked torch DLL or no internet on first run
        print(f"Classifier could not be loaded ({error}): using placeholder results.")
        classifier = None
else:
    print("Classifier libraries not installed (torch, transformers): using placeholder results.")

# While there is no classifier, use the first label the database knows,
# so the database lookup (Step B) can already be tested with real rules.
_known_items = database_manager.get_all_items()
PLACEHOLDER_LABEL = _known_items[0].label if _known_items else "glass jar"


class UnusableImageError(Exception):
    """The classifier could not use the uploaded file (empty, broken, unsupported)."""


class UnknownWasteItemError(Exception):
    """The classifier returned a label that has no disposal rule in the database."""

    def __init__(self, label):
        super().__init__(f"No disposal rule found for '{label}'.")
        self.label = label


def classify_image(image_bytes):
    """
    Classifies the image and returns a dict in the format that
    ClassificationResultView.display_result() expects.

    This is the ONLY function that changes when the classifier and the
    AI guidance are connected.
    """
    # --- Step A: label + confidence from the classifier ---------------------
    if classifier is None:
        prediction = {"label": PLACEHOLDER_LABEL, "confidence": 0.94}  # TEMPORARY
    else:
        # {"status", "label", "category", "confidence", "message", "inference_ms"}
        prediction = classifier.classify(image_bytes)
        if prediction["status"] == "invalid_image":
            raise UnusableImageError(prediction["message"])
        if prediction["status"] == "error":
            raise RuntimeError(prediction["message"])  # -> 503 below

    # Labels in the database are lowercase with spaces, e.g. "glass jar"
    label = str(prediction["label"]).strip().lower().replace("_", " ")
    confidence = float(prediction["confidence"])
    if confidence > 1:  # classifier returned a percentage, e.g. 94 -> 0.94
        confidence = confidence / 100
    # The classifier decides completed/uncertain with its own threshold
    status = prediction.get("status") or (
        "completed" if confidence >= UNCERTAIN_THRESHOLD else "uncertain")

    # --- Step B: disposal rule from the database ----------------------------
    rule = database_manager.get_rule(label, region=REGION)
    if rule is None:
        if classifier is not None:
            database_manager.save_classification(label, confidence, "uncertain", region=REGION)
        raise UnknownWasteItemError(label)

    disposal_instruction = f"{rule['bin_type']}: {rule['instruction']}"
    if rule["is_deposit"]:
        disposal_instruction += " (Deposit item - return it to a deposit machine.)"

    # --- Step C: educational explanation (Ha's GuidanceService) --------------
    # Checks the cache, then asks the AI, then falls back to the official
    # rule if there is no key / the daily limit is reached / the AI fails.
    guidance = guidance_service.explain(label, REGION, rule=rule)

    # --- Save the result, so it appears on the dashboard --------------------
    # Only real classifier results are stored (no placeholder data).
    classification_id = None
    if classifier is not None:
        classification_id = database_manager.save_classification(
            label, confidence, status, region=REGION)

    return {
        "waste_name": label.capitalize(),
        "category": rule["category"],
        "confidence": confidence,
        "disposal_instruction": disposal_instruction,
        "explanation": guidance["explanation"],
        # extra fields the result page can show (e.g. an "AI-generated" label)
        "classification_id": classification_id,
        "label": label,
        "status": status,
        "bin_type": rule["bin_type"],
        "is_deposit": rule["is_deposit"],
        "explanation_ai_generated": guidance["ai_generated"],
        "region": REGION,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")


@app.route("/analyse", methods=["POST"])
def analyse_image():

    upload_view = WasteUploadView()
    analysis_controller = AnalysisController()
    result_view = ClassificationResultView()

    image = request.files.get("image")

    if image is None or image.filename == "":
        return jsonify(result_view.display_error(
            "Please select an image."
        )), 400

    # Step 1: Store the uploaded image
    upload_view.select_image(image)

    # Step 2: Check whether an image was selected
    if not upload_view.submit_image():
        return jsonify(result_view.display_error(
            "Image upload failed."
        )), 400

    # Step 3: Validate the image
    analysis_response = analysis_controller.request_analysis(
        image, image.filename
    )

    if analysis_response["status"] == "error":
        return jsonify(result_view.display_error(
            analysis_response["message"]
        )), 400

    # Step 4: Classify the image
    image_bytes = image.read()
    image.seek(0)

    try:
        classification = classify_image(image_bytes)
        formatted_result = result_view.display_result(classification)
    except UnusableImageError as error:
        return jsonify(result_view.display_error(str(error))), 400
    except UnknownWasteItemError:
        return jsonify(result_view.display_error(
            "This item could not be matched to a disposal rule. "
            "Please try another photo."
        )), 422
    except Exception:
        analysis_controller.handle_error("Classification service unavailable.")
        return jsonify(result_view.display_error(
            analysis_controller.error_message
        )), 503

    # Extra fields for the result page (deposit hint, AI label)
    for key in ("classification_id", "label", "status", "bin_type", "is_deposit",
                "explanation_ai_generated", "region"):
        formatted_result[key] = classification.get(key)

    # Step 5: Send the result back to the webpage
    return jsonify({
        "status": "success",
        "message": "Image processed successfully.",
        "result": formatted_result
    })


@app.route("/dashboard", methods=["GET"])
def dashboard():
    try:
        municipality_dashboard = MunicipalityDashboard(database_manager, region="Dortmund")
        municipality_dashboard.load_data()
    except Exception as error:
        return render_template("dashboard.html", error=str(error)), 500

    return render_template(
        "dashboard.html",
        error=None,
        region=municipality_dashboard.get_region_name(),
        total=municipality_dashboard.get_total_analysed_items(),
        recyclable_percentage=municipality_dashboard.get_recyclable_percentage(),
        distribution=municipality_dashboard.get_category_distribution(),
    )


@app.errorhandler(413)
def file_too_large(error):
    return jsonify({
        "status": "error",
        "message": "File is too large. Maximum size is 10 MB."
    }), 413


if __name__ == "__main__":
    app.run(debug=True)