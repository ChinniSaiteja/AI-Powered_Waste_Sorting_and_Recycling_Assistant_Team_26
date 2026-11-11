

from flask import Flask, jsonify, request, render_template  # type: ignore[import-not-found]
from web_interface.analysis_controller import AnalysisController
from web_interface.classification_result_view import ClassificationResultView
from web_interface.waste_upload_view import WasteUploadView

app = Flask(__name__)

# Limit uploaded files to 10 MB
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

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

    # Step 4: Temporary dummy classification result
    # Replace this with the real classifier function later.
    dummy_result = {
        "waste_name": "Plastic bottle",
        "category": "RECYCLABLE",
        "confidence": 0.94,
        "disposal_instruction": "Place in the appropriate recycling bin.",
        "explanation": "This is a temporary demonstration result."
    }

    # Step 5: Display the classification result
    formatted_result = result_view.display_result(dummy_result)

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