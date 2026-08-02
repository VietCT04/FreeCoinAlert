const SIGNAL_SOUND_FREQUENCY_HZ = 880;
const SIGNAL_SOUND_DURATION_SECONDS = 0.12;
const SIGNAL_SOUND_MAX_GAIN = 0.08;

export function createSignalAudioContext(): AudioContext {
  const AudioContextConstructor =
    window.AudioContext ??
    (
      window as typeof window & {
        webkitAudioContext?: typeof AudioContext;
      }
    ).webkitAudioContext;

  if (!AudioContextConstructor) {
    throw new Error("Audio is not supported by this browser.");
  }

  return new AudioContextConstructor();
}

export async function playSignalPip(audioContext: AudioContext): Promise<void> {
  if (audioContext.state !== "running") {
    throw new Error("Audio is not active for this browser session.");
  }

  const oscillator = audioContext.createOscillator();
  const gain = audioContext.createGain();
  const startAt = audioContext.currentTime;
  const peakAt = startAt + 0.01;
  const stopAt = startAt + SIGNAL_SOUND_DURATION_SECONDS;

  oscillator.type = "sine";
  oscillator.frequency.setValueAtTime(SIGNAL_SOUND_FREQUENCY_HZ, startAt);
  gain.gain.setValueAtTime(0.0001, startAt);
  gain.gain.linearRampToValueAtTime(SIGNAL_SOUND_MAX_GAIN, peakAt);
  gain.gain.exponentialRampToValueAtTime(0.0001, stopAt);
  oscillator.connect(gain);
  gain.connect(audioContext.destination);

  await new Promise<void>((resolve) => {
    oscillator.addEventListener(
      "ended",
      () => {
        oscillator.disconnect();
        gain.disconnect();
        resolve();
      },
      { once: true },
    );
    oscillator.start(startAt);
    oscillator.stop(stopAt);
  });
}
