// Karma configuration

module.exports = function(config) {
  config.set({
  basePath: '',
  frameworks: ['jasmine'],
  files: [
    './test/phantomjs-shims.js',
    './test/common.js',
    './node_modules/jasmine-ajax/lib/mock-ajax.js',
    './test/src/**/*.js'
  ],
  preprocessors: {
    './test/src/**/*.js': ['webpack'],
    './test/common.js': ['webpack']
  },
  webpack: {
    cache: true,
    module: {
      loaders: [
        {test: /sinon.js/, loader: "imports?define=>false"},
        {test: /\.js$/, loader: 'jsx-loader'},
        {test: /\.css$/, loader: 'style!css'},
        {test: /\.scss$/, loader: "style!css!sass"},
        {test: /\.ttf$/, loader: "url-loader"},
        {test: /\.svg$/, loader: "url-loader"}
      ]
    }
  },
  webpackServer: {
    quiet: true,
    stats: {
      colors: true,
    },
  },
  reporters: ['progress'],
  port: 9876,
  colors: true,
  logLevel: config.LOG_INFO,
  autoWatch: true,
  captureTimeout: 60000,
  singleRun: true,
  plugins: [
    require("karma-jasmine"),
    require("karma-chrome-launcher"),
    require("karma-phantomjs-launcher"),
    require("karma-firefox-launcher"),
    require("karma-webpack")
  ]
  });
};
