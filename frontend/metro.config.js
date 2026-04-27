if (!Array.prototype.toReversed) {
  Array.prototype.toReversed = function() {
    return [...this].reverse();
  };
}
const { getDefaultConfig } = require('expo/metro-config');
const { FileStore } = require('metro-cache');
const path = require('path');

const config = getDefaultConfig(__dirname);

// Use project-local cache dir to avoid /tmp permission issues
config.cacheStores = [
  new FileStore({
    root: path.join(__dirname, 'metro-cache'),
  }),
];

config.resolver.assetExts.push('bin', 'wav', 'gguf');

module.exports = config;
