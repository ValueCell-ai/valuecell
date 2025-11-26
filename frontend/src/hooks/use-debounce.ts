import { useEffect, useState } from "react";

/**
 * Debounce value hook
 * @param value The value to debounce
 * @param delay The delay time (milliseconds)
 * @returns The debounced value
 */
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(timer);
    };
  }, [value, delay]);

  return debouncedValue;
}

export function debounce(fn: () => void, delay: number) {
  let timeout: ReturnType<typeof setTimeout> | null = null;

  return (...args: Parameters<typeof fn>) => {
    if (timeout) {
      clearTimeout(timeout);
    }
    timeout = setTimeout(() => fn(...args), delay);
  };
}
