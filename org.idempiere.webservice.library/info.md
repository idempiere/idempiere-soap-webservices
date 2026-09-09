# iDempiere Web Service Library

**Summary:** A single OSGi bundle that carries the Apache CXF runtime the iDempiere web service extensions need. iDempiere core stopped shipping CXF when the SOAP module moved out of core (IDEMPIERE-6955), so it now travels with the extensions that use it. Spring stays in core, where other plugins can keep using it, and this bundle imports it from there.

## 🚀 Contents

* **Apache CXF 3.6.5:** core, JAX-WS and JAX-RS frontends, SOAP and XML bindings, JAXB data binding, HTTP transport, WSDL, WS-Addressing, WS-Policy, WS-Transfer, RS service description and security.
* **Apache CXF 3.6.3 (iDempiere repackaged):** the XmlBeans data binding and the XmlBeans JAX-RS providers, which Apache dropped after CXF 3.1 and iDempiere keeps alive.
* **Support libraries:** Neethi 3.2.0, XmlSchema Core 2.3.1 and WSDL4J 1.6.3.

Everything is embedded through `Bundle-ClassPath` and re-exported, so a consumer requires one bundle instead of a dozen and a half, and CXF resolves its own extensions inside a single class loader. Spring is not embedded: core ships it as the `wrapped.org.springframework.spring-*` bundles and this library imports the packages CXF needs, so there is only ever one Spring on the class path.

## ⚙️ Compatibility

* **iDempiere Version:** 14.0
* **Java Version:** 17+

## 📦 Database Changes

None. This extension installs no dictionary entries and runs no migration script.

## 🛠 Usage & Configuration

Nothing to configure. Install it before any extension that declares it as a dependency - the extension manager does not install dependencies automatically, it refuses the install and tells you what is missing.

It can only be uninstalled once every extension that depends on it has been uninstalled.

Extensions consume it by requiring the bundle:

```text
Require-Bundle: org.idempiere.webservice.library;bundle-version="14.0.0"
```

## 👤 Author / Support

* **Developer:** iDempiere Community
* **Source Code:** [https://github.com/idempiere/idempiere-soap-webservices](https://github.com/idempiere/idempiere-soap-webservices)
* **Issue Tracker:** [https://idempiere.atlassian.net/browse/IDEMPIERE-6955](https://idempiere.atlassian.net/browse/IDEMPIERE-6955)
