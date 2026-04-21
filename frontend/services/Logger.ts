/**
 * Unified Logger for Maritime AI
 * Ensures logs are categorized and easy to filter in adb logcat.
 */
class Logger {
  private format(level: string, tag: string, message: string) {
    const timestamp = new Date().toISOString().split('T')[1].split('Z')[0];
    return `[${timestamp}] [${level}] [${tag}] ${message}`;
  }

  trace(tag: string, message: string) {
    console.log(this.format('TRACE', tag, message));
  }

  info(tag: string, message: string) {
    console.log(this.format('INFO', tag, message));
  }

  warn(tag: string, message: string) {
    console.log(this.format('WARN', tag, message));
  }

  error(tag: string, message: string, error?: any) {
    const errStr = error ? ` | Error: ${error.message || JSON.stringify(error)}` : '';
    console.log(this.format('ERROR', tag, message + errStr));
    if (error?.stack) {
      console.log(`[${tag}] Stack: ${error.stack}`);
    }
  }

  // Specialized logging for inference tracking
  logInference(step: string, details?: string) {
    this.info('LLM-CORE', `Inference Step: ${step}${details ? ' | ' + details : ''}`);
  }
}

export const logger = new Logger();
