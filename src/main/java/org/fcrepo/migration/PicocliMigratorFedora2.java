/*
 * Copyright 2015 DuraSpace, Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.fcrepo.migration;

import ch.qos.logback.classic.Level;
import ch.qos.logback.classic.LoggerContext;

import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVPrinter;
import org.fcrepo.migration.foxml.InternalIDResolver;
import org.fcrepo.migration.foxml.LegacyFSIDResolver;
import org.fcrepo.migration.foxml.NativeFoxmlDirectoryObjectSource;
import org.fcrepo.migration.handlers.Fedora2ExportStreamingFedoraObjectHandler;
import org.fcrepo.migration.handlers.Fedora2InfoStreamingFedoraObjectHandler;
import org.fcrepo.migration.pidlist.PidListManager;
import org.fcrepo.migration.pidlist.ResumePidListManager;
import org.fcrepo.migration.pidlist.UserProvidedPidListManager;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import picocli.CommandLine;
import picocli.CommandLine.Command;
import picocli.CommandLine.Option;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.File;
import java.io.FileReader;
import java.io.FileWriter;
import java.io.IOException;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.Callable;

import com.fasterxml.jackson.core.JsonFactory;

import static edu.wisc.library.ocfl.api.util.Enforce.expressionTrue;
import static edu.wisc.library.ocfl.api.util.Enforce.notNull;
import static org.slf4j.LoggerFactory.getLogger;
import static picocli.CommandLine.Help.Visibility.ALWAYS;


/**
 * This class provides a simple CLI for running and configuring migration-utils
 * - See README.md for usage details
 *
 * @author Remi Malessa
 * @author awoods
 * @since 2019-11-15
 */
@Command(name = "migration-utils", mixinStandardHelpOptions = true, sortOptions = false,
        version = "Migration Utils - 4.4.1.b")
public class PicocliMigratorFedora2 implements Callable<Integer> {

    private static final Logger LOGGER = getLogger(PicocliMigratorFedora2.class);

    private enum F3SourceTypes {
        AKUBRA, LEGACY, EXPORTED;

        static F3SourceTypes toType(final String v) {
            return valueOf(v.toUpperCase());
        }
    }

    private enum F3Actions {
        INFO, EXPORT;

        static F3Actions toType(final String v) {
            return valueOf(v.toUpperCase());
        }
    }

    // @Option(names = {"--source-type", "-t"}, required = true, order = 1,
    //         description = "Fedora 3 source type. Choices: akubra | legacy | exported")
    private final F3SourceTypes f3SourceType = F3SourceTypes.LEGACY;

    @Option(names = {"--action", "-a"}, defaultValue="info", showDefaultValue = ALWAYS, order = 1,
            description="Fedora 2 Action. Choices: info | export")
    private final F3Actions f3Action = F3Actions.INFO;

    @Option(names = {"--datastreams-dir", "-d"}, order = 2,
            description = "Directory containing Fedora 3 datastreams (used with --source-type 'akubra' or 'legacy')")
    private File f3DatastreamsDir;

    @Option(names = {"--objects-dir", "-o"}, order = 3,
            description = "Directory containing Fedora 3 objects (used with --source-type 'akubra' or 'legacy')")
    private File f3ObjectsDir;

    @Option(names = {"--exported-dir", "-e"}, order = 4,
            description = "Directory containing Fedora 3 export (used with --source-type 'exported')")
    private File f3ExportedDir;

    @Option(names = {"--target-dir", "-t"}, required = true, order = 5,
            description = "Directory where supporting state will be written")
    private File targetDir;

    @Option(names = {"--delete-inactive", "-I"}, defaultValue = "false", showDefaultValue = ALWAYS, order = 18,
            description = "Migrate objects and datastreams in the Inactive state as deleted. Default: false.")
    private boolean deleteInactive;

    @Option(names = {"--limit", "-l"}, defaultValue = "-1", order = 21,
            description = "Limit number of objects to be processed.\n  Default: no limit")
    private int objectLimit;

    @Option(names = {"--resume", "-r"}, defaultValue = "false", showDefaultValue = ALWAYS, order = 22,
            description = "Resume from last successfully migrated Fedora 3 object")
    private boolean resume;

    @Option(names = {"--continue-on-error", "-c"}, defaultValue = "false", showDefaultValue = ALWAYS, order = 23,
            description = "Continue to next PID if an error occurs (instead of exiting). Disabled by default.")
    private boolean continueOnError;

    @Option(names = {"--pid-file", "-p"}, order = 24,
            description = "PID file listing which Fedora 3 objects to migrate")
    private File pidFile;

    @Option(names = {"--index-dir", "-i"}, order = 25,
            description = "Directory where cached index of datastreams (will reuse index if already exists)")
    private File indexDir;

    @Option(names = {"--extensions", "-x"}, defaultValue = "false", showDefaultValue = ALWAYS, order = 26,
            description = "Add file extensions to migrated datastreams based on mimetype recorded in FOXML")
    private boolean addExtensions;

    @Option(names = {"--f3hostname", "-f"}, defaultValue = "fedora.info", showDefaultValue = ALWAYS, order = 27,
            description = "Hostname of Fedora 3, used for replacing placeholder in 'E' and 'R' datastream URLs")
    private String f3hostname;

    @Option(names = {"--username", "-u"}, defaultValue = "fedoraAdmin", showDefaultValue = ALWAYS, order = 28,
            description = "The username to associate with all of the migrated resources.")
    private String user;

    @Option(names = {"--user-uri", "-U"}, defaultValue = "info:fedora/fedoraAdmin", showDefaultValue = ALWAYS,
            order = 29, description = "The username to associate with all of the migrated resources.")
    private String userUri;

    @Option(names = {"--debug"}, order = 30, description = "Enables debug logging")
    private boolean debug;

    @Option(names = {"--filter-json"}, order = 30, description = "Input file required for the --action=export option; specifies the UMDM and UMAM to export; formatted as output from scripts/filter.py")
    private File filterJson;

    /**
     * @param args Command line arguments
     */
    public static void main(final String[] args) {
        final PicocliMigratorFedora2 migrator = new PicocliMigratorFedora2();
        final CommandLine cmd = new CommandLine(migrator);
        cmd.registerConverter(F3SourceTypes.class, F3SourceTypes::toType);
        cmd.registerConverter(F3Actions.class, F3Actions::toType);
        cmd.setExecutionExceptionHandler(new PicoliMigrationFedora2ExceptionHandler(migrator));

        cmd.execute(args);
    }

    private static class PicoliMigrationFedora2ExceptionHandler implements CommandLine.IExecutionExceptionHandler {

        private final PicocliMigratorFedora2 migrator;

        PicoliMigrationFedora2ExceptionHandler(final PicocliMigratorFedora2 migrator) {
            this.migrator = migrator;
        }

        @Override
        public int handleExecutionException(
                final Exception ex,
                final CommandLine commandLine,
                final CommandLine.ParseResult parseResult) {
            commandLine.getErr().println(ex.getMessage());
            if (migrator.debug) {
                ex.printStackTrace(commandLine.getErr());
            }
            commandLine.usage(commandLine.getErr());
            return commandLine.getCommandSpec().exitCodeOnExecutionException();
        }
    }

    private static void setDebugLogLevel() {
        final LoggerContext loggerContext = (LoggerContext) LoggerFactory.getILoggerFactory();
        final ch.qos.logback.classic.Logger logger = loggerContext.getLogger("org.fcrepo.migration");
        logger.setLevel(Level.toLevel("DEBUG"));
    }

    @Override
    public Integer call() throws Exception {

        // Set debug log level if requested
        if (debug) {
            setDebugLogLevel();
        }

        // Pre-processing directory verification
        notNull(targetDir, "targetDir must be provided!");
        if (!targetDir.exists()) {
            targetDir.mkdirs();
        }

        // Create PID list dir
        final File pidDir = new File(targetDir, "pid");
        if (!pidDir.exists()) {
            pidDir.mkdirs();
        }

        // Which F3 source are we using? - verify associated options
        final ObjectSource objectSource;
        final InternalIDResolver idResolver;
        switch (f3SourceType) {
            case LEGACY:
                notNull(f3DatastreamsDir, "f3DatastreamsDir must be used with 'akubra' or 'legacy' source!");
                notNull(f3ObjectsDir, "f3ObjectsDir must be used with 'akubra' or 'legacy' source!");
                expressionTrue(f3ObjectsDir.exists(), f3ObjectsDir, "f3ObjectsDir must exist! " +
                        f3ObjectsDir.getAbsolutePath());

                idResolver = new LegacyFSIDResolver(indexDir, f3DatastreamsDir);
                objectSource = new NativeFoxmlDirectoryObjectSource(f3ObjectsDir, idResolver, f3hostname);
                break;
            default:
                throw new RuntimeException("Should never happen");
        }

        // Action: INFO or EXPORT
        switch(f3Action) {

            case INFO:
                StreamingFedoraObjectHandler objectHandler = null;
                BufferedWriter jsonWriter = null;

                try {
                    jsonWriter = new BufferedWriter(new FileWriter(new File(targetDir, "info.json")));
                    objectHandler = new Fedora2InfoStreamingFedoraObjectHandler(jsonWriter);
                } catch (IOException e) {
                    // Should not happen based on previous check
                    throw new RuntimeException(e);
                }

                // PID-list-managers
                // - Resume PID manager: the second arg is "acceptAll". If resuming, we do not "acceptAll")
                final ResumePidListManager resumeManager = new ResumePidListManager(pidDir, !resume);

                // - PID-list manager
                final UserProvidedPidListManager pidListManager = new UserProvidedPidListManager(pidFile);

                final List<PidListManager> pidListManagerList = Arrays.asList(pidListManager, resumeManager);

                final MigratorFedora2Info infoMigrator = new MigratorFedora2Info();
                infoMigrator.setLimit(objectLimit);
                infoMigrator.setSource(objectSource);
                infoMigrator.setHandler(objectHandler);
                infoMigrator.setPidListManagers(pidListManagerList);
                infoMigrator.setContinueOnError(continueOnError);

                try {
                    infoMigrator.run();
                } finally {
                    if (jsonWriter != null) {
                        jsonWriter.close();
                    }
                }
                break;

            case EXPORT:
                notNull(filterJson, "filterJson input file must be provided!");

                final BufferedReader jsonReader = new BufferedReader(new FileReader(filterJson));
                final CSVPrinter csvWriter = new CSVPrinter(new FileWriter(new File(targetDir, "export.csv")),
                        CSVFormat.DEFAULT.withHeader("umdm", "umam", "location", "title"));

                final MigratorFedora2Export exportMigrator = new MigratorFedora2Export(
                    targetDir, csvWriter,
                    new Fedora2ExportStreamingFedoraObjectHandler(),
                    jsonReader, idResolver, f3hostname);

                try {
                    exportMigrator.run();
                } finally {
                    if (csvWriter != null) {
                        csvWriter.close();
                    }
                }
                break;

            default:
                throw new RuntimeException("Should never happen");
        }



        return 0;
    }

}
