var gtpSettings = new Packages.org.herac.tuxguitar.io.gtp.GTPSettings();
gtpSettings.setCharset("UTF-8");
// Export original source directly with the same capo mapping and PDF profile.
var manager = new Packages.org.herac.tuxguitar.song.managers.TGSongManager();
var reader = new Packages.org.herac.tuxguitar.io.base.TGSongReaderHandle();
reader.setFactory(manager.getFactory());
reader.setContext(new Packages.org.herac.tuxguitar.io.base.TGSongStreamContext());
var input = new java.io.BufferedInputStream(new java.io.FileInputStream(arguments[0]));
reader.setInputStream(input);
try {
    if (String(arguments[0]).toLowerCase().endsWith('.gpx')) {
        new Packages.org.herac.tuxguitar.io.gpx.v6.GPXInputStream().read(reader);
    } else {
        new Packages.org.herac.tuxguitar.io.gpx.v7.GPXInputStream().read(reader);
    }
} finally { input.close(); }
// GP7 capo metadata is omitted by the 1.6.6 importer; retain it explicitly.
if (String(arguments[0]).toLowerCase().endsWith('.gp')) {
    var zip = new java.util.zip.ZipFile(arguments[0]);
    try {
        var factory = javax.xml.parsers.DocumentBuilderFactory.newInstance();
        factory.setFeature('http://apache.org/xml/features/disallow-doctype-decl', true);
        factory.setFeature('http://xml.org/sax/features/external-general-entities', false);
        factory.setFeature('http://xml.org/sax/features/external-parameter-entities', false);
        var stream = zip.getInputStream(zip.getEntry('Content/score.gpif'));
        var doc;
        try { doc = factory.newDocumentBuilder().parse(stream); } finally { stream.close(); }
        var xpath = javax.xml.xpath.XPathFactory.newInstance().newXPath();
        var tracks = xpath.evaluate('/GPIF/Tracks/Track', doc, javax.xml.xpath.XPathConstants.NODESET);
        if (tracks.getLength() != reader.getSong().countTracks()) throw new Error('Track mapping mismatch');
        for (var i = 0; i < tracks.getLength(); i++) {
            var capo = String(xpath.evaluate("Staves/Staff[1]/Properties/Property[@name='CapoFret']/Fret", tracks.item(i)));
            if (capo.length) reader.getSong().getTrack(i).setOffset(parseInt(capo, 10));
        }
    } finally { zip.close(); }
}
manager.autoCompleteSilences(reader.getSong());
manager.orderBeats(reader.getSong());
var writer = new Packages.org.herac.tuxguitar.io.base.TGSongWriterHandle();
writer.setFactory(manager.getFactory());
writer.setSong(reader.getSong());
writer.setContext(new Packages.org.herac.tuxguitar.io.base.TGSongStreamContext());
var output = new java.io.BufferedOutputStream(new java.io.FileOutputStream(arguments[1]));
writer.setOutputStream(output);
try {
    new Packages.org.herac.tuxguitar.io.pdf.PDFSongWriter(new Packages.org.herac.tuxguitar.util.TGContext()).write(writer);
} finally { output.close(); }
