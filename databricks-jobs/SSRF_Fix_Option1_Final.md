# Server-Side Request Forgery (SSRF) — Fix Implementation Guide
**Snyk-Code | CWE-918**  
**File:** `src/main/java/com/jpmorgan/cib/lrirdr/rdrjobrunner/jobexecution/impl/RpfAwsEpsJobExecutor.java` (line 290)  
**Approach:** Option 1 — Defense-in-Depth (Recommended)

---

## Summary

Unsanitized input from a database flows into `org.apache.http.client.methods.HttpGet`,
where it is used as a URL to perform a request. This may result in a Server-Side Request
Forgery vulnerability. The fix applies validation at **three layers**: the DAO source,
the URL construction service, and the final HTTP client — ensuring no tainted value
can reach the network.

---

## Complete Data Flow (End-to-End)

```
DB Query (EpsAwsCfgLookupDAOImpl.java:62)
  └─► dataset_id read from ResultSet  ← UNTRUSTED SOURCE
        └─► EpsAwsJobVo object constructed with dataset_id
              └─► EpsJobsDefService.java: findEpsAwsJobsDef() returns list
                    └─► for loop: dvo.getDatasetID() stored into Map
                          └─► RpfAwsEpsJobExecutor.java:381
                                └─► lookUpRunIDs(jobMap, cobDate)
                                      └─► for each entry: lookUpRunID(e.getValue(), cobDate)
                                            └─► lookUpRunID(submitVo, cobDate)
                                                  └─► httpService.getRunID(submitVo.getDatasetID(), cobDate)
                                                        └─► EpsHttpService.java: buildHttpURL(datasetID, cobDate)
                                                              └─► TextUtils.replaceString() ← blind substitution, no validation
                                                                    └─► httpJobConnect.httpGet(url)
                                                                          └─► new HttpGet(httpGetURL)  ← SSRF SINK ✗
```

---

## Key Observations

| Issue | Detail |
|---|---|
| **No validation anywhere** | `datasetID` travels through 43 nodes from DB → HTTP with zero sanitization |
| **URL built by string replacement** | `TextUtils.replaceString()` performs blind substitution — no encoding or allowlisting |
| **Tainted value also logged** | `log.info("GETTING: [" + httpGetURL + "]")` — secondary log injection risk |
| **Direct `HttpGet` construction** | Apache `HttpGet` will faithfully execute any URL passed to it |

---

## Why It's Dangerous

If an attacker can write a malicious value into the `dataset_id` column
(e.g. `http://169.254.169.254/latest/meta-data/`), the server will issue
requests to internal infrastructure, potentially exposing:

- Cloud instance credentials (AWS/GCP/Azure metadata endpoints)
- Internal microservices behind the firewall
- Network topology that bypasses perimeter controls

---

## URI-Safe Character Allowlist Reference

Based on [RFC 3986](https://www.rfc-editor.org/rfc/rfc3986), the following characters
are valid within a URI segment and are included in the validation regex used across all fixes:

| Character Class | Characters | Allowed |
|---|---|---|
| Alphanumeric | `a-z  A-Z  0-9` | ✅ |
| Dot | `.` | ✅ |
| Dash | `-` | ✅ |
| Underscore | `_` | ✅ |
| Tilde | `~` | ✅ |
| Exclamation | `!` | ✅ |
| Dollar | `$` | ✅ |
| Ampersand | `&` | ✅ |
| Single quote | `'` | ✅ |
| Parentheses | `( )` | ✅ |
| Asterisk | `*` | ✅ |
| Plus | `+` | ✅ |
| Comma | `,` | ✅ |
| Semicolon | `;` | ✅ |
| Equals | `=` | ✅ |
| Colon | `:` | ✅ |
| At symbol | `@` | ✅ |
| Percent (encoding prefix) | `%` | ✅ |
| Slash, Question mark, Hash | `/ ? #` | ❌ Reserved URI structural delimiters — excluded to prevent URL manipulation |
| Spaces, angle brackets, braces | `space < > { }` | ❌ Invalid/unsafe in URIs — excluded |

**Regex used across all three fixes:**
```
^[a-zA-Z0-9._~!$&'()*+,;=:@%-]{1,128}$
```

> **Note on `%`:** Included to support percent-encoded values (e.g. `%20`, `%2F`).
> If your `datasetID` values never use percent-encoding, remove `%` for a stricter allowlist:
> `^[a-zA-Z0-9._~!$&'()*+,;=:@-]{1,128}$`

---

## Fix Implementation — Option 1: Defense-in-Depth

Three files are modified. Each layer independently rejects a tainted value,
so a bypass at one layer is caught by the next.

---

### Fix 1a — `EpsAwsCfgLookupDAOImpl.java`
**Layer: Database source — validate as soon as data is read**

```java
import java.util.regex.Pattern;

public class EpsAwsCfgLookupDAOImpl {

    // RFC 3986 URI-safe characters: letters, digits, . - _ ~ ! $ & ' ( ) * + , ; = : @ %
    // Max length 128 to accommodate any realistic dataset ID
    private static final Pattern SAFE_DATASET_ID =
        Pattern.compile("^[a-zA-Z0-9._~!$&'()*+,;=:@%-]{1,128}$");

    public List<EpsAwsJobVo> findEpsAwsJobsDef(String mrRunGroup) {
        // ... existing SQL and parameter setup ...

        return jdbcTemplate.query(sql, parameters, new RowMapper<EpsAwsJobVo>() {

            @Override
            public EpsAwsJobVo mapRow(ResultSet rs, int rowNum) throws SQLException {
                String datasetId = rs.getString("dataset_id");

                // ✅ FIX: Validate at the source before the value enters the application
                if (datasetId == null || !SAFE_DATASET_ID.matcher(datasetId).matches()) {
                    throw new SQLException(
                        "Rejected unsafe dataset_id from database: [" + datasetId + "]"
                    );
                }

                return new EpsAwsJobVo(
                    datasetId,
                    rs.getString("aws_job_name"),
                    rs.getString("job_service_name")
                );
            }
        });
    }
}
```

---

### Fix 1b — `EpsHttpService.java`
**Layer: URL construction — validate input AND the fully assembled URL**

```java
import java.net.URI;
import java.net.URISyntaxException;
import java.util.regex.Pattern;

public class EpsHttpService {

    // ✅ Configure these to match your actual internal service
    private static final String  ALLOWED_SCHEME     = "https";
    private static final String  ALLOWED_HOST       = "your-internal-eps-host.company.com"; // ← replace
    private static final int     ALLOWED_PORT       = 8080;                                  // ← replace

    // Same RFC 3986 pattern as DAO layer (defense-in-depth — validate again here)
    private static final Pattern SAFE_DATASET_ID =
        Pattern.compile("^[a-zA-Z0-9._~!$&'()*+,;=:@%-]{1,128}$");

    public EpsResponseVo getRunID(String datasetID, String cobDate) throws Exception {
        // ✅ FIX: Validate before any processing begins
        if (datasetID == null || !SAFE_DATASET_ID.matcher(datasetID).matches()) {
            throw new SecurityException(
                "Rejected unsafe datasetID in getRunID: [" + datasetID + "]"
            );
        }

        HttpJobResponse jobResponse = getEpsHttpStatus(datasetID, cobDate);
        return parseResponse(jobResponse);
    }

    public HttpJobResponse getEpsHttpStatus(String datasetID, String cobDate) throws Exception {
        String url = this.buildHttpURL(datasetID, cobDate);
        return this.httpJobConnect.httpGet(url);
    }

    public String buildHttpURL(String dataSetID, String cobDate) {
        // ✅ FIX: Re-validate input (catches any path that bypasses getRunID)
        if (dataSetID == null || !SAFE_DATASET_ID.matcher(dataSetID).matches()) {
            throw new SecurityException(
                "Rejected unsafe dataSetID in buildHttpURL: [" + dataSetID + "]"
            );
        }

        // Perform existing template substitution
        String urlTemplate = /* load from config */ EPSJobConstants.URL_TEMPLATE;
        urlTemplate = TextUtils.replaceString(urlTemplate, EPSJobConstants.P_DATASET_ID, dataSetID);
        urlTemplate = TextUtils.replaceString(urlTemplate, EPSJobConstants.P_COB_DATE, cobDate);

        // ✅ FIX: Validate the fully constructed URL — scheme, host, and port must match allowlist
        try {
            URI uri = new URI(urlTemplate);

            if (!ALLOWED_SCHEME.equals(uri.getScheme())
                    || !ALLOWED_HOST.equals(uri.getHost())
                    || uri.getPort() != ALLOWED_PORT) {
                throw new SecurityException(
                    "SSRF blocked — URL does not match allowed target. " +
                    "scheme=[" + uri.getScheme() + "] " +
                    "host=[" + uri.getHost() + "] " +
                    "port=[" + uri.getPort() + "]"
                );
            }
        } catch (URISyntaxException e) {
            throw new SecurityException("Malformed URL constructed: [" + urlTemplate + "]", e);
        }

        return urlTemplate;
    }
}
```

---

### Fix 1c — `HttpJobConnect.java`
**Layer: HTTP client — final gate, never trust what arrives here**

```java
import java.net.URI;
import java.net.URISyntaxException;

public class HttpJobConnect {

    // Must match the value declared in EpsHttpService
    private static final String ALLOWED_HOST = "your-internal-eps-host.company.com"; // ← replace
    private static final int    ALLOWED_PORT = 8080;                                  // ← replace

    public HttpJobResponse httpGet(String httpGetURL) throws Exception {

        // ✅ FIX: Last line of defense — independently verify host before issuing request
        try {
            URI uri = new URI(httpGetURL);

            if (!ALLOWED_HOST.equals(uri.getHost()) || uri.getPort() != ALLOWED_PORT) {
                throw new SecurityException(
                    "HttpGet blocked — unexpected target: [" + uri.getHost() + ":" + uri.getPort() + "]"
                );
            }

            // ✅ FIX: Log only safe parts of the URL, not user-influenced query params
            log.info("GETTING: [" + uri.getHost() + uri.getPath() + "]");

        } catch (URISyntaxException e) {
            throw new SecurityException("Malformed URL passed to httpGet: [" + httpGetURL + "]", e);
        }

        HttpGet httpGetObj = new HttpGet(httpGetURL);
        // ... rest of your existing HTTP execution logic ...
    }
}
```

---

## Files Modified — Summary

| # | File | Package Path | What Changed |
|---|---|---|---|
| 1 | `EpsAwsCfgLookupDAOImpl.java` | `eps/dao/impl/` | Added `SAFE_DATASET_ID` pattern; validate `dataset_id` immediately on DB read |
| 2 | `EpsHttpService.java` | `eps/service/` | Added `SAFE_DATASET_ID` pattern; validate input in `getRunID()` and `buildHttpURL()`; validate assembled URL scheme/host/port |
| 3 | `HttpJobConnect.java` | `http/client/` | Added final host/port check before `HttpGet`; replaced full-URL logging with safe partial log |

---

## Before You Deploy — Checklist

- [ ] Replace `ALLOWED_HOST` in **both** `EpsHttpService.java` and `HttpJobConnect.java` with your real internal hostname
- [ ] Replace `ALLOWED_PORT` with your real service port
- [ ] Confirm `ALLOWED_SCHEME` is `"https"` (not `"http"`) in production
- [ ] If `datasetID` values in your DB never contain `%`, remove `%` from the regex for a tighter allowlist
- [ ] Run existing unit/integration tests — any test that passes an ID with `/`, `?`, `#`, or spaces will now throw `SecurityException` (this is correct behaviour)
- [ ] Add unit tests covering: valid IDs, null, too-long strings, IDs containing `/` or `http://`, and mismatched hosts

---

## Imports Required

| File | New Imports |
|---|---|
| `EpsAwsCfgLookupDAOImpl.java` | `java.util.regex.Pattern` |
| `EpsHttpService.java` | `java.net.URI`, `java.net.URISyntaxException`, `java.util.regex.Pattern` |
| `HttpJobConnect.java` | `java.net.URI`, `java.net.URISyntaxException` |

---

*SSRF remediation guide — Snyk CWE-918 | Option 1: Defense-in-Depth with RFC 3986 URI-safe allowlist*
