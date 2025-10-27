import dayjs, { type Dayjs } from "dayjs";
import utc from "dayjs/plugin/utc";

// Extend dayjs with plugins
dayjs.extend(utc);

/**
 * Common time format constants
 */
export const TIME_FORMATS = {
  DATE: "YYYY/MM/DD",
  TIME: "HH:mm:ss",
  DATETIME: "YYYY-MM-DD HH:mm:ss",
  DATETIME_SHORT: "YYYY-MM-DD HH:mm",
  MARKET: "MM/DD HH:mm",
  MODAL_TRADE_TIME: "MMM DD HH:mm",
} as const;

/**
 * Time input types
 */
export type TimeInput = string | number | Date | Dayjs;

// biome-ignore lint/complexity/noStaticOnlyClass: need to be static
export class TimeUtils {
  /**
   * Get current UTC time
   * @returns Current UTC time as Dayjs instance
   */
  static nowUTC(): Dayjs {
    return dayjs.utc();
  }

  /**
   * Create UTC time from input
   * @param input - Time input (optional, defaults to current time)
   * @returns UTC time as Dayjs instance
   */
  static createUTC(input?: TimeInput): Dayjs {
    return input ? dayjs.utc(input) : dayjs.utc();
  }

  /**
   * Convert UTC time to local time
   * @param time - UTC time input
   * @returns Local time as Dayjs instance
   */
  static fromUTC(time: TimeInput): Dayjs {
    return dayjs.utc(time).local();
  }

  /**
   * Format time with specified format
   * @param time - Time input to format
   * @param fmt - Format string (defaults to DATETIME)
   * @returns Formatted time string
   */
  static format(time: TimeInput, fmt: string = TIME_FORMATS.DATETIME): string {
    return dayjs(time).format(fmt);
  }

  /**
   * Format UTC time with specified format
   * @param time - Time input to format as UTC
   * @param fmt - Format string (defaults to DATETIME)
   * @returns Formatted UTC time string
   */
  static formatUTC(
    time: TimeInput,
    fmt: string = TIME_FORMATS.DATETIME,
  ): string {
    return dayjs.utc(time).format(fmt);
  }
}
