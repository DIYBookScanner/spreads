WEBPACK_BIN=./node_modules/.bin/webpack

all: development production

node_modules:
	npm install

production: node_modules
	$(WEBPACK_BIN) -p --progress

development: node_modules
	$(WEBPACK_BIN) -d --config webpack.config.dev.js --progress

watch: node_modules
	$(WEBPACK_BIN) -d --config webpack.config.dev.js --watch

.PHONY: production development watch
