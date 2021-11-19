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

import java.io.Writer;
import java.util.AbstractMap;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedList;
import java.util.Map;
import java.util.Set;

import javax.xml.stream.XMLInputFactory;
import javax.xml.stream.XMLStreamConstants;
import javax.xml.stream.XMLStreamReader;

import com.fasterxml.jackson.core.JsonFactory;
import com.fasterxml.jackson.core.JsonGenerator;
import com.fasterxml.jackson.core.JsonGenerator.Feature;

import org.fcrepo.migration.DatastreamInfo;
import org.fcrepo.migration.DatastreamVersion;
import org.fcrepo.migration.ObjectInfo;
import org.fcrepo.migration.ObjectProperties;
import org.fcrepo.migration.ObjectProperty;
import org.fcrepo.migration.StreamingFedoraObjectHandler;

/**
 * A simple StreamingFedoraObjectHandler implementation that gathers
 * information about Fedora 2 FOXML objects.
 * @author wallberg@umd.edu
 */
public class Fedora2InfoStreamingFedoraObjectHandler implements StreamingFedoraObjectHandler {

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

    Writer jsonObjectWriter = null;
    JsonFactory factory = null;
    JsonGenerator json = null;

    public Fedora2InfoStreamingFedoraObjectHandler(final Writer jsonObjectWriter) {
        this.jsonObjectWriter = jsonObjectWriter;
        factory = new JsonFactory();
        factory.configure(Feature.AUTO_CLOSE_TARGET, false);
    }

    @Override
    public void beginObject(final ObjectInfo object) {
        start = System.currentTimeMillis();

        try {
            json = factory.createGenerator(this.jsonObjectWriter);

            // write one object per line, no pretty print
            json.writeStartObject();
            json.writeFieldName("pid");
            json.writeString(object.getPid());
            json.writeFieldName("foxml");
            json.writeString(object.getFile().toString());
        } catch (Exception e) {
            System.out.println("json exception in beginObject: " + e);
        }
    }

    @Override
    public void processObjectProperties(final ObjectProperties properties) {
        try {
            // Add all FOXML properties
            for (final ObjectProperty p : properties.listProperties()) {
                String name = p.getName();
                if (propertiesMap.containsKey(name)) {
                    name = propertiesMap.get(name);
                }

                json.writeFieldName(name);
                json.writeString(p.getValue());
            }

            // Start the list of datastreams
            json.writeFieldName("ds");
            json.writeStartObject();
        } catch (Exception e) {
            System.out.println("json exception in processObjectProperties: " + e);
        }

    }

    @Override
    public void processDatastreamVersion(final DatastreamVersion ds) {

        try {

            final DatastreamInfo info = ds.getDatastreamInfo();

            final String id = info.getDatastreamId();

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

            json.writeFieldName("mimeType");
            json.writeString(ds.getMimeType());

            json.writeFieldName("size");
            json.writeNumber(ds.getSize());

            json.writeFieldName("location");
            json.writeString(ds.getContentLocation());

            if (id.equals("rels-mets")) {
                processRelsMets(ds);

            } else if (id.equals("doInfo") || id.equals("amInfo")) {
                processDoAmInfo(ds);

            } else if (id.equals("umdm")) {
                processUMDM(ds);
            }

            json.writeEndObject();
        } catch (Exception e) {
            System.out.println("Exception processing datastream: " + e);
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

            // We've collected all of the relationships, now write them out
            json.writeFieldName("rels");
            json.writeStartObject();
            for (Map.Entry<String,Set<String>> entry : mapRelationships.entrySet()) {
                json.writeArrayFieldStart(entry.getKey());
                for (String pidRels: entry.getValue()) {
                    json.writeString(pidRels);
                }
                json.writeEndArray();
            };
            json.writeEndObject();
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

                        json.writeFieldName(name);
                        json.writeString(reader.getText());

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

            final UmdmTitleParser titleParser = new UmdmTitleParser();

            while (reader.hasNext()) {
                reader.next();
                titleParser.parse(reader);
            }

            // Add the title
            json.writeFieldName("umdm_title");
            json.writeString(titleParser.getTitle());

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
        try {
            // Finish the datastreams
            json.writeEndObject();

            // Finish the FOXML object
            json.writeEndObject();
            json.flush();
            json.close();

            // Write the end of line for this record
            jsonObjectWriter.write("\n");
        } catch (Exception e) {
            System.out.println("json exception in completeObject: " + e);
        }
        System.out.println(object.getPid() + " parsed in " + (System.currentTimeMillis() - start) + "ms.");
    }

    @Override
    public void abortObject(final ObjectInfo object) {
        try {
            json.writeEndObject();
            json.close();

            // Write the end of line for this record
            jsonObjectWriter.write("\n");
        } catch (Exception e) {
            System.out.println("json exception in abortObject: " + e);
        }
        System.out.println(object.getPid() + " failed to parse in " + (System.currentTimeMillis() - start) + "ms.");
    }

    private static class UmdmTitleParser {
        private LinkedList<String> xmlPathStack = new LinkedList<>();
        private StringBuilder title = new StringBuilder();
        private String title_type = "";

        public void parse(final XMLStreamReader reader) {
            final int event = reader.getEventType();
            if (event == XMLStreamConstants.START_ELEMENT) {
                final String name = reader.getLocalName();
                xmlPathStack.push(name);

                if (name.equals("title")) {
                    title_type = reader.getAttributeValue(null, "type");
                }

            } else if (event == XMLStreamConstants.END_ELEMENT) {
                title_type = "";
                xmlPathStack.pop();

            } else if (event == XMLStreamConstants.CHARACTERS) {
                String parentTag = null;
                if (xmlPathStack.size() > 1) {
                    parentTag = xmlPathStack.get(1);
                }

                if ("descMeta".equals(parentTag) && title_type != null && title_type.equals("main")) {

                    if (title.length() > 0) {
                        title.append(" / ");
                    }
                    title.append(reader.getText());
                }
            }
        }

        public String getTitle() {
            return title.toString();
        }
    }
}
