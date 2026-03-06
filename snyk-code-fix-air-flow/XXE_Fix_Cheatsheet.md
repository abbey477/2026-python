# XXE Injection Fix Cheat Sheet (CWE-611 / Snyk SNYK-CODE)
> **Target file:** `BusTextHelper.java` → `parseXmlFile()` method  
> **Vulnerability:** Unsanitized JMS message flows into `DocumentBuilder.parse()` — allows external entity expansion

---

## 🥇 Option 1 — Recommended (Snyk ✅ Confirmed)

Use when your XML **never needs DOCTYPE/DTD support** (true for JMS message payloads).

```java
import javax.xml.XMLConstants;
import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.ParserConfigurationException;
import org.xml.sax.InputSource;
import org.xml.sax.SAXException;
import java.io.IOException;
import java.io.StringReader;

public static Document parseXmlFile(String in) throws RDTBusHandlerException {
    try {
        DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();

        // PRIMARY fix — blocks all DOCTYPE, stops XXE entirely
        dbf.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);

        // Bonus: also prevents DoS (XML bomb / Billion Laughs attacks)
        dbf.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
        dbf.setXIncludeAware(false);

        DocumentBuilder db = dbf.newDocumentBuilder();
        return db.parse(new InputSource(new StringReader(in)));

    } catch (ParserConfigurationException | SAXException | IOException e) {
        throw new RDTBusHandlerException("XML parsing error", e);
    }
}
```

**Why it works:** `disallow-doctype-decl` is the exact pattern Snyk Code looks for to mark the sink as sanitized.  
**Bonus:** Also blocks XML bomb / Billion Laughs DoS attacks.

---

## 🥈 Option 2 — If you DO Need DTD Support

Use when the JMS XML messages legitimately contain DTD declarations but you still need to block external entity resolution.

```java
DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();

// Allow DOCTYPE but block ALL external entity resolution
dbf.setFeature("http://xml.org/sax/features/external-general-entities", false);
dbf.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
dbf.setFeature("http://apache.org/xml/features/nonvalidating/load-external-dtd", false);
dbf.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
dbf.setXIncludeAware(false);
dbf.setExpandEntityReferences(false);

DocumentBuilder db = dbf.newDocumentBuilder();
return db.parse(new InputSource(new StringReader(in)));
```

**Why it works:** Allows DOCTYPE declarations but prevents external resources from being fetched or expanded.  
**Warning:** You need **all three** entity features set together — missing even one can leave you vulnerable.

---

## 🥉 Option 3 — setAttribute Style (Java 7u40+ / Java 8+ only)

Alternative API approach, achieves the same result as Option 2.

```java
DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();

dbf.setAttribute(XMLConstants.ACCESS_EXTERNAL_DTD, "");     // block external DTD
dbf.setAttribute(XMLConstants.ACCESS_EXTERNAL_SCHEMA, "");  // block external schema
dbf.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);

DocumentBuilder db = dbf.newDocumentBuilder();
return db.parse(new InputSource(new StringReader(in)));
```

**Why it works:** Uses the `XMLConstants` attribute API to restrict external access.  
**Warning:** Only works on Java 7u40+ / Java 8+. Will silently fail on older JVMs.

---

## ⚠️ Gotchas — Read Before You Commit

| Gotcha | Detail |
|---|---|
| **`FEATURE_SECURE_PROCESSING` alone is NOT enough** | It prevents DoS and restricts external resources, but does not fully disallow DTD processing — Snyk may still flag the finding |
| **`setExpandEntityReferences(false)` alone is NOT enough** | Doesn't prevent *fetching* external entities; also has a known bug in OpenJDK < 13 (JDK-8206132) |
| **Option 2 needs ALL 3 features** | Missing even one of the three entity features can still leave you vulnerable to XXE |
| **`disallow-doctype-decl` is Xerces-specific** | Works on all standard JDK distributions (which ship Xerces internally), but may throw `SAXNotRecognizedException` on non-standard XML processors (e.g. some IBM JVMs) |
| **Static shared `DocumentBuilder` is NOT thread-safe** | Always create a new `DocumentBuilderFactory` + `DocumentBuilder` per method call, as shown above |
| **Wrap each `setFeature` in its own try/catch** | If one `setFeature()` call fails and you swallow the exception, all subsequent calls will be skipped silently |

---

## 📊 Quick Comparison

| Option | Blocks XXE | Blocks DoS | DTD Support | Java Version | Snyk ✅ |
|---|---|---|---|---|---|
| **1. disallow-doctype-decl** | ✅ Full | ✅ Yes | ❌ No | Any (with Xerces) | ✅ Confirmed |
| **2. Disable entities individually** | ✅ Full | ❌ No | ✅ Yes | 7u67 / 8u20+ | ✅ Yes |
| **3. ACCESS_EXTERNAL_DTD setAttribute** | ✅ Full | ❌ No | ✅ Yes | 7u40 / 8+ | ✅ Yes |

---

## ✅ TL;DR for This Specific Case

Your code is a **JMS listener parsing untrusted input** — use **Option 1**.  
It's 3 lines, clears the Snyk finding, and blocks both XXE and XML bomb DoS attacks in one shot.

```java
DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
dbf.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
dbf.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
dbf.setXIncludeAware(false);
DocumentBuilder db = dbf.newDocumentBuilder();
return db.parse(new InputSource(new StringReader(in)));
```

---

## 📚 References

- [OWASP XXE Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/XML_External_Entity_Prevention_Cheat_Sheet.html)
- [Semgrep Java XXE Guide](https://semgrep.dev/docs/cheat-sheets/java-xxe)
- [Sonar: How to Disable XXE Processing](https://www.sonarsource.com/blog/secure-xml-processor/)
- [CWE-611: Improper Restriction of XML External Entity Reference](https://cwe.mitre.org/data/definitions/611.html)
- [OpenJDK Bug JDK-8206132](https://bugs.openjdk.java.net/browse/JDK-8206132) — `setExpandEntityReferences` bug in OpenJDK < 13
