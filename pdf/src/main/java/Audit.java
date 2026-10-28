import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.rendering.PDFRenderer;
import org.apache.pdfbox.Loader;
import java.awt.image.BufferedImage;
import java.io.File;

/** Per-page content-height audit: finds pages that are mostly empty. */
public class Audit {
    public static void main(String[] a) throws Exception {
        try (PDDocument d = Loader.loadPDF(new File(a[0]))) {
            PDFRenderer r = new PDFRenderer(d);
            for (int i = 0; i < d.getNumberOfPages(); i++) {
                BufferedImage img = r.renderImageWithDPI(i, 60);
                int W = img.getWidth(), H = img.getHeight();
                float ph = d.getPage(i).getMediaBox().getHeight() / 72f * 25.4f;
                boolean land = d.getPage(i).getMediaBox().getWidth() > d.getPage(i).getMediaBox().getHeight();
                float phMm = ph;
                boolean landscape = land;
                int yTop = (int)((landscape ? 15f : 17f) / phMm * H);
                int yBot = (int)((phMm - (landscape ? 14f : 16f)) / phMm * H);
                int last = -1, first = -1;
                for (int y = yTop; y < yBot; y++) {
                    boolean ink = false;
                    for (int x = 0; x < W; x++) {
                        int p = img.getRGB(x,y) & 0xFFFFFF;
                        if (((p>>16)&255)<242 || ((p>>8)&255)<242 || (p&255)<242) { ink = true; break; }
                    }
                    if (ink) { if (first < 0) first = y; last = y; }
                }
                // ignore the running header/footer band when judging fill
                float bodyTop = land ? 15f : 17f, bodyBot = ph - (land ? 14f : 16f);
                float lastMm = last * ph / H;
                float fill = Math.max(0, (lastMm - bodyTop)) / (bodyBot - bodyTop) * 100;
                String flag = fill < 55 ? "  <-- half empty" : "";
                System.out.printf("p%-3d %s  content to %.0f mm / %.0f mm   fill %3.0f%%%s%n",
                    i+1, land ? "L" : "P", lastMm, bodyBot, fill, flag);
            }
        }
    }
}
