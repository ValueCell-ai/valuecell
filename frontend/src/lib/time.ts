import dayjs, { type Dayjs } from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import timezone from "dayjs/plugin/timezone";
import utc from "dayjs/plugin/utc";

// Extend dayjs with plugins
dayjs.extend(utc);
dayjs.extend(timezone);
dayjs.extend(relativeTime);

/**
 * Common time format constants
 */
export const TIME_FORMATS = {
  DATE: "YYYY-MM-DD",
  TIME: "HH:mm:ss",
  DATETIME: "YYYY-MM-DD HH:mm:ss",
  DATETIME_SHORT: "YYYY-MM-DD HH:mm",
  MARKET: "MM/DD HH:mm",
} as const;

/**
 * Time input types
 */
export type TimeInput = string | number | Date | Dayjs;

/**
 * Time format type
 */
export type TimeFormat = (typeof TIME_FORMATS)[keyof typeof TIME_FORMATS];

/**
 * Timezone string type
 */
export type TimezoneString = string;

/**
 * Time unit type
 */
export type TimeUnit =
  | "year"
  | "month"
  | "day"
  | "hour"
  | "minute"
  | "second"
  | "millisecond";

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
   * Get current local time
   * @returns Current local time as Dayjs instance
   */
  static now(): Dayjs {
    return dayjs();
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
   * Convert time to UTC
   * @param time - Time input to convert
   * @returns UTC time as Dayjs instance
   */
  static toUTC(time: TimeInput): Dayjs {
    return dayjs(time).utc();
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
   * Convert time to specific timezone
   * @param time - Time input to convert
   * @param timezone - Target timezone string
   * @returns Time in specified timezone as Dayjs instance
   */
  static toTimezone(time: TimeInput, timezone: TimezoneString): Dayjs {
    return dayjs(time).tz(timezone);
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

  /**
   * Get relative time from now (e.g., "2 hours ago")
   * @param time - Time input to get relative time for
   * @returns Relative time string
   */
  static fromNow(time: TimeInput): string {
    return dayjs(time).fromNow();
  }

  /**
   * Get time difference in milliseconds
   * @param time1 - End time
   * @param time2 - Start time
   * @returns Time difference in milliseconds
   */
  static diff(time1: TimeInput, time2: TimeInput): number {
    return dayjs(time1).diff(dayjs(time2));
  }

  /**
   * Get time difference in specified unit
   * @param time1 - End time
   * @param time2 - Start time
   * @param unit - Time unit for difference calculation
   * @returns Time difference in specified unit
   */
  static diffIn(time1: TimeInput, time2: TimeInput, unit: TimeUnit): number {
    return dayjs(time1).diff(dayjs(time2), unit);
  }

  /**
   * Check if time is valid
   * @param time - Time input to validate
   * @returns True if time is valid, false otherwise
   */
  static isValid(time: TimeInput): boolean {
    return dayjs(time).isValid();
  }

  /**
   * Check if two times are the same day
   * @param time1 - First time
   * @param time2 - Second time
   * @param useUTC - Whether to compare in UTC (defaults to false)
   * @returns True if same day, false otherwise
   */
  static isSameDay(
    time1: TimeInput,
    time2: TimeInput,
    useUTC: boolean = false,
  ): boolean {
    if (useUTC) {
      return dayjs.utc(time1).isSame(dayjs.utc(time2), "day");
    }
    return dayjs(time1).isSame(dayjs(time2), "day");
  }

  /**
   * Add time to a given time
   * @param time - Base time
   * @param amount - Amount to add
   * @param unit - Time unit
   * @returns New time with added amount
   */
  static add(time: TimeInput, amount: number, unit: TimeUnit): Dayjs {
    return dayjs(time).add(amount, unit);
  }

  /**
   * Subtract time from a given time
   * @param time - Base time
   * @param amount - Amount to subtract
   * @param unit - Time unit
   * @returns New time with subtracted amount
   */
  static subtract(time: TimeInput, amount: number, unit: TimeUnit): Dayjs {
    return dayjs(time).subtract(amount, unit);
  }

  /**
   * Get start of day
   * @param time - Time input
   * @param useUTC - Whether to use UTC (defaults to false)
   * @returns Start of day as Dayjs instance
   */
  static startOfDay(time: TimeInput, useUTC: boolean = false): Dayjs {
    return useUTC ? dayjs.utc(time).startOf("day") : dayjs(time).startOf("day");
  }

  /**
   * Get end of day
   * @param time - Time input
   * @param useUTC - Whether to use UTC (defaults to false)
   * @returns End of day as Dayjs instance
   */
  static endOfDay(time: TimeInput, useUTC: boolean = false): Dayjs {
    return useUTC ? dayjs.utc(time).endOf("day") : dayjs(time).endOf("day");
  }
}
