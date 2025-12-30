import { useRef, useCallback } from 'react';

export const useCardFlipSound = () => {
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const playFlipSound = useCallback(() => {
    try {
      if (!audioRef.current) {
        audioRef.current = new Audio('/assets/sounds/card-flip.mp3');
        audioRef.current.volume = 0.3;
      }
      audioRef.current.currentTime = 0;
      audioRef.current.play().catch(() => {
        // Ignore autoplay restrictions
      });
    } catch (e) {
      // Ignore audio errors
    }
  }, []);

  return { playFlipSound };
};
