"""Extract the user-provided dotLottie without changing its animation data.

lottie-web consumes JSON. The original .lottie archive remains the source asset.
"""
from pathlib import Path
import json
import zipfile

folder = Path(__file__).resolve().parents[1] / 'public/animations'
with zipfile.ZipFile(folder / 'animation.lottie') as archive:
    manifest = json.loads(archive.read('manifest.json'))
    animation_id = manifest['animations'][0]['id']
    candidates = [f'animations/{animation_id}.json', f'a/{animation_id}.json']
    name = next((n for n in candidates if n in archive.namelist()), None)
    if name is None:
        raise ValueError('Cannot find the default animation in animation.lottie.')
    payload = archive.read(name)
    data = json.loads(payload)
    # This selected user animation contains vector/precomp assets only.
    if any(asset.get('p') and not asset.get('e') for asset in data.get('assets', [])):
        raise ValueError('External image assets require explicit extraction; no silent missing images.')
    (folder / 'animation.json').write_bytes(payload)
print(f'Prepared user animation: {animation_id}')
