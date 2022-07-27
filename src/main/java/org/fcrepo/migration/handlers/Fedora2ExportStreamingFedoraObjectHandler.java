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
package org.fcrepo.migration.handlers;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.FileWriter;
import java.io.InputStream;
import java.io.OutputStream;
import java.io.Writer;
import java.net.MalformedURLException;
import java.net.URL;
import java.util.AbstractMap;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

import javax.xml.stream.XMLInputFactory;
import javax.xml.stream.XMLStreamConstants;
import javax.xml.stream.XMLStreamReader;

import com.fasterxml.jackson.core.JsonFactory;
import com.fasterxml.jackson.core.JsonGenerator;
import com.fasterxml.jackson.core.JsonGenerator.Feature;

import org.fcrepo.migration.ContentDigest;
import org.fcrepo.migration.DatastreamInfo;
import org.fcrepo.migration.DatastreamVersion;
import org.fcrepo.migration.ObjectInfo;
import org.fcrepo.migration.ObjectProperties;
import org.fcrepo.migration.ObjectProperty;
import org.fcrepo.migration.StreamingFedoraObjectHandler;
import org.fcrepo.migration.handlers.ocfl.ArchiveGroupHandler;

/**
 * A simple StreamingFedoraObjectHandler implementation that gathers
 * information about Fedora 2 FOXML objects.
 * @author wallberg@umd.edu
 */
public class Fedora2ExportStreamingFedoraObjectHandler implements StreamingFedoraObjectHandler {

    private long start;

    final static String MetsNS = "http://www.loc.gov/METS/";
    final static String XlinkNS = "http://www.w3.org/1999/xlink";
    final static String DoinfoNS = "http://www.itd.umd.edu/fedora/doInfo";
    final static String AminfoNS = "http://www.itd.umd.edu/fedora/amInfo";

    final static Map<String, String> propertiesMap = Map.ofEntries(
        new AbstractMap.SimpleEntry<String, String>("http://purl.org/dc/terms/type", "type"),
        new AbstractMap.SimpleEntry<String, String>("info:fedora/fedora-system:def/model#state" , "state"),
        new AbstractMap.SimpleEntry<String, String>("info:fedora/fedora-system:def/model#label" , "label"),
        new AbstractMap.SimpleEntry<String, String>("info:fedora/fedora-system:def/model#createdDate" , "createdDate"),
        new AbstractMap.SimpleEntry<String, String>("info:fedora/fedora-system:def/view#lastModifiedDate" ,
                                                    "lastModifiedDate"),
        new AbstractMap.SimpleEntry<String, String>("info:fedora/fedora-system:def/model#contentModel" , "contentModel")
    );

    private File objectDir;

    private Set<String> datastreamsInclude;

    final static Set<String> includeDsId = new HashSet<>(
        Arrays.asList("doInfo", "amInfo", "umdm", "umam", "rels-mets", "image", "ocr", "hocr", "tei"));

    JsonFactory factory = null;

    public Fedora2ExportStreamingFedoraObjectHandler(final Set<String> datastreamsInclude) {
        factory = new JsonFactory();
        factory.configure(Feature.AUTO_CLOSE_TARGET, true);
        this.datastreamsInclude = datastreamsInclude;
    }

    /**
     * Set the object directory to stash the files.
     * @param objectDir
     */
    public void setObjectDir(final File objectDir) {
        this.objectDir = objectDir;
    }

