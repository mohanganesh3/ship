with open("app/_layout.tsx", "r") as f:
    content = f.read()

content = content.replace("SplashScreen.preventAutoHideAsync();", "SplashScreen.preventAutoHideAsync().catch(() => {});")

old_useEffect = """  useEffect(() => {
    async function checkProvisioning() {
      const isProvisioned = await ModelProvisioner.isModelProvisioned();
      setNeedsProvisioning(!isProvisioned);
      
      if (isProvisioned) {
        initApp();
      }
    }

    async function initApp() {
      await seedDemoData();
      try {
        await loadModel();
      } catch (e) {
        console.warn("Soft-failing model load during init:", e);
      }
      setAppReady(true);
    }

    if (fontsLoaded) {
      SplashScreen.hideAsync();
      checkProvisioning();
    }
  }, [fontsLoaded]);"""

new_useEffect = """  useEffect(() => {
    async function checkProvisioning() {
      const isProvisioned = await ModelProvisioner.isModelProvisioned();
      setNeedsProvisioning(!isProvisioned);
      
      if (isProvisioned) {
        await initApp();
      }
    }

    async function initApp() {
      await seedDemoData();
      try {
        await loadModel();
      } catch (e) {
        console.warn("Soft-failing model load during init:", e);
      }
      setAppReady(true);
    }

    if (fontsLoaded) {
      checkProvisioning();
    }
  }, [fontsLoaded]);

  useEffect(() => {
    if (fontsLoaded && needsProvisioning !== null) {
      SplashScreen.hideAsync().catch(() => {});
    }
  }, [fontsLoaded, needsProvisioning]);"""

content = content.replace(old_useEffect, new_useEffect)

if old_useEffect not in content:
    print("WARNING: old_useEffect not found\n")

with open("app/_layout.tsx", "w") as f:
    f.write(content)
print("Successfully patched app/_layout.tsx")
