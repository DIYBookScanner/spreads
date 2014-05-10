var path = require('path'),
    webpack = require('webpack');

module.exports = {
  cache: true,
  entry: './src/main.js',
  output: {
    path: path.join(__dirname, "packages"),
    filename: "bundle.js"
  },
  module: {
    loaders: [
      {test: /\.js$/, loader: 'jsx-loader'},
      {test: /\.css$/, loader: 'style!css'},
      {test: /\.scss$/, loader: "style!css!sass"},
      {test: /\.ttf$/, loader: "url-loader"}
      {test: /\.svg$/, loader: "url-loader"},
    ]
  },
  plugins: [
    new webpack.optimize.DedupePlugin(),
    new webpack.optimize.UglifyJsPlugin()
  ]
}
