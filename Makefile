PLUGIN_VERSION=0.0.2
PLUGIN_ID=meteonomiqs-api

plugin:
	cat plugin.json|json_pp > /dev/null
	rm -rf dist
	mkdir dist
	zip -r dist/dss-plugin-${PLUGIN_ID}-${PLUGIN_VERSION}.zip parameter-sets python-connectors python-lib plugin.json

include ../Makefile.inc