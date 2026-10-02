"""Harbor delivery check. Never interpret its reward as arrangement quality."""
import argparse, json, os, subprocess, zipfile
from pathlib import Path


def check(output, runtime):
    candidates=[p for p in output.iterdir() if p.name in {'arrangement.gp'}] if output.is_dir() else []
    if len(candidates)!=1:
        return {'status':'missing_or_ambiguous_submission','parseable_score':0}
    p=candidates[0]
    if p.is_symlink() or not p.is_file() or not 0<p.stat().st_size<=20*1024*1024:
        return {'status':'invalid_file','parseable_score':0}
    # Bound expanded GP7 archives and reject external entity declarations.
    if p.suffix=='.gp':
        try:
            with zipfile.ZipFile(p) as z:
                entries=z.infolist()
                if len(entries)>2000 or sum(x.file_size for x in entries)>100*1024*1024:
                    raise ValueError('archive exceeds limits')
                if sum(x.filename=='Content/score.gpif' for x in entries)!=1:
                    raise ValueError('expected one Content/score.gpif')
                xml=z.read('Content/score.gpif')
                if b'<!DOCTYPE' in xml.upper() or b'<!ENTITY' in xml.upper():
                    raise ValueError('DTD/entities are unsupported')
        except (OSError, ValueError, KeyError, zipfile.BadZipFile) as e:
            return {'status':'invalid_gp_archive','detail':str(e),'parseable_score':0}
    command=[os.environ.get('JAVA','java'),'-Xmx512m','-cp',str(runtime/'lib'/'*'),
             'org.mozilla.javascript.tools.shell.Main',str(runtime/'inspect_score.js'),str(p)]
    try:
        result=subprocess.run(command,capture_output=True,text=True,timeout=45, encoding='utf-8')
    except FileNotFoundError:
        raise RuntimeError('Java runtime missing; verifier infrastructure failure')
    except subprocess.TimeoutExpired:
        return {'status':'parser_timeout','parseable_score':0}
    if result.returncode:
        return {'status':'parse_error_or_unsupported','detail':result.stderr[-3000:],'parseable_score':0}
    try:
        summary=json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError('Parser returned malformed JSON') from e
    valid=summary['track_count']>0 and summary['note_count']>0
    return {'status':'parsed_nonempty' if valid else 'empty_score',
            'parseable_score':int(valid),'file':p.name,'summary':summary}


def main():
    a=argparse.ArgumentParser()
    a.add_argument('--output',type=Path,default=Path('/workspace/output'))
    a.add_argument('--logs',type=Path,default=Path('/logs/verifier'))
    args=a.parse_args()
    args.logs.mkdir(parents=True,exist_ok=True)
    # Fail as infrastructure error without emitting a zero music score.
    (args.logs/'reward.json').unlink(missing_ok=True)
    report=check(args.output,Path(__file__).resolve().parent)
    report['scope']='File parsing only; musical quality is pending blind Codex A/B evaluation.'
    (args.logs/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n', encoding='utf-8')
    (args.logs/'reward.json').write_text(json.dumps({'parseable_score':report['parseable_score']})+'\n', encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__': main()
