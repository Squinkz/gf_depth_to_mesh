import com.sqrt.liblab.codec.BitmapCodec;
import com.sqrt.liblab.entry.graphics.GrimBitmap;
import com.sqrt.liblab.io.DiskDataSource;

import java.awt.image.BufferedImage;
import java.awt.image.DataBufferUShort;
import java.io.File;
import java.io.PrintWriter;
import java.io.RandomAccessFile;

public class DumpExtractedZbm {
    public static void main(String[] args) throws Exception {
        if (args.length != 2) {
            System.out.println("Usage:");
            System.out.println("java DumpExtractedZbm <input.zbm> <output.csv>");
            return;
        }

        File inputFile = new File(args[0]);
        File outputFile = new File(args[1]);

        BitmapCodec codec = new BitmapCodec();

        try (RandomAccessFile randomAccessFile = new RandomAccessFile(inputFile, "r")) {
            DiskDataSource source = new DiskDataSource(null, inputFile.getName(), randomAccessFile);

            GrimBitmap bitmap = codec.read(source);
            BufferedImage image = bitmap.images.get(0);

            int width = image.getWidth();
            int height = image.getHeight();

            DataBufferUShort buffer = (DataBufferUShort) image.getRaster().getDataBuffer();
            short[] rawPixels = buffer.getData();

            try (PrintWriter writer = new PrintWriter(outputFile)) {
                writer.println("x,y,value");

                for (int y = 0; y < height; y++) {
                    for (int x = 0; x < width; x++) {
                        int index = y * width + x;
                        int value = rawPixels[index] & 0xffff;
                        writer.println(x + "," + y + "," + value);
                    }
                }
            }

            source.close();

            System.out.println("Image size: " + width + " x " + height);
            System.out.println("Wrote: " + outputFile.getAbsolutePath());
        }
    }
}