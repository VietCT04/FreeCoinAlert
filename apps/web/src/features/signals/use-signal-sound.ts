"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import type { AuthStatus } from "../auth/types";
import { createSignalAudioContext, playSignalPip } from "./signal-sound";

const SOUND_PREFERENCE_KEY = "freecoinalert.signalSound.enabled.v1";
const SOUND_COALESCE_MS = 500;

export type SignalSoundState = {
  preferenceEnabled: boolean;
  sessionActive: boolean;
  error: string | null;
  announcement: string | null;
  activate: () => Promise<boolean>;
  mute: () => void;
  playLivePip: () => Promise<void>;
};

function readSoundPreference(): boolean {
  try {
    return window.localStorage.getItem(SOUND_PREFERENCE_KEY) === "true";
  } catch {
    return false;
  }
}

function writeSoundPreference(enabled: boolean): void {
  try {
    window.localStorage.setItem(SOUND_PREFERENCE_KEY, String(enabled));
  } catch {
    // A storage failure must not affect live visual updates or sound controls.
  }
}

function suspendAudioContext(audioContext: AudioContext | null): void {
  if (audioContext?.state === "running") {
    void audioContext.suspend().catch(() => undefined);
  }
}

export function useSignalSound(authStatus: AuthStatus): SignalSoundState {
  const [preferenceEnabled, setPreferenceEnabled] = useState(false);
  const [sessionActive, setSessionActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [announcement, setAnnouncement] = useState<string | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const lastPipAtRef = useRef(0);

  useEffect(() => {
    setPreferenceEnabled(readSoundPreference());
  }, []);

  const activate = useCallback(async (): Promise<boolean> => {
    if (document.visibilityState !== "visible") {
      setError("Sound can be activated only while this page is visible.");
      return false;
    }

    try {
      const audioContext =
        !audioContextRef.current || audioContextRef.current.state === "closed"
          ? createSignalAudioContext()
          : audioContextRef.current;
      audioContextRef.current = audioContext;

      if (audioContext.state === "suspended") {
        await audioContext.resume();
      }
      await playSignalPip(audioContext);

      writeSoundPreference(true);
      setPreferenceEnabled(true);
      setSessionActive(true);
      setError(null);
      setAnnouncement("Sound enabled for new live signals.");
      return true;
    } catch {
      writeSoundPreference(false);
      setPreferenceEnabled(false);
      setSessionActive(false);
      setError("Sound could not be activated in this browser session.");
      return false;
    }
  }, []);

  const mute = useCallback(() => {
    writeSoundPreference(false);
    setPreferenceEnabled(false);
    setSessionActive(false);
    setError(null);
    setAnnouncement("Sound muted.");
    suspendAudioContext(audioContextRef.current);
  }, []);

  const playLivePip = useCallback(async () => {
    if (
      !preferenceEnabled ||
      !sessionActive ||
      document.visibilityState !== "visible"
    ) {
      return;
    }

    const now = Date.now();
    if (now - lastPipAtRef.current < SOUND_COALESCE_MS) {
      return;
    }

    const audioContext = audioContextRef.current;
    if (!audioContext || audioContext.state !== "running") {
      return;
    }

    lastPipAtRef.current = now;
    try {
      await playSignalPip(audioContext);
    } catch {
      writeSoundPreference(false);
      setPreferenceEnabled(false);
      setSessionActive(false);
      setError("Sound is no longer active for this browser session.");
    }
  }, [preferenceEnabled, sessionActive]);

  useEffect(() => {
    if (authStatus !== "authenticated") {
      setSessionActive(false);
      setError(null);
      setAnnouncement(null);
      suspendAudioContext(audioContextRef.current);
    }
  }, [authStatus]);

  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === "hidden") {
        setSessionActive(false);
        suspendAudioContext(audioContextRef.current);
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, []);

  useEffect(() => {
    return () => suspendAudioContext(audioContextRef.current);
  }, []);

  return {
    preferenceEnabled,
    sessionActive,
    error,
    announcement,
    activate,
    mute,
    playLivePip,
  };
}
