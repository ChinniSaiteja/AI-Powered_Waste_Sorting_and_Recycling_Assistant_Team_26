from io import BytesIO

from waste_upload_view import WasteUploadView  # type: ignore[import-not-found]

upload_view = WasteUploadView()

print(upload_view.upload_status)
print(upload_view.selected_image)

result = upload_view.submit_image()

print(result)
print(upload_view.upload_status)

class MockImage:
    filename = "plastic_bottle.jpg"
    content_type = "image/jpeg"

    def __init__(self):
        self.file = BytesIO(b"sample image data")

    def read(self):
        return self.file.read()

    def seek(self, position):
        self.file.seek(position)


image = MockImage()

upload_view.select_image(image)

print(upload_view.image_name)
print(upload_view.image_size)
print(upload_view.image_type)
print(upload_view.upload_status)

result = upload_view.submit_image()

print(result)
print(upload_view.upload_status)