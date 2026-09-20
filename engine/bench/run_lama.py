"""Four photographic removal cases with exact mask protection and review sheets."""
import hashlib
import json
import time
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from pixelmend_engine.models.lama_onnx import LamaInpaint
from pixelmend_engine.models.opencv_inpaint import OpenCVInpaint
from pixelmend_engine.paths import get_models_dir

root = Path(__file__).parent / 'fixtures'
out = Path('apps/desktop/test-results/mac-acceptance/lama')
out.mkdir(parents=True, exist_ok=True)
adapter = LamaInpaint(get_models_dir())
rows = []
# Deliberately include flat background, irregular texture, structural lines and an edge selection.
cases = [('astronaut', 'flat', (.62,.10,.69,.18)), ('coffee', 'texture', (.1,.15,.2,.28)),
         ('brick', 'lines', (.42,.42,.58,.58)), ('chelsea', 'edge', (0,.4,.08,.55))]
for name, category, box in cases:
    path = root / ('original-' + name + '.png')
    image = Image.open(path).convert('RGB'); image.thumbnail((512,512))
    pixels = np.asarray(image).copy(); w,h = image.size
    x0,y0,x1,y1 = [round(v*n) for v,n in zip(box,[w,h,w,h])]
    mask = np.zeros((h,w),np.uint8);mask[y0:y1,x0:x1]=255
    started=time.monotonic(); ai=adapter.run(pixels,mask); elapsed=time.monotonic()-started
    fast=OpenCVInpaint('telea').run(pixels,mask)
    np.testing.assert_array_equal(ai[mask==0],pixels[mask==0])
    np.testing.assert_array_equal(fast[mask==0],pixels[mask==0])
    for label,array in [('lama',ai),('opencv',fast),('mask',mask)]: Image.fromarray(array).save(out/f'{name}-{label}.png')
    sheet=Image.new('RGB',(w*3,h+25),'white'); marked=image.copy();ImageDraw.Draw(marked).rectangle((x0,y0,x1,y1),outline='red',width=2)
    for i,(label,result) in enumerate([('Source / mask',marked),('OpenCV',Image.fromarray(fast)),('LaMa',Image.fromarray(ai))]):
        sheet.paste(result,(i*w,25));ImageDraw.Draw(sheet).text((i*w+5,5),label,fill='black')
    sheet.save(out/f'{name}-comparison.png')
    rows.append(dict(photo=name,category=category,source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),mask_box=[x0,y0,x1,y1],unmasked_exact=True,seconds=elapsed,visual_review='pending'))
(out/'report.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps(rows),flush=True)
