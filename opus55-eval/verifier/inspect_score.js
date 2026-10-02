// Native TuxGuitar import only: this is not a musical quality evaluator.
var path=String(arguments[0]);
var reader=new Packages.org.herac.tuxguitar.io.base.TGSongReaderHandle();
reader.setFactory(new Packages.org.herac.tuxguitar.song.managers.TGSongManager().getFactory());
reader.setContext(new Packages.org.herac.tuxguitar.io.base.TGSongStreamContext());
var input=new java.io.BufferedInputStream(new java.io.FileInputStream(path));
reader.setInputStream(input);
try {
  if(path.endsWith('.gp5')) {
    var settings=new Packages.org.herac.tuxguitar.io.gtp.GTPSettings(); settings.setCharset('UTF-8');
    new Packages.org.herac.tuxguitar.io.gtp.GP5InputStream(settings).read(reader);
  } else if(path.endsWith('.gpx')) {
    new Packages.org.herac.tuxguitar.io.gpx.v6.GPXInputStream().read(reader);
  } else {
    new Packages.org.herac.tuxguitar.io.gpx.v7.GPXInputStream().read(reader);
  }
} finally { input.close(); }
var song=reader.getSong(), tracks=[], total=0;
for(var ti=0;ti<song.countTracks();ti++) {
  var t=song.getTrack(ti), notes=0;
  for(var mi=0;mi<t.countMeasures();mi++) {
    var m=t.getMeasure(mi);
    for(var bi=0;bi<m.countBeats();bi++) {
      var b=m.getBeat(bi);
      for(var vi=0;vi<b.countVoices();vi++) notes+=b.getVoice(vi).countNotes();
    }
  }
  total+=notes;
  tracks.push({name:String(t.getName()),percussion:t.isPercussion(),strings:t.getStrings().size(),measures:t.countMeasures(),notes:notes});
}
print(JSON.stringify({track_count:tracks.length,note_count:total,tracks:tracks}));
