import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.rendering.PDFRenderer;
import org.apache.pdfbox.Loader;
import java.awt.image.BufferedImage;
import java.io.File;

/** Report the ink bounding box of a page, in mm, to calibrate diagram sizing. */
public class Measure {
    public static void main(String[] a) throws Exception {
        File pdf = new File(a[0]);
        int page = Integer.parseInt(a[1]) - 1;
        int dpi = 150;
        try (PDDocument d = Loader.loadPDF(pdf)) {
            float pwPt = d.getPage(page).getMediaBox().getWidth();
            float phPt = d.getPage(page).getMediaBox().getHeight();
            BufferedImage img = new PDFRenderer(d).renderImageWithDPI(page, dpi);
            int W = img.getWidth(), H = img.getHeight();
            double mmPerPx = (pwPt / 72.0 * 25.4) / W;
            int x0=W, y0=H, x1=-1, y1=-1;
            for (int y = 0; y < H; y++) for (int x = 0; x < W; x++) {
                int p = img.getRGB(x,y) & 0xFFFFFF;
                int r=(p>>16)&255, g=(p>>8)&255, b=p&255;
                if (r<245 || g<245 || b<245) { if(x<x0)x0=x; if(x>x1)x1=x; if(y<y0)y0=y; if(y>y1)y1=y; }
            }
            System.out.printf("page %d  %.0f x %.0f pt  (%.0f x %.0f mm)%n",
                page+1, pwPt, phPt, pwPt/72*25.4, phPt/72*25.4);
            System.out.printf("  ink bbox: x %.1f–%.1f mm   y %.1f–%.1f mm   (w %.1f mm, h %.1f mm)%n",
                x0*mmPerPx, x1*mmPerPx, y0*mmPerPx, y1*mmPerPx,
                (x1-x0)*mmPerPx, (y1-y0)*mmPerPx);
        }
    }
}