    @Override
    public void beginObject(final ObjectInfo object) {
        start = System.currentTimeMillis();

        if (!objectDir.exists()) {
            objectDir.mkdirs();
            System.out.println("Created directory " + objectDir.toPath());
        }

        // Make a copy of the FOXML file itself
        if (this.datastreamsInclude == null || datastreamsInclude.contains("foxml.xml")) {
            InputStream is = null;
            OutputStream os = null;
            final File foxml = new File(objectDir, "foxml.xml");
            try {
                is = new FileInputStream(object.getFile());
                os = new FileOutputStream(foxml);

                final byte[] buffer = new byte[8 * 1024];
                int bytesRead;
                while ((bytesRead = is.read(buffer)) != -1) {
                    os.write(buffer, 0, bytesRead);
                }
            } catch (Exception e) {
                System.out.println("IO exception writing " + foxml.toPath() + " in beginObject: " + e);
            } finally {
                if (os != null) {
                    try {
                        os.close();
                    } catch (Exception e) {
                        System.out.println("IO exception writing " + foxml.toPath() + " in beginObject: " + e);
                    }
                }
            }
        }
    }

    @Override
    public void processObjectProperties(final ObjectProperties properties) {

        // Write all Object Properties out to properties.json
        if (this.datastreamsInclude == null || datastreamsInclude.contains("properties.json")) {

            JsonGenerator json = null;
            try {
                final Writer jsonWriter = new BufferedWriter(new FileWriter(new File(objectDir, "properties.json")));
                json = factory.createGenerator(jsonWriter);

                json.writeStartObject();

                // Iterate over each property
                for (final ObjectProperty p : properties.listProperties()) {
                    String name = p.getName();
                    if (propertiesMap.containsKey(name)) {
                        name = propertiesMap.get(name);
                    }

                    json.writeFieldName(name);
                    json.writeString(p.getValue());
                }

                json.writeEndObject();
            } catch (Exception e) {
                System.out.println("json exception in processObjectProperties: " + e);
            } finally {
                if (json != null) {
                    try {
                        json.close();
                    } catch (Exception e) {
                        System.out.println("json exception in processObjectProperties: " + e);
                    }
                }
            }
        }
    }

    @Override
    public void processDatastreamVersion(final DatastreamVersion ds) {


        final DatastreamInfo info = ds.getDatastreamInfo();
        final String id = info.getDatastreamId();

        if (!includeDsId.contains(id)) {
            return;
        }

        // Write all Datastream Properties out to <id>-properties.json
        final String propertiesName = id + "-properties.json";

        if (this.datastreamsInclude == null || datastreamsInclude.contains(propertiesName)) {

            JsonGenerator json = null;
            try {
                final Writer jsonWriter = new BufferedWriter(new FileWriter(new File(objectDir, propertiesName)));
                json = factory.createGenerator(jsonWriter);

                json.writeStartObject();

                json.writeFieldName(id);
                json.writeStartObject();

                json.writeFieldName("version");
                json.writeString(ds.getVersionId());

                json.writeFieldName("label");
                json.writeString(ds.getLabel());

                json.writeFieldName("state");
                json.writeString(info.getState());

                json.writeFieldName("controlGroup");
                json.writeString(info.getControlGroup());

                json.writeFieldName("created");
                json.writeString(ds.getCreated());

                json.writeFieldName("formatUri");
                json.writeString(ds.getFormatUri());

                json.writeFieldName("mimeType");
                json.writeString(ds.getMimeType());

                json.writeFieldName("size");
                json.writeNumber(ds.getSize());

                json.writeFieldName("location");
                json.writeString(ds.getContentLocation());

                final ContentDigest digest = ds.getContentDigest();
                if (digest != null) {
                    json.writeFieldName("digest");
                    json.writeStartObject();
                    json.writeFieldName("type");
                    json.writeString(digest.getType());
                    json.writeFieldName("value");
                    json.writeString(digest.getDigest());
                    json.writeEndObject();
                }

                json.writeEndObject();
            } catch (Exception e) {
                System.out.println("json exception in processDatastreamVersion: " + e);
            } finally {
                if (json != null) {
                    try {
                        json.close();
                    } catch (Exception e) {
                        System.out.println("json exception in processDatastreamVersion: " + e);
                    }
                }
            }
        }

        // Don't export the datastream if it is pointing to fcrepo.lib.umd.edu
        try {
            final URL url = new URL(ds.getContentLocation());
            if (url.getHost().equals("fcrepo.lib.umd.edu")) {
                // skip
                return;
            }
        } catch (MalformedURLException e) {
            // ignore, if it is not a url then we are not interested
        }

        // Get the Datastream export file name
        String dsName = id;
        final String extension = ArchiveGroupHandler.getExtension(ds.getMimeType());
        if (dsName == null || dsName.equals("")) {
            dsName = ".dat";
        }
        dsName += extension;

        if (this.datastreamsInclude == null || datastreamsInclude.contains(dsName)) {

            final File dsFile = new File(objectDir, dsName);

            // Write the datastream
            InputStream is = null;
            OutputStream os = null;
            try {
                is = ds.getContent();
                os = new FileOutputStream(dsFile);

                final byte[] buffer = new byte[8 * 1024];
                int bytesRead;
                while ((bytesRead = is.read(buffer)) != -1) {
                    os.write(buffer, 0, bytesRead);
                }
            } catch (Exception e) {
                System.out.println("IO exception writing " + dsFile.toPath() + " in processDatastreamVersion: " + e);
            } finally {
                if (os != null) {
                    try {
                        os.close();
                    } catch (Exception e) {
                        System.out.println("IO exception writing " + dsFile.toPath() +
                                        " in processDatastreamVersion: " + e);
                    }
                }
            }
        }
    }

