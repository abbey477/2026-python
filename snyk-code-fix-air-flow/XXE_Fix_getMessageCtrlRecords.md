# XXE Fix — `getMessageCtrlRecords()` in `MQMessageDispatcher.java`

## The 3 Problems

Here's the exact broken sequence in the original code:

```java
// Line 1 — factory created ✅
DocumentBuilderFactory dbFactory = DocumentBuilderFactory.newInstance();

// Inside try:
dBuilder = dbFactory.newDocumentBuilder();            // ❌ PROBLEM 1: builder created BEFORE features are set

dbFactory.setFeature("disallow-doctype-decl"...);     // ❌ too late — builder already made
dbFactory.setFeature("external-general-entities"...); // ❌ too late
dbFactory.setFeature("external-parameter-entities"...); // ❌ too late
dbFactory.setFeature("load-external-dtd"...);         // ❌ too late
dbFactory.setXIncludeAware(false);                    // ❌ too late
dbFactory.setExpandEntityReferences(false);           // ❌ too late

dbFactory.newDocumentBuilder()                        // ❌ PROBLEM 2: throwaway second
         .parse(new InputSource(                      //    unprotected builder+parse
             new StringReader(msgBody)));              //    result is never used!

Document doc = dBuilder.parse(in);                    // ❌ PROBLEM 3: uses the unsafe builder from Problem 1
```

| # | Problem | Impact |
|---|---|---|
| 1 | `newDocumentBuilder()` called **before** `setFeature()` | All security features are ignored — builder is already unsafe |
| 2 | Dead throwaway `dbFactory.newDocumentBuilder().parse(...)` | Second unprotected parse call, result unused |
| 3 | `dBuilder.parse(in)` uses the unsafe builder | Snyk flags this as the vulnerable sink |

---

## The Fixed Method

