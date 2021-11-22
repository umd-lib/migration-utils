package org.fcrepo.migration.utils;

import java.io.IOException;
import java.nio.file.FileVisitResult;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.SimpleFileVisitor;
import java.nio.file.attribute.BasicFileAttributes;
import java.util.Arrays;

import junit.framework.AssertionFailedError;

/**
 * Utility methods for tests.
 * @author dsteelma
 */
public class TestUtils {
    private TestUtils() {
    }

    /**
     * Assertion that compares all the files in a file hierarchy.
     *
     * Largely derived from https://stackoverflow.com/a/39584230
     *
     * @param expected
     *             the Path containing the expected directory hierarchy
     * @param actual
     *             the Path containing the actual directory hierarchy generated
     *             by the test.
     * @throws IOException
     *             if an I/O exception occurs.
     */
    public static void assertDirsAreEqual(final Path expected, final Path actual) throws IOException {
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
