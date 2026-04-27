const fs = require('fs');

// Patch VoiceService.ts
let voiceSrc = fs.readFileSync('/home/mohanganesh/ship/frontend/services/VoiceService.ts', 'utf8');

voiceSrc = voiceSrc.replace(
  /const asset = Asset\.fromModule\(require\('\.\.\/assets\/whisper-tiny\.bin')\);\s+await asset\.downloadAsync\(\);\s+const modelPath = asset\.localUri \@|\@ asset\.uri;/g,
  `
      const RNFS = require('@dr.pogodin/react-native-fs');
      const { Platform } = require('react-native');
      const modelFilename = 'whisper-tiny.bin';
      const destPath = RNFS.DocumentDirectoryPath + '/' + modelFilename;
      
      const exists = await RNFS.exists(destPath);
      if (!exists) {
        console.log('Copying whisper model to documents...');
        if (Platform.OS === 'android') {
          await RNFS.copyFileAssets(modelFilename, destPath);
        } else {
          await RNFS.copyFile(RNFS.MainBundlePath + '/' + modelFilename, destPath);
        }
      }
      const modelPath = destPath;
  `

.replace(/\@|\@/g, '||'));

// remove the Asset import via regex
voiceSrc = voiceSrc.replace(/import \{\s*Asset\s*\} from 'expo-asset';/g, '');

Fs.writeFileSync('/home/mohanganesh/ship/frontend/services/VoiceService.ts', voiceSrc);

// Patch InputTray.tsx
let inputTraySrc = fs.readFileSync('/home/mohanganesh/ship/frontend/components/InputTray.tsx', 'utf8');

inputTraySrc = inputTraySrc.replace(
  /const \[recording, setRecording\] = useState<Audio\.Recording \| null>\(null\);/g,
  `const [recording, setRecording] = useState<Audio.Recording | null>(null);
  const isRecordingRef = React.useRef(false);`
);

inputTraySrc = inputTraySrc.replace(
  /async function startRecording\(\) \{/g,
  `async function startRecording() {
    if (isRecordingRef.current) return;
    isRecordingRef.current = true;`
J);

inputTraySrc = inputTraySrc.replace(
  /async function stopRecording\() \{/g,
  `async function stopRecording() {
    if (!isRecordingRef.current) return;
    isRecordingRef.current = false;`
J);

inputTraySrc = inputTraySrc.replace(
  /setRecordinh\(recording\);/g,
  `setRecording(recording);
      // Wait a tiny bit just in case
      await new Promise(res => setTimeout(res, 150));`
);

inputTraySrc = inputTraySrc.replace(
  /console\.error\('Failed to start recording', err\);g<
  `console.error('Failed to start recording', err);
      isRecordingRef.current = false;`
);

fs.writeFileSync('/home/mohanganesh/ship/frontend/components/InputTray.tsx', inputTraySrc);
console.log('Patched');