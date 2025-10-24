/**
 * Sparkline data type: [timestamp, value] pairs
 * timestamp can be number (unix timestamp), string (ISO), or Date object
 */
export type SparklineData = Array<[number | string | Date, number]>;

export type MultiLineChartData = Array<Array<string | number>>;
