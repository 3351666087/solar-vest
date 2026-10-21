import com.openhtmltopdf.pdfboxout.PdfRendererBuilder;
import com.openhtmltopdf.svgsupport.BatikSVGDrawer;
import com.openhtmltopdf.outputdevice.helper.BaseRendererBuilder.FontStyle;
import java.io.*;
import java.nio.file.*;
import java.util.Locale;
import com.openhtmltopdf.bidi.support.ICUBreakers;

public class Render {
    static void f(PdfRendererBuilder b, String file, String fam, int w) {
        File x = new File("assets/fonts", file);
        if (!x.exists()) { System.err.println("!! missing " + x); return; }
        b.useFont(x, fam, w, FontStyle.NORMAL, true);
    }
    public static void main(String[] a) throws Exception {
        String out = a[0];
        long t0 = System.currentTimeMillis();
        java.util.List<File> parts = new java.util.ArrayList<>();
        for (int i = 1; i < a.length; i++) parts.add(renderOne(a[i]));
        org.apache.pdfbox.multipdf.PDFMergerUtility m = new org.apache.pdfbox.multipdf.PDFMergerUtility();
        m.setDestinationFileName(out);
        for (File f : parts) m.addSource(f);
        m.mergeDocuments(org.apache.pdfbox.io.MemoryUsageSetting.setupMainMemoryOnly().streamCache);
        for (File f : parts) f.delete();
        stampPageNumbers(out);
        System.out.printf("OK %s  %,d bytes  %d ms%n", out, new File(out).length(), System.currentTimeMillis()-t0);
    }

    /** Continuous page numbers across the merged parts; the cover stays unnumbered. */
    static void stampPageNumbers(String path) throws Exception {
        File f = new File(path);
        try (org.apache.pdfbox.pdmodel.PDDocument d = org.apache.pdfbox.Loader.loadPDF(f)) {
            org.apache.pdfbox.pdmodel.font.PDFont font = org.apache.pdfbox.pdmodel.font.PDType0Font
                .load(d, new File("assets/fonts/Inter-SemiBold.ttf"));
            int n = d.getNumberOfPages();
            for (int i = 1; i < n; i++) {   // page 0 = cover
                org.apache.pdfbox.pdmodel.PDPage pg = d.getPage(i);
                float pw = pg.getMediaBox().getWidth();
                boolean land = pw > pg.getMediaBox().getHeight();
                float right = land ? 39.7f : 45.4f;   // 14mm / 16mm
                float baseY = land ? 25f : 28f;
                String s = String.valueOf(i);
                float size = 9f;
                float tw = font.getStringWidth(s) / 1000f * size;
                try (org.apache.pdfbox.pdmodel.PDPageContentStream cs =
                         new org.apache.pdfbox.pdmodel.PDPageContentStream(d, pg,
                             org.apache.pdfbox.pdmodel.PDPageContentStream.AppendMode.APPEND, true, true)) {
                    cs.beginText();
                    cs.setFont(font, size);
                    cs.setNonStrokingColor(0.27f, 0.33f, 0.43f);
                    cs.newLineAtOffset(pw - right - tw, baseY);
                    cs.showText(s);
                    cs.endText();
                }
            }
            File tmp = new File(f.getParentFile(), f.getName() + ".stamp.tmp");
            d.save(tmp);
            java.nio.file.Files.move(tmp.toPath(), f.toPath(),
                java.nio.file.StandardCopyOption.REPLACE_EXISTING);
        }
    }

    static File renderOne(String in) throws Exception {
        String xhtml = Files.readString(Path.of(in));
        File tmp = File.createTempFile("part-", ".pdf", new File("."));
        try (OutputStream os = new FileOutputStream(tmp)) {
            PdfRendererBuilder b = new PdfRendererBuilder();
            b.useFastMode();
            b.useSVGDrawer(new BatikSVGDrawer());
            // 中日韩断行：默认断行器只认空格，必须换成 ICU
            b.useUnicodeLineBreaker(new ICUBreakers.ICULineBreaker(Locale.CHINA));
            b.useUnicodeCharacterBreaker(new ICUBreakers.ICUCharacterBreaker(Locale.CHINA));
            // Latin — Inter (static weights)
            f(b, "Inter-Regular.ttf",          "UI", 400);
            f(b, "Inter-Medium.ttf",           "UI", 500);
            f(b, "Inter-SemiBold.ttf",         "UI", 600);
            f(b, "Inter-Bold.ttf",             "UI", 700);
            f(b, "InterDisplay-Medium.ttf",    "Display", 500);
            f(b, "InterDisplay-SemiBold.ttf",  "Display", 600);
            f(b, "InterDisplay-Bold.ttf",      "Display", 700);
            // CJK — STHeiti SC (real two weights, glyf outlines)
            f(b, "STHeitiSC-Light.ttf",        "CJK", 400);
            f(b, "STHeitiSC-Light.ttf",        "CJK", 500);
            f(b, "STHeitiSC-Medium.ttf",       "CJK", 600);
            f(b, "STHeitiSC-Medium.ttf",       "CJK", 700);
            // Mono
            f(b, "Menlo-Regular.ttf",          "Mono", 400);
            f(b, "Menlo-Bold.ttf",             "Mono", 700);
            b.withHtmlContent(xhtml, new File(".").toURI().toString());
            b.toStream(os);
            b.run();
        }
        return tmp;
    }
}
