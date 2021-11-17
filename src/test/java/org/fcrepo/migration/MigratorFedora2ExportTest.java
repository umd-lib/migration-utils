package org.fcrepo.migration;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.FileWriter;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.file.FileVisitResult;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.SimpleFileVisitor;
import java.nio.file.attribute.BasicFileAttributes;
import java.util.Arrays;

import javax.xml.stream.XMLStreamException;

import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVPrinter;
import org.fcrepo.migration.foxml.FoxmlInputStreamFedoraObjectProcessor;
import org.fcrepo.migration.foxml.InternalIDResolver;
import org.fcrepo.migration.foxml.LegacyFSIDResolver;
import org.fcrepo.migration.handlers.Fedora2ExportStreamingFedoraObjectHandler;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import junit.framework.AssertionFailedError;

/**
 * @author dsteelma
 */
public class MigratorFedora2ExportTest {
    @Rule
    public TemporaryFolder tempTargetDir = new TemporaryFolder();

    /**
     * Creates and returns an MigratorFedora2Export for use in testing.
     *
     * @param exportOutputDir
     *            a File representing the (temporary) directory to write the
     *            exported files to.
     * @param csvWriter
     *            the CSVPrinter to use in writing the CSV files
     * @return a MigratorFedora2Export to use in testing
     * @throws Exception
     *             if an exception occurs
     */
    public MigratorFedora2Export createExportMigrator(
            final File exportOutputDir, final CSVPrinter csvWriter) throws Exception {
        final File baseInputsDir = new File(
                this.getClass().getClassLoader().getResource("migration/export/fedora2/").getFile());
        final File inputsDir = new File(baseInputsDir, "inputs/");

        final InternalIDResolver idResolver = new LegacyFSIDResolver(null, inputsDir);
        final String f3hostname = "fcrepo.example.com";
        final Fedora2ExportStreamingFedoraObjectHandler objectHandler = new Fedora2ExportStreamingFedoraObjectHandler();

        final File filterJsonInputFile = new File(inputsDir, "filter.json");
        final InputStream filterJsonStream = new FileInputStream(filterJsonInputFile);

        final BufferedReader jsonReader = new BufferedReader(new InputStreamReader(filterJsonStream));

        final MigratorFedora2Export exportMigrator = new TestMigratorFedora2Export(exportOutputDir, csvWriter,
                objectHandler,
                jsonReader, idResolver, f3hostname, inputsDir);
        return exportMigrator;
    }

    @Test
    public void testSanity() throws Exception {
        final File exportOutputDir = tempTargetDir.getRoot();
        final File csvOutputFile = new File(exportOutputDir, "export.csv");
        final CSVPrinter csvWriter = new CSVPrinter(new FileWriter(csvOutputFile),
                CSVFormat.DEFAULT.withHeader("umdm", "umam", "location", "title", "handle"));

        final MigratorFedora2Export exportMigrator = createExportMigrator(exportOutputDir, csvWriter);
        try {
            exportMigrator.run();
        } finally {
            if (csvWriter != null) {
                csvWriter.close();
            }
        }

        final File expectedOutputDir = new File(
                this.getClass().getClassLoader().getResource("migration/export/fedora2/expected").getFile());
        verifyDirsAreEqual(expectedOutputDir.toPath(), exportOutputDir.toPath());
    }

    /**
     * Subclass of MigratorFedora2Export that enables overrides of methods
     * needed to facilitate testing.
     */
    public static class TestMigratorFedora2Export extends MigratorFedora2Export {
        private File inputsDir;

        public TestMigratorFedora2Export(
                final File targetDir, final CSVPrinter csvWriter,
                final Fedora2ExportStreamingFedoraObjectHandler handler,
                final BufferedReader jsonReader,
                final InternalIDResolver resolver, final String localFedoraServer,
                final File inputsDir) {
            super(targetDir, csvWriter, handler, jsonReader, resolver, localFedoraServer);
            this.inputsDir = inputsDir;
        }

        @Override
        protected FoxmlInputStreamFedoraObjectProcessor createProcessor(final File umdmFile)
                throws FileNotFoundException, XMLStreamException {
            final File objectFile = new File(inputsDir, umdmFile.getPath());
            return new FoxmlInputStreamFedoraObjectProcessor(
                    objectFile, new FileInputStream(objectFile), fetcher, resolver, localFedoraServer);
        }
    }

    /**
     * Helper class that compares all the files in a file hierarchy.
     *
     * Largely derived from https://stackoverflow.com/a/39584230
     *
     * @param expected
     * @param actual
     * @throws IOException
     *             if an I/O exception occurs.
     */
    private static void verifyDirsAreEqual(final Path expected, final Path actual) throws IOException {
        Files.walkFileTree(expected, new SimpleFileVisitor<Path>() {
            @Override
            public FileVisitResult visitFile(final Path file,
                    final BasicFileAttributes attrs)
                    throws IOException {
                final FileVisitResult result = super.visitFile(file, attrs);

                // get the relative file name from path "one"
                final Path relativize = expected.relativize(file);
                // construct the path for the counterpart file in "other"
                final Path fileInOther = actual.resolve(relativize);

                final byte[] otherBytes = Files.readAllBytes(fileInOther);
                final byte[] theseBytes = Files.readAllBytes(file);
                if (!Arrays.equals(otherBytes, theseBytes)) {
                    throw new AssertionFailedError(file + " is not equal to " + fileInOther);
                }
                return result;
            }
        });
    }
}