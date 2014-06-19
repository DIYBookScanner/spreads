var path = require('path'),
    webpack = require('webpack');

module.exports = {
  cache: true,
  entry: './src/main.js',
  output: {
    path: path.join(__dirname, "build"),
    filename: "bundle.js"
  },
  module: {
    loaders: [
      {test: /\.js$/, loader: 'jsx-loader?harmony'},
      {test: /\.css$/, loader: 'style!css'},
      {test: /\.scss$/, loader: "style!css!sass"},
      {test: /\.ttf$/, loader: "file-loader"},
      {test: /\.svg$/, loader: "file-loader"},
      {test: /\.eot$/, loader: "file-loader"},
      {test: /\.woff$/, loader: "file-loader"}
    ]
  },
  plugins: [
    new webpack.optimize.DedupePlugin(),
    new webpack.optimize.UglifyJsPlugin()
  ]
}