    /**
     * Extract METS object relationships from the rels-mets datastream.
     * @param ds
     */

    public void processRelsMets(final DatastreamVersion ds) {

        try {

            final XMLInputFactory factory = XMLInputFactory.newInstance();
            final XMLStreamReader reader = factory.createXMLStreamReader(ds.getContent());

            String fileID = "";
            boolean isInRels = false;
            String relationship = "";

            final Map<String, String> map = new HashMap<String, String>();
            final Map<String, Set<String>> mapRelationships = new HashMap<>();

            while (reader.hasNext()) {
                final int event = reader.next();

                if (event == XMLStreamConstants.START_ELEMENT) {
                    final String name = reader.getLocalName();
                    final String ns = reader.getNamespaceURI();

                    // final String attr = parser.getAttributeValue()

                    if (ns.equals(MetsNS) && name.equals("file")) {
                        fileID = reader.getAttributeValue(null, "ID");

                    } else if (ns.equals(MetsNS) && name.equals("FLocat")) {
                        final String pid = reader.getAttributeValue(XlinkNS, "href");
                        map.put(fileID, pid);

                    } else if (ns.equals(MetsNS) && name.equals("div")) {
                        final String divID = reader.getAttributeValue(null, "ID");
                        if (divID != null) {
                            if (divID.equals("rels")) {
                                isInRels = true;
                                } else if (isInRels) {
                                relationship = divID;
                                }
                        }

                    } else if (ns.equals(MetsNS) && name.equals("fptr") && isInRels) {
                        final String fileIDRels = reader.getAttributeValue(null, "FILEID");
                        if (fileIDRels != null) {
                            final String pidRels = map.get(fileIDRels);
                            if (pidRels != null) {
                                Set<String> values = mapRelationships.get(relationship);
                                if (values == null) {
                                    values = new HashSet<>();
                                    mapRelationships.put(relationship, values);
                                }
                                values.add(pidRels);
                            }
                        }

                    }

                } else if (event == XMLStreamConstants.END_ELEMENT) {
                    final String name = reader.getLocalName();
                    final String ns = reader.getNamespaceURI();

                    if (ns.equals(MetsNS) && name.equals("structMap") && isInRels) {
                        isInRels = false;
                    }
                }
            }

            // // We've collected all of the relationships, now write them out
            // json.writeFieldName("rels");
            // json.writeStartObject();
            // for (Map.Entry<String,Set<String>> entry : mapRelationships.entrySet()) {
            //     json.writeArrayFieldStart(entry.getKey());
            //     for (String pidRels: entry.getValue()) {
            //         json.writeString(pidRels);
            //     }
            //     json.writeEndArray();
            // };
            // json.writeEndObject();
        } catch (Exception e) {
            System.out.println("Exception processing rels-mets: " + e);
        }
    }

