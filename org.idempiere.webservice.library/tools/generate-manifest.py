#!/usr/bin/env python3
"""Regenerate META-INF/MANIFEST.MF for org.idempiere.webservice.library.

The bundle embeds the Apache CXF and Spring jars that iDempiere core no longer
ships (see IDEMPIERE-6955) and re-exports their packages, so that the SOAP web
service extension - and any other extension that needs CXF - can require a
single bundle instead of two dozen.

Export-Package is every package that holds a class in lib/*.jar.
Import-Package is every package those classes reference from outside the bundle
that iDempiere core actually exports; anything else is an optional dependency of
CXF or Spring that iDempiere does not use, and is deliberately left out.

Usage:
    python3 tools/generate-manifest.py [--core-plugins DIR] [--print-dropped]

DIR defaults to the plugins folder of a locally built iDempiere p2 repository.
"""

import argparse
import os
import re
import struct
import sys
import zipfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(HERE, "lib")
MANIFEST = os.path.join(HERE, "META-INF", "MANIFEST.MF")

BUNDLE_SYMBOLIC_NAME = "org.idempiere.webservice.library"
BUNDLE_VERSION = "14.0.0.qualifier"
BUNDLE_NAME = "iDempiere Web Service Library"

# version exported for the packages of each embedded jar
VERSIONS = {
    "cxf-rt-databinding-xmlbeans": "3.6.3",
    "cxf-rt-rs-extension-providers": "3.6.3",
    "neethi": "3.2.0",
    "wsdl4j": "1.6.3",
    "xmlschema-core": "2.3.1",
}
DEFAULT_VERSIONS = (("cxf-", "3.6.5"), ("spring-", "5.3.27"))

# imports that must stay mandatory even when no embedded jar declares them so:
# without these nothing works, and a resolution error beats a NoClassDefFoundError
ALWAYS_MANDATORY = {"javax.servlet", "javax.servlet.http", "org.apache.commons.logging"}

# JDK owned packages: the system bundle provides them, they are never imported.
# Everything else is decided by whether an iDempiere core bundle exports it.
NEVER_IMPORT = re.compile(r"^(java|jdk|sun|org\.w3c|org\.xml\.sax)\.")


def jar_version(jar):
    base = os.path.basename(jar)[:-4]
    if base in VERSIONS:
        return VERSIONS[base]
    for prefix, version in DEFAULT_VERSIONS:
        if base.startswith(prefix):
            return version
    raise SystemExit("no version mapping for " + base)


def class_refs(data):
    """Package names referenced by the constant pool of one class file."""
    if data[:4] != b"\xca\xfe\xba\xbe":
        return set()
    count = struct.unpack_from(">H", data, 8)[0]
    utf8, class_idx, descriptors, i, pos = {}, set(), set(), 1, 10
    while i < count:
        tag = data[pos]
        pos += 1
        if tag == 1:                                  # Utf8
            length = struct.unpack_from(">H", data, pos)[0]
            utf8[i] = data[pos + 2:pos + 2 + length].decode("utf-8", "replace")
            pos += 2 + length
        elif tag == 7:                                # Class
            class_idx.add(struct.unpack_from(">H", data, pos)[0])
            pos += 2
        elif tag == 12:                               # NameAndType
            descriptors.add(struct.unpack_from(">H", data, pos + 2)[0])
            pos += 4
        elif tag in (3, 4, 9, 10, 11, 18):
            pos += 4
        elif tag in (5, 6):                           # Long/Double take two slots
            pos += 8
            i += 1
        elif tag in (8, 16, 19, 20):
            pos += 2
        elif tag == 15:
            pos += 3
        elif tag == 17:
            pos += 4
        else:
            return set()                              # unknown tag, give up
        i += 1

    names = {utf8[i] for i in class_idx if i in utf8}
    for i in descriptors:
        names.update(re.findall(r"L([^;<>]+);", utf8.get(i, "")))
    packages = set()
    for name in names:
        name = name.lstrip("[")
        if name.startswith("L") and name.endswith(";"):
            name = name[1:-1]
        if "/" in name:
            packages.add(name.rsplit("/", 1)[0].replace("/", "."))
    return packages


def declared_mandatory_imports(jars):
    """Packages the embedded OSGi bundles import without resolution:=optional.

    Spring, wsdl4j and cxf-rt-ws-transfer ship no OSGi metadata, so anything only
    they reference stays optional - those are integrations iDempiere never calls.
    """
    mandatory = set(ALWAYS_MANDATORY)
    for jar in jars:
        try:
            raw = zipfile.ZipFile(os.path.join(LIB, jar)).read("META-INF/MANIFEST.MF")
        except Exception:
            continue
        text = raw.decode("utf-8", "replace").replace("\r\n", "\n").replace("\n ", "")
        for line in text.split("\n"):
            if line.startswith("Import-Package:"):
                for entry in header_entries_raw(line.split(":", 1)[1]):
                    if "resolution:=optional" not in entry.replace(" ", ""):
                        mandatory.add(entry.strip().split(";")[0].strip())
    return mandatory


