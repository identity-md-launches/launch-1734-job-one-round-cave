"""Check the numbered record and required wall bytes, without networking."""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    'thumbnail_delivery_39', ROOT / 'shared/wall-thumbnail/thumbnail.py')
thumbnail = importlib.util.module_from_spec(spec)
spec.loader.exec_module(thumbnail)


def jpeg_size(data):
    assert data[:2] == b'\xff\xd8' and data[-2:] == b'\xff\xd9'
    pos = 2
    while pos < len(data):
        assert data[pos] == 255
        marker = data[pos + 1]
        length = int.from_bytes(data[pos + 2:pos + 4], 'big')
        if marker == 0xc0:
            depth, height, width, components = struct.unpack(
                '>BHHB', data[pos + 4:pos + 10])
            assert depth == 8 and components == 3
            return width, height
        assert marker not in (0xda, 0xd9)
        pos += 2 + length
    raise AssertionError('no baseline JPEG frame')


def main():
    folder = ROOT / 'dist/line-3'
    numbered = sorted(path for path in folder.glob('*.json')
                      if len(path.stem) == 2 and path.stem.isdigit())
    assert len(numbered) == 39 and numbered[-1].name == '39.json'
    wall = ROOT / 'artifacts/line-3/wall-v19.png'
    data = wall.read_bytes()
    assert data == (ROOT / 'artifacts/line-3/wall.png').read_bytes()
    width, height, _ = thumbnail.png_rgb(wall)
    assert (width, height) == (1254, 1254)
    digest = hashlib.sha256(data).hexdigest()
    record = json.loads((folder / '39.json').read_text())
    assert set(record) == {'name', 'image', 'attributes'}
    assert record['name'] == 'The Compared Trails'
    assert record['image'] == 'https://api.imd.fun/artifacts/' + digest
    traits = record['attributes']
    assert all(set(row) == {'trait_type', 'value'} for row in traits)
    assert [row['trait_type'] for row in traits] == [
        'Cave', 'Wall', 'Number', 'Left behind', 'Meaning', 'One thing']
    assert [row['value'] for row in traits] == [
        'Moss', 'Line 3', 39, 'Code Frontier Delta',
        'Pepe compares proved trails and keeps newly revealed branches visible.',
        'Ethereum executable code identity']
    assert type(traits[2]['value']) is int
    jpeg = (folder / '39.jpg').read_bytes()
    assert jpeg_size(jpeg) == (512, 512) and len(jpeg) < 100_000
    visual = json.loads((ROOT / 'line-3/visual-checks-39.json').read_text())
    assert visual['wall_sha256'] == digest
    assert visual['changed_pixels'] > 0
    assert visual['changed_pixels_outside_addition'] == 0
    assert visual['unmet_visual_requirements'] == []
    assert visual['visual_review'] != 'pending'
    assert (ROOT / 'line-3/GOAL.md').read_text().strip() == (
        'Let any worker identify and verify the executable code behind an '
        'Ethereum contract address before trusting it.')
    for path in (ROOT / 'line-3/tools/code-frontier-delta').iterdir():
        if path.is_file():
            assert path.stat().st_size <= 100_000, path
    return {'delivery_passed': True, 'record': 'dist/line-3/39.json',
            'wall': str(wall.relative_to(ROOT)), 'wall_sha256': digest,
            'wall_format': 'PNG', 'wall_dimensions': [width, height],
            'thumbnail_format': 'JPEG', 'thumbnail_dimensions': [512, 512],
            'thumbnail_bytes': len(jpeg), 'record_count': len(numbered),
            'goal_text_matches': True, 'unmet_visual_requirements': [],
            'scope': 'Local byte and record checks; no independent behavioral or visual certification.'}


if __name__ == '__main__':
    print(json.dumps(main(), indent=2))
