

import os
import sys

from flask import Flask, jsonify, request  # type: ignore[import-not-found]
from web_interface.analysis_controller import AnalysisController
from web_interface.classification_result_view import ClassificationResultView
from web_interface.waste_upload_view import WasteUploadView

# Make the project root importable (database/ lives next to this folder)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.db import DatabaseManager  # noqa: E402
from database.exceptions import DataManagementError  # noqa: E402
from database.guidance import GuidanceService  # noqa: E402

app = Flask(__name__)

# Limit uploaded files to 10 MB
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

# ---------------------------------------------------------------------------
# Data Management & AI Guidance (Ha) - database + AI explanations
# ---------------------------------------------------------------------------
DEFAULT_REGION = "Dortmund"
database_manager = DatabaseManager()
database_manager.initialize()          # creates database/waste.db + Dortmund rules on first start
guidance_service = GuidanceService(database_manager)


# ---------------------------------------------------------------------------
# Classifier connection (Azi)
# ---------------------------------------------------------------------------
# Load the real model ONCE here, when the app starts (not on every request):
#   from classifier import WasteClassifier
#   classifier = WasteClassifier()
#   classifier.warm_up()
classifier = None


class ImageRejectedError(ValueError):
    """The classifier could not use the image (status 'invalid_image')."""


def classify_image(image_bytes, region=DEFAULT_REGION):
    """
    Sends the image to the classifier, looks up the Dortmund rule, gets the
    AI explanation and saves the result. Returns a dict in the format that
    ClassificationResultView.display_result() expects (plus extra fields).
    """
    # --- Step A: classifier -> {"status", "label", "category", "confidence", "message"}
    if classifier is None:
        # TEMPORARY placeholder until the real classifier is connected
        prediction = {"status": "completed", "label": "plastic bottle",
                      "category": "recyclable", "confidence": 0.94}
    else:
        prediction = classifier.classify(image_bytes)

    status = prediction.get("status", "completed")
    if status == "invalid_image":
        raise ImageRejectedError(prediction.get("message") or "The image could not be read.")
    if status not in ("completed", "uncertain"):          # "error" -> model failed
        raise RuntimeError(prediction.get("message") or "Classifier error.")

    label = str(prediction["label"]).strip().lower()
    confidence = prediction.get("confidence")

    # --- Step B: Dortmund rule + AI explanation (Ha's GuidanceService) --------
    rule = database_manager.get_rule(label, region)
    explanation = guidance_service.explain(label, region, rule=rule)

    # --- Step C: save the result for the dashboard ----------------------------
    classification_id = database_manager.save_classification(
        label, confidence=confidence, status=status, region=region)

    category = (rule or {}).get("category") or prediction.get("category") or "landfill"
    if rule:
        disposal_instruction = f"{rule['bin_type']}: {rule['instruction']}"
    else:
        disposal_instruction = (f"No local rule for '{label}' yet. "
                                "Please check the EDG Dortmund website (www.edg.de).")
    return {
        "waste_name": label.capitalize(),
        "category": category,
        "confidence": confidence,
        "disposal_instruction": disposal_instruction,
        "explanation": explanation["explanation"],
        # extra fields for the result page
        "classification_id": classification_id,
        "label": label,
        "status": status,
        "message": prediction.get("message", ""),
        "bin_type": (rule or {}).get("bin_type"),
        "is_deposit": (rule or {}).get("is_deposit", False),
        "explanation_ai_generated": explanation["ai_generated"],
        "region": region,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/", methods=["GET"])
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Waste Sorting Assistant</title>
    </head>
    <body>
        <h1>AI-Powered Waste Sorting Assistant</h1>

        <form action="/analyse" method="POST"
              enctype="multipart/form-data">

            <label>Select a waste image:</label>
            <input type="file" name="image"
                   accept=".png,.jpg,.jpeg" required>

            <button type="submit">Analyse Image</button>
        </form>
    </body>
    </html>
    """


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

    region = request.form.get("region", DEFAULT_REGION).strip() or DEFAULT_REGION

    try:
        classification = classify_image(image_bytes, region)
        formatted_result = result_view.display_result(classification)
    except ImageRejectedError as error:          # classifier status "invalid_image"
        return jsonify(result_view.display_error(str(error))), 400
    except Exception:
        analysis_controller.handle_error("Classification service unavailable.")
        return jsonify(result_view.display_error(
            analysis_controller.error_message
        )), 503

    # Extra fields for the result page (feedback button, deposit hint, AI label,
    # "uncertain" message)
    for key in ("classification_id", "label", "status", "message", "bin_type",
                "is_deposit", "explanation_ai_generated", "region"):
        formatted_result[key] = classification.get(key)

    # Step 5: Send the result back to the webpage
    return jsonify({
        "status": "success",
        "message": "Image processed successfully.",
        "result": formatted_result
    })


# ---------------------------------------------------------------------------
# Data Management & AI Guidance routes (JSON)
# ---------------------------------------------------------------------------
@app.route("/feedback", methods=["POST"])
def submit_feedback():
    """'Wrong result?' button. JSON: classification_id, is_correct, correct_label (optional)."""
    data = request.get_json(silent=True) or {}
    try:
        database_manager.save_feedback(
            int(data["classification_id"]),
            bool(data.get("is_correct", False)),
            data.get("correct_label") or None,
        )
    except DataManagementError as error:          # unknown id / feedback already given
        return jsonify({"status": "error", **error.to_dict()}), error.http_status
    except (KeyError, TypeError, ValueError):
        return jsonify({"status": "error",
                        "message": "classification_id (number) is required."}), 400
    return jsonify({"status": "success"})


@app.route("/ask", methods=["POST"])
def ask_question():
    """Follow-up question to the AI. JSON: question, label (optional), region (optional)."""
    data = request.get_json(silent=True) or {}
    try:
        answer = guidance_service.ask(
            data.get("question", ""),
            label=data.get("label") or None,
            region=data.get("region") or DEFAULT_REGION,
        )
    except DataManagementError as error:          # empty or too long question
        return jsonify({"status": "error", **error.to_dict()}), error.http_status
    return jsonify({"status": "success", **answer})


def _region_arg():
    """?region=Dortmund (default) or ?region=all"""
    region = request.args.get("region", DEFAULT_REGION)
    return None if region.lower() == "all" else region


@app.route("/api/dashboard/stats", methods=["GET"])
def dashboard_stats():
    """Dashboard statistics (Kanika's MunicipalityDashboard)."""
    return jsonify(database_manager.get_stats(_region_arg()))


@app.route("/api/dashboard/records", methods=["GET"])
def dashboard_records():
    """Latest classification records. ?region=Dortmund&limit=50"""
    try:
        records = database_manager.get_classification_records(
            _region_arg(), request.args.get("limit", 50))
    except DataManagementError as error:
        return jsonify({"status": "error", **error.to_dict()}), error.http_status
    return jsonify(records)


@app.errorhandler(413)
def file_too_large(error):
    return jsonify({
        "status": "error",
        "message": "File is too large. Maximum size is 10 MB."
    }), 413


if __name__ == "__main__":
    app.run(debug=True)