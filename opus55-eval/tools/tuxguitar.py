#!/usr/bin/env python3
"""Native .gp creation utilities and pinned TuxGuitar import/PDF checks."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET
from gp_archive import child, read_gp, write_gp
ROOT=Path(__file__).resolve().parent


def blank(guitars):
    root=ET.Element('GPIF');child(root,'GPVersion','7.0');child(root,'GPRevision','12024',required='12024',recommended='12024')
    score=child(root,'Score')
    for k in ['Title','SubTitle','Artist','Album','Words','Music','Copyright']:child(score,k,'Untitled' if k=='Title' else '')
    master=child(root,'MasterTrack');child(master,'Tracks',' '.join(map(str,range(guitars))))
    a=child(child(master,'Automations'),'Automation')
    for k,v in [('Type','Tempo'),('Linear','false'),('Bar',0),('Position',0),('Visible','true'),('Value','120 2')]:child(a,k,v)
    tracks=child(root,'Tracks');mb=child(child(root,'MasterBars'),'MasterBar');key=child(mb,'Key');child(key,'AccidentalCount',0);child(key,'Mode','Major');child(mb,'Time','4/4');child(mb,'Bars',' '.join(map(str,range(guitars))))
    bars=child(root,'Bars');voices=child(root,'Voices');beats=child(root,'Beats');child(root,'Notes')
    rhythm=child(child(root,'Rhythms'),'Rhythm',id=0);child(rhythm,'NoteValue','Whole')
    for i in range(guitars):
        t=child(tracks,'Track',id=i);child(t,'Name','Guitar '+str(i+1))
        child(t,'Color','65 85 110')
        midi=child(t,'MidiConnection')
        for k,v in [('Port',0),('PrimaryChannel',i*2),('SecondaryChannel',i*2+1)]:child(midi,k,v)
        sound=child(child(t,'Sounds'),'Sound')
        for k,v in [('Name','Steel String Guitar'),('Label','Steel String Guitar'),('Path','Midi/25'),('Role','Factory')]:child(sound,k,v)
        midi=child(sound,'MIDI')
        for k,v in [('LSB',0),('MSB',0),('Program',25)]:child(midi,k,v)
        props=child(child(child(t,'Staves'),'Staff'),'Properties')
        child(child(props,'Property',name='Tuning'),'Pitches','40 45 50 55 59 64')
        child(child(props,'Property',name='CapoFret'),'Fret',0);child(child(props,'Property',name='FretCount'),'Fret',24)
        b=child(bars,'Bar',id=i);child(b,'Clef','G2');child(b,'Voices',str(i)+' -1 -1 -1')
        child(child(voices,'Voice',id=i),'Beats',str(i));child(child(beats,'Beat',id=i),'Rhythm',ref=0)
    return root


def java():
    if os.environ.get('JAVA'):return os.environ['JAVA']
    if os.environ.get('JAVA_HOME'):return str(Path(os.environ['JAVA_HOME'])/'bin/java')
    config=ROOT/'runtime.json'
    if config.exists():return json.loads(config.read_text(encoding='utf-8'))['java']
    found=shutil.which('java')
    if not found:raise RuntimeError('Java is required; set JAVA or JAVA_HOME')
    return found


def invoke(script, args):
    vendor=ROOT/'vendor'
    cp=os.pathsep.join(map(str,[vendor/'tuxguitar-pdf-unicode.jar',vendor/'rhino-1.7.15.jar',vendor/'tuxguitar-1.6.6/*']))
    cmd=[java(),'-Xmx768m','-Djava.awt.headless=true','-Dguitar.pdf.font='+str(vendor/'fonts/NotoSansCJKsc-Regular.otf'),'-Dguitar.pdf.font.bold='+str(vendor/'fonts/NotoSansCJKsc-Bold.otf'),'-cp',cp,'org.mozilla.javascript.tools.shell.Main',str(ROOT/script)]+[str(x) for x in args]
    p=subprocess.run(cmd,text=True,capture_output=True,timeout=120, encoding='utf-8')
    if p.returncode:raise RuntimeError(p.stderr[-6000:] or p.stdout[-6000:])
    return p.stdout


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('operation',choices=['init','inspect','check','pdf']);ap.add_argument('score',type=Path);ap.add_argument('output',nargs='?',type=Path);ap.add_argument('--guitars',type=int,choices=[1,2,3],default=1);a=ap.parse_args()
    if a.score.suffix.lower()!='.gp':ap.error('Only native .gp output/input is accepted')
    if a.operation=='init':
        if a.score.exists():ap.error('init will not overwrite an existing score')
        write_gp(blank(a.guitars),a.score);print(a.score);return
    read_gp(a.score)
    if a.operation=='pdf':
        if a.output is None:ap.error('pdf requires an output PDF path')
        a.output.parent.mkdir(parents=True,exist_ok=True);invoke('export_source_pdf.js',[a.score.resolve(),a.output.resolve()]);print(a.output);return
    result=json.loads(invoke('extract_gp_native.js',[a.score.resolve(),ROOT/'gp_native_read.js']))
    if a.operation=='inspect':print(json.dumps(result,ensure_ascii=False,indent=2));return
    count=sum(len(v['notes']) for t in result['tracks'] for m in t['measures'] for b in m['beats'] for v in b['voices'])
    print(json.dumps({'native_gp':True,'tracks':len(result['tracks']),'notes':count,'parseable_nonempty':count>0},ensure_ascii=False))
    if count==0:raise SystemExit(1)

if __name__=='__main__':main()
