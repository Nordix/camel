/*
 * Licensed to the Apache Software Foundation (ASF) under one or more
 * contributor license agreements.  See the NOTICE file distributed with
 * this work for additional information regarding copyright ownership.
 * The ASF licenses this file to You under the Apache License, Version 2.0
 * (the "License"); you may not use this file except in compliance with
 * the License.  You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.camel.component.xmlsecurity;

import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;

import javax.xml.parsers.DocumentBuilderFactory;

import org.w3c.dom.Document;
import org.w3c.dom.bootstrap.DOMImplementationRegistry;
import org.w3c.dom.ls.DOMImplementationLS;
import org.w3c.dom.ls.LSOutput;
import org.w3c.dom.ls.LSSerializer;

/**
 * Tells whether the JDK's DOM serializer writes a line break after the XML declaration.
 * <p>
 * XmlSignatureHelper serializes with the same LSSerializer, so the expected message bodies in the tests have to
 * follow it. This differs between JDK 8 builds (and vendors), so probe it instead of guessing from the Java version.
 */
final class XmlDeclarationSupport {

    private XmlDeclarationSupport() {
    }

    static boolean newLineAfterXmlDeclaration() {
        try {
            DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
            Document doc = dbf.newDocumentBuilder().newDocument();
            doc.appendChild(doc.createElement("root"));

            DOMImplementationLS ls
                    = (DOMImplementationLS) DOMImplementationRegistry.newInstance().getDOMImplementation("LS");
            LSOutput out = ls.createLSOutput();
            out.setEncoding("UTF-8");
            ByteArrayOutputStream os = new ByteArrayOutputStream();
            out.setByteStream(os);
            LSSerializer serializer = ls.createLSSerializer();
            serializer.getDomConfig().setParameter("xml-declaration", true);
            serializer.write(doc, out);

            String xml = new String(os.toByteArray(), StandardCharsets.UTF_8);
            return xml.contains("?>\n") || xml.contains("?>\r\n");
        } catch (Exception e) {
            throw new IllegalStateException("Cannot probe the DOM serializer", e);
        }
    }
}
