# iDempiere SOAP Webservices Plugin

An OSGi plugin for [iDempiere](https://github.com/idempiere/idempiere) that provides the SOAP/REST webservice API (`/ADInterface`). This functionality was extracted from iDempiere core and is distributed as an optional plugin.

***

## Overview

This plugin exposes iDempiere's `CompositeService` and `ModelADService` SOAP endpoints, built on top of Apache CXF and Spring. When installed, it registers with core via the OSGi Declarative Services interfaces `IModelFactory` and `IProcessFactory` - no changes to iDempiere core are required.

**Default endpoint:** `http://<host>:<port>/ADInterface/services`

***

## Repository Structure

```
idempiere-soap-webservices/
├── pom.xml                                    # Root aggregator (Tycho build)
├── org.idempiere.soap.parent/
│   └── pom.xml                                # Tycho config, iDempiere core P2 repository
├── org.idempiere.webservice.library/          # Embedded Apache CXF + Spring runtime
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
| `org.idempiere.webservice.library` | Library bundle. Embeds Apache CXF 3.6.5, Spring 5.3.27, Neethi, XmlSchema Core and WSDL4J through `Bundle-ClassPath` and re-exports them. iDempiere core stopped shipping these libraries in IDEMPIERE-6955, so they travel with the extension. Published as its own extension, declared as a dependency by this one. |
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

When a jar version changes, edit the version properties in
`org.idempiere.webservice.library/pom.xml` and regenerate the bundle manifest:

```bash
cd org.idempiere.webservice.library
mvn validate
python3 tools/generate-manifest.py --print-dropped
```

The generator exports every package of the embedded jars and imports every package they reference
that iDempiere core actually exports; `--print-dropped` lists the referenced packages core does not
have, which are the optional CXF and Spring integrations iDempiere never calls.

By default the build assumes iDempiere core is cloned as a sibling folder:

```
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
