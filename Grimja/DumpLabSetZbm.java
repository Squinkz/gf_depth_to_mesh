import com.sqrt.liblab.LabCollection;
import com.sqrt.liblab.LabFile;
import com.sqrt.liblab.codec.BitmapCodec;
import com.sqrt.liblab.entry.graphics.GrimBitmap;
import com.sqrt.liblab.io.DataSource;
import com.sqrt.liblab.io.DiskDataSource;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.awt.image.DataBufferUShort;
import java.io.File;
import java.io.FileOutputStream;
import java.io.PrintWriter;
import java.io.RandomAccessFile;

public class DumpLabSetZbm {
    public static void main(String[] args) throws Exception {
        if (args.length != 2) {
            System.out.println("Usage:");
            System.out.println("java DumpLabSetZbm <input.lab> <outputFolder>");
            return;
        }

        File inputLab = new File(args[0]);
        File outputFolder = new File(args[1]);
        outputFolder.mkdirs();

        LabCollection collection = LabCollection.open(inputLab.getParentFile());

        LabFile labFile = null;

        for (Object object : collection.labs) {
            LabFile currentLab = (LabFile)object;

            if (currentLab.getName().equalsIgnoreCase(inputLab.getName())) {
                labFile = currentLab;
                break;
            }
        }

        if (labFile == null) {
            throw new RuntimeException("Could not find LAB: " + inputLab.getAbsolutePath());
        }

        for (Object object : labFile.entries) {
            DataSource entry = (DataSource)object;

            String name = entry.getName();
            String lowerName = name.toLowerCase();

            entry.position(0);

            if (lowerName.endsWith(".set")) {
                File outFile = new File(outputFolder, name);
                WriteRawEntry(entry, outFile);

                System.out.println("Extracted SET: " + outFile.getAbsolutePath());
            }
            else if (lowerName.endsWith(".zbm")) {
                File extractedZbm = new File(outputFolder, name);
                WriteRawEntry(entry, extractedZbm);

                String csvName = name.substring(0, name.length() - 4) + ".csv";
                File csvFile = new File(outputFolder, csvName);

                WriteExtractedZbmCsv(extractedZbm, csvFile);

                System.out.println("Extracted ZBM: " + extractedZbm.getAbsolutePath());
                System.out.println("Wrote CSV: " + csvFile.getAbsolutePath());
            }
            else if (lowerName.endsWith(".bm")) {
                File extractedBm = new File(outputFolder, name);
                WriteRawEntry(entry, extractedBm);

                String pngName = name.substring(0, name.length() - 3) + ".png";
                File pngFile = new File(outputFolder, pngName);

                WriteExtractedBmPng(extractedBm, pngFile);

                System.out.println("Extracted BM: " + extractedBm.getAbsolutePath());
                System.out.println("Wrote PNG: " + pngFile.getAbsolutePath());
            }
        }
    }

    private static void WriteRawEntry(DataSource entry, File outputFile) throws Exception {
        outputFile.getParentFile().mkdirs();
        entry.position(0);

        try (FileOutputStream outputStream = new FileOutputStream(outputFile)) {
            byte[] buffer = new byte[8192];

            while (entry.remaining() > 0) {
                int readSize = (int)Math.min(buffer.length, entry.remaining());
                entry.get(buffer, 0, readSize);
                outputStream.write(buffer, 0, readSize);
            }
        }
    }

    private static void WriteExtractedZbmCsv(File inputFile, File outputFile) throws Exception {
        outputFile.getParentFile().mkdirs();

        BitmapCodec codec = new BitmapCodec();

        try (RandomAccessFile randomAccessFile = new RandomAccessFile(inputFile, "r")) {
            DiskDataSource source = new DiskDataSource(null, inputFile.getName(), randomAccessFile);

            GrimBitmap bitmap = codec.read(source);
            BufferedImage image = bitmap.images.get(0);

            int width = image.getWidth();
            int height = image.getHeight();

            DataBufferUShort buffer = (DataBufferUShort)image.getRaster().getDataBuffer();
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

            System.out.println("ZBM size: " + width + " x " + height);
        }
    }

    private static void WriteExtractedBmPng(File inputFile, File outputFile) throws Exception {
        outputFile.getParentFile().mkdirs();

        BitmapCodec codec = new BitmapCodec();

        try (RandomAccessFile randomAccessFile = new RandomAccessFile(inputFile, "r")) {
            DiskDataSource source = new DiskDataSource(null, inputFile.getName(), randomAccessFile);

            GrimBitmap bitmap = codec.read(source);
            BufferedImage image = bitmap.images.get(0);

            if (!ImageIO.write(image, "png", outputFile)) {
                throw new RuntimeException("Could not write PNG: " + outputFile.getAbsolutePath());
            }

            source.close();

            System.out.println("BM size: " + image.getWidth() + " x " + image.getHeight());
        }
    }
}