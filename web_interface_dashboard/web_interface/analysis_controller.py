class AnalysisController:
    def __init__(self):
        self._request_status = "Not Requested"
        self._error_message = None

    @property
    def request_status(self):
        return self._request_status

    @property
    def error_message(self):
        return self._error_message
    
    def validate_upload(self, image, filename):
        if image and filename:
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                self._request_status = "Valid Upload"
                return True
            else:
                self._error_message = "Please upload a valid image file (PNG, JPG, JPEG)."
                return False
        else:
            self._error_message = "Please provide both an image and a filename."
            return False

    def handle_error(self, error_message):
        self._error_message = error_message
        self._request_status = "Error"

    def request_analysis(self, image, filename):
        if not self.validate_upload(image, filename):
            return {
                "status": "error",
                "message": self._error_message
            }
    
        self._error_message = None
        self._request_status = "Analysis Requested"
    
        return {
            "status": "success",
            "message": "Image is ready for analysis"
    }