```java
public RpfEventMessageDefinitionList getMessageCtrlRecords(String msgBody) throws Exception {
    final Logger log = Log4jLoggerBuilder.getLogger(MQMessageDispatcher.class);
    RpfEventMessageDefinitionVo eventMessageRecord = null;
    RpfEventMessageDefinitionList msgRcdList = new RpfEventMessageDefinitionList();
    InputStream in = IOUtils.toInputStream(msgBody);
    String message;

    try {
        // ✅ STEP 1: Create factory
        DocumentBuilderFactory dbFactory = DocumentBuilderFactory.newInstance();

        // ✅ STEP 2: Set ALL security features BEFORE newDocumentBuilder()
        dbFactory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
        dbFactory.setFeature("http://xml.org/sax/features/external-general-entities", false);
        dbFactory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
        dbFactory.setFeature("http://apache.org/xml/features/nonvalidating/load-external-dtd", false);
        dbFactory.setXIncludeAware(false);
        dbFactory.setExpandEntityReferences(false);
        dbFactory.setAttribute(XMLConstants.ACCESS_EXTERNAL_DTD, "");
        dbFactory.setAttribute(XMLConstants.ACCESS_EXTERNAL_SCHEMA, "");

        // ✅ STEP 3: NOW build — inherits all secure settings
        DocumentBuilder dBuilder = dbFactory.newDocumentBuilder();

        // ✅ STEP 4: ONE parse call using the secured builder
        //    Removed the dead throwaway dbFactory.newDocumentBuilder().parse() line
        Document doc = dBuilder.parse(in);

        doc.getDocumentElement().normalize();
        NodeList nList = doc.getElementsByTagName("event");

        if (!doc.hasChildNodes()) return msgRcdList;

        Node timeStampNode = doc.getElementsByTagName("bme:Timestamp").item(0);

        for (int idx = 0; idx < nList.getLength(); idx++) {
            VerboseLogging.log("" + " Event Xml Iteration[" + idx + "]", VerboseLogging.LOG_CRITICAL);
            Node nNode = nList.item(idx);

            if ((nNode != null) && (nNode.getNodeType() == Node.ELEMENT_NODE)) {
                eventMessageRecord = new RpfEventMessageDefinitionVo();
                Element eElement = (Element) nNode;

                Node objTypeNode = eElement.getElementsByTagName("objectType").item(0);
                if (null == objTypeNode) {
                    message = "objectType [NULL] is NOT found in the message.\n ...skipping logging into STGCRDBO.RPF_EVENT_MSG_LOAD_LOG";
                    VerboseLogging.log(message, VerboseLogging.LOG_NORMAL);
                    continue;
                }

                boolean isFoundMatch = false;
                String objectType = objTypeNode.getTextContent().trim();
                isFoundMatch = MessageServiceDefCache.getInstance().containsServiceClass(objectType);

                if (!isFoundMatch) {
                    message = "No message object type match found  [" + objectType
                            + "] in the Asset Control List.\n  ... skipping logging into STGCRDBO.RPF_EVENT_MSG_LOAD_LOG";
                    VerboseLogging.log(message, VerboseLogging.LOG_NORMAL);
                    continue;
                }

                // PUMA PRICING — contributorId and source
                Node assetGroup       = eElement.getElementsByTagName("assetGroup").item(0);
                Node securityType     = eElement.getElementsByTagName("securityType").item(0);
                Node securitySubtype  = eElement.getElementsByTagName("securitySubtype").item(0);
                Node vendor           = eElement.getElementsByTagName("vendor").item(0);
                Node region           = eElement.getElementsByTagName("region").item(0);
                Node category         = eElement.getElementsByTagName("categoryType").item(0);
                Node eventId          = eElement.getElementsByTagName("contributorId").item(0);
                Node source           = eElement.getElementsByTagName("source").item(0);
                Node createdTimeStamp = eElement.getElementsByTagName("createdTimestamp").item(0);

                eventMessageRecord.setServiceName(getNodeText(objTypeNode));
                eventMessageRecord.setAssetGroupCd(getNodeText(assetGroup));
                eventMessageRecord.setSecurityTypCd(getNodeText(securityType));
                eventMessageRecord.setSecuritySubtypCd(getNodeText(securitySubtype));
                eventMessageRecord.setCategoryTypCd(getNodeText(category));
                eventMessageRecord.setVendorCd(getNodeText(vendor));
                eventMessageRecord.setRegion(getNodeText(region));

                if (null != createdTimeStamp) {
                    eventMessageRecord.setCobDate(getCobDate(createdTimeStamp));
                } else if (null != timeStampNode) {
                    eventMessageRecord.setCobDate(getCobDate(timeStampNode));
                } else {
                    log.warn("DEFAULTING(3): Error on Timestamp [ NO VALID TIMESTAMP OBJECT ]");
                    eventMessageRecord.setCobDate(WatcherUtils.getCobDateNOW());
                }

                eventMessageRecord.setEventCd(getNodeText(eventId));
                eventMessageRecord.setSourceCd(getNodeText(source));

                if (!MessageServiceDefCache.getInstance().contains(eventMessageRecord)) {
                    message = "MATCH_NOT_FOUND_IN_ASSET_CONTROL_LIST [" + eventMessageRecord.toString()
                            + "]\n  ... SKIPPING logging to stgcrdbo.RPF_EVENT_MSG_LOAD_LOG";
                    VerboseLogging.log(message, VerboseLogging.LOG_NORMAL);
                    continue;
                }

                RpfEventMessageDefinitionVo cachedMessageRecord =
                        MessageServiceDefCache.getInstance().getMatch(eventMessageRecord);
                eventMessageRecord.setMsgId(cachedMessageRecord.getMsgId());
                msgRcdList.add(eventMessageRecord);
                this.logMessageRecord(eventMessageRecord, msgBody);

            }
        } // for loop

    } catch (Exception e) {
        VerboseLogging.log("" + "Failed Getting Events", e, VerboseLogging.LOG_NORMAL);
        throw new RDTBusHandlerException("COULD NOT PARSE", e);
    } finally {
        CoreStreamUtils.attemptCloseQuietly(in);
    }

    VerboseLogging.log("" + " Total[" + msgRcdList.size() + "] Events Received..", VerboseLogging.LOG_HIGH);

    if (!msgRcdList.isEmpty()) {
        log.info("RDI_EVENT_RECEIVED: [" + msgRcdList.size() + "]" + System.lineSeparator() + msgBody);
    } else {
        log.info("RDI_EVENT_IGNORED: [" + msgRcdList.size() + "]" + msgBody);
    }

    return msgRcdList;
}
```

