"""Small, standard-library GP7 archive API. No GP5 conversion or ID expansion."""
from pathlib import Path
from fractions import Fraction
import argparse
import copy
import zipfile
import xml.etree.ElementTree as ET

SECTIONS = ('Tracks', 'Bars', 'Voices', 'Beats', 'Notes', 'Rhythms')
VALUES = {'Whole': 1, 'Half': 2, 'Quarter': 4, 'Eighth': 8,
          '16th': 16, '32nd': 32, '64th': 64, '128th': 128}


def read_gp(path):
    path = Path(path)
    if path.stat().st_size > 5_000_000:
        raise ValueError('GP archive exceeds 5 MB')
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if len(names) != len(set(names)) or len(names) > 1000:
            raise ValueError('Duplicate or excessive archive entries')
        if sum(i.file_size for i in z.infolist()) > 20_000_000:
            raise ValueError('Expanded archive exceeds 20 MB')
        raw = z.read('Content/score.gpif')
    # Reject declarations before handing XML to either Python or the Java reader.
    decoded = raw.decode('utf-8-sig')
    if '<!DOCTYPE' in decoded.upper() or '<!ENTITY' in decoded.upper():
        raise ValueError('DTD and entity declarations are forbidden')
    root = ET.fromstring(decoded)
    validate(root)
    return root


def index(root):
    out = {}
    for section in SECTIONS:
        parents = root.findall(section)
        if len(parents) != 1:
            raise ValueError('Expected one ' + section)
        nodes = list(parents[0])
        ids = [n.get('id') for n in nodes]
        if None in ids or len(ids) != len(set(ids)):
            raise ValueError('Missing or duplicate IDs in ' + section)
        out[section] = dict(zip(ids, nodes))
    return out


def validate(root):
    if root.tag != 'GPIF':
        raise ValueError('Expected GPIF root')
    tables = index(root)
    if not 1 <= len(tables['Tracks']) <= 32:
        raise ValueError('Invalid track count')
    masters = root.find('MasterBars')
    if masters is None or not 1 <= len(masters) <= 2000:
        raise ValueError('Invalid measure count')
    links = [(root.find('MasterTrack'), 'Tracks', 'Tracks', False)]
    links += [(n, 'Bars', 'Bars', True) for n in masters]
    links += [(n, 'Voices', 'Voices', True) for n in tables['Bars'].values()]
    links += [(n, 'Beats', 'Beats', False) for n in tables['Voices'].values()]
    links += [(n, 'Notes', 'Notes', False) for n in tables['Beats'].values()]
    for node, field, target, negative in links:
        if node is None:
            raise ValueError('Missing reference owner')
        for ref in (node.findtext(field) or '').split():
            if not (negative and ref == '-1') and ref not in tables[target]:
                raise ValueError('Dangling ' + target + ' reference: ' + ref)
    for beat in tables['Beats'].values():
        rhythm = beat.find('Rhythm')
        if rhythm is None or rhythm.get('ref') not in tables['Rhythms']:
            raise ValueError('Dangling rhythm reference')
    return tables


def write_gp(root, path):
    """Create a fresh minimal GP7 container; never copies history or source extras.

    TuxGuitar compatibility is checked separately by the native reader. This is
    not a claim that every Guitar Pro desktop version accepts minimal archives.
    """
    validate(root)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('VERSION', '7.0')
        z.writestr('Content/score.gpif', ET.tostring(root, encoding='utf-8', xml_declaration=True))


def child(parent, tag, value=None, **attrs):
    node = ET.SubElement(parent, tag, {k: str(v) for k, v in attrs.items()})
    if value is not None:
        node.text = str(value)
    return node


