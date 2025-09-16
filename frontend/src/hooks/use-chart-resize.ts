import type { ECharts } from "echarts/core";
import { useEffect } from "react";

/**
 * deal with ECharts window resize event
 * @param chartInstance ECharts instance ref
 * @param dependencies additional dependencies array, when these dependencies change, the resize listener will be re-set
 */
export function useChartResize(
  chartInstance: React.RefObject<ECharts | null>,
  dependencies: React.DependencyList = [],
) {
  useEffect(() => {
    const handleResize = () => {
      chartInstance.current?.resize();
    };

    // add resize event listener
    window.addEventListener("resize", handleResize);

    // cleanup function: remove event listener
    return () => {
      window.removeEventListener("resize", handleResize);
    };
  }, [chartInstance, ...dependencies]);
}
