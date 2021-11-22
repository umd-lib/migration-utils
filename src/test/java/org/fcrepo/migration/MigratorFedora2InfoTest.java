package org.fcrepo.migration;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.io.Writer;
import java.nio.file.Path;

import org.fcrepo.migration.handlers.Fedora2InfoStreamingFedoraObjectHandler;
import org.fcrepo.migration.utils.TestUtils;
import org.fcrepo.migration.foxml.InternalIDResolver;
import org.fcrepo.migration.foxml.LegacyFSIDResolver;
import org.fcrepo.migration.foxml.NativeFoxmlDirectoryObjectSource;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

/**
 * Tests for the Fedora 2 "info" migration action
 * @author dsteelma
 */
public class MigratorFedora2InfoTest {
    @Rule
    public TemporaryFolder tempTargetDir = new TemporaryFolder();

    /**
     * Creates and returns an MigratorFedora2Info for use in testing.
     *
     * @param objectSource
     * @param writer
     * @return a MigratorFedora2Info to use in testing
     * @throws Exception
     *             if an exception occurs
     */
    public MigratorFedora2Info createInfoMigrator(
            final ObjectSource objectSource, final Writer writer, final Path testDataBasePath) throws Exception {

        final Fedora2InfoStreamingFedoraObjectHandler objectHandler =
                new TestFedora2InfoStreamingFedoraObjectHandler(writer, testDataBasePath);
        final MigratorFedora2Info infoMigrator = new MigratorFedora2Info(objectSource, objectHandler);
        return infoMigrator;
    }

    @Test
    public void testInfoAction() throws Exception {
        final File testInputsDir = new File(
                this.getClass().getClassLoader().getResource("migration/info/fedora2/inputs/").getFile());
        final File objectStore = new File(testInputsDir, "objects");
        final InternalIDResolver idResolver = new LegacyFSIDResolver(null, testInputsDir);
        final String f3hostname = "fcrepo.example.com";

        final ObjectSource objectSource = new NativeFoxmlDirectoryObjectSource(objectStore, idResolver, f3hostname);

        final File exportOutputDir = tempTargetDir.getRoot();
        final BufferedWriter jsonWriter = new BufferedWriter(new FileWriter(new File(exportOutputDir, "info.json")));

        final MigratorFedora2Info infoMigrator = createInfoMigrator(objectSource, jsonWriter, testInputsDir.toPath());
        try {
            infoMigrator.run();
        } finally {
            if (jsonWriter != null) {
                jsonWriter.close();
            }
        }

        final File expectedOutputDir = new File(
                this.getClass().getClassLoader().getResource("migration/info/fedora2/expected").getFile());
        TestUtils.assertDirsAreEqual(expectedOutputDir.toPath(), exportOutputDir.toPath());
    }

    /**
     * Subclass of Fedora2InfoStreamingFedoraObjectHandler that overrides of
     * methods needed to facilitate testing.
     *
     */
    public static class TestFedora2InfoStreamingFedoraObjectHandler extends Fedora2InfoStreamingFedoraObjectHandler {
        private Path testDataBasePath;

        /**
         * The additional "testDataBasePath" parameter points to the test
         * resources directory containing the "objects" directory tree.
         *
         * @param jsonObjectWriter
         *          the Writer used for the JSON output
         * @param testDataBasePath
         *          the Path to the test resources directory containing the
         *          "objects" directory tree used for input
         */
        public TestFedora2InfoStreamingFedoraObjectHandler(final Writer jsonObjectWriter, final Path testDataBasePath) {
            super(jsonObjectWriter);
            this.testDataBasePath = testDataBasePath;
        }


        /**
         * Overridden to replace the "ObjectInfo" parameter with an ObjectInfo
         * that has a relative filepath. This ensures that the generated JSON
         * file will have a consistent location for the objects, which is needed
         * to properly compare the output files.
         */
        @Override
        public void beginObject(final ObjectInfo object) {
            final File actualFile = object.getFile();
            final Path filePath = actualFile.toPath();
            final Path relativePath = testDataBasePath.relativize(filePath);

            final ObjectInfo modifiedObjectInfo = new DefaultObjectInfo(
                    relativePath.toFile(),
                    object.getPid(),
                    object.getFedoraURI());
            super.beginObject(modifiedObjectInfo);
        }
    }
}