    /**
     * Extract type and status information from doInfo and amInfo datastreams.
     * @param ds
     */
    public void processDoAmInfo(final DatastreamVersion ds) {

        try {

            final XMLInputFactory factory = XMLInputFactory.newInstance();
            final XMLStreamReader reader = factory.createXMLStreamReader(ds.getContent());

            String name = "";
            String ns = "";

            while (reader.hasNext()) {
                final int event = reader.next();

                if (event == XMLStreamConstants.START_ELEMENT) {
                    name = reader.getLocalName();
                    ns = reader.getNamespaceURI();

                } else if (event == XMLStreamConstants.END_ELEMENT) {
                    name = "";
                    ns = "";

                } else if (event == XMLStreamConstants.CHARACTERS) {
                    if ((ns.equals(DoinfoNS) || ns.equals(AminfoNS)) &&
                        (name.equals("type") || name.equals("status"))) {

                        // json.writeFieldName(name);
                        // json.writeString(reader.getText());

                    }
                }
            }
        } catch (Exception e) {
            System.out.println("Exception processing doInfo/amInfo: " + e);
        }
    }

    /**
     * Extract type and status information from doInfo and amInfo datastreams.
     * @param ds
     */
    public void processUMDM(final DatastreamVersion ds) {

        try {

            final XMLInputFactory factory = XMLInputFactory.newInstance();
            final XMLStreamReader reader = factory.createXMLStreamReader(ds.getContent());

            String name = "";
            String ns = "";
            String title_type = "";
            final StringBuilder title = new StringBuilder();

            while (reader.hasNext()) {
                final int event = reader.next();

                if (event == XMLStreamConstants.START_ELEMENT) {
                    name = reader.getLocalName();
                    ns = reader.getNamespaceURI();

                    if (name.equals("title")) {
                        title_type = reader.getAttributeValue(null, "type");
                    }

                } else if (event == XMLStreamConstants.END_ELEMENT) {
                    name = "";
                    ns = "";
                    title_type = "";

                } else if (event == XMLStreamConstants.CHARACTERS) {
                    if (title_type != null && title_type.equals("main")) {

                        if (title.length() > 0) {
                            title.append(" / ");
                        }
                        title.append(reader.getText());
                    }
                }
            }

            // // Add the title
            // json.writeFieldName("umdm_title");
            // json.writeString(title.toString());

        } catch (Exception e) {
            System.out.println("Exception processing doInfo/amInfo: " + e);
        }
    }

    @Override
    public void processDisseminator() {
        // Ignore
    }

    @Override
    public void completeObject(final ObjectInfo object) {
        // try {
        //     // Finish the datastreams
        //     json.writeEndObject();

        //     // Finish the FOXML object
        //     json.writeEndObject();
        //     json.flush();
        //     json.close();

        //     // Write the end of line for this record
        //     jsonObjectWriter.write("\n");
        // }
        // catch (Exception e) {
        //     System.out.println("json exception in completeObject: " + e);
        // }
        System.out.println(object.getPid() + " parsed in " + (System.currentTimeMillis() - start) + "ms.");
    }

    @Override
    public void abortObject(final ObjectInfo object) {
        // try {
        //     json.writeEndObject();
        //     json.close();

        //     // Write the end of line for this record
        //     jsonObjectWriter.write("\n");
        // }
        // catch (Exception e) {
        //     System.out.println("json exception in abortObject: " + e);
        // }
        System.out.println(object.getPid() + " failed to parse in " + (System.currentTimeMillis() - start) + "ms.");
    }
}
