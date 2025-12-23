import { Check } from "lucide-react";
import type { FC } from "react";

interface StepIndicatorProps {
  steps: { step: number; title: string }[];
  currentStep: number;
}

export const StepIndicator: FC<StepIndicatorProps> = ({
  steps,
  currentStep,
}) => {
  const getStepState = (stepNumber: number) => ({
    isCompleted: stepNumber < currentStep,
    isCurrent: stepNumber === currentStep,
    isActive: stepNumber <= currentStep,
    isLast: stepNumber === steps.length,
  });

  const renderStepNumber = (
    step: number,
    isCurrent: boolean,
    isCompleted: boolean,
  ) => {
    if (isCompleted) {
      return (
        <div className="flex size-6 items-center justify-center rounded-full bg-primary">
          <Check className="size-3 text-primary-foreground" />
        </div>
      );
    }

    return (
      <div className="relative flex size-6 items-center justify-center">
        <div
          className={`absolute inset-0 rounded-full border-2 ${
            isCurrent ? "border-primary bg-primary" : "border-border"
          }`}
        />
        <span
          className={`relative font-semibold text-base ${
            isCurrent ? "text-primary-foreground" : "text-muted-foreground"
          }`}
        >
          {step}
        </span>
      </div>
    );
  };

  return (
    <div className="flex items-start">
      {steps.map((step) => {
        const { isCompleted, isCurrent, isActive, isLast } = getStepState(
          step.step,
        );

        return (
          <div key={step.step} className="flex min-w-0 flex-1 items-start">
            <div className="flex w-full items-start gap-2">
              {/* Step number/icon */}
              <div className="shrink-0">
                {renderStepNumber(step.step, isCurrent, isCompleted)}
              </div>

              {/* Step title and connector line */}
              <div className="flex min-w-0 flex-1 items-center gap-3 pr-3">
                <span
                  className={`shrink-0 whitespace-nowrap text-base ${
                    isActive ? "text-foreground" : "text-muted-foreground"
                  }`}
                >
                  {step.title}
                </span>

                {!isLast && (
                  <div
                    className={`h-0.5 min-w-0 flex-1 ${
                      isCompleted ? "bg-primary" : "bg-border"
                    }`}
                  />
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};
