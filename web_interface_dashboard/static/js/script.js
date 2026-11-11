
const uploadForm = document.getElementById("uploadForm");

const imageInput = document.getElementById("imageInput");
const cameraInput = document.getElementById("cameraInput");

const analyseButton = document.getElementById("analyseButton");

const previewContainer = document.getElementById("previewContainer");
const imagePreview = document.getElementById("imagePreview");
const fileName = document.getElementById("fileName");

const statusMessage = document.getElementById("statusMessage");
const resultSection = document.getElementById("resultSection");

// Store the selected image, regardless of its source
let selectedFile = null;


// Handle image selection from either source
function handleImageSelection(file) {

    resultSection.classList.add("hidden");
    statusMessage.textContent = "";

    if (!file) {
        return;
    }

    const allowedTypes = ["image/png", "image/jpeg"];

    if (!allowedTypes.includes(file.type)) {
        statusMessage.textContent =
            "Please select a PNG or JPG image.";

        analyseButton.disabled = true;
        return;
    }

    if (file.size > 10 * 1024 * 1024) {
        statusMessage.textContent =
            "File size must not exceed 10 MB.";

        analyseButton.disabled = true;
        return;
    }

    selectedFile = file;

    const imageURL = URL.createObjectURL(file);

    imagePreview.src = imageURL;
    fileName.textContent = file.name;

    previewContainer.classList.remove("hidden");
    analyseButton.disabled = false;

    statusMessage.textContent = "Image selected successfully.";
}


// Gallery selection
imageInput.addEventListener("change", function () {

    const file = imageInput.files[0];

    cameraInput.value = "";

    handleImageSelection(file);
});


// Camera capture
cameraInput.addEventListener("change", function () {

    const file = cameraInput.files[0];

    imageInput.value = "";

    handleImageSelection(file);
});


// Submit image for analysis
uploadForm.addEventListener("submit", async function (event) {

    event.preventDefault();

    if (!selectedFile) {
        statusMessage.textContent =
            "Please select or capture an image first.";
        return;
    }

    const formData = new FormData();

    formData.append("image", selectedFile);

    analyseButton.disabled = true;
    analyseButton.textContent = "Analysing...";

    statusMessage.textContent = "Processing your image...";
    resultSection.classList.add("hidden");

    try {

        const response = await fetch("/analyse", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.message || "Image analysis failed."
            );
        }

        const result = data.result;

        document.getElementById("wasteName").textContent =
            result.waste_name;

        document.getElementById("category").textContent =
            result.category;

        document.getElementById("confidence").textContent =
            (result.confidence * 100).toFixed(1) + "%";

        document.getElementById("disposalInstruction").textContent =
            result.disposal_instruction;

        document.getElementById("explanation").textContent =
            result.explanation;

        resultSection.classList.remove("hidden");

        statusMessage.textContent =
            "Analysis completed successfully!";

    } catch (error) {

        statusMessage.textContent = error.message;

    } finally {

        analyseButton.disabled = false;
        analyseButton.textContent = "Analyse Image";
    }
});