def core_exports(plugins_dir):
    """Package -> exporting bundle, for every bundle of an iDempiere build."""
    exported = set()
    for entry in sorted(os.listdir(plugins_dir)):
        path = os.path.join(plugins_dir, entry)
        try:
            if os.path.isdir(path):
                raw = open(os.path.join(path, "META-INF/MANIFEST.MF"), "rb").read()
            else:
                raw = zipfile.ZipFile(path).read("META-INF/MANIFEST.MF")
        except Exception:
            continue
        text = raw.decode("utf-8", "replace").replace("\r\n", "\n").replace("\n ", "")
        for line in text.split("\n"):
            if line.startswith("Export-Package:"):
                exported.update(header_entries(line.split(":", 1)[1]))
    return exported


def header_entries(value):
    """Split an OSGi header on top level commas and return the entry names."""
    return [e.strip().split(";")[0].strip() for e in header_entries_raw(value) if e.strip()]


def header_entries_raw(value):
    """Split an OSGi header on top level commas, keeping the directives."""
    entries, depth, quoted, current = [], 0, False, ""
    for char in value:
        if char == '"':
            quoted = not quoted
        if char in "([" and not quoted:
            depth += 1
        elif char in ")]" and not quoted:
            depth -= 1
        if char == "," and depth == 0 and not quoted:
            entries.append(current)
            current = ""
            continue
        current += char
    entries.append(current)
    return [e for e in entries if e.strip()]


def wrap(header, entries):
    """Format an OSGi header, one entry per line, folded to the 72 byte limit."""
    lines = []
    for index, entry in enumerate(entries):
        text = ("%s: %s" % (header, entry)) if index == 0 else (" " + entry)
        if index < len(entries) - 1:
            text += ","
        while len(text.encode("utf-8")) > 72:
            lines.append(text[:71])
            text = " " + text[71:]
        lines.append(text)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--core-plugins", default=os.path.join(
        HERE, "..", "..", "idempiere-master", "org.idempiere.p2", "target", "repository", "plugins"))
    parser.add_argument("--print-dropped", action="store_true")
    args = parser.parse_args()

    jars = sorted(f for f in os.listdir(LIB) if f.endswith(".jar"))
    if not jars:
        raise SystemExit("lib/ is empty - run 'mvn validate' first")

    exports, referenced = {}, set()
    for jar in jars:
        version = jar_version(jar)
        with zipfile.ZipFile(os.path.join(LIB, jar)) as zf:
            for name in zf.namelist():
                if not name.endswith(".class"):
                    continue
                package = os.path.dirname(name).replace("/", ".")
                if not package:
                    continue
                if exports.get(package, "0") < version:
                    exports[package] = version
                referenced.update(class_refs(zf.read(name)))

    available = core_exports(os.path.abspath(args.core_plugins))
    if not available:
        raise SystemExit("no core bundle found under " + args.core_plugins)

    mandatory = declared_mandatory_imports(jars)
    candidates = {p for p in referenced if p not in exports and not NEVER_IMPORT.match(p)}
    imports = [p if p in mandatory else p + ";resolution:=optional"
               for p in sorted(candidates & available)]
    dropped = sorted(candidates - available)

    lines = [
        "Manifest-Version: 1.0",
        "Bundle-ManifestVersion: 2",
        "Bundle-Name: " + BUNDLE_NAME,
        "Bundle-SymbolicName: " + BUNDLE_SYMBOLIC_NAME,
        "Bundle-Version: " + BUNDLE_VERSION,
        "Bundle-Vendor: iDempiere Community",
        "Automatic-Module-Name: " + BUNDLE_SYMBOLIC_NAME,
        "Bundle-RequiredExecutionEnvironment: JavaSE-17",
        'Require-Capability: osgi.ee;filter:="(&(osgi.ee=JavaSE)(version>=17))"',
        wrap("Bundle-ClassPath", ["."] + ["lib/" + j for j in jars]),
        wrap("Export-Package", ['%s;version="%s"' % (p, v) for p, v in sorted(exports.items())]),
        wrap("Import-Package", imports),
        "",
    ]
    with open(MANIFEST, "w", newline="\n") as fh:
        fh.write("\n".join(lines))

    print("%d jars, %d exported packages, %d imported packages, %d dropped"
          % (len(jars), len(exports), len(imports), len(dropped)))
    if args.print_dropped:
        for package in dropped:
            print("  dropped:", package)


if __name__ == "__main__":
    sys.exit(main())
