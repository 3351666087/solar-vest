import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.rendering.PDFRenderer;
import org.apache.pdfbox.Loader;
import javax.imageio.ImageIO;
import java.io.File;

public class Preview {
    public static void main(String[] a) throws Exception {
        File pdf = new File(a[0]);
        String outDir = a.length > 1 ? a[1] : "preview";
        int dpi = a.length > 2 ? Integer.parseInt(a[2]) : 110;
        new File(outDir).mkdirs();
        try (PDDocument d = Loader.loadPDF(pdf)) {
            PDFRenderer r = new PDFRenderer(d);
            int n = d.getNumberOfPages();
            for (int i = 0; i < n; i++) {
                ImageIO.write(r.renderImageWithDPI(i, dpi), "png",
                    new File(outDir, String.format("p%02d.png", i+1)));
            }
            System.out.println("pages=" + n + " -> " + outDir);
        }
    }
}
