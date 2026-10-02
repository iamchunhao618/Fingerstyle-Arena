// Arguments: submitted.gp, pinned gp_native_read.js. Emit JSON, not GP5.
load(String(arguments[1]));
var song = reader.getSong();
var out = {title:String(song.getName()),author:String(song.getAuthor()),tracks:[]};
var flags = ['DeadNote','Vibrato','Bend','TremoloBar','Trill','TremoloPicking','Hammer','Slide',
    'GhostNote','AccentuatedNote','HeavyAccentuatedNote','PalmMute','Staccato','LetRing',
    'Popping','Slapping','Tapping','Harmonic','Grace','FadeIn'];
for(var ti=0;ti<song.countTracks();ti++) {
    var track=song.getTrack(ti), tr={name:String(track.getName()),capo:track.getOffset(),
        percussion:track.isPercussion(),strings:[],measures:[]};
    var strings=track.getStrings();
    for(var si=0;si<strings.size();si++)tr.strings.push([strings.get(si).getNumber(),strings.get(si).getValue()]);
    for(var mi=0;mi<track.countMeasures();mi++) {
        var m=track.getMeasure(mi), h=m.getHeader(), meter=m.getTimeSignature();
        var mr={time:[meter.getNumerator(),meter.getDenominator().getValue()],length:Number(m.getLength()),
            key:m.getKeySignature(),clef:m.getClef(),tempo:m.getTempo().getValue(),
            repeat_open:m.isRepeatOpen(),repeat_close:m.getRepeatClose(),ending:h.getRepeatAlternative(),
            triplet_feel:m.getTripletFeel(),marker:m.getMarker()==null?'':String(m.getMarker().getTitle()),beats:[]};
        for(var bi=0;bi<m.countBeats();bi++) {
            var b=m.getBeat(bi), br={onset:Number(b.getStart()-m.getStart()),stroke:b.getStroke().getDirection(),
                text:b.isTextBeat()?String(b.getText().getValue()):'',chord:b.isChordBeat(),voices:[]};
            for(var vi=0;vi<b.countVoices();vi++) {
                var v=b.getVoice(vi);if(v.isEmpty())continue;
                var d=v.getDuration(), vr={index:vi,duration:[d.getValue(),d.isDotted(),d.isDoubleDotted(),
                    d.getDivision().getEnters(),d.getDivision().getTimes()],ticks:Number(d.getTime()),notes:[]};
                for(var ni=0;ni<v.countNotes();ni++) {
                    var n=v.getNote(ni), e=n.getEffect(), nr={string:n.getString(),fret:n.getValue(),tie:n.isTiedNote(),effects:[]};
                    for(var fi=0;fi<flags.length;fi++)if(e['is'+flags[fi]]())nr.effects.push(flags[fi]);
                    vr.notes.push(nr);
                }
                br.voices.push(vr);
            }
            mr.beats.push(br);
        }
        tr.measures.push(mr);
    }
    out.tracks.push(tr);
}
print(JSON.stringify(out));