---

## Summary of All 3 Changes

| # | Problem | Fix |
|---|---|---|
| 1 | `newDocumentBuilder()` called before `setFeature()` | Moved all feature calls **above** `newDocumentBuilder()` |
| 2 | Dead throwaway `dbFactory.newDocumentBuilder().parse(...)` line | **Deleted** — it was unsafe and its result was never used |
| 3 | `dBuilder.parse(in)` used an unsafe builder | Now uses the builder created **after** all features are set |

---

## Why Each Security Feature Matters

| Feature | Protection |
|---|---|
| `disallow-doctype-decl = true` | Blocks `<!DOCTYPE>` declarations entirely — strongest fix, also prevents DoS (Billion Laughs) |
| `external-general-entities = false` | Prevents `&externalEntity;` references |
| `external-parameter-entities = false` | Prevents `%externalParam;` in DTDs |
| `load-external-dtd = false` | Stops fetching remote DTD files |
| `setXIncludeAware(false)` | Disables XInclude processing |
| `setExpandEntityReferences(false)` | Prevents entity expansion |
| `ACCESS_EXTERNAL_DTD = ""` | Blocks all protocols for external DTD access (Java 7u67+ / 8u20+) |
| `ACCESS_EXTERNAL_SCHEMA = ""` | Blocks all protocols for external schema access |

---

## Key Rule to Remember

> **Always set `setFeature()` / `setAttribute()` on the factory BEFORE calling `newDocumentBuilder()`.**
> Features set after the builder is created have no effect. This is the most common XXE fix mistake.

---

---

# XXE Fix — `parseXmlFile()` in `BusTextHelper.java`

## The 2 Problems

```java
DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();

dbf.setFeature("disallow-doctype-decl", true);        // ✅ good
dbf.setFeature("external-general-entities", false);   // ✅ good
dbf.setFeature("external-parameter-entities", false); // ✅ good
dbf.setFeature("load-external-dtd", false);           // ✅ good
dbf.setXIncludeAware(false);                          // ✅ good
dbf.setExpandEntityReferences(false);                 // ✅ good

dbf.newDocumentBuilder()                              // ❌ PROBLEM 1: throwaway unprotected
   .parse(new InputSource(new StringReader(in)));     //    parse — result is NEVER used

DocumentBuilder db = dbf.newDocumentBuilder();        // ✅ this builder is fine
InputSource is = new InputSource(new StringReader(in));
return db.parse(is);                                  // ❌ PROBLEM 2: Snyk sees TWO parse()
                                                      //    calls in the same method and
                                                      //    flags the whole method as unsafe
```

| # | Problem | Impact |
|---|---|---|
| 1 | Throwaway `dbf.newDocumentBuilder().parse(...)` line | Snyk traces it as an unsafe sink — result is never stored or returned |
| 2 | Two `parse()` calls in the same method | Snyk flags the entire method even though the second builder is safe |

---

## The Fix

```java
public static Document parseXmlFile(String in) throws RDTBusHandlerException {
    try {
        DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();

        // ✅ Security features set BEFORE newDocumentBuilder()
        dbf.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
        dbf.setFeature("http://xml.org/sax/features/external-general-entities", false);
        dbf.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
        dbf.setFeature("http://apache.org/xml/features/nonvalidating/load-external-dtd", false);
        dbf.setXIncludeAware(false);
        dbf.setExpandEntityReferences(false);
        dbf.setAttribute(XMLConstants.ACCESS_EXTERNAL_DTD, "");
        dbf.setAttribute(XMLConstants.ACCESS_EXTERNAL_SCHEMA, "");

        // ✅ ONE builder, ONE parse — throwaway line removed
        DocumentBuilder db = dbf.newDocumentBuilder();
        InputSource is = new InputSource(new StringReader(in));
        return db.parse(is);

    } catch (Exception e) {
        throw new RDTBusHandlerException(e);
    }
}
```

## Summary of Change

The **only change** needed — delete this line entirely:

```java
// ❌ DELETE THIS LINE
dbf.newDocumentBuilder().parse(new InputSource(new StringReader(in)));
```

It does nothing useful — its result is never stored or returned — and it is the line Snyk is flagging as the vulnerable sink.
