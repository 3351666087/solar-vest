import com.openhtmltopdf.pdfboxout.*;
import com.openhtmltopdf.outputdevice.helper.BaseRendererBuilder.FontStyle;
import com.openhtmltopdf.extend.FSSupplier;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.font.*;
import org.apache.fontbox.ttf.*;
import org.apache.pdfbox.io.RandomAccessReadBufferedFile;
import java.io.*;

public class FontTest {
  static final String HTML = """
    <?xml version="1.0" encoding="UTF-8"?><!DOCTYPE html>
    <html xmlns="http://www.w3.org/1999/xhtml"><head><meta charset="UTF-8"/><style>
    @page{size:A4;margin:15mm} body{font-family:PF;font-size:11pt}
    </style></head><body>
    <p style="font-weight:400">正文 400：太阳能采集供电的可穿戴健康监测系统，能量自主率 EAR 3.91。</p>
    <p style="font-weight:700">标题 700：电磁兼容是本项目的头号技术风险 — EMC Risk</p>
    <p>Latin 0123456789 — 18V/1.67A, 2500mAh, ±0.4%/°C</p>
    </body></html>""";

  static PDFont otf(PDDocument doc, String path) throws IOException {
    OTFParser p = new OTFParser();
    OpenTypeFont f = p.parse(new RandomAccessReadBufferedFile(new File(path)));
    return PDType0Font.load(doc, f, true);
  }

  public static void main(String[] a) throws Exception {
    String fdir = "assets/fonts/";

    // --- A: PingFang via OTFParser + PDFontSupplier ---
    try (PDDocument doc = new PDDocument(); OutputStream os = new FileOutputStream("ft_pingfang.pdf")) {
      PdfRendererBuilder b = new PdfRendererBuilder();
      b.useFastMode(); b.usePDDocument(doc);
      PDFont reg = otf(doc, fdir+"PingFangSC-Regular.ttf");
      PDFont bold= otf(doc, fdir+"PingFangSC-Semibold.ttf");
      b.useFont(new PDFontSupplier(reg), "PF", 400, FontStyle.NORMAL, true);
      b.useFont(new PDFontSupplier(bold),"PF", 700, FontStyle.NORMAL, true);
      b.withHtmlContent(HTML, new File(".").toURI().toString());
      b.toStream(os); b.run();
      System.out.println("A PingFang OTF  : OK");
    } catch (Throwable t) { System.out.println("A PingFang OTF  : FAIL " + t); }

    // --- B: Noto Sans SC variable ---
    try (OutputStream os = new FileOutputStream("ft_noto.pdf")) {
      PdfRendererBuilder b = new PdfRendererBuilder(); b.useFastMode();
      b.useFont(new File(fdir+"NotoSansSC.ttf"), "PF", 400, FontStyle.NORMAL, true);
      b.useFont(new File(fdir+"NotoSansSC.ttf"), "PF", 700, FontStyle.NORMAL, true);
      b.withHtmlContent(HTML, new File(".").toURI().toString());
      b.toStream(os); b.run();
      System.out.println("B NotoSansSC var: OK");
    } catch (Throwable t) { System.out.println("B NotoSansSC var: FAIL " + t); }

    // --- C: STHeiti glyf ---
    try (OutputStream os = new FileOutputStream("ft_stheiti.pdf")) {
      PdfRendererBuilder b = new PdfRendererBuilder(); b.useFastMode();
      b.useFont(new File(fdir+"STHeitiSC-Light.ttf"),  "PF", 400, FontStyle.NORMAL, true);
      b.useFont(new File(fdir+"STHeitiSC-Medium.ttf"), "PF", 700, FontStyle.NORMAL, true);
      b.withHtmlContent(HTML, new File(".").toURI().toString());
      b.toStream(os); b.run();
      System.out.println("C STHeiti glyf  : OK");
    } catch (Throwable t) { System.out.println("C STHeiti glyf  : FAIL " + t); }

    // --- D: can AWT/Batik see CJK families? ---
    String[] fams = java.awt.GraphicsEnvironment.getLocalGraphicsEnvironment().getAvailableFontFamilyNames();
    int n=0; StringBuilder sb=new StringBuilder();
    for (String f : fams) if (f.matches(".*(PingFang|Heiti|Songti|Hiragino|Noto Sans).*")) { if(n++<8) sb.append(f).append(" | "); }
    System.out.println("D AWT CJK families: "+n+"  e.g. "+sb);
  }
}
