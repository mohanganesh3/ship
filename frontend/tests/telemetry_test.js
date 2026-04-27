
// Simulated Speed Logic Test
function testSpeedCalc() {
  let lastBytes = 0;
  let lastTime = Date.now();
  
  // Simulated res.bytesWritten
  const simBytes = [1000000, 5000000, 15000000, 30000000];
  const simTimes = [500, 1000, 1500, 2000]; // ms delays
  
  console.log("--- Starting Speed Calculation Test ---");
  
  simBytes.forEach((bytesWritten, index) => {
    const now = lastTime + simTimes[index];
    const timeGap = (now - lastTime) / 1000;
    
    let speedStr = "-- MB/s";
    if (timeGap > 0.0) {
      const bytesGap = bytesWritten - lastBytes;
      const speedKB = (bytesGap / 1024) / timeGap;
      speedStr = speedKB > 1024 
        ? `${(speedKB / 1024).toFixed(1)} MB/s` 
        : `${speedKB.toFixed(0)} KB/s`;
        
      console.log(`Step ${index + 1}: ${bytesWritten} bytes, Speed: ${speedStr} (${timeGap}s gap)`);
      
      lastBytes = bytesWritten;
      lastTime = now;
    }
  });
}

testSpeedCalc();
