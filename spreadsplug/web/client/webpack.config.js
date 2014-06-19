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
      {test: /\.js$/, loader: 'jsx-loader?harmony'},
      {test: /\.css$/, loader: 'style!css'},
      {test: /\.scss$/, loader: "style!css!sass"},
      {test: /\.ttf$/, loader: "file-loader?prefix=static/"},
      {test: /\.svg$/, loader: "file-loader?prefix=static/"},
      {test: /\.eot$/, loader: "file-loader?prefix=static/"},
      {test: /\.woff$/, loader: "file-loader?prefix=static/"}
    ]
  },
  plugins: [
    new webpack.optimize.DedupePlugin(),
    new webpack.optimize.UglifyJsPlugin()
  ]
}
