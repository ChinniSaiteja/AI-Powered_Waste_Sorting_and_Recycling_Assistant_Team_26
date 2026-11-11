
from analysis_controller import AnalysisController

controller = AnalysisController()

# Test 1: Valid image
print(controller.validate_upload(b"image data", "bottle.jpg"))
print(controller.request_status)
print(controller.error_message)

# Test 2: Invalid extension
print(controller.validate_upload(b"image data", "document.pdf"))
print(controller.error_message)

# Test 3: Missing image
print(controller.validate_upload(None, None))
print(controller.error_message)

controller.handle_error("Classification service unavailable")

print(controller.request_status)
print(controller.error_message)