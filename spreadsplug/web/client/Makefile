WEBPACK_BIN=./node_modules/.bin/webpack
KARMA_BIN=./node_modules/.bin/karma

ifndef $(BROWSERS)
BROWSERS=PhantomJS
endif

all: development production

node_modules:
	npm install

production: node_modules
	$(WEBPACK_BIN) -p --progress

development: node_modules
	$(WEBPACK_BIN) -d --config webpack.config.dev.js --progress

watch: node_modules
	$(WEBPACK_BIN) -d --config webpack.config.dev.js --watch

test-ci: node_modules
	$(KARMA_BIN) --browsers PhantomJS,Chrome,Firefox start

test-debug: node_modules
	$(KARMA_BIN) --browsers Chrome --no-single-run start

test: node_modules
	$(KARMA_BIN) --browsers $(BROWSERS) start

.PHONY: production development watch start-karma test test-debug test-ci
