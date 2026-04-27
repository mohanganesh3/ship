const fs = require('fs');
const app = JSON.parse(fs.readFileSync('app.json', 'utf8'));
if (!app.expo.plugins) app.expo.plugins = [];
app.expo.plugins.push([
  "expo-notifications",
  {
    "icon": "./assets/images/icon.png",
    "color": "#D4943A"
  }
]);
app.expo.android.permissions = [
  "android.permission.POST_NOTIFICATIONS",
  "android.permission.WAKE_LOCK",
  "android.permission.FOREGROUND_SERVICE",
  "android.permission.FOREGROUND_SERVICE_DATA_SYNC"
];
fs.writeFileSync('app.json', JSON.stringify(app, null, 2));