def blank_from(root):
    """Fresh one-bar rest; only public tuning, capo, meter, key and tempo copied."""
    track = root.find('Tracks/Track')
    new = ET.Element('GPIF')
    child(new, 'GPVersion', '7.0')
    child(new, 'GPRevision', '12024', required='12024', recommended='12024')
    score = child(new, 'Score')
    for key in ('Title', 'SubTitle', 'Artist', 'Album', 'Words', 'Music', 'Copyright'):
        child(score, key)
    mastertrack = child(new, 'MasterTrack'); child(mastertrack, 'Tracks', '0')
    automations = child(mastertrack, 'Automations')
    tempo = next((a for a in root.findall('MasterTrack/Automations/Automation')
                  if a.findtext('Type') == 'Tempo'), None)
    if tempo is not None:
        a = copy.deepcopy(tempo)
        a.find('Bar').text = '0'; a.find('Position').text = '0'
        automations.append(a)
    t = child(child(new, 'Tracks'), 'Track', id='0'); child(t, 'Name', 'Guitar')
    midi = child(t, 'GeneralMidi', table='Instrument')
    for k, v in [('Port', 0), ('Program', 25), ('PrimaryChannel', 0), ('SecondaryChannel', 1)]:
        child(midi, k, v)
    props = child(child(child(t, 'Staves'), 'Staff'), 'Properties')
    source_props = track.find('Staves/Staff/Properties')
    for name in ('Tuning', 'CapoFret', 'FretCount'):
        p = source_props.find("Property[@name='%s']" % name)
        if p is not None:
            if name == 'Tuning':
                child(child(props, 'Property', name=name), 'Pitches', p.findtext('Pitches'))
            else:
                props.append(copy.deepcopy(p))
    mb = child(child(new, 'MasterBars'), 'MasterBar')
    source_mb = root.find('MasterBars/MasterBar')
    for key in ('Key', 'Time'):
        mb.append(copy.deepcopy(source_mb.find(key)))
    child(mb, 'Bars', '0')
    bar = child(child(new, 'Bars'), 'Bar', id='0'); child(bar, 'Clef', 'G2'); child(bar, 'Voices', '0 -1 -1 -1')
    voice = child(child(new, 'Voices'), 'Voice', id='0')
    beats, rhythms = child(new, 'Beats'), child(new, 'Rhythms')
    child(new, 'Notes')
    n, d = map(int, source_mb.findtext('Time').split('/')); remaining = Fraction(n, d)
    ids = []
    for label, denom in VALUES.items():
        while remaining >= Fraction(1, denom):
            ref = str(len(ids)); ids.append(ref)
            beat = child(beats, 'Beat', id=ref); child(beat, 'Rhythm', ref=ref)
            child(child(rhythms, 'Rhythm', id=ref), 'NoteValue', label)
            remaining -= Fraction(1, denom)
    if remaining:
        raise ValueError('Cannot represent blank meter')
    child(voice, 'Beats', ' '.join(ids))
    return new


def renumber(root):
    """Semantics-preserving ID rewrite; useful for scorer invariance checks."""
    root = copy.deepcopy(root); tables = index(root)
    maps = {k: {old: str(10000 + i) for i, old in enumerate(reversed(list(v)))} for k, v in tables.items()}
    for section, nodes in tables.items():
        for old, n in nodes.items():
            n.set('id', maps[section][old])
        root.find(section)[:] = list(reversed(list(nodes.values())))
    links = [(root.find('MasterTrack'), 'Tracks')]
    links += [(n, 'Bars') for n in root.find('MasterBars')]
    links += [(n, 'Voices') for n in tables['Bars'].values()]
    links += [(n, 'Beats') for n in tables['Voices'].values()]
    links += [(n, 'Notes') for n in tables['Beats'].values()]
    for n, key in links:
        e = n.find(key)
        if e is not None:
            e.text = ' '.join(maps[key].get(x, x) for x in (e.text or '').split())
    for b in tables['Beats'].values():
        e = b.find('Rhythm'); e.set('ref', maps['Rhythms'][e.get('ref')])
    return root


def detach_note(root, measure, beat, note, voice=0):
    """Copy-on-write one occurrence, using zero-based measure/beat/note indices.

    Clone a shared ancestor before checking children, so newly duplicated
    references are counted. Unrelated occurrences and IDs remain untouched.
    """
    tables = index(root)
    owner = list(root.find('MasterBars'))[measure]
    steps = [('Bars', 0, list(root.find('MasterBars'))),
             ('Voices', voice, None), ('Beats', beat, None), ('Notes', note, None)]
    previous = None
    for section, offset, owners in steps:
        if owners is None:
            owners = list(tables[previous].values())
        field = owner.find(section)
        ids = field.text.split(); old = ids[offset]
        target = tables[section][old]
        refs = sum((n.findtext(section) or '').split().count(old) for n in owners)
        if refs > 1:
            target = copy.deepcopy(target)
            new = str(max(map(int, tables[section]), default=-1) + 1)
            target.set('id', new); root.find(section).append(target); tables[section][new] = target
            ids[offset] = new; field.text = ' '.join(ids)
        owner = target; previous = section
    return owner


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('operation', choices=['unpack', 'pack', 'blank', 'renumber'])
    ap.add_argument('source', type=Path); ap.add_argument('output', type=Path)
    a = ap.parse_args()
    if a.operation == 'pack':
        write_gp(ET.parse(a.source).getroot(), a.output)
    else:
        root = read_gp(a.source)
        if a.operation == 'unpack':
            a.output.write_bytes(ET.tostring(root, encoding='utf-8', xml_declaration=True))
        else:
            write_gp(blank_from(root) if a.operation == 'blank' else renumber(root), a.output)
