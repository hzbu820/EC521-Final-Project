const path = require('path');
const CopyWebpackPlugin = require('copy-webpack-plugin');

/** @type {import('webpack').Configuration} */
module.exports = {
  entry: {
    background: path.resolve(__dirname, 'src/background/index.js'),
    contentScript: path.resolve(__dirname, 'src/content/contentScript.js'),
    popup: path.resolve(__dirname, 'src/popup/popup.js')
  },
  output: {
    path: path.resolve(__dirname, 'dist'),
    filename: '[name].js',
    clean: true
  },
  devtool: 'source-map',
  resolve: {
    extensions: ['.js'],
    alias: {
      '@utils': path.resolve(__dirname, 'src/utils')
    }
  },
  plugins: [
    new CopyWebpackPlugin({
      patterns: [
        { from: 'manifest.json', to: '.' },
        { from: 'icons', to: 'icons' },
        { from: 'src/popup/popup.html', to: 'popup.html' },
        { from: 'src/popup/popup.css', to: 'popup.css' }
      ]
    })
  ]
};
