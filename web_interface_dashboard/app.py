

from flask import Flask, jsonify, request  # type: ignore[import-not-found]
from web_interface.analysis_controller import AnalysisController
from web_interface.classification_result_view import ClassificationResultView
from web_interface.waste_upload_view import WasteUploadView

app = Flask(__name__)

# Limit uploaded files to 10 MB
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


# ---------------------------------------------------------------------------
# Classifier connection
# ---------------------------------------------------------------------------
# Load the real model ONCE here, when the app starts (not on every request).
# Replace these two lines when the classifier is ready, e.g.:
#   from ml_classifier.classifier import WasteClassifier
#   classifier = WasteClassifier("path/to/model")
classifier = None

# Maps the classifier's labels to the WasteCategory names
# (RECYCLABLE, COMPOSTABLE, LANDFILL). Extend this with the real labels.
LABEL_TO_CATEGORY = {
    "plastic_bottle": "RECYCLABLE",
    "paper": "RECYCLABLE",
    "glass": "RECYCLABLE",
    "metal_can": "RECYCLABLE",
    "food_waste": "COMPOSTABLE",
    "banana_peel": "COMPOSTABLE",
    "styrofoam": "LANDFILL",
}


def classify_image(image_bytes):
    """
    Sends the image to the classifier and returns a dict in the format that
    ClassificationResultView.display_result() expects.

    This is the ONLY function that changes when the real classifier is ready.
    """
    # --- Step A: get label + confidence from the classifier -----------------
    if classifier is None:
        # TEMPORARY placeholder until the real classifier is connected
        prediction = {"label": "plastic_bottle", "confidence": 0.94}
    else:
        # Adjust this line to how your colleague's classifier is called
        prediction = classifier.predict(image_bytes)

    label = prediction["label"]
    confidence = float(prediction["confidence"])
    if confidence > 1:  # classifier returned a percentage, e.g. 94 -> 0.94
        confidence = confidence / 100

    # --- Step B: get disposal guidance ---------------------------------------
    # Later: ask the backend's GuidanceService for these two texts
    disposal_instruction = "Place in the appropriate recycling bin."
    explanation = "This is a temporary demonstration result."

    return {
        "waste_name": label.replace("_", " ").capitalize(),
        "category": LABEL_TO_CATEGORY.get(label, "LANDFILL"),
        "confidence": confidence,
        "disposal_instruction": disposal_instruction,
        "explanation": explanation,
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

    try:
        classification = classify_image(image_bytes)
        formatted_result = result_view.display_result(classification)
    except Exception:
        analysis_controller.handle_error("Classification service unavailable.")
        return jsonify(result_view.display_error(
            analysis_controller.error_message
        )), 503

    # Step 5: Send the result back to the webpage
    return jsonify({
        "status": "success",
        "message": "Image processed successfully.",
        "result": formatted_result
    })


@app.errorhandler(413)
def file_too_large(error):
    return jsonify({
        "status": "error",
        "message": "File is too large. Maximum size is 10 MB."
    }), 413


if __name__ == "__main__":
    app.run(debug=True)