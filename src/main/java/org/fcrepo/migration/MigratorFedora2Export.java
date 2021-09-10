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

import org.apache.commons.csv.CSVPrinter;
import org.fcrepo.migration.foxml.FoxmlInputStreamFedoraObjectProcessor;
import org.fcrepo.migration.foxml.HttpClientURLFetcher;
import org.fcrepo.migration.foxml.InternalIDResolver;
import org.fcrepo.migration.foxml.URLFetcher;
import org.fcrepo.migration.handlers.Fedora2ExportStreamingFedoraObjectHandler;
import org.fcrepo.migration.pidlist.PidListManager;
import org.slf4j.Logger;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.context.support.FileSystemXmlApplicationContext;
import org.springframework.core.io.ClassPathResource;

import javax.xml.stream.XMLStreamException;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.core.JsonFactory;
import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.Reader;
import java.util.List;

import static org.slf4j.LoggerFactory.getLogger;

/**
 * A class that performs an export of Fedora 2 objects.
 */
public class MigratorFedora2Export {

    private static final Logger LOGGER = getLogger(MigratorFedora2Export.class);

    private BufferedReader jsonReader;

    private Fedora2ExportStreamingFedoraObjectHandler handler;

    private InternalIDResolver resolver;

    private String localFedoraServer;

    private URLFetcher fetcher;

    private CSVPrinter csvWriter;

    private File targetDir;

    /**
     * Constructor.
     */
    public MigratorFedora2Export(final File targetDir, final CSVPrinter csvWriter, Fedora2ExportStreamingFedoraObjectHandler handler, BufferedReader jsonReader, final InternalIDResolver resolver, final String localFedoraServer) {
        this.targetDir = targetDir;
        this.csvWriter = csvWriter;
        this.handler = handler;
        this.jsonReader = jsonReader;
        this.resolver = resolver;
        this.fetcher = new HttpClientURLFetcher();
        this.localFedoraServer = localFedoraServer;
    }

    /**
     * the run method for migrator.
     *
     * @throws XMLStreamException xml stream exception
     */
    public void run() throws XMLStreamException {

        final ObjectMapper mapper = new ObjectMapper();
        FoxmlInputStreamFedoraObjectProcessor processor = null;

        try {
            // Read one JSON document for each UMDM object
            String line;
            while ((line = jsonReader.readLine()) != null) {

                UMDM umdm = mapper.readValue(line, UMDM.class);

                // Process the UMDM
                LOGGER.info("Processing UMDM=" + umdm.pid + " @ " + umdm.foxml);

                final File umdmFile = new File(umdm.foxml);
                processor = new FoxmlInputStreamFedoraObjectProcessor(umdmFile,
                    new FileInputStream(umdmFile), fetcher, resolver, localFedoraServer);

                final String umdmDirName = umdm.pid.replace(":", "_");
                final File umdmDir = new File(targetDir, umdmDirName);
                handler.setObjectDir(umdmDir);

                csvWriter.printRecord(umdm.pid, "", umdmDirName, umdm.title, umdm.handle);
                csvWriter.flush();

                processor.processObject(handler);

                if (umdm.hasPart != null) {
                    for (UMAM umam: umdm.hasPart) {
                        // Process the UMAM
                        LOGGER.info("Processing UMDM=" + umdm.pid + ", UMAM=" + umam.pid + " @ " + umam.foxml);

                        final File umamFile = new File(umam.foxml);
                        processor = new FoxmlInputStreamFedoraObjectProcessor(umamFile,
                            new FileInputStream(umamFile), fetcher, resolver, localFedoraServer);

                        final String umamDirName = umam.pid.replace(":", "_");
                        final File umamDir = new File(umdmDir, umamDirName);
                        handler.setObjectDir(umamDir);

                        csvWriter.printRecord(umdm.pid, umam.pid, umdmDirName + "/" + umamDirName, "");
                        csvWriter.flush();

                        processor.processObject(handler);

                    }
                }
            }

        } catch (Exception ex) {
            final String message = "Error in MigratorFedora2Export.run()";
            LOGGER.error(message, ex);
            throw new RuntimeException(message, ex);
        }
    }

    /**
     * POJO for mapping input JSON object: UMDM.
     */
    @JsonIgnoreProperties({"type", "state", "label", "createdDate", "lastModifiedDate","contentModel","ds"})
    public static class UMDM {

        public String pid;
        public String foxml;
        public List<UMAM> hasPart;
        public String title;
        public String handle;
    }

    /**
     * POJO for mapping input JSON object: UMAM.
     */
    @JsonIgnoreProperties({"type", "state", "label", "createdDate", "lastModifiedDate","contentModel","ds","title"})
    public static class UMAM {

        public String pid;
        public String foxml;
    }

}
