class WasteUploadView:
    
    def __init__(self):
        self._selected_image = None
        self._image_name = None
        self._image_size = 0
        self._image_type = None
        self._upload_status = "Not Uploaded"

    @property
    # Getter and setter for the selected image
    def selected_image(self):
        return self._selected_image

    @selected_image.setter
    def selected_image(self, image):
        self._selected_image = image
        self._image_name = image.filename
        self._image_size = len(image.read())
        image.seek(0)
        self._image_type = image.content_type
        self._upload_status = "Uploaded"



    @property
    def image_name(self):
        return self._image_name

    @property
    def image_size(self):
        return self._image_size

    @property
    def image_type(self):
        return self._image_type

    @property
    def upload_status(self):
        return self._upload_status

    def select_image(self, image):
        self.selected_image = image
        return self.selected_image
    
    def submit_image(self):
        if self.selected_image:
            # Here you can add logic to save the image to a database or file system
            self._upload_status = "Successfully Uploaded"
            return True
        else:
            self._upload_status = "No Image Selected"
            return False
upload_view = WasteUploadView()