# iDempiere SOAP Webservices Plugin

An OSGi plugin for [iDempiere](https://github.com/idempiere/idempiere) that provides the SOAP/REST webservice API (`/ADInterface`). This functionality was extracted from iDempiere core and is distributed as an optional plugin.

***

## Overview

This plugin exposes iDempiere's `CompositeService` and `ModelADService` SOAP endpoints, built on top of Apache CXF and Spring. When installed, it registers with core via the OSGi Declarative Services interfaces `IModelFactory` and `IProcessFactory` - no changes to iDempiere core are required.

**Default endpoint:** `http://<host>:<port>/ADInterface/services`

***

## Repository Structure

```text
idempiere-soap-webservices/
├── pom.xml                                    # Root aggregator (Tycho build)
├── org.idempiere.soap.parent/
│   └── pom.xml                                # Tycho config, iDempiere core P2 repository
├── org.idempiere.webservice.library/          # Embedded Apache CXF runtime
├── org.idempiere.webservices.resources/       # CXF servlet config, XSD schemas, Spring context
├── org.idempiere.webservices/                 # Main SOAP bundle (Web-ContextPath: ADInterface)
└── org.idempiere.webservice.client/           # Standalone Maven-to-P2 step, not part of the build
    └── pom.xml
```

### Bundle responsibilities

| Bundle | Purpose |
|---|---|
| `org.idempiere.webservices` | Main OSGi web bundle. Hosts the SOAP endpoints, model classes (`MWebService`, `MWebServiceType`), and OSGi service registrations. Deployed at `/ADInterface`. |
| `org.idempiere.webservices.resources` | Helper bundle. Provides the CXF servlet config (`cxf-servlet.xml`), Spring `ContextLoaderListener`, and XSD schemas consumed by CXF at runtime. |
| `org.idempiere.webservice.library` | Library bundle. Embeds Apache CXF 3.6.5, Neethi, XmlSchema Core and WSDL4J through `Bundle-ClassPath` and re-exports them. iDempiere core stopped shipping CXF in IDEMPIERE-6955, so it travels with the extension. Spring stays in core - the library imports it from the `wrapped.org.springframework.spring-*` bundles rather than embedding a second copy. Published as its own extension, declared as a dependency by this one. |
| `org.idempiere.webservice.client` | **Not a Tycho module.** A standalone Maven build using the Reficio `p2-maven-plugin` to pull JAX-WS client JARs from Maven Central and wrap them as OSGi bundles. Kept for reference; the client feature stayed in iDempiere core. |

***

## Prerequisites

- Java 17+
- Maven 3.9+
- A built iDempiere core P2 repository (see [iDempiere](https://github.com/idempiere/idempiere))

***

## Building

```bash
mvn clean verify
```

The `org.idempiere.webservice.library` module downloads its jars from Maven Central into `lib/`
during `validate`, plus the two repackaged CXF jars that Apache no longer publishes, which come
from `https://docs.idempiere.org/binary.file/p2.repackaged`. Those jars are build output, they are
not in git.

Maven verifies the checksum of everything it fetches from Central. The two repackaged jars do not
come from a Maven repository, so their SHA-256 is pinned in `cxf.repackaged.xmlbeans.sha256` and
`cxf.repackaged.extproviders.sha256` and verified after the download - the build fails rather than
package an artifact it cannot identify. The `12.0.1` in that URL is the release in which the
repackaged set was last regenerated, not the iDempiere release consuming it. iDempiere core used to
pin the same folder in `org.idempiere.p2.targetplatform/base.target`; it stopped when CXF left core,
so this build is now the only consumer of those two jars.

When a jar version changes, edit the version properties in
`org.idempiere.webservice.library/pom.xml` - for `cxf.repackaged.version` also recompute the two
pinned `sha256` values (`sha256sum org.idempiere.webservice.library/lib/*.jar` after a successful
download) - run `mvn validate` in that module to refresh `lib/`, and redo
`org.idempiere.webservice.library/META-INF/MANIFEST.MF` by these rules:

* **`Bundle-ClassPath`** - `.` followed by every jar in `lib/`. The same list has to appear in
  `build.properties` (`bin.includes`) and in `.classpath` as `kind="lib"` entries; all three plus the
  contents of `lib/` must agree name for name.
* **`Export-Package`** - every package that holds a `.class` in those jars, at the version of the
  artifact it came from (CXF 3.6.5, the two repackaged CXF jars 3.6.3, neethi 3.2.0, xmlschema-core
  2.3.1, wsdl4j 1.6.3); the highest version wins when a package appears in two jars. A package that an
  embedded jar only *partially* vendors is not exported at all - exporting an incomplete copy of an
  API hands a future consumer a bundle that resolves and then fails on a missing class.
* **`Import-Package`** - every package the embedded classes reference that this bundle does not
  export itself, that is not JDK owned (`java.`, `jdk.`, `sun.`, `org.w3c.`, `org.xml.sax.`) and that
  an iDempiere core bundle does export. Packages core does not export are left out entirely: they are
  optional CXF integrations iDempiere never calls. An entry is mandatory when one of the embedded OSGi
  bundles declares it mandatory, and additionally for `javax.servlet`, `javax.servlet.http`,
  `org.apache.commons.logging` and the `org.springframework.*` packages listed below; everything else
  gets `;resolution:=optional`.
* **Spring** - core owns it, this bundle must not embed or export it. CXF declares every
  `org.springframework` import optional because CXF can run without Spring, but the iDempiere SOAP
  stack cannot, so the packages CXF actually references are imported mandatorily at
  `version="[5.3.27,6)"`: `aop`, `aop.framework`, `aop.support`, `beans`, `beans.factory`,
  `beans.factory.config`, `beans.factory.support`, `beans.factory.wiring`, `beans.factory.xml`,
  `context`, `context.annotation`, `context.event`, `context.support`, `core`, `core.io`,
  `core.io.support`, `core.type`, `core.type.classreading`, `util`, `web.context`,
  `web.context.support`. `org.springframework.web.servlet*` (spring-webmvc) and
  `org.springframework.osgi.*` (Spring-DM) stay out - core has never shipped either.
* Fold every header to 72 bytes, one entry per line.

Then prove it: `mvn clean verify` at the repository root, and install the rebuilt bundle in a running
instance and read `diag org.idempiere.webservices`. Static resolution alone does not prove CXF can
still find its bus extensions.

By default the build assumes iDempiere core is cloned as a sibling folder:

```text
parent-folder/
├── idempiere-master/   ← iDempiere core (must be built first: mvn clean verify)
└── idempiere-soap-webservices/
```

To override the core P2 repository path:

```bash
mvn clean verify \
  -Didempiere.core.repository.url=file:///absolute/path/to/idempiere/org.idempiere.p2/target/repository
```

To point to a remote P2 site (e.g., nightly build):

```bash
mvn clean verify \
  -Didempiere.core.repository.url=https://jenkins.idempiere.org/job/iDempiere14/lastSuccessfulBuild/artifact/org.idempiere.p2/target/repository
```

***

## Importing into Eclipse

Build first: the 19 jars in `org.idempiere.webservice.library/lib/` are build output, so a fresh
clone has an empty `lib/` and the classpath entries of that project point at missing files.

```bash
mvn clean verify
```

Then **File > Import > General > Existing Projects into Workspace**, select the repository root and
import the three plugin projects. `org.idempiere.webservices` resolves
`Require-Bundle: org.idempiere.webservice.library` from the workspace, the rest of its dependencies
from the iDempiere core target platform, so core has to be built and set as the active target
platform first.

***

## Installing into iDempiere

### Option A — Extension manager (recommended)

Open **System Admin > Extension > Extension Browser** and install, in this order:

1. `org.idempiere.webservice.library`
2. `org.idempiere.webservices`

The extension manager does not install dependencies by itself. Installing the SOAP extension first
fails with a missing dependency message naming the library.

### Option B — OSGi console (runtime install)

Install the library first, otherwise the web service bundles do not resolve:

```bash
osgi> install file:///path/to/org.idempiere.webservice.library-14.0.0.jar
osgi> install file:///path/to/org.idempiere.webservices.resources-14.0.0.jar
osgi> install file:///path/to/org.idempiere.webservices-14.0.0.jar
osgi> start <bundle-id>
```

## Configuration

After installation, configure web services through the iDempiere Application Dictionary:

- **Window:** `Web Service` (`WS_WebService`)
- **Window:** `Web Service Type` (`WS_WebServiceType`)
- **Process:** `Web Service Type - Create Parameters`

The database tables (`WS_WebService`, `WS_WebServiceType`, `WS_WebServiceMethod`, `WS_WebService_Para`, `WS_WebServiceFieldInput`, `WS_WebServiceFieldOutput`, `WS_WebServiceTypeAccess`) are created by the core migration scripts already present in iDempiere. No additional migration scripts are needed.

Verify the plugin is active by browsing to `http://<host>:<port>/ADInterface/services` -
you should see `CompositeService` and `ModelADService` listed with their WSDL links.

***

## Documentation

- [Web Services Reference](https://wiki.idempiere.org/en/Web_services) — full parameter reference for `ModelADService` and `CompositeService` methods, login data requirements, and field-level documentation.
- [Web Services First Steps](https://wiki.idempiere.org/en/Web_Services_First_Steps) — beginner walkthrough: creating a Web Service Type in the Application Dictionary, testing with SoapUI, and sending requests via `curl` and `wget`.
- [Web Services Security](https://wiki.idempiere.org/en/Web_Services_Security) — how to configure roles, parameters (Free vs Constant), and access control on web service types.
- [NF1.0 Web Services Improvements](https://wiki.idempiere.org/en/NF1.0_Web_Services_Improvements) — background on the original extraction from ADempiere, migration from XFire to CXF, and the introduction of `CompositeService`.

## License

[GPL v2](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html) — same as iDempiere core.
