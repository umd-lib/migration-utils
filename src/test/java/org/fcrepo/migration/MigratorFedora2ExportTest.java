package org.fcrepo.migration;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;

import javax.xml.stream.XMLStreamException;

import org.fcrepo.migration.MigratorFedora2Export.ExportWriter;
import org.fcrepo.migration.MigratorFedora2Export.CSVExportWriter;
import org.fcrepo.migration.foxml.FoxmlInputStreamFedoraObjectProcessor;
import org.fcrepo.migration.foxml.InternalIDResolver;
import org.fcrepo.migration.foxml.LegacyFSIDResolver;
import org.fcrepo.migration.handlers.Fedora2ExportStreamingFedoraObjectHandler;
import org.fcrepo.migration.utils.TestUtils;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

/**
 * Tests for the Fedora 2 "export" migration action
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
     * @param exportWriter
     *            the ExportWriter to use in writing the export metadata file
     * @return a MigratorFedora2Export to use in testing
     * @throws Exception
     *             if an exception occurs
     */
    public MigratorFedora2Export createExportMigrator(
            final File exportOutputDir, final ExportWriter exportWriter,
            final Set<String> datastreamsInclude) throws Exception {
        final File testInputsDir = new File(
                this.getClass().getClassLoader().getResource("migration/export/fedora2/inputs/").getFile());

        final InternalIDResolver idResolver = new LegacyFSIDResolver(null, testInputsDir);
        final String f3hostname = "fcrepo.example.com";
        final Fedora2ExportStreamingFedoraObjectHandler objectHandler =
            new Fedora2ExportStreamingFedoraObjectHandler(datastreamsInclude);

        final File filterJsonInputFile = new File(testInputsDir, "filter.json");
        final InputStream filterJsonStream = new FileInputStream(filterJsonInputFile);

        final BufferedReader jsonReader = new BufferedReader(new InputStreamReader(filterJsonStream));

        final MigratorFedora2Export exportMigrator = new TestMigratorFedora2Export(exportOutputDir, exportWriter,
                objectHandler,
                jsonReader, idResolver, f3hostname, testInputsDir);
        return exportMigrator;
    }

    @Test
    public void testCsvExport() throws Exception {
        final File exportOutputDir = tempTargetDir.getRoot();
        final File csvOutputFile = new File(exportOutputDir, "export.csv");
        final ExportWriter exportWriter = new CSVExportWriter(csvOutputFile.toString());

        final HashSet<String> datastreamsInclude = null;

        final MigratorFedora2Export exportMigrator =
            createExportMigrator(exportOutputDir, exportWriter, datastreamsInclude);
        try {
            exportMigrator.run();
        } finally {
            if (exportWriter != null) {
                exportWriter.close();
            }
        }

        final File expectedOutputDir = new File(
                this.getClass().getClassLoader().getResource("migration/export/fedora2/expected").getFile());
        TestUtils.assertDirsAreEqual(expectedOutputDir.toPath(), exportOutputDir.toPath());
    }

    @Test
    public void testCsvExportDatastreamList() throws Exception {
        final File exportOutputDir = tempTargetDir.getRoot();
        final File csvOutputFile = new File(exportOutputDir, "export.csv");
        final ExportWriter exportWriter = new CSVExportWriter(csvOutputFile.toString());

        final HashSet<String> datastreamsInclude = new HashSet<String>(Arrays.asList(
            new String[]{"amInfo-properties.json", "amInfo.xml", "doInfo-properties.json", "doInfo.xml", "foxml.xml",
                         "properties.json", "rels-mets-properties.json", "rels-mets.xml", "umam-properties.json",
                         "umam.xml", "umdm-properties.json", "umdm.xml"}
        ));

        final MigratorFedora2Export exportMigrator =
            createExportMigrator(exportOutputDir, exportWriter, datastreamsInclude);
        try {
            exportMigrator.run();
        } finally {
            if (exportWriter != null) {
                exportWriter.close();
            }
        }

        final File expectedOutputDir = new File(
                this.getClass().getClassLoader().getResource("migration/export/fedora2/expected").getFile());
        TestUtils.assertDirsAreEqual(expectedOutputDir.toPath(), exportOutputDir.toPath());
    }

    @Test
    public void testCsvExportLimitedFiles() throws Exception {
        final File exportOutputDir = tempTargetDir.getRoot();
        final File csvOutputFile = new File(exportOutputDir, "export.csv");
        final ExportWriter exportWriter = new CSVExportWriter(csvOutputFile.toString());

        final HashSet<String> datastreamsInclude = new HashSet<String>(Arrays.asList(
            new String[]{"amInfo-properties.json", "umdm.xml"}
        ));

        final MigratorFedora2Export exportMigrator =
            createExportMigrator(exportOutputDir, exportWriter, datastreamsInclude);
        try {
            exportMigrator.run();
        } finally {
            if (exportWriter != null) {
                exportWriter.close();
            }
        }

        final File expectedOutputDir = new File(
                this.getClass().getClassLoader()
                    .getResource("migration/export/fedora2/expected_limited_files").getFile());
        TestUtils.assertDirsAreEqual(expectedOutputDir.toPath(), exportOutputDir.toPath());
    }


    /**
     * Subclass of MigratorFedora2Export that enables overrides of methods
     * needed to facilitate testing.
     */
    public static class TestMigratorFedora2Export extends MigratorFedora2Export {
        private File testInputsDir;

        /**
         * The additional "testInputsDir" points to the test resources directory
         * containing the "filter.json" file, and "object" directory tree
         *
         * @param targetDir
         *          the directory to write the output to
         * @param exportWriter
         *          the ExportWriter to use to generate the export metadata file
         * @param handler
         *          the Fedora2ExportStreamingFedoraObjectHandler that exports
         *          the object information
         * @param jsonReader
         *          the BufferedReader that reads the JSON file generated by
         *          the "scripts/filter.py" script.
         * @param resolver
         *          the InternalIDResolver for resolving fedora/FOXML IDs
         * @param localFedoraServer
         *          the host and port where the content is exposed
         * @param testInputsDir
         *          the test resources directory containing the "filter.json"
         *          file, and "object" directory tree used for input
         */
        public TestMigratorFedora2Export(
                final File targetDir, final ExportWriter exportWriter,
                final Fedora2ExportStreamingFedoraObjectHandler handler,
                final BufferedReader jsonReader,
                final InternalIDResolver resolver, final String localFedoraServer,
                final File testInputsDir) {
            super(targetDir, exportWriter, handler, jsonReader, resolver, localFedoraServer);
            this.testInputsDir = testInputsDir;
        }

        /**
         * Overriding the original method because the "umdmFile.getPath()"
         * method returns a relative path to the objects
         * (i.e., "objects/2006/.."). This override modifies the path to prepend
         * the test resource directory path for the "objects" directory tree.
         */
        @Override
        protected FoxmlInputStreamFedoraObjectProcessor createProcessor(final File umdmFile)
                throws FileNotFoundException, XMLStreamException {
            final File objectFile = new File(testInputsDir, umdmFile.getPath());
            return new FoxmlInputStreamFedoraObjectProcessor(
                    objectFile, new FileInputStream(objectFile), fetcher, resolver, localFedoraServer);
        }
    }
}