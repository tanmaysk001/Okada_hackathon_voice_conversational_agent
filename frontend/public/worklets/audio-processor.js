// /public/worklets/audio-processor.js

class AudioProcessor extends AudioWorkletProcessor {
  constructor(options) {
    super(options);
    this.bufferSize = options.processorOptions.bufferSize || 4096;
    this.buffer = new Int16Array(this.bufferSize);
    this.bufferIndex = 0;
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0];
    if (input.length > 0) {
      const inputChannel = input[0]; // Assuming mono input
      
      // Convert Float32Array [-1, 1] to Int16Array [-32768, 32767]
      for (let i = 0; i < inputChannel.length; i++) {
        const s = Math.max(-1, Math.min(1, inputChannel[i]));
        this.buffer[this.bufferIndex++] = s < 0 ? s * 0x8000 : s * 0x7FFF;

        if (this.bufferIndex >= this.bufferSize) {
          // Send the filled buffer back to the main thread
          this.port.postMessage({ pcmData: this.buffer.buffer.slice(0) });
          this.bufferIndex = 0;
        }
      }
    }
    return true; // Keep the processor alive
  }
}

registerProcessor('audio-processor', AudioProcessor);