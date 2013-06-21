from spreads.plugin import BaseCamera


class MockCamera(BaseCamera):
    @classmethod
    def match(cls, vendor_id, product_id):
        pass

    def __init__(self, bus=0, device=0, orientation='left'):
        self._port = (bus, device)
        self.orientation = orientation

    def set_orientation(self, orientation):
        self.orientation = orientation

    def delete_files(self):
        pass

    def download_files(self, path):
        pass

    def set_record_mode(self):
        pass

    def get_zoom(self):
        return self._zoom or 0

    def set_zoom(self, level):
        self._zoom = level

    def disable_flash(self):
        pass

    def set_iso(self, iso_value):
        pass

    def disable_ndfilter(self):
        pass

    def shoot(self, shutter_speed, iso_value):
        pass

    def play_sound(self, sound_num):
        pass
