from io import BytesIO

import numpy as np
import pytest
from PIL import Image

from pixelmend_engine.imageio import load_image


@pytest.mark.parametrize('format', ['PNG', 'WEBP', 'TIFF', 'JPEG'])
def test_export_removes_private_metadata_and_preserves_color_alpha(format):
    from pixelmend_engine.imageio import encode_export

    source = BytesIO()
    exif = Image.Exif()
    exif[315] = 'Private photographer'
    Image.new('RGBA', (8, 8), (0, 0, 0, 0)).save(source, format='PNG', exif=exif)
    asset = load_image(source)
    with Image.open(BytesIO(encode_export(asset, format))) as output:
        assert output.size == (8, 8)
        assert output.info.get('icc_profile')
        assert 315 not in output.getexif()
        assert 274 not in output.getexif()
        if format == 'JPEG':
            assert np.asarray(output)[0, 0].tolist() == [255, 255, 255]
        else:
            assert output.convert('RGBA').getpixel((0, 0))[3] == 